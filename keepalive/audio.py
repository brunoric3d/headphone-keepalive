"""Motor de audio: mantem um stream de saida rodando com o sinal escolhido.

Sem numpy. O sinal fica pronto em memoria como PCM de 16 bits ja com o volume
aplicado e os canais montados, e o callback so copia bytes. Isso mantem o custo
de CPU perto de zero e, mais importante, deixa reabrir o stream sem recalcular
nada, que era a causa do silencio de alguns centesimos a cada reconexao.
"""

from __future__ import annotations

import sys
import threading
import time
from array import array
from typing import Callable, Dict, List, Optional

import sounddevice as sd

from . import signals, syslevel

BLOCKSIZE = 2048
WATCHDOG_SECONDS = 2.0
# teto absoluto da compensacao: e o mesmo nivel do preset mais alto do app,
# entao compensar nunca deixa o som mais forte do que o usuario ja podia
# escolher na mao. isso limita o susto se a leitura do volume vier errada
MAX_LEVEL_DB = -30.0
# so re-renderiza quando o volume do sistema mexeu mais que isso
LEVEL_EPSILON_DB = 1.0
# so usado onde nao da para perguntar ao sistema se a lista de saidas mudou
FALLBACK_POLL_SECONDS = 60.0
FALLBACK_RATES = (48000, 44100, 32000, 22050)


def db_to_amp(db: float) -> float:
    return float(10.0 ** (float(db) / 20.0))


def refresh_devices() -> None:
    """Recarrega a lista de dispositivos do PortAudio.

    Sem isso o app nao enxerga um fone que acabou de conectar.
    """
    try:
        sd._terminate()
    except Exception:
        pass
    try:
        sd._initialize()
    except Exception:
        pass


def device_fingerprint() -> Optional[int]:
    """Numero que muda quando o conjunto de saidas do sistema muda.

    No Windows da para perguntar isso ao sistema sem tocar no PortAudio, o que
    permite detectar um fone novo sem interromper o som. Nos outros sistemas
    ainda nao temos um jeito barato, entao devolve None e o watchdog cai para
    a sondagem por tempo.
    """
    if sys.platform == "win32":
        try:
            import ctypes

            return int(ctypes.windll.winmm.waveOutGetNumDevs())
        except Exception:
            return None
    return None


# o mesmo fone aparece uma vez por API de audio do sistema. essa e a ordem de
# preferencia de qual API mostrar para nao encher a lista de repetidos
PREFERRED_HOSTAPIS = {
    "win32": ("wasapi", "directsound", "wdm-ks", "mme"),
    "darwin": ("core audio",),
    "linux": ("pulseaudio", "pipewire", "alsa"),
}


def _hostapi_list() -> List[str]:
    try:
        return [str(h.get("name", "?")) for h in sd.query_hostapis()]
    except Exception:
        return []


def preferred_hostapi() -> Optional[int]:
    """Indice da API de audio que vale a pena mostrar na lista."""
    names = _hostapi_list()
    if not names:
        return None
    key = "win32" if sys.platform == "win32" else ("darwin" if sys.platform == "darwin" else "linux")
    for wanted in PREFERRED_HOSTAPIS.get(key, ()):  # ordem de preferencia
        for index, name in enumerate(names):
            if wanted in name.lower():
                return index
    try:
        return int(sd.default.hostapi)
    except Exception:
        return 0


def list_output_devices(all_apis: bool = False) -> List[Dict]:
    """Saidas de audio, sem os duplicados que vem de cada API do sistema.

    Cada item tem index, name e hostapi. Com all_apis=True vem tudo.
    """
    everything: List[Dict] = []
    try:
        hostapis = _hostapi_list()
        for index, info in enumerate(sd.query_devices()):
            if int(info.get("max_output_channels", 0)) <= 0:
                continue
            api_index = int(info.get("hostapi", -1))
            everything.append(
                {
                    "index": index,
                    "name": str(info.get("name", f"dispositivo {index}")).strip(),
                    "hostapi": hostapis[api_index] if 0 <= api_index < len(hostapis) else "?",
                    "hostapi_index": api_index,
                }
            )
    except Exception:
        return []

    if all_apis:
        chosen = everything
    else:
        pref = preferred_hostapi()
        chosen = [d for d in everything if d["hostapi_index"] == pref] or everything

    seen = set()
    result = []
    for dev in chosen:
        key = (dev["name"].lower(), dev["hostapi_index"])
        if key in seen:
            continue
        seen.add(key)
        result.append(dev)
    return result


def default_output_name() -> Optional[str]:
    try:
        info = sd.query_devices(kind="output")
        return str(info.get("name")).strip() if info else None
    except Exception:
        return None


def _resolve_device(name: Optional[str], hostapi: Optional[str] = None) -> Optional[int]:
    """Acha o indice do dispositivo pelo nome salvo. None usa o padrao."""
    if not name:
        return None
    devices = list_output_devices(all_apis=True)
    wanted = name.strip().lower()
    if hostapi:
        for dev in devices:
            if dev["name"].lower() == wanted and dev["hostapi"] == hostapi:
                return dev["index"]
    for dev in devices:
        if dev["name"].lower() == wanted:
            return dev["index"]
    for dev in devices:
        if wanted in dev["name"].lower():
            return dev["index"]
    return None


