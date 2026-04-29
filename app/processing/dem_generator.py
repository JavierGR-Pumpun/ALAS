"""
ALAS — DEM Generator
Generación de MDT, MDS y CHM a partir de nubes de puntos clasificadas.
"""

import numpy as np
from typing import Optional, Tuple
from scipy.interpolate import griddata
from scipy.spatial import cKDTree

from app.core.point_cloud import PointCloudData
from app.core.raster_layer import RasterLayer
from app.config import (
    DEFAULT_DEM_RESOLUTION, DEFAULT_IDW_POWER, DEFAULT_NODATA,
    DEFAULT_INTERPOLATION_METHOD
)
from app.logger import get_logger

logger = get_logger("processing.dem_generator")


def generate_dtm(pc: PointCloudData, resolution: float = None,
                 method: str = None, power: float = None) -> RasterLayer:
    """
    Genera un MDT (Modelo Digital del Terreno) solo con puntos de suelo.
    """
    resolution = resolution or DEFAULT_DEM_RESOLUTION
    method = method or DEFAULT_INTERPOLATION_METHOD
    power = power or DEFAULT_IDW_POWER

    logger.info(f"Generando MDT: res={resolution}m, método={method}")

    # Extraer solo puntos de suelo
    ground = pc.get_ground_points()
    if ground.point_count == 0:
        raise ValueError("No hay puntos de suelo clasificados. Ejecuta la clasificación primero.")

    return _points_to_raster(
        ground.xyz, resolution, method, power,
        name="MDT", epsg=pc.crs_epsg
    )


def generate_dsm(pc: PointCloudData, resolution: float = None,
                 method: str = None) -> RasterLayer:
    """
    Genera un MDS (Modelo Digital de Superficie) con primeros retornos.
    """
    resolution = resolution or DEFAULT_DEM_RESOLUTION
    method = method or DEFAULT_INTERPOLATION_METHOD

    logger.info(f"Generando MDS: res={resolution}m, método={method}")

    # Usar primeros retornos si están disponibles, sino todos los puntos
    if pc.return_number is not None:
        try:
            first_returns = pc.get_first_returns()
            points = first_returns.xyz
        except Exception:
            points = pc.xyz
    else:
        points = pc.xyz

    # Para MDS, usar el punto más alto en cada celda (máximo)
    return _points_to_raster_max(
        points, resolution,
        name="MDS", epsg=pc.crs_epsg
    )


def generate_chm(dtm: RasterLayer, dsm: RasterLayer,
                 name: str = "CHM") -> RasterLayer:
    """
    Genera un CHM (Canopy Height Model) = MDS - MDT.
    """
    logger.info("Generando CHM (MDS - MDT)")

    dtm_data = dtm.get_band(0)
    dsm_data = dsm.get_band(0)

    # Verificar dimensiones compatibles
    if dtm_data.shape != dsm_data.shape:
        # Resamplear al más pequeño
        min_rows = min(dtm_data.shape[0], dsm_data.shape[0])
        min_cols = min(dtm_data.shape[1], dsm_data.shape[1])
        dtm_data = dtm_data[:min_rows, :min_cols]
        dsm_data = dsm_data[:min_rows, :min_cols]
        logger.warning(f"Recortando a {min_cols}x{min_rows} px")

    # Calcular diferencia
    chm = dsm_data - dtm_data

    # Valores negativos → 0 (artefactos)
    chm[chm < 0] = 0

    # Nodata donde cualquiera sea nodata
    nodata_mask = (dtm_data == dtm.nodata) | (dsm_data == dsm.nodata)
    chm[nodata_mask] = DEFAULT_NODATA

    result = RasterLayer.from_array(
        chm, dtm.bounds, epsg=dtm.crs_epsg,
        nodata=DEFAULT_NODATA, name=name
    )

    stats = result.statistics()
    logger.info(
        f"CHM generado: rango {stats.get('min', 0):.1f} - "
        f"{stats.get('max', 0):.1f} m"
    )
    return result


