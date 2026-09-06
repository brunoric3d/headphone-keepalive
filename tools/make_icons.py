#!/usr/bin/env python3
"""Gera os arquivos de icone a partir do logo.

Entrada:  assets/keepalive_logo.png
Saida:    assets/tray-mask.png   silhueta usada pelo icone da bandeja
          assets/icon.png        logo com folga, para README e empacotamento
          assets/icon.ico        icone do executavel no Windows
          assets/icon.icns       icone do app no macOS
          assets/tray-*.png      previews dos tres estados

Uso: python tools/make_icons.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

ASSETS = ROOT / "assets"
LOGO = ASSETS / "keepalive_logo.png"

MASK_SIZE = 512
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
# folga em volta do glifo, como pede o icone de aplicativo de cada sistema
APP_PADDING = 0.90
# a silhueta da bandeja usa quase todo o quadro, o espaco ali e curto
TRAY_PADDING = 0.98


def squared(img: Image.Image, fill_ratio: float, size: int) -> Image.Image:
    """Recorta o vazio, deixa quadrado e centraliza com a folga pedida."""
    img = img.crop(img.getbbox())
    inner = max(1, int(round(size * fill_ratio)))
    w, h = img.size
    scale = inner / max(w, h)
    img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(img, ((size - img.size[0]) // 2, (size - img.size[1]) // 2))
    return canvas


def main() -> int:
    if not LOGO.is_file():
        print(f"nao achei {LOGO}")
        return 1

    logo = Image.open(LOGO).convert("RGBA")

    # silhueta da bandeja: so o canal alfa, que o app pinta por estado
    mask = squared(logo, TRAY_PADDING, MASK_SIZE).split()[-1]
    mask.save(ASSETS / "tray-mask.png", optimize=True)
    print("assets/tray-mask.png")

    # icone do aplicativo, com o logo colorido
    app = squared(logo, APP_PADDING, 1024)
    app.save(ASSETS / "icon.png")
    print("assets/icon.png")

    app.save(ASSETS / "icon.ico", sizes=[(s, s) for s in ICO_SIZES])
    print("assets/icon.ico")

    try:
        app.save(ASSETS / "icon.icns")
        print("assets/icon.icns")
    except Exception as exc:
        print(f"icns nao gerado aqui ({exc}). O build do macOS gera na hora.")

    # previews dos estados, para o README e para conferencia
    from keepalive.icon import make_icon  # noqa: E402  precisa da mascara acima

    for state in ("on", "off", "error"):
        make_icon(state, 256).save(ASSETS / f"tray-{state}.png")
    print("assets/tray-on.png, tray-off.png, tray-error.png")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
