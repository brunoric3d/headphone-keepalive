"""Os sinais quase inaudiveis, em PCM de 16 bits, sem numpy.

Os ruidos sao renderizados na hora do build por tools/make_audio.py e vem
prontos em assets/. Aqui a gente so carrega. Os tons e o pulso sao baratos e
saem na hora, no sample rate real do dispositivo.

Tudo aqui devolve array('h'), mono, na escala cheia de 16 bits. Quem aplica o
volume e monta os canais e o audio.py.
"""

from __future__ import annotations

import math
import sys
from array import array
from typing import Dict, Optional

from .resources import asset_path

# sample rate em que os assets foram renderizados
ASSET_SAMPLERATE = 48000

TONE_LOW_HZ = 20
TONE_HIGH_HZ = 19000
PULSE_MS = 80.0

# folga usada no build, para o sinal nunca encostar no teto de 16 bits
FULL_SCALE = 32000

NOISE_FILES = {
    "pink": "noise-pink.s16",
    "brown": "noise-brown.s16",
}

_noise_cache: Dict[str, Optional[array]] = {}


def load_noise(kind: str) -> Optional[array]:
    """Le um ruido pronto de assets/. None quando o arquivo nao esta la."""
    if kind in _noise_cache:
        return _noise_cache[kind]

    result: Optional[array] = None
    name = NOISE_FILES.get(kind)
    if name:
        path = asset_path(name)
        if path is not None:
            try:
                data = array("h")
                with open(path, "rb") as handle:
                    data.frombytes(handle.read())
                if sys.byteorder == "big":
                    # os arquivos sao little endian
                    data.byteswap()
                if len(data):
                    result = data
            except (OSError, ValueError):
                result = None

    _noise_cache[kind] = result
    return result


def _tone(samplerate: int, freq: int) -> array:
    """Um segundo de tom. Frequencia inteira faz o loop fechar na fase certa."""
    step = 2.0 * math.pi * freq / samplerate
    sin = math.sin
    return array("h", (int(FULL_SCALE * sin(step * i)) for i in range(samplerate)))


def _pulse(samplerate: int, interval: float, source: Optional[array]) -> array:
    """Silencio com um estalo curto de ruido no comeco de cada intervalo."""
    interval = max(1.0, float(interval))
    total = int(samplerate * interval)
    out = array("h", bytes(2 * total))

    burst = int(samplerate * PULSE_MS / 1000.0)
    if burst <= 0:
        return out
    if source is None or len(source) < burst:
        # sem o asset, um tom curto resolve
        step = 2.0 * math.pi * 1000.0 / samplerate
        source = array("h", (int(FULL_SCALE * math.sin(step * i)) for i in range(burst)))

    # janela de Hann, para o estalo nao virar um clique seco
    for i in range(burst):
        window = 0.5 - 0.5 * math.cos(2.0 * math.pi * i / (burst - 1)) if burst > 1 else 1.0
        out[i] = int(source[i] * window)
    return out


def build_int16(kind: str, samplerate: int, pulse_interval: float = 20.0) -> array:
    """Buffer mono de 16 bits para o tipo de som pedido.

    Os ruidos vem do arquivo, que foi feito a 48 kHz. Tocando em outra taxa o
    espectro desloca um pouco, o que para ruido nao muda nada na pratica.
    """
    if kind in NOISE_FILES:
        data = load_noise(kind)
        if data is not None:
            return data
        # sem o asset, cai para o tom grave, que sempre da para gerar
        kind = "tone_low"

    if kind == "tone_low":
        return _tone(samplerate, TONE_LOW_HZ)
    if kind == "tone_high":
        return _tone(samplerate, min(TONE_HIGH_HZ, samplerate // 2 - 1000))
    if kind == "pulse":
        return _pulse(samplerate, pulse_interval, load_noise("pink"))

    data = load_noise("pink")
    return data if data is not None else _tone(samplerate, TONE_LOW_HZ)
