"""
ALAS — Colormap Utilities
Utilidades para colormaps personalizados.
"""

import numpy as np
from matplotlib import colormaps
from matplotlib.colors import LinearSegmentedColormap, ListedColormap

from app.config import ASPRS_COLORS


def get_terrain_cmap():
    """Colormap personalizado para terreno: azul → verde → marrón → blanco."""
    colors = [
        (0.0, '#1a5276'),   # Azul profundo
        (0.15, '#2ecc71'),  # Verde
        (0.35, '#27ae60'),  # Verde oscuro
        (0.5, '#f39c12'),   # Naranja
        (0.7, '#8b4513'),   # Marrón
        (0.85, '#d3d3d3'),  # Gris claro
        (1.0, '#ffffff'),   # Blanco (nieve)
    ]
    positions = [c[0] for c in colors]
    hex_colors = [c[1] for c in colors]

    cmap = LinearSegmentedColormap.from_list("alas_terrain", list(zip(positions, hex_colors)))
    return cmap


def get_classification_cmap():
    """Colormap discreto para clasificaciones ASPRS."""
    max_code = max(ASPRS_COLORS.keys()) + 1
    colors_list = []
    for i in range(max_code):
        if i in ASPRS_COLORS:
            r, g, b, a = ASPRS_COLORS[i]
            colors_list.append((r/255, g/255, b/255, a/255))
        else:
            colors_list.append((0.5, 0.5, 0.5, 1.0))

    return ListedColormap(colors_list, name="alas_classification")


def get_change_cmap():
    """Colormap divergente para DoD: rojo (erosión) → blanco → azul (deposición)."""
    colors = ['#d32f2f', '#ef5350', '#ffcdd2', '#ffffff',
              '#bbdefb', '#42a5f5', '#1565c0']
    return LinearSegmentedColormap.from_list("alas_change", colors)


def apply_colormap(data: np.ndarray, cmap_name: str,
                    vmin: float = None, vmax: float = None) -> np.ndarray:
    """
    Aplica un colormap a datos y devuelve RGB uint8 (N, 3).
    """
    if vmin is None:
        vmin = np.nanmin(data)
    if vmax is None:
        vmax = np.nanmax(data)

    rng = vmax - vmin
    if rng == 0:
        rng = 1.0

    normalized = np.clip((data - vmin) / rng, 0, 1)

    try:
        cmap = colormaps.get_cmap(cmap_name)
    except ValueError:
        cmap = colormaps.get_cmap("viridis")

    rgba = cmap(normalized)
    return (rgba[..., :3] * 255).astype(np.uint8)
