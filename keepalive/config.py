"""Leitura e escrita das configuracoes em disco, com caminho por sistema."""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict

from . import APP_ID

DEFAULTS: Dict[str, Any] = {
    # ligado ou desligado quando o app abre
    "enabled": True,
    # pink, brown, tone_low, tone_high, pulse
    "sound": "pink",
    # nivel do sinal em dBFS. quanto menor, mais silencioso
    "level_db": -54.0,
    # nome do dispositivo de saida, ou None para usar o padrao do sistema
    "device": None,
    # API de audio do dispositivo escolhido, para nao confundir homonimos
    "device_hostapi": None,
    # mostrar as saidas de todas as APIs de audio, com repeticao
    "show_all_apis": False,
    # segue o dispositivo padrao do sistema e reconecta sozinho
    "follow_default": True,
    # intervalo em segundos do modo pulso
    "pulse_interval": 20.0,
    # taxa de amostragem preferida
    "samplerate": 48000,
    # iniciar junto com o sistema
    "autostart": False,
    # auto segue o idioma do sistema; ou um codigo como en, pt, es
    "language": "auto",
    # sobe o sinal quando o volume do sistema esta baixo, para o fone nao achar
    # que e silencio. limitado ao nivel do preset mais alto do app
    "compensate_system": True,
}

# chave de traducao e nivel em dBFS
LEVEL_PRESETS = [
    ("level_min", -66.0),
    ("level_very_low", -60.0),
    ("level_low", -54.0),
    ("level_medium", -48.0),
    ("level_high", -40.0),
    ("level_very_high", -30.0),
]

# valor salvo no config e chave de traducao
SOUND_LABELS = [
    ("pink", "sound_pink"),
    ("brown", "sound_brown"),
    ("tone_low", "sound_tone_low"),
    ("tone_high", "sound_tone_high"),
    ("pulse", "sound_pulse"),
]

PULSE_INTERVALS = [5.0, 10.0, 20.0, 30.0, 60.0]


def config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    path = Path(base) / APP_ID
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_file() -> Path:
    return config_dir() / "config.json"


class Config:
    """Dicionario de configuracao que salva sozinho a cada mudanca."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        path = config_file()
        if not path.exists():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(raw, dict):
            return
        with self._lock:
            for key, value in raw.items():
                if key in DEFAULTS:
                    self._data[key] = value

    def save(self) -> None:
        path = config_file()
        try:
            with self._lock:
                payload = json.dumps(self._data, indent=2, ensure_ascii=False)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(payload, encoding="utf-8")
            tmp.replace(path)
        except OSError:
            # nao vale derrubar o app por causa de disco cheio ou permissao
            pass

    def get(self, key: str) -> Any:
        with self._lock:
            return self._data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value
        self.save()

    def as_dict(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data)
