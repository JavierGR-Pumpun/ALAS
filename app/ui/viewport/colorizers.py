"""
ALAS — Colorizers
Funciones para generar arrays RGBA desde atributos de nubes de puntos.
"""

import numpy as np
from matplotlib import colormaps
from typing import Optional

from app.config import (
    ASPRS_COLORS, DEFAULT_HEIGHT_CMAP, DEFAULT_INTENSITY_CMAP
)


def _apply_cmap(values: np.ndarray, cmap_name: str,
                vmin: float = None, vmax: float = None) -> np.ndarray:
    """
    Aplica un colormap de matplotlib a un array de valores.
    Devuelve (N, 4) RGBA float en [0, 1].
    """
    if vmin is None:
        vmin = np.nanmin(values)
    if vmax is None:
        vmax = np.nanmax(values)

    rng = vmax - vmin
    if rng == 0:
        rng = 1.0

    normalized = np.clip((values - vmin) / rng, 0, 1)
    cmap = colormaps.get_cmap(cmap_name)
    return cmap(normalized).astype(np.float32)


def colorize_by_height(z: np.ndarray,
                        vmin: float = None,
                        vmax: float = None,
                        cmap: str = None) -> np.ndarray:
    """
    Coloriza por altura (Z). Devuelve (N, 3) RGB uint8.
    """
    cmap = cmap or DEFAULT_HEIGHT_CMAP
    rgba = _apply_cmap(z, cmap, vmin, vmax)
    return (rgba[:, :3] * 255).astype(np.uint8)


def colorize_by_intensity(intensity: np.ndarray,
                           cmap: str = None) -> np.ndarray:
    """
    Coloriza por intensidad. Devuelve (N, 3) RGB uint8.
    """
    cmap = cmap or DEFAULT_INTENSITY_CMAP
    values = intensity.astype(np.float32)
    rgba = _apply_cmap(values, cmap)
    return (rgba[:, :3] * 255).astype(np.uint8)


def colorize_by_classification(classification: np.ndarray) -> np.ndarray:
    """
    Coloriza por código de clasificación ASPRS.
    Devuelve (N, 3) RGB uint8.
    """
    colors = np.zeros((len(classification), 3), dtype=np.uint8)
    for code, rgba in ASPRS_COLORS.items():
        mask = classification == code
        if mask.any():
            colors[mask] = rgba[:3]
    return colors


def colorize_by_return_number(return_number: np.ndarray) -> np.ndarray:
    """
    Coloriza por número de retorno. Devuelve (N, 3) RGB uint8.
    Paleta categórica para retornos 1-5+.
    """
    palette = {
        1: (46, 204, 113),    # Verde
        2: (52, 152, 219),    # Azul
        3: (231, 76, 60),     # Rojo
        4: (241, 196, 15),    # Amarillo
        5: (155, 89, 182),    # Púrpura
    }

    colors = np.full((len(return_number), 3), 128, dtype=np.uint8)
    for ret_num, rgb in palette.items():
        mask = return_number == ret_num
        if mask.any():
            colors[mask] = rgb

    # Retornos > 5
    mask = return_number > 5
    if mask.any():
        colors[mask] = (149, 165, 166)

    return colors


def colorize_rgb(rgb_uint16: np.ndarray) -> np.ndarray:
    """
    Convierte RGB uint16 (0-65535) del LAS a RGB uint8 (0-255).
    Devuelve (N, 3) RGB uint8.
    """
    if rgb_uint16.max() > 255:
        return (rgb_uint16 / 256).astype(np.uint8)
    return rgb_uint16.astype(np.uint8)


def colorize_single(n_points: int,
                     color: tuple = (100, 149, 237)) -> np.ndarray:
    """
    Color sólido para todos los puntos. Devuelve (N, 3) RGB uint8.
    """
    colors = np.full((n_points, 3), color, dtype=np.uint8)
    return colors


def get_colorizer(mode: str):
    """Devuelve la función colorizer según el modo."""
    return {
        "height": colorize_by_height,
        "intensity": colorize_by_intensity,
        "classification": colorize_by_classification,
        "return_number": colorize_by_return_number,
        "rgb": colorize_rgb,
        "single_color": colorize_single,
    }.get(mode)
