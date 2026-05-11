"""
ALAS — DEM Generator
Generation of DEM, DSM and CHM from classified point clouds.
"""

import numpy as np
from typing import Optional, Tuple
from scipy.interpolate import griddata
from scipy.ndimage import distance_transform_edt
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
    Generates a DTM (Digital Terrain Model) using only ground points.
    """
    resolution = DEFAULT_DEM_RESOLUTION if resolution is None else resolution
    method = DEFAULT_INTERPOLATION_METHOD if method is None else method
    power = DEFAULT_IDW_POWER if power is None else power

    logger.info(f"Generating DTM: res={resolution}m, method={method}")

    # Extract only ground points
    ground = pc.get_ground_points()
    if ground.point_count == 0:
        raise ValueError("No classified ground points. Run classification first.")

    return _points_to_raster(
        ground.xyz, resolution, method, power,
        name="DTM", epsg=pc.crs_epsg
    )


def generate_dsm(pc: PointCloudData, resolution: float = None,
                 method: str = None) -> RasterLayer:
    """
    Generates a DSM (Digital Surface Model) using first returns.
    """
    resolution = DEFAULT_DEM_RESOLUTION if resolution is None else resolution
    method = DEFAULT_INTERPOLATION_METHOD if method is None else method

    logger.info(f"Generating DSM: res={resolution}m, method={method}")

    # Use first returns if available, otherwise all points
    if pc.return_number is not None:
        try:
            first_returns = pc.get_first_returns()
            points = first_returns.xyz
        except Exception:
            points = pc.xyz
    else:
        points = pc.xyz

    # For DSM, use the highest point in each cell (maximum)
    return _points_to_raster_max(
        points, resolution,
        name="DSM", epsg=pc.crs_epsg
    )


def generate_chm(dtm: RasterLayer, dsm: RasterLayer,
                 name: str = "CHM") -> RasterLayer:
    """
    Generates a CHM (Canopy Height Model) = DSM - DTM.
    """
    logger.info("Generating CHM (DSM - DTM)")

    dtm_data = dtm.get_band(0)
    dsm_data = dsm.get_band(0)

    # Verify compatible dimensions
    if dtm_data.shape != dsm_data.shape:
        # Resample to the smaller one
        min_rows = min(dtm_data.shape[0], dsm_data.shape[0])
        min_cols = min(dtm_data.shape[1], dsm_data.shape[1])
        dtm_data = dtm_data[:min_rows, :min_cols]
        dsm_data = dsm_data[:min_rows, :min_cols]
        logger.warning(f"Cropping to {min_cols}x{min_rows} px")

    # Calculate difference
    chm = dsm_data - dtm_data

    # Negative values → 0 (artifacts)
    chm[chm < 0] = 0

    # Nodata where either is nodata
    nodata_mask = (dtm_data == dtm.nodata) | (dsm_data == dsm.nodata)
    chm[nodata_mask] = DEFAULT_NODATA

    result = RasterLayer.from_array(
        chm, dtm.bounds, epsg=dtm.crs_epsg,
        nodata=DEFAULT_NODATA, name=name
    )

    stats = result.statistics()
    logger.info(
        f"CHM generated: range {stats.get('min', 0):.1f} - "
        f"{stats.get('max', 0):.1f} m"
    )
    return result


def _points_to_raster(points: np.ndarray, resolution: float,
                       method: str, power: float,
                       name: str = "raster",
                       epsg: int = None) -> RasterLayer:
    """Interpolates points to a regular grid."""
    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2]

    # Create grid
    xmin, xmax = x.min(), x.max()
    ymin, ymax = y.min(), y.max()

    cols = int(np.ceil((xmax - xmin) / resolution))
    rows = int(np.ceil((ymax - ymin) / resolution))

    if cols <= 0 or rows <= 0:
        raise ValueError("Cloud extent is too small.")

    logger.info(f"Grid: {cols}x{rows} cells ({resolution}m/px)")

    xi = xmin + resolution / 2 + np.arange(cols) * resolution
    yi = ymax - resolution / 2 - np.arange(rows) * resolution
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
        f"{name} generated: {cols}x{rows}px | "
        f"Z: {stats.get('min', 0):.1f} - {stats.get('max', 0):.1f} m"
    )
    return result


def _points_to_raster_max(points: np.ndarray, resolution: float,
                            name: str = "raster",
                            epsg: int = None) -> RasterLayer:
    """
    Rasterizes points using the maximum Z value in each cell.
    For DSM (surface, highest point wins).
    """
    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2]

    xmin, xmax = x.min(), x.max()
    ymin, ymax = y.min(), y.max()

    cols = int(np.ceil((xmax - xmin) / resolution))
    rows = int(np.ceil((ymax - ymin) / resolution))

    if cols <= 0 or rows <= 0:
        raise ValueError("Extent too small.")

    grid_z = np.full((rows, cols), DEFAULT_NODATA, dtype=np.float32)

    # Assign each point to its cell
    col_idx = np.clip(((x - xmin) / resolution).astype(int), 0, cols - 1)
    row_idx = np.clip(((ymax - y) / resolution).astype(int), 0, rows - 1)

    # Vectorized max-per-cell using a -inf sentinel, then restore nodata
    temp = np.full((rows, cols), -np.inf, dtype=np.float32)
    np.maximum.at(temp, (row_idx, col_idx), z.astype(np.float32))
    grid_z = np.where(np.isfinite(temp), temp, DEFAULT_NODATA).astype(np.float32)

    # Fill gaps with nearest-valid-cell using EDT (O(N) vs KDTree O(N log N))
    nodata_mask = grid_z == DEFAULT_NODATA
    if nodata_mask.any() and not nodata_mask.all():
        _, nearest = distance_transform_edt(nodata_mask, return_indices=True)
        grid_z[nodata_mask] = grid_z[nearest[0][nodata_mask], nearest[1][nodata_mask]]

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

    # Avoid division by 0
    distances = np.maximum(distances, 1e-10)

    weights = 1.0 / (distances ** power)
    weight_sum = weights.sum(axis=1)

    z_values = z[indices]
    grid_z = (z_values * weights).sum(axis=1) / weight_sum

    return grid_z.reshape(xx.shape)
