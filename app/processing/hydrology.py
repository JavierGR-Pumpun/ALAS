"""
ALAS — Hydrology
Hydrological analysis: basins, flow, drainage network, ponding.
"""

import numpy as np
import tempfile
import os
from typing import Optional, Tuple

# Compatibility patch for NumPy 2.x+: np.in1d was removed, use np.isin.
if not hasattr(np, "in1d"):
    def _in1d(ar1, ar2, assume_unique=False, invert=False):
        return np.isin(ar1, ar2, invert=invert)
    np.in1d = _in1d

from app.core.raster_layer import RasterLayer
from app.config import DEFAULT_NODATA, DEFAULT_FLOW_ACC_THRESHOLD
from app.logger import get_logger

logger = get_logger("processing.hydrology")


# ------------------------------------------------------------------
# Public functions
# ------------------------------------------------------------------

def condition_dem(dtm: RasterLayer) -> RasterLayer:
    """
    Conditions the DTM for hydrological analysis:
    filling pits, depressions, and resolving flat areas.

    Returns:
        RasterLayer with conditioned DTM.
    """
    logger.info("Conditioning DTM for hydrology...")

    grid, path = _get_grid_and_path(dtm)
    dem = grid.read_raster(path)

    inflated = _condition_raw(grid, dem)

    result_arr = np.array(inflated, dtype=np.float32)
    result_arr[np.isnan(result_arr)] = DEFAULT_NODATA

    result = _build_result(result_arr, dtm, name="DTM_conditioned")
    logger.info("DTM conditioned successfully.")
    return result


def flow_direction(dtm: RasterLayer,
                   conditioned: Optional[RasterLayer] = None) -> RasterLayer:
    """
    Calculates flow direction (D8).

    Args:
        dtm: Original or already conditioned DTM.
        conditioned: If an already conditioned DTM is passed, it is used directly
                     to avoid reprocessing.

    Returns:
        RasterLayer with flow direction.
    """
    logger.info("Calculating flow direction (D8)...")

    grid, dem = _prepare_dem(dtm, conditioned)
    fdir = grid.flowdir(dem)

    fdir_arr = np.array(fdir, dtype=np.float32)
    fdir_arr[np.isnan(fdir_arr)] = DEFAULT_NODATA

    logger.info("Flow direction calculated.")
    return _build_result(fdir_arr, dtm, name="Flow_direction")


def flow_accumulation(dtm: RasterLayer,
                      conditioned: Optional[RasterLayer] = None) -> RasterLayer:
    """
    Calculates flow accumulation.

    Args:
        dtm: Original DTM.
        conditioned: Already conditioned DTM (optional, avoids reprocessing).

    Returns:
        RasterLayer with flow accumulation.
    """
    logger.info("Calculating flow accumulation...")

    grid, dem = _prepare_dem(dtm, conditioned)
    fdir = grid.flowdir(dem)
    acc = grid.accumulation(fdir)

    acc_arr = np.array(acc, dtype=np.float32)
    acc_arr[np.isnan(acc_arr)] = DEFAULT_NODATA

    logger.info(f"Maximum accumulation: {np.nanmax(acc_arr):.0f} cells")
    return _build_result(acc_arr, dtm, name="Flow_accumulation")


def delineate_watershed(dtm: RasterLayer,
                         pour_point: Tuple[float, float],
                         snap_threshold: int = 100,
                         conditioned: Optional[RasterLayer] = None) -> RasterLayer:
    """
    Delineates a watershed from a pour point.

    Args:
        dtm: Original DTM.
        pour_point: (x, y) in raster coordinates (DTM reference system).
        snap_threshold: Minimum accumulation threshold to snap the pour point.
        conditioned: Already conditioned DTM (optional).

    Returns:
        RasterLayer with watershed mask (1 = basin, 0/nodata = outside).
    """
    logger.info(
        f"Delineating watershed from ({pour_point[0]:.1f}, {pour_point[1]:.1f})"
    )

    grid, dem = _prepare_dem(dtm, conditioned)
    fdir = grid.flowdir(dem)
    acc = grid.accumulation(fdir)

    # snap_to_mask expects an array of shape (N, 2) with (x, y) pairs
    xy = np.array([[pour_point[0], pour_point[1]]])
    snapped = grid.snap_to_mask(acc > snap_threshold, xy)
    x_snap, y_snap = float(snapped[0, 0]), float(snapped[0, 1])

    logger.info(f"Point snapped to high accumulation: ({x_snap:.1f}, {y_snap:.1f})")

    catch = grid.catchment(x=x_snap, y=y_snap, fdir=fdir, xytype="coordinate")
    catch_arr = np.array(catch, dtype=np.float32)
    catch_arr[np.isnan(catch_arr)] = DEFAULT_NODATA

    area_cells = int(np.sum(catch_arr == 1))
    if dtm.resolution and area_cells > 0:
        area_m2 = area_cells * dtm.resolution[0] * dtm.resolution[1]
        logger.info(f"Basin: {area_cells} cells ({area_m2 / 10_000:.2f} ha)")

    return _build_result(catch_arr, dtm, name="Watershed")


