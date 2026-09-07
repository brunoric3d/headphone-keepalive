"""Le quanto o volume do sistema esta atenuando a saida, em dB.

Serve para o app compensar: se o sistema esta em 10%, o sinal chega no fone
20 dB mais fraco do que o escolhido, e o fone pode considerar isso silencio.

Devolve sempre uma atenuacao negativa ou zero, onde 0 dB significa volume no
maximo. None quando nao deu para descobrir, e nesse caso o app nao compensa
nada, que e o comportamento seguro.
"""

from __future__ import annotations

import math
import re
import subprocess
import sys
from typing import Optional

# --------------------------------------------------------------------- windows
# Core Audio, alcancado por ctypes puro para nao acrescentar dependencia.

_CLSID_MMDeviceEnumerator = "{BCDE0395-E52F-467C-8E3D-C4579291692E}"
_IID_IMMDeviceEnumerator = "{A95664D2-9614-4F35-A746-DE8DB63617E6}"
_IID_IAudioEndpointVolume = "{5CDF2C82-841E-4546-9722-0CF74078229A}"

# posicoes na vtable de cada interface
_VT_RELEASE = 2
_VT_GET_DEFAULT_ENDPOINT = 4   # IMMDeviceEnumerator
_VT_ACTIVATE = 3               # IMMDevice
_VT_GET_MASTER_LEVEL_DB = 8    # IAudioEndpointVolume::GetMasterVolumeLevel
_VT_GET_MASTER_SCALAR = 9      # IAudioEndpointVolume::GetMasterVolumeLevelScalar
_VT_GET_MUTE = 15              # IAudioEndpointVolume::GetMute

_E_RENDER = 0
_E_CONSOLE = 0


def _win_query():
    """Devolve (atenuacao_db, escala_0a1, mudo) do dispositivo de saida padrao."""
    import ctypes
    from ctypes import POINTER, byref, c_float, c_int, c_void_p

    ole32 = ctypes.windll.ole32

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                    ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]

    def guid(text: str) -> GUID:
        out = GUID()
        if ole32.CLSIDFromString(ctypes.c_wchar_p(text), byref(out)) != 0:
            raise OSError("CLSIDFromString falhou")
        return out

    def call(interface, index, *args):
        """Chama o metodo `index` da vtable de uma interface COM."""
        vtable = ctypes.cast(interface, POINTER(POINTER(c_void_p)))[0]
        prototype = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, *[type(a) for a in args])
        return prototype(vtable[index])(interface, *args)

    ole32.CoInitialize(None)
    enumerator = c_void_p()
    device = c_void_p()
    volume = c_void_p()
    try:
        if ole32.CoCreateInstance(byref(guid(_CLSID_MMDeviceEnumerator)), None, 1,
                                  byref(guid(_IID_IMMDeviceEnumerator)),
                                  byref(enumerator)) != 0:
            return None

        if call(enumerator, _VT_GET_DEFAULT_ENDPOINT,
                c_int(_E_RENDER), c_int(_E_CONSOLE), byref(device)) != 0:
            return None

        if call(device, _VT_ACTIVATE, byref(guid(_IID_IAudioEndpointVolume)),
                c_int(1), None, byref(volume)) != 0:
            return None

        level_db = c_float()
        scalar = c_float()
        muted = c_int()
        ok_db = call(volume, _VT_GET_MASTER_LEVEL_DB, byref(level_db)) == 0
        ok_scalar = call(volume, _VT_GET_MASTER_SCALAR, byref(scalar)) == 0
        ok_mute = call(volume, _VT_GET_MUTE, byref(muted)) == 0

        return (
            float(level_db.value) if ok_db else None,
            float(scalar.value) if ok_scalar else None,
            bool(muted.value) if ok_mute else None,
        )
    finally:
        for interface in (volume, device, enumerator):
            if interface:
                try:
                    call(interface, _VT_RELEASE)
                except Exception:
                    pass


# ----------------------------------------------------------------------- macos

def _mac_query():
    """AppleScript devolve o volume de 0 a 100, sem dB. A conversao e aproximada."""
    try:
        out = subprocess.run(
            ["osascript", "-e", "output volume of (get volume settings)",
             "-e", "output muted of (get volume settings)"],
            capture_output=True, text=True, timeout=4,
        ).stdout.split()
        percent = float(out[0])
        muted = out[1].strip().lower() == "true" if len(out) > 1 else None
        scalar = max(0.0, min(1.0, percent / 100.0))
        level_db = 20.0 * math.log10(scalar) if scalar > 0 else -96.0
        return level_db, scalar, muted
    except Exception:
        return None


# ----------------------------------------------------------------------- linux

def _linux_query():
    """PulseAudio e PipeWire dao a atenuacao em dB direto pelo pactl."""
    try:
        out = subprocess.run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                             capture_output=True, text=True, timeout=4).stdout
        db = re.search(r"/\s*(-?[\d.]+|-inf)\s*dB", out)
        percent = re.search(r"/\s*(\d+)%", out)
        level_db = None
        if db:
            level_db = -96.0 if db.group(1) == "-inf" else float(db.group(1))
        scalar = float(percent.group(1)) / 100.0 if percent else None
        muted = None
        try:
            mute_out = subprocess.run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"],
                                      capture_output=True, text=True, timeout=4).stdout
            muted = "yes" in mute_out.lower()
        except Exception:
            pass
        if level_db is None and scalar:
            level_db = 20.0 * math.log10(scalar) if scalar > 0 else -96.0
        return (level_db, scalar, muted) if level_db is not None else None
    except Exception:
        return None


# ------------------------------------------------------------------------- api

def query():
    """(atenuacao_db, escala_0a1, mudo), ou None quando nao deu para ler."""
    try:
        if sys.platform == "win32":
            result = _win_query()
        elif sys.platform == "darwin":
            result = _mac_query()
        else:
            result = _linux_query()
    except Exception:
        return None

    if not result or result[0] is None:
        return None
    level_db, scalar, muted = result
    # acima de 0 dB seria amplificacao do sistema, que nao nos interessa
    return min(0.0, float(level_db)), scalar, muted


def attenuation_db() -> Optional[float]:
    """Quanto o volume do sistema tira do sinal, em dB. 0 = volume no maximo."""
    result = query()
    return result[0] if result else None
