"""
ALAS — Geomorphology
Geomorphological analysis: slope, aspect, curvature, roughness, hillshade.
"""

import numpy as np
from typing import Optional

from app.core.raster_layer import RasterLayer
from app.config import (
    DEFAULT_NODATA, DEFAULT_HILLSHADE_AZIMUTH, DEFAULT_HILLSHADE_ALTITUDE,
    DEFAULT_SLOPE_CMAP, DEFAULT_ASPECT_CMAP, DEFAULT_CURVATURE_CMAP,
    DEFAULT_HILLSHADE_CMAP
)
from app.logger import get_logger

logger = get_logger("processing.geomorphology")


def calculate_slope(dtm: RasterLayer) -> RasterLayer:
    """Calculates slope in degrees."""
    logger.info("Calculating slope...")
    import richdem as rd

    arr = dtm.get_band(0).copy()
    arr[arr == dtm.nodata] = np.nan

    rd_dem = rd.rdarray(arr, no_data=np.nan)
    if dtm.resolution:
        rd_dem.geotransform = (0, dtm.resolution[0], 0, 0, 0, -dtm.resolution[1])

    slope = rd.TerrainAttribute(rd_dem, attrib='slope_degrees')
    slope_arr = np.array(slope, dtype=np.float32)
    slope_arr[np.isnan(slope_arr)] = DEFAULT_NODATA

    result = RasterLayer.from_array(
        slope_arr, dtm.bounds, epsg=dtm.crs_epsg,
        nodata=DEFAULT_NODATA, name="Slope"
    )
    result.transform = dtm.transform
    result.crs = dtm.crs

    stats = result.statistics()
    logger.info(f"Slope: {stats.get('min', 0):.1f}° - {stats.get('max', 0):.1f}°")
    return result


def calculate_aspect(dtm: RasterLayer) -> RasterLayer:
    """Calculates aspect in degrees (0-360)."""
    logger.info("Calculating aspect...")
    import richdem as rd

    arr = dtm.get_band(0).copy()
    arr[arr == dtm.nodata] = np.nan

    rd_dem = rd.rdarray(arr, no_data=np.nan)
    if dtm.resolution:
        rd_dem.geotransform = (0, dtm.resolution[0], 0, 0, 0, -dtm.resolution[1])

    aspect = rd.TerrainAttribute(rd_dem, attrib='aspect')
    aspect_arr = np.array(aspect, dtype=np.float32)
    aspect_arr[np.isnan(aspect_arr)] = DEFAULT_NODATA

    result = RasterLayer.from_array(
        aspect_arr, dtm.bounds, epsg=dtm.crs_epsg,
        nodata=DEFAULT_NODATA, name="Aspect"
    )
    result.transform = dtm.transform
    result.crs = dtm.crs
    return result


def calculate_curvature(dtm: RasterLayer,
                         curvature_type: str = "profile") -> RasterLayer:
    """
    Calculates terrain curvature.
    curvature_type: 'profile', 'planform', or 'total'
    """
    logger.info(f"Calculating curvature ({curvature_type})...")
    import richdem as rd

    arr = dtm.get_band(0).copy()
    arr[arr == dtm.nodata] = np.nan

    rd_dem = rd.rdarray(arr, no_data=np.nan)
    if dtm.resolution:
        rd_dem.geotransform = (0, dtm.resolution[0], 0, 0, 0, -dtm.resolution[1])

    attrib_map = {
        "profile": "profile_curvature",
        "planform": "planform_curvature",
        "total": "curvature",
    }
    attrib = attrib_map.get(curvature_type, "curvature")

    curv = rd.TerrainAttribute(rd_dem, attrib=attrib)
    curv_arr = np.array(curv, dtype=np.float32)
    curv_arr[np.isnan(curv_arr)] = DEFAULT_NODATA

    result = RasterLayer.from_array(
        curv_arr, dtm.bounds, epsg=dtm.crs_epsg,
        nodata=DEFAULT_NODATA, name=f"Curvature_{curvature_type}"
    )
    result.transform = dtm.transform
    result.crs = dtm.crs
    return result


