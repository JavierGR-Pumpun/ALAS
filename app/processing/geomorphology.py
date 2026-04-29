"""
ALAS — Geomorphology
Análisis geomorfológico: pendiente, orientación, curvatura, rugosidad, sombreado.
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
    """Calcula la pendiente en grados."""
    logger.info("Calculando pendiente...")
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
        nodata=DEFAULT_NODATA, name="Pendiente"
    )
    result.transform = dtm.transform
    result.crs = dtm.crs

    stats = result.statistics()
    logger.info(f"Pendiente: {stats.get('min', 0):.1f}° - {stats.get('max', 0):.1f}°")
    return result


def calculate_aspect(dtm: RasterLayer) -> RasterLayer:
    """Calcula la orientación (aspecto) en grados (0-360)."""
    logger.info("Calculando orientación...")
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
        nodata=DEFAULT_NODATA, name="Orientación"
    )
    result.transform = dtm.transform
    result.crs = dtm.crs
    return result


def calculate_curvature(dtm: RasterLayer,
                         curvature_type: str = "profile") -> RasterLayer:
    """
    Calcula la curvatura del terreno.
    curvature_type: 'profile', 'planform', o 'total'
    """
    logger.info(f"Calculando curvatura ({curvature_type})...")
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
        nodata=DEFAULT_NODATA, name=f"Curvatura_{curvature_type}"
    )
    result.transform = dtm.transform
    result.crs = dtm.crs
    return result


def calculate_roughness(dtm: RasterLayer, window: int = 3) -> RasterLayer:
    """
    Calcula el índice de rugosidad del terreno (TRI).
    TRI = diferencia media entre una celda y sus vecinas.
    """
    logger.info(f"Calculando rugosidad (ventana={window})...")
    from scipy.ndimage import generic_filter

    arr = dtm.get_band(0).copy().astype(np.float64)
    arr[arr == dtm.nodata] = np.nan

    def tri_func(values):
        center = values[len(values) // 2]
        if np.isnan(center):
            return np.nan
        valid = values[~np.isnan(values)]
        if len(valid) < 2:
            return 0.0
        return np.sqrt(np.mean((valid - center) ** 2))

    roughness = generic_filter(arr, tri_func, size=window)
    roughness = roughness.astype(np.float32)
    roughness[np.isnan(roughness)] = DEFAULT_NODATA

    result = RasterLayer.from_array(
        roughness, dtm.bounds, epsg=dtm.crs_epsg,
        nodata=DEFAULT_NODATA, name="Rugosidad"
    )
    result.transform = dtm.transform
    result.crs = dtm.crs
    return result


def calculate_hillshade(dtm: RasterLayer,
                         azimuth: float = None,
                         altitude: float = None) -> RasterLayer:
    """
    Calcula el sombreado del relieve (hillshade).
    azimuth: dirección del sol (grados, 0=Norte, 315=default)
    altitude: altura del sol sobre el horizonte (grados)
    """
    azimuth = azimuth or DEFAULT_HILLSHADE_AZIMUTH
    altitude = altitude or DEFAULT_HILLSHADE_ALTITUDE

    logger.info(f"Calculando hillshade (azimut={azimuth}°, altitud={altitude}°)")

    arr = dtm.get_band(0).copy().astype(np.float64)
    arr[arr == dtm.nodata] = np.nan

    res = dtm.resolution[0] if dtm.resolution else 1.0

    # Calcular gradientes
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

    # Normalizar a 0-255
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
    Clasificación morfométrica: crestas, vaguadas y llanuras
    basada en curvatura del perfil y curvatura planimétrica.
    Valores: 1=cresta, 2=vaguada, 3=llanura
    """
    logger.info("Clasificación morfométrica...")
    import richdem as rd

    arr = dtm.get_band(0).copy()
    arr[arr == dtm.nodata] = np.nan

    rd_dem = rd.rdarray(arr, no_data=np.nan)
    if dtm.resolution:
        rd_dem.geotransform = (0, dtm.resolution[0], 0, 0, 0, -dtm.resolution[1])

    profile = np.array(rd.TerrainAttribute(rd_dem, attrib='profile_curvature'), dtype=np.float32)
    planform = np.array(rd.TerrainAttribute(rd_dem, attrib='planform_curvature'), dtype=np.float32)

    morph = np.full_like(profile, 3, dtype=np.float32)  # Default: llanura

    # Crestas: curvatura perfil positiva y planform negativa
    ridges = (profile > 0.01) & (planform < -0.01)
    morph[ridges] = 1

    # Vaguadas: curvatura perfil negativa y planform positiva
    valleys = (profile < -0.01) & (planform > 0.01)
    morph[valleys] = 2

    morph[np.isnan(arr)] = DEFAULT_NODATA

    result = RasterLayer.from_array(
        morph, dtm.bounds, epsg=dtm.crs_epsg,
        nodata=DEFAULT_NODATA, name="Morfometría"
    )
    result.transform = dtm.transform
    result.crs = dtm.crs
    return result
