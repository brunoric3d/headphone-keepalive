#!/usr/bin/env python3
"""Renderiza os ruidos na hora do build, para o app nao precisar do numpy.

O numpy so existe aqui, no ambiente de build. O executavel final carrega os
arquivos prontos e nao leva a biblioteca junto, o que corta mais de 20 MB.

Saida: assets/noise-pink.s16 e assets/noise-brown.s16
       PCM cru, mono, 16 bits com sinal, little endian, 48000 Hz.

Uso: python tools/make_audio.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

import numpy as np  # noqa: E402

SAMPLERATE = 48000
# 5 segundos ja e loop demais para um ruido inaudivel, e sao 480 KB por arquivo
SECONDS = 5.0
# emenda entre o fim e o comeco do loop
CROSSFADE = 0.05
# corta o que fone e ouvido nao aproveitam
HIGHPASS_HZ = 30.0

KINDS = {
    # nome do arquivo: expoente do espectro 1/f**n
    "pink": 0.5,
    "brown": 1.0,
}


def shaped_noise(seconds: float, exponent: float, seed: int) -> np.ndarray:
    """Ruido com espectro 1/f**exponent, normalizado em -1..1."""
    rng = np.random.default_rng(seed)
    n = int(SAMPLERATE * seconds)
    spectrum = np.fft.rfft(rng.standard_normal(n))
    freqs = np.fft.rfftfreq(n, d=1.0 / SAMPLERATE)

    shape = np.ones_like(freqs)
    shape[1:] = 1.0 / np.power(freqs[1:], exponent)
    shape[0] = 0.0
    shape[freqs < HIGHPASS_HZ] = 0.0

    out = np.fft.irfft(spectrum * shape, n=n)
    peak = float(np.max(np.abs(out)))
    return out / peak if peak else out


def seamless(buf: np.ndarray) -> np.ndarray:
    """Mistura o fim no comeco para o loop nao dar clique na emenda."""
    fade = int(SAMPLERATE * CROSSFADE)
    if fade <= 0 or buf.size <= fade * 2:
        return buf
    ramp = np.linspace(0.0, 1.0, fade)
    head, tail = buf[:fade].copy(), buf[-fade:].copy()
    buf = buf[:-fade]
    buf[:fade] = head * ramp + tail * (1.0 - ramp)
    return buf


def to_int16(buf: np.ndarray) -> np.ndarray:
    """Vai para 16 bits deixando uma folga, para nunca estourar."""
    peak = float(np.max(np.abs(buf)))
    if peak:
        buf = buf / peak
    return np.clip(buf * 32000.0, -32768, 32767).astype("<i2")


def main() -> int:
    ASSETS.mkdir(exist_ok=True)
    for index, (name, exponent) in enumerate(KINDS.items()):
        data = to_int16(seamless(shaped_noise(SECONDS, exponent, 20260906 + index)))
        path = ASSETS / f"noise-{name}.s16"
        path.write_bytes(data.tobytes())

        seam = abs(int(data[0]) - int(data[-1])) / 32768.0
        rms = float(np.sqrt(np.mean((data.astype(np.float64) / 32768.0) ** 2)))
        print(
            f"assets/{path.name}  {data.size} amostras  "
            f"{data.size / SAMPLERATE:.2f}s  {path.stat().st_size / 1024:.0f} KB  "
            f"rms {20 * np.log10(rms):.1f} dBFS  emenda {seam:.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