def extract_drainage_network(dtm: RasterLayer,
                              threshold: Optional[int] = None,
                              conditioned: Optional[RasterLayer] = None) -> dict:
    """
    Extracts drainage network as vector geometries (GeoJSON-like).

    Args:
        dtm: Original DTM.
        threshold: Accumulation threshold to define channels.
        conditioned: Already conditioned DTM (optional).

    Returns:
        Dictionary with FeatureCollection of network segments.
    """
    threshold = threshold or DEFAULT_FLOW_ACC_THRESHOLD
    logger.info(f"Extracting drainage network (threshold={threshold})...")

    grid, dem = _prepare_dem(dtm, conditioned)
    fdir = grid.flowdir(dem)
    acc = grid.accumulation(fdir)

    branches = grid.extract_river_network(fdir, acc > threshold)

    n_features = len(branches.get("features", []))
    logger.info(f"Drainage network: {n_features} segments extracted.")
    return branches


def simulate_rainfall(dtm: RasterLayer,
                      rainfall_mm_h: float,
                      conditioned: Optional[RasterLayer] = None) -> RasterLayer:
    """
    Simulates rainfall and computes accumulated runoff volume per cell.

    Each cell contributes its area multiplied by the rainfall intensity to the
    downstream flow accumulation, resulting in a runoff volume map (m³/h).

    Args:
        dtm: Original DTM.
        rainfall_mm_h: Rainfall intensity in mm/h.
        conditioned: Pre-conditioned DTM (optional, avoids reprocessing).

    Returns:
        RasterLayer with accumulated runoff volume in m³/h per cell.
    """
    logger.info(f"Simulating rainfall at {rainfall_mm_h} mm/h...")

    grid, dem = _prepare_dem(dtm, conditioned)
    fdir = grid.flowdir(dem)

    cell_area_m2 = 1.0
    if dtm.resolution:
        cell_area_m2 = float(dtm.resolution[0]) * float(dtm.resolution[1])

    rainfall_m_h = rainfall_mm_h / 1000.0
    weight_per_cell = rainfall_m_h * cell_area_m2

    weights = np.full_like(fdir, weight_per_cell, dtype=np.float64)
    acc = grid.accumulation(fdir, weights=weights)

    acc_arr = np.array(acc, dtype=np.float32)
    acc_arr[np.isnan(acc_arr)] = DEFAULT_NODATA

    valid = acc_arr[acc_arr != DEFAULT_NODATA]
    if valid.size > 0:
        logger.info(
            f"Rainfall simulation complete. Max runoff: {float(np.max(valid)):.4f} m³/h, "
            f"cell area: {cell_area_m2:.2f} m²"
        )

    result = _build_result(acc_arr, dtm, name=f"Runoff_{rainfall_mm_h}mmh")
    result.rainfall_mm_h = rainfall_mm_h
    result.rainfall_cell_area_m2 = cell_area_m2
    return result


def simulate_flood(dtm: RasterLayer, water_height: float) -> RasterLayer:
    """
    Simulates a flood scenario by flooding all terrain cells whose elevation
    is below a given absolute water level.

    Args:
        dtm: Original DTM raster layer.
        water_height: Absolute water surface elevation in the same units as the DTM.

    Returns:
        RasterLayer where each cell value is the flood depth (water_height - elevation)
        for inundated cells, and 0 for cells above the water level.
    """
    logger.info(f"Simulating flood at water level {water_height} m...")

    arr = np.asarray(dtm.data, dtype=np.float32)
    if arr.ndim > 2:
        arr = arr[0]

    nodata_mask = np.isnan(arr) | (arr == DEFAULT_NODATA)

    depth = np.zeros_like(arr, dtype=np.float32)
    flooded = (~nodata_mask) & (arr < water_height)
    depth[flooded] = water_height - arr[flooded]
    depth[nodata_mask] = DEFAULT_NODATA

    flooded_cells = int(np.sum(flooded))
    if dtm.resolution and flooded_cells > 0:
        area_m2 = flooded_cells * dtm.resolution[0] * dtm.resolution[1]
        logger.info(
            f"Flood simulation complete. Inundated: {flooded_cells} cells "
            f"({area_m2 / 10_000:.2f} ha), max depth: {float(np.max(depth[flooded])):.2f} m"
        )
    else:
        logger.info("Flood simulation complete. No cells inundated at this water level.")

    result = _build_result(depth, dtm, name=f"Flood_{water_height:.1f}m")
    result.flood_water_height = water_height
    result.flood_terrain_arr = arr
    return result


