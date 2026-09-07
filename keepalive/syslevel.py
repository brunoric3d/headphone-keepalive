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
_VT_QUERY_HW_SUPPORT = 19      # IAudioEndpointVolume::QueryHardwareSupport
_VT_GET_VOLUME_RANGE = 20      # IAudioEndpointVolume::GetVolumeRange

_E_RENDER = 0
_E_CONSOLE = 0


def _win_query(debug=False):
    """(atenuacao_db, escala_0a1, mudo) do dispositivo de saida padrao.

    Fala com o Core Audio por COM cru. Cada passo reporta o HRESULT quando
    debug=True, para dar para diagnosticar sem ter a maquina na mao.
    """
    import ctypes
    from ctypes import POINTER, byref, c_float, c_int, c_ubyte, c_ulong, c_ushort, c_void_p

    passos = []

    def registra(texto):
        passos.append(texto)
        if debug:
            print(f"  {texto}")

    ole32 = ctypes.windll.ole32

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", c_ulong), ("Data2", c_ushort),
                    ("Data3", c_ushort), ("Data4", c_ubyte * 8)]

    def guid(text):
        out = GUID()
        hr = ole32.CLSIDFromString(ctypes.c_wchar_p(text), byref(out))
        if hr != 0:
            raise OSError(f"CLSIDFromString({text}) = 0x{hr & 0xFFFFFFFF:08X}")
        return out

    def method(interface, index, *argtypes):
        """Monta o ponteiro de funcao do metodo `index` da vtable.

        Os tipos dos argumentos precisam ser declarados: um prototipo criado
        com WINFUNCTYPE tem aridade fixa, ao contrario de uma funcao carregada
        de DLL, que aceita qualquer coisa quando argtypes nao foi definido.
        """
        vtable = ctypes.cast(interface, POINTER(POINTER(c_void_p))).contents
        address = vtable[index]
        if not address:
            raise OSError(f"vtable[{index}] vazia")
        return ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, *argtypes)(address)

    hr_init = ole32.CoInitialize(None)
    registra(f"CoInitialize = 0x{hr_init & 0xFFFFFFFF:08X}")

    enumerator = c_void_p()
    device = c_void_p()
    volume = c_void_p()
    try:
        hr = ole32.CoCreateInstance(
            byref(guid(_CLSID_MMDeviceEnumerator)), None, 1,
            byref(guid(_IID_IMMDeviceEnumerator)), byref(enumerator))
        registra(f"CoCreateInstance(MMDeviceEnumerator) = 0x{hr & 0xFFFFFFFF:08X}")
        if hr != 0 or not enumerator:
            return None

        get_endpoint = method(enumerator, _VT_GET_DEFAULT_ENDPOINT,
                              c_int, c_int, POINTER(c_void_p))
        hr = get_endpoint(enumerator, _E_RENDER, _E_CONSOLE, byref(device))
        registra(f"GetDefaultAudioEndpoint = 0x{hr & 0xFFFFFFFF:08X}")
        if hr != 0 or not device:
            return None

        activate = method(device, _VT_ACTIVATE,
                          POINTER(GUID), c_ulong, c_void_p, POINTER(c_void_p))
        hr = activate(device, byref(guid(_IID_IAudioEndpointVolume)), 1, None, byref(volume))
        registra(f"Activate(IAudioEndpointVolume) = 0x{hr & 0xFFFFFFFF:08X}")
        if hr != 0 or not volume:
            return None

        level_db = c_float()
        scalar = c_float()
        muted = c_int()

        hr = method(volume, _VT_GET_MASTER_LEVEL_DB, POINTER(c_float))(volume, byref(level_db))
        registra(f"GetMasterVolumeLevel = 0x{hr & 0xFFFFFFFF:08X} -> {level_db.value:.2f} dB")
        ok_db = hr == 0

        hr = method(volume, _VT_GET_MASTER_SCALAR, POINTER(c_float))(volume, byref(scalar))
        registra(f"GetMasterVolumeLevelScalar = 0x{hr & 0xFFFFFFFF:08X} -> {scalar.value:.3f}")
        ok_scalar = hr == 0

        hr = method(volume, _VT_GET_MUTE, POINTER(c_int))(volume, byref(muted))
        registra(f"GetMute = 0x{hr & 0xFFFFFFFF:08X} -> {bool(muted.value)}")
        ok_mute = hr == 0

        if debug:
            # so para diagnostico: da para saber se a faixa de dB do dispositivo
            # tem qualquer utilidade, ou se ele so sabe responder pela escala
            lo, hi, step = c_float(), c_float(), c_float()
            hr_range = method(volume, _VT_GET_VOLUME_RANGE,
                              POINTER(c_float), POINTER(c_float), POINTER(c_float))(
                volume, byref(lo), byref(hi), byref(step))
            registra(f"GetVolumeRange = 0x{hr_range & 0xFFFFFFFF:08X} -> "
                     f"min {lo.value:.2f} dB, max {hi.value:.2f} dB, passo {step.value:.2f} dB")
            hw = c_ulong()
            hr_hw = method(volume, _VT_QUERY_HW_SUPPORT, POINTER(c_ulong))(volume, byref(hw))
            registra(f"QueryHardwareSupport = 0x{hr_hw & 0xFFFFFFFF:08X} -> 0x{hw.value:X}")

        if not ok_db and not ok_scalar:
            return None

        escala = float(scalar.value) if ok_scalar else None
        db_bruto = float(level_db.value) if ok_db else None

        # Varios dispositivos nao expoem faixa de dB de verdade e devolvem um
        # numero perto de zero mesmo com o slider baixo. Quando o dB diz "sem
        # atenuacao" e a escala diz o contrario, a escala ganha.
        db_suspeito = (
            db_bruto is None
            or (db_bruto > -0.5 and escala is not None and escala < 0.95)
        )
        if db_suspeito and escala is not None:
            db = 20.0 * math.log10(escala) if escala > 0 else -96.0
            origem = "escala"
        else:
            db = db_bruto if db_bruto is not None else 0.0
            origem = "dB do dispositivo"
        registra(f"origem da atenuacao: {origem} -> {db:+.1f} dB")

        return (db, escala, bool(muted.value) if ok_mute else None)
    except Exception as exc:
        registra(f"excecao: {type(exc).__name__}: {exc}")
        if debug:
            import traceback
            traceback.print_exc()
        return None
    finally:
        for interface in (volume, device, enumerator):
            if interface:
                try:
                    method(interface, _VT_RELEASE)(interface)
                except Exception:
                    pass
        try:
            ole32.CoUninitialize()
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

def query(debug: bool = False):
    """(atenuacao_db, escala_0a1, mudo), ou None quando nao deu para ler."""
    try:
        if sys.platform == "win32":
            result = _win_query(debug=debug)
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