def calculate_roughness(dtm: RasterLayer, window: int = 3) -> RasterLayer:
    """
    Calculates terrain roughness index (TRI).
    TRI = mean difference between a cell and its neighbors.
    """
    logger.info(f"Calculating roughness (window={window})...")
    from scipy.ndimage import generic_filter

    arr = dtm.get_band(0).copy().astype(np.float64)
    arr[arr == dtm.nodata] = np.nan

    def tri_func(values):
        center = values[len(values) // 2]
        if np.isnan(center):
            return np.nan
        neighbors = np.delete(values, len(values) // 2)
        valid = neighbors[~np.isnan(neighbors)]
        if len(valid) < 1:
            return 0.0
        return np.sqrt(np.sum((valid - center) ** 2))

    roughness = generic_filter(arr, tri_func, size=window)
    roughness = roughness.astype(np.float32)
    roughness[np.isnan(roughness)] = DEFAULT_NODATA

    result = RasterLayer.from_array(
        roughness, dtm.bounds, epsg=dtm.crs_epsg,
        nodata=DEFAULT_NODATA, name="Roughness"
    )
    result.transform = dtm.transform
    result.crs = dtm.crs
    return result


def calculate_hillshade(dtm: RasterLayer,
                         azimuth: float = None,
                         altitude: float = None) -> RasterLayer:
    """
    Calculates relief hillshade.
    azimuth: sun direction (degrees, 0=North, 315=default)
    altitude: sun height above horizon (degrees)
    """
    azimuth = DEFAULT_HILLSHADE_AZIMUTH if azimuth is None else azimuth
    altitude = DEFAULT_HILLSHADE_ALTITUDE if altitude is None else altitude

    logger.info(f"Calculating hillshade (azimuth={azimuth}°, altitude={altitude}°)")

    arr = dtm.get_band(0).copy().astype(np.float64)
    arr[arr == dtm.nodata] = np.nan

    res = dtm.resolution[0] if dtm.resolution else 1.0

    # Calculate gradients
    dy, dx = np.gradient(arr, res)

    # Hillshade formula
    az_rad = np.radians(360 - azimuth + 90)
    alt_rad = np.radians(altitude)

    slope_rad = np.arctan(np.sqrt(dx**2 + dy**2))
    aspect_rad = np.arctan2(-dy, dx)

    hillshade = (
        np.sin(alt_rad) * np.cos(slope_rad) +
        np.cos(alt_rad) * np.sin(slope_rad) *
        np.cos(az_rad - aspect_rad)
    )

    # Normalize to 0-255
    hillshade = np.clip(hillshade * 255, 0, 255).astype(np.float32)
    hillshade[np.isnan(arr)] = DEFAULT_NODATA

    result = RasterLayer.from_array(
        hillshade, dtm.bounds, epsg=dtm.crs_epsg,
        nodata=DEFAULT_NODATA, name="Hillshade"
    )
    result.transform = dtm.transform
    result.crs = dtm.crs
    return result


def morphometric_classification(dtm: RasterLayer) -> RasterLayer:
    """
    Morphometric classification: ridges, valleys, and plains
    based on profile curvature and planform curvature.
    Values: 1=ridge, 2=valley, 3=plain
    """
    logger.info("Morphometric classification...")
    import richdem as rd

    arr = dtm.get_band(0).copy()
    arr[arr == dtm.nodata] = np.nan

    rd_dem = rd.rdarray(arr, no_data=np.nan)
    if dtm.resolution:
        rd_dem.geotransform = (0, dtm.resolution[0], 0, 0, 0, -dtm.resolution[1])

    profile = np.array(rd.TerrainAttribute(rd_dem, attrib='profile_curvature'), dtype=np.float32)
    planform = np.array(rd.TerrainAttribute(rd_dem, attrib='planform_curvature'), dtype=np.float32)

    morph = np.full_like(profile, 3, dtype=np.float32)  # Default: plain

    # Ridges: convex (negative profile curvature) and divergent (negative planform)
    ridges = (profile < -0.01) & (planform < -0.01)
    morph[ridges] = 1

    # Valleys: concave (positive profile curvature) and convergent (positive planform)
    valleys = (profile > 0.01) & (planform > 0.01)
    morph[valleys] = 2

    morph[np.isnan(arr)] = DEFAULT_NODATA

    result = RasterLayer.from_array(
        morph, dtm.bounds, epsg=dtm.crs_epsg,
        nodata=DEFAULT_NODATA, name="Morphometry"
    )
    result.transform = dtm.transform
    result.crs = dtm.crs
    return result
