"""
ALAS — CRS Utilities
Utilidades para sistemas de coordenadas.
"""

from typing import Optional, Tuple
import numpy as np

from app.logger import get_logger

logger = get_logger("utils.crs")


def get_crs_info(epsg: int) -> dict:
    """Obtiene información legible sobre un código EPSG."""
    try:
        from pyproj import CRS
        crs = CRS.from_epsg(epsg)
        return {
            "epsg": epsg,
            "name": crs.name,
            "type": crs.type_name,
            "units": str(crs.axis_info[0].unit_name) if crs.axis_info else "unknown",
            "area": crs.area_of_use.name if crs.area_of_use else "unknown",
            "wkt": crs.to_wkt(),
        }
    except Exception as e:
        return {"epsg": epsg, "name": f"EPSG:{epsg}", "error": str(e)}


def transform_coords(points: np.ndarray, from_epsg: int,
                      to_epsg: int) -> np.ndarray:
    """
    Reproyecta coordenadas de un CRS a otro.
    points: (N, 2) o (N, 3) array.
    """
    from pyproj import Transformer

    transformer = Transformer.from_crs(
        f"EPSG:{from_epsg}", f"EPSG:{to_epsg}", always_xy=True
    )

    if points.shape[1] >= 3:
        x, y, z = points[:, 0], points[:, 1], points[:, 2]
        tx, ty, tz = transformer.transform(x, y, z)
        return np.column_stack([tx, ty, tz])
    else:
        x, y = points[:, 0], points[:, 1]
        tx, ty = transformer.transform(x, y)
        return np.column_stack([tx, ty])


def validate_crs_compatibility(epsg_a: int, epsg_b: int) -> dict:
    """Verifica si dos CRS son compatibles para superponer."""
    try:
        from pyproj import CRS
        crs_a = CRS.from_epsg(epsg_a)
        crs_b = CRS.from_epsg(epsg_b)

        same_datum = crs_a.datum == crs_b.datum
        same_units = (
            crs_a.axis_info[0].unit_name == crs_b.axis_info[0].unit_name
            if crs_a.axis_info and crs_b.axis_info else False
        )

        return {
            "compatible": epsg_a == epsg_b,
            "same_datum": same_datum,
            "same_units": same_units,
            "needs_reprojection": epsg_a != epsg_b,
            "crs_a": crs_a.name,
            "crs_b": crs_b.name,
        }
    except Exception as e:
        return {"compatible": False, "error": str(e)}
