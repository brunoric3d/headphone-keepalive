"""Acha arquivos empacotados, tanto rodando do codigo quanto congelado."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional


def bundled_path(*parts: str) -> Optional[Path]:
    """Caminho de um arquivo empacotado, ex: bundled_path("assets", "x.png")."""
    relative = Path(*parts)
    candidates = []
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        candidates.append(Path(bundled) / relative)
    here = Path(__file__).resolve().parent
    candidates.append(here.parent / relative)
    candidates.append(here / relative)
    for path in candidates:
        try:
            if path.is_file():
                return path
        except OSError:
            continue
    return None


def asset_path(name: str) -> Optional[Path]:
    """Atalho para assets/<name>."""
    return bundled_path("assets", name)
