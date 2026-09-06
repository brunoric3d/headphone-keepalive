"""Icone da bandeja, colorido por estado.

O desenho vem da silhueta do logo, guardada em assets/tray-mask.png como um
canal alfa. A cada estado a gente pinta essa silhueta de uma cor. Silhueta
chapada em vez do logo colorido porque a bandeja tem 16 pixels: o degrade do
logo vira sujeira nesse tamanho, e o sombreado escuro dele some em barra de
tarefas escura.
"""

from __future__ import annotations

from typing import Optional

from PIL import Image, ImageDraw

from .resources import asset_path

CANVAS = 512

COLORS = {
    "on": (108, 66, 255, 255),      # violeta do logo
    "off": (150, 152, 158, 255),    # cinza neutro
    "error": (226, 88, 72, 255),    # vermelho
}

MASK_NAME = "tray-mask.png"


def _mask_path():
    """Acha a mascara, tanto rodando do codigo quanto dentro do executavel."""
    return asset_path(MASK_NAME)


_mask: Optional[Image.Image] = None
_mask_tried = False


def _load_mask() -> Optional[Image.Image]:
    global _mask, _mask_tried
    if _mask_tried:
        return _mask
    _mask_tried = True
    path = _mask_path()
    if path is None:
        return None
    try:
        _mask = Image.open(path).convert("L")
    except Exception:
        _mask = None
    return _mask


def _fallback(size: int) -> Image.Image:
    """Fone desenhado na mao, caso a mascara nao esteja disponivel."""
    img = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    band_box = [96, 80, 416, 400]
    band_width = 56
    d.arc(band_box, start=180, end=360, fill=(255, 255, 255, 255), width=band_width)
    half = band_width / 2.0
    cy = (band_box[1] + band_box[3]) / 2.0
    for cx in (band_box[0] + half, band_box[2] - half):
        d.ellipse([cx - half, cy - half, cx + half, cy + half], fill=(255, 255, 255, 255))
    for box in ([32, 204, 160, 432], [352, 204, 480, 432]):
        d.rounded_rectangle(box, radius=58, fill=(255, 255, 255, 255))
    return img.split()[-1].resize((size, size), Image.LANCZOS)


_cache = {}


def make_icon(state: str = "off", size: int = 64) -> Image.Image:
    """Icone quadrado RGBA no estado pedido: on, off ou error."""
    key = (state, size)
    if key in _cache:
        return _cache[key]

    mask = _load_mask()
    alpha = mask.resize((size, size), Image.LANCZOS) if mask is not None else _fallback(size)

    color = COLORS.get(state, COLORS["off"])
    icon = Image.new("RGBA", (size, size), color[:3] + (0,))
    icon.putalpha(alpha)
    _cache[key] = icon
    return icon