def render_pcm(kind: str, samplerate: int, pulse_interval: float, level_db: float, channels: int) -> bytes:
    """Monta o buffer final: volume aplicado, canais montados, pronto para tocar."""
    mono = signals.build_int16(kind, samplerate, pulse_interval)
    gain = db_to_amp(level_db)

    scaled = array("h", (int(sample * gain) for sample in mono))
    if channels <= 1:
        return scaled.tobytes()

    out = array("h", bytes(2 * len(scaled) * channels))
    for channel in range(channels):
        out[channel::channels] = scaled
    return out.tobytes()


class AudioEngine:
    def __init__(self, config, on_state_change: Optional[Callable[[], None]] = None) -> None:
        self.config = config
        self.on_state_change = on_state_change

        self._lock = threading.RLock()
        self._stream: Optional[sd.RawOutputStream] = None

        self._pcm = b""
        self._pos = 0
        self._frame_bytes = 2
        self._render_key: Optional[tuple] = None

        self._channels = 1
        self._samplerate = int(config.get("samplerate") or 48000)

        self._running = False
        self._status = ("stopped", "")
        self._active_device = None

        self._attenuation = 0.0
        self._clamped = False
        self._tick = 0

        self._fingerprint = device_fingerprint()
        self._last_poll = time.monotonic()

        self._stop_event = threading.Event()
        self._watchdog = threading.Thread(target=self._watch, name="keepalive-watchdog", daemon=True)
        self._watchdog.start()

    # ------------------------------------------------------------------ estado

    @property
    def running(self) -> bool:
        with self._lock:
            return self._running and self._stream is not None and self._stream.active

    @property
    def status(self) -> tuple:
        """(estado, detalhe), com estado em stopped, playing ou error."""
        with self._lock:
            return self._status

    @property
    def status_text(self) -> str:
        """Versao em ingles, usada na linha de comando."""
        state, detail = self.status
        if state == "playing":
            return f"playing on {self._active_device or 'default output'}"
        if state == "error":
            return f"no audio output ({detail})"
        return "stopped"

    @property
    def compensation(self) -> tuple:
        """(atenuacao_do_sistema_db, nivel_efetivo_db, bateu_no_teto)."""
        with self._lock:
            return self._attenuation, self._target_level_db(), self._clamped

    def _target_level_db(self) -> float:
        """Nivel digital a usar, ja compensando o volume do sistema."""
        base = float(self.config.get("level_db"))
        if not self.config.get("compensate_system"):
            self._clamped = False
            return base
        wanted = base - self._attenuation  # atenuacao e negativa
        capped = min(wanted, MAX_LEVEL_DB)
        self._clamped = capped < wanted - 0.01
        return capped

    def _read_system_level(self) -> bool:
        """Le o volume do sistema. True quando mudou o bastante para re-render."""
        if not self.config.get("compensate_system"):
            if self._attenuation != 0.0:
                self._attenuation = 0.0
                return True
            return False
        value = syslevel.attenuation_db()
        if value is None:
            # sem leitura confiavel a gente nao inventa ganho
            if self._attenuation != 0.0:
                self._attenuation = 0.0
                return True
            return False
        if abs(value - self._attenuation) < LEVEL_EPSILON_DB:
            return False
        self._attenuation = value
        return True

    @property
    def active_device(self) -> Optional[str]:
        with self._lock:
            return self._active_device

    def _notify(self) -> None:
        if self.on_state_change:
            try:
                self.on_state_change()
            except Exception:
                pass

    # ------------------------------------------------------------------ audio

    def _callback(self, outdata, frames, time_info, status) -> None:
        pcm = self._pcm
        total = len(pcm)
        need = frames * self._frame_bytes
        if total < self._frame_bytes:
            outdata[:] = bytes(need)
            return

        pos = self._pos
        end = pos + need
        if end <= total:
            outdata[:] = pcm[pos:end]
            self._pos = end if end < total else 0
            return

        chunks = [pcm[pos:]]
        rest = need - (total - pos)
        while rest >= total:
            chunks.append(pcm)
            rest -= total
        if rest:
            chunks.append(pcm[:rest])
        outdata[:] = b"".join(chunks)
        self._pos = rest

    def _render(self, samplerate: int, channels: int, force: bool = False) -> None:
        """Refaz o buffer so quando algum parametro mudou de verdade."""
        key = (
            str(self.config.get("sound")),
            int(samplerate),
            float(self.config.get("pulse_interval") or 20.0),
            round(self._target_level_db(), 2),
            int(channels),
        )
        if key == self._render_key and not force:
            return

        pcm = render_pcm(key[0], key[1], key[2], key[3], key[4])
        with self._lock:
            self._pcm = pcm
            self._frame_bytes = 2 * max(1, channels)
            self._render_key = key
            if self._pos >= len(pcm):
                self._pos = 0
            else:
                # mantem a posicao alinhada ao quadro depois da troca
                self._pos -= self._pos % self._frame_bytes

    def apply_settings(self) -> None:
        """Troca som, volume ou intervalo sem parar o stream. Sem buraco."""
        with self._lock:
            samplerate, channels = self._samplerate, self._channels
        self._render(samplerate, channels)
        self._notify()

    def _open_stream(self) -> None:
        device = _resolve_device(self.config.get("device"), self.config.get("device_hostapi"))
        wanted = int(self.config.get("samplerate") or 48000)

        info = None
        try:
            info = sd.query_devices(device if device is not None else sd.default.device[1])
        except Exception:
            info = None

        rates = [wanted]
        if info:
            native = int(round(float(info.get("default_samplerate") or 0)))
            if native and native not in rates:
                rates.insert(0, native)
        for rate in FALLBACK_RATES:
            if rate not in rates:
                rates.append(rate)

        max_ch = int(info.get("max_output_channels", 2)) if info else 2
        channel_options = [c for c in (1, 2) if c <= max(1, max_ch)] or [1]

        last_error: Optional[Exception] = None
        for rate in rates:
            for channels in channel_options:
                try:
                    self._render(rate, channels)
                    stream = sd.RawOutputStream(
                        device=device,
                        samplerate=rate,
                        channels=channels,
                        dtype="int16",
                        blocksize=BLOCKSIZE,
                        latency="high",
                        callback=self._callback,
                    )
                    stream.start()
                    with self._lock:
                        self._stream = stream
                        self._samplerate = rate
                        self._channels = channels
                        self._active_device = (
                            str(info.get("name")) if info else default_output_name()
                        )
                        self._status = ("playing", "")
                    return
                except Exception as exc:  # taxa recusada ou dispositivo sumiu
                    last_error = exc
                    continue

        with self._lock:
            self._stream = None
            self._active_device = None
            self._status = ("error", type(last_error).__name__ if last_error else "?")

    def _close_stream(self) -> None:
        with self._lock:
            stream = self._stream
            self._stream = None
        if stream is not None:
            try:
                stream.stop()
            except Exception:
                pass
            try:
                stream.close()
            except Exception:
                pass

    # ------------------------------------------------------------------ api

    def start(self) -> None:
        with self._lock:
            self._running = True
        self._read_system_level()
        self._close_stream()
        self._open_stream()
        self._fingerprint = device_fingerprint()
        self._last_poll = time.monotonic()
        self._notify()

    def stop(self) -> None:
        with self._lock:
            self._running = False
            self._status = ("stopped", "")
            self._active_device = None
        self._close_stream()
        self._notify()

    def toggle(self) -> None:
        if self._running:
            self.stop()
        else:
            self.start()

    def restart(self) -> None:
        """Reabre o stream. So precisa quando o dispositivo muda."""
        if not self._running:
            self._notify()
            return
        self._close_stream()
        self._open_stream()
        self._fingerprint = device_fingerprint()
        self._last_poll = time.monotonic()
        self._notify()

    def rescan(self) -> None:
        """Recarrega os dispositivos e reabre o stream."""
        was_running = self._running
        self._close_stream()
        refresh_devices()
        if was_running:
            self._open_stream()
        self._fingerprint = device_fingerprint()
        self._last_poll = time.monotonic()
        self._notify()

    def set_level_db(self, db: float) -> None:
        self.config.set("level_db", float(db))
        self.apply_settings()

    def shutdown(self) -> None:
        self._stop_event.set()
        self._close_stream()

    # ------------------------------------------------------------------ watchdog

    def _should_follow(self) -> bool:
        return bool(self.config.get("follow_default")) and not self.config.get("device")

    def _watch(self) -> None:
        while not self._stop_event.wait(WATCHDOG_SECONDS):
            try:
                if not self._running:
                    continue

                self._tick += 1
                # no Windows a leitura e uma chamada de API barata, nos outros
                # sistemas envolve processo externo, entao vai mais devagar
                cadence = 1 if sys.platform == "win32" else 3
                if self._tick % cadence == 0 and self._read_system_level():
                    self.apply_settings()

                stream = self._stream
                if stream is None or not stream.active:
                    # o fone caiu ou o driver derrubou o stream
                    self.rescan()
                    continue

                if not self._should_follow():
                    continue

                fingerprint = device_fingerprint()
                if fingerprint is not None:
                    # da para perguntar ao sistema, entao so mexemos no audio
                    # quando um dispositivo entrou ou saiu de verdade
                    if fingerprint != self._fingerprint:
                        self._fingerprint = fingerprint
                        previous = self._active_device
                        self.rescan()
                        if self._active_device != previous:
                            self._notify()
                    continue

                # sem sinal barato do sistema, sobra olhar de tempos em tempos
                if time.monotonic() - self._last_poll >= FALLBACK_POLL_SECONDS:
                    previous = self._active_device
                    self.rescan()
                    if self._active_device != previous:
                        self._notify()
            except Exception:
                # o watchdog nunca pode morrer
                time.sleep(1.0)