def _points_to_raster(points: np.ndarray, resolution: float,
                       method: str, power: float,
                       name: str = "raster",
                       epsg: int = None) -> RasterLayer:
    """Interpola puntos a un grid regular."""
    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2]

    # Crear grid
    xmin, xmax = x.min(), x.max()
    ymin, ymax = y.min(), y.max()

    cols = int(np.ceil((xmax - xmin) / resolution))
    rows = int(np.ceil((ymax - ymin) / resolution))

    if cols <= 0 or rows <= 0:
        raise ValueError("La extensión de la nube es demasiado pequeña.")

    logger.info(f"Grid: {cols}x{rows} celdas ({resolution}m/px)")

    xi = np.linspace(xmin + resolution / 2, xmax - resolution / 2, cols)
    yi = np.linspace(ymax - resolution / 2, ymin + resolution / 2, rows)
    xx, yy = np.meshgrid(xi, yi)

    if method == "idw":
        grid_z = _idw_interpolation(x, y, z, xx, yy, power=power)
    elif method == "tin":
        grid_z = griddata(
            np.column_stack([x, y]), z,
            (xx, yy), method="linear", fill_value=DEFAULT_NODATA
        )
    elif method == "nearest":
        grid_z = griddata(
            np.column_stack([x, y]), z,
            (xx, yy), method="nearest", fill_value=DEFAULT_NODATA
        )
    else:
        grid_z = _idw_interpolation(x, y, z, xx, yy, power=power)

    grid_z = grid_z.astype(np.float32)

    bounds = (xmin, ymin, xmax, ymax)
    result = RasterLayer.from_array(grid_z, bounds, epsg=epsg,
                                     nodata=DEFAULT_NODATA, name=name)

    stats = result.statistics()
    logger.info(
        f"{name} generado: {cols}x{rows}px | "
        f"Z: {stats.get('min', 0):.1f} - {stats.get('max', 0):.1f} m"
    )
    return result


def _points_to_raster_max(points: np.ndarray, resolution: float,
                            name: str = "raster",
                            epsg: int = None) -> RasterLayer:
    """
    Rasteriza puntos usando el valor máximo Z en cada celda.
    Para MDS (superficie, punto más alto gana).
    """
    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2]

    xmin, xmax = x.min(), x.max()
    ymin, ymax = y.min(), y.max()

    cols = int(np.ceil((xmax - xmin) / resolution))
    rows = int(np.ceil((ymax - ymin) / resolution))

    if cols <= 0 or rows <= 0:
        raise ValueError("Extensión demasiado pequeña.")

    grid_z = np.full((rows, cols), DEFAULT_NODATA, dtype=np.float32)

    # Asignar cada punto a su celda
    col_idx = np.clip(((x - xmin) / resolution).astype(int), 0, cols - 1)
    row_idx = np.clip(((ymax - y) / resolution).astype(int), 0, rows - 1)

    # Usar máximo por celda
    for i in range(len(z)):
        r, c = row_idx[i], col_idx[i]
        if grid_z[r, c] == DEFAULT_NODATA or z[i] > grid_z[r, c]:
            grid_z[r, c] = z[i]

    # Rellenar huecos con interpolación nearest
    nodata_mask = grid_z == DEFAULT_NODATA
    if nodata_mask.any() and not nodata_mask.all():
        valid_mask = ~nodata_mask
        valid_coords = np.argwhere(valid_mask)
        nodata_coords = np.argwhere(nodata_mask)
        tree = cKDTree(valid_coords)
        _, nearest_idx = tree.query(nodata_coords, k=1)
        grid_z[nodata_mask] = grid_z[valid_mask][nearest_idx]

    bounds = (xmin, ymin, xmax, ymax)
    return RasterLayer.from_array(grid_z, bounds, epsg=epsg,
                                   nodata=DEFAULT_NODATA, name=name)


def _idw_interpolation(x, y, z, xx, yy, power: float = 2.0,
                        k: int = 12) -> np.ndarray:
    """Inverse Distance Weighting interpolation."""
    points_xy = np.column_stack([x, y])
    grid_points = np.column_stack([xx.ravel(), yy.ravel()])

    tree = cKDTree(points_xy)
    distances, indices = tree.query(grid_points, k=k)

    # Evitar div por 0
    distances = np.maximum(distances, 1e-10)

    weights = 1.0 / (distances ** power)
    weight_sum = weights.sum(axis=1)

    z_values = z[indices]
    grid_z = (z_values * weights).sum(axis=1) / weight_sum

    return grid_z.reshape(xx.shape)
