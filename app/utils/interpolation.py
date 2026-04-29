"""
ALAS — Interpolation Utilities
Métodos de interpolación: IDW, TIN, grid generation.
"""

import numpy as np
from scipy.spatial import cKDTree, Delaunay
from scipy.interpolate import griddata, LinearNDInterpolator
from typing import Tuple

from app.config import DEFAULT_IDW_POWER, DEFAULT_NODATA
from app.logger import get_logger

logger = get_logger("utils.interpolation")


def idw_interpolation(points: np.ndarray, values: np.ndarray,
                       grid_x: np.ndarray, grid_y: np.ndarray,
                       power: float = None, k: int = 12) -> np.ndarray:
    """
    Inverse Distance Weighting.
    points: (N, 2) coordenadas XY.
    values: (N,) valores Z.
    grid_x, grid_y: meshgrids de salida.
    """
    power = power or DEFAULT_IDW_POWER

    tree = cKDTree(points)
    grid_points = np.column_stack([grid_x.ravel(), grid_y.ravel()])

    distances, indices = tree.query(grid_points, k=k)
    distances = np.maximum(distances, 1e-10)

    weights = 1.0 / (distances ** power)
    weight_sum = weights.sum(axis=1)

    z_values = values[indices]
    result = (z_values * weights).sum(axis=1) / weight_sum

    return result.reshape(grid_x.shape)


def tin_interpolation(points: np.ndarray, values: np.ndarray,
                       grid_x: np.ndarray, grid_y: np.ndarray) -> np.ndarray:
    """
    Interpolación por TIN (Triangulated Irregular Network).
    """
    result = griddata(points, values, (grid_x, grid_y),
                       method='linear', fill_value=DEFAULT_NODATA)
    return result


def nearest_interpolation(points: np.ndarray, values: np.ndarray,
                            grid_x: np.ndarray, grid_y: np.ndarray) -> np.ndarray:
    """Interpolación al vecino más cercano."""
    result = griddata(points, values, (grid_x, grid_y),
                       method='nearest', fill_value=DEFAULT_NODATA)
    return result


def grid_from_bounds(bounds: Tuple[float, float, float, float],
                      resolution: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Genera un grid regular desde una extensión geográfica.
    bounds: (xmin, ymin, xmax, ymax)
    Devuelve (grid_x, grid_y) meshgrids.
    """
    xmin, ymin, xmax, ymax = bounds
    cols = int(np.ceil((xmax - xmin) / resolution))
    rows = int(np.ceil((ymax - ymin) / resolution))

    xi = np.linspace(xmin + resolution/2, xmax - resolution/2, cols)
    yi = np.linspace(ymax - resolution/2, ymin + resolution/2, rows)

    return np.meshgrid(xi, yi)