def detect_ponding_zones(dtm: RasterLayer,
                          threshold: float = 0.1) -> RasterLayer:
    """
    Detects zones with potential ponding.

    The difference between the filled DTM and the original indicates the depth
    of depressions. Uses the DTM *without* resolve_flats to preserve the
    actual fill magnitude.

    Args:
        dtm: Original DTM (unconditioned).
        threshold: Minimum depth (meters) to consider ponding.

    Returns:
        RasterLayer with potential ponding depth.
    """
    logger.info("Detecting ponding zones...")

    grid, path = _get_grid_and_path(dtm)
    dem = grid.read_raster(path)

    # Original DTM as array
    original = np.array(dem, dtype=np.float32)

    # Only fill_pits + fill_depressions — NO resolve_flats, to preserve
    # the actual magnitude of filled depressions.
    pit_filled = grid.fill_pits(dem)
    filled = np.array(grid.fill_depressions(pit_filled), dtype=np.float32)

    # Ponding depth
    depth = filled - original

    # Apply nodata and threshold consistently (>= threshold on both sides)
    nodata_mask = np.isnan(original) | (original == DEFAULT_NODATA)
    depth[nodata_mask] = DEFAULT_NODATA
    depth[~nodata_mask & (depth < threshold)] = 0.0

    result = _build_result(depth, dtm, name="Ponding")

    ponding_cells = int(np.sum(depth[~nodata_mask] >= threshold))
    if dtm.resolution and ponding_cells > 0:
        area_m2 = ponding_cells * dtm.resolution[0] * dtm.resolution[1]
        logger.info(f"Ponding zones: {ponding_cells} cells ({area_m2:.0f} m²)")
    else:
        logger.info("No significant ponding zones detected.")

    return result


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _get_grid_and_path(dtm: RasterLayer):
    """
    Gets the pysheds Grid and raster path.

    pysheds works internally with GeoTIFF files.
    If the RasterLayer has no disk path, a temporary one is written.
    """
    from pysheds.grid import Grid

    if dtm.file_path and os.path.isfile(dtm.file_path):
        return Grid.from_raster(dtm.file_path), dtm.file_path

    # Write to temporary file
    tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    tmp.close()
    dtm.to_geotiff(tmp.name)
    logger.debug(f"DTM exported to temp: {tmp.name}")
    return Grid.from_raster(tmp.name), tmp.name


def _condition_raw(grid, dem):
    """
    Applies the complete conditioning pipeline on a pysheds dem object.

    Returns:
        conditioned dem (pit_filled → flooded → inflated).
    """
    pit_filled = grid.fill_pits(dem)
    flooded = grid.fill_depressions(pit_filled)
    inflated = grid.resolve_flats(flooded)
    return inflated


def _prepare_dem(dtm: RasterLayer, conditioned: Optional[RasterLayer] = None):
    """
    Prepares the DTM for hydrological analysis.

    If an already processed `conditioned` is passed, it is used directly
    avoiding recalculating conditioning. Otherwise, `dtm` is conditioned.

    Returns:
        (grid, conditioned_dem) ready for flowdir/accumulation calculation.
    """
    from pysheds.grid import Grid

    source = conditioned if conditioned is not None else dtm
    grid, path = _get_grid_and_path(source)
    dem = grid.read_raster(path)

    # Clean up temp file if one was written (source has no valid on-disk path)
    if not (source.file_path and os.path.isfile(source.file_path)):
        try:
            os.unlink(path)
        except OSError:
            logger.debug(f"Could not remove temp file: {path}")

    if conditioned is None:
        dem = _condition_raw(grid, dem)

    return grid, dem


def _build_result(arr: np.ndarray, dtm: RasterLayer, name: str) -> RasterLayer:
    """
    Builds a result RasterLayer copying the georeferencing from the source DTM.
    """
    result = RasterLayer.from_array(
        arr, dtm.bounds, epsg=dtm.crs_epsg,
        nodata=DEFAULT_NODATA, name=name
    )
    result.transform = dtm.transform
    result.crs = dtm.crs
    return result