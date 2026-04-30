"""
ALAS — Hydrology
Análisis hidrológico: cuencas, flujo, red de drenaje, encharcamiento.
"""

import numpy as np
from typing import Optional, Tuple

from app.core.raster_layer import RasterLayer
from app.config import DEFAULT_NODATA, DEFAULT_FLOW_ACC_THRESHOLD
from app.logger import get_logger

logger = get_logger("processing.hydrology")


def condition_dem(dtm: RasterLayer) -> RasterLayer:
    """
    Acondiciona el MDT para análisis hidrológico:
    relleno de pozos, depresiones y resolución de zonas planas.
    """
    logger.info("Acondicionando MDT para hidrología...")
    from pysheds.grid import Grid

    grid, path = _get_grid_and_path(dtm)
    dem = grid.read_raster(path)

    # Fill pits
    pit_filled = grid.fill_pits(dem)
    # Fill depressions
    flooded = grid.fill_depressions(pit_filled)
    # Resolve flats
    inflated = grid.resolve_flats(flooded)

    result_arr = np.array(inflated, dtype=np.float32)
    result_arr[np.isnan(result_arr)] = DEFAULT_NODATA

    result = RasterLayer.from_array(
        result_arr, dtm.bounds, epsg=dtm.crs_epsg,
        nodata=DEFAULT_NODATA, name="MDT_condicionado"
    )
    result.transform = dtm.transform
    result.crs = dtm.crs

    logger.info("MDT acondicionado para hidrología")
    return result


def flow_direction(dtm: RasterLayer) -> RasterLayer:
    """Calcula la dirección de flujo (D8)."""
    logger.info("Calculando dirección de flujo (D8)...")
    from pysheds.grid import Grid

    grid, dem = _prepare_dem(dtm)

    fdir = grid.flowdir(dem)
    fdir_arr = np.array(fdir, dtype=np.float32)
    fdir_arr[np.isnan(fdir_arr)] = DEFAULT_NODATA

    result = RasterLayer.from_array(
        fdir_arr, dtm.bounds, epsg=dtm.crs_epsg,
        nodata=DEFAULT_NODATA, name="Dirección_flujo"
    )
    result.transform = dtm.transform
    result.crs = dtm.crs
    return result


def flow_accumulation(dtm: RasterLayer) -> RasterLayer:
    """Calcula la acumulación de flujo."""
    logger.info("Calculando acumulación de flujo...")
    from pysheds.grid import Grid

    grid, dem = _prepare_dem(dtm)

    fdir = grid.flowdir(dem)
    acc = grid.accumulation(fdir)
    acc_arr = np.array(acc, dtype=np.float32)
    acc_arr[np.isnan(acc_arr)] = DEFAULT_NODATA

    result = RasterLayer.from_array(
        acc_arr, dtm.bounds, epsg=dtm.crs_epsg,
        nodata=DEFAULT_NODATA, name="Acumulación_flujo"
    )
    result.transform = dtm.transform
    result.crs = dtm.crs

    logger.info(f"Acumulación máxima: {np.nanmax(acc_arr):.0f} celdas")
    return result


def delineate_watershed(dtm: RasterLayer,
                         pour_point: Tuple[float, float]) -> RasterLayer:
    """
    Delimita una cuenca vertiente desde un punto de vertido.
    pour_point: (x, y) en coordenadas del raster.
    """
    logger.info(f"Delimitando cuenca desde ({pour_point[0]:.1f}, {pour_point[1]:.1f})")
    from pysheds.grid import Grid

    grid, dem = _prepare_dem(dtm)
    fdir = grid.flowdir(dem)
    acc = grid.accumulation(fdir)

    # Snap pour point to high accumulation
    x_snap, y_snap = grid.snap_to_mask(acc > 100, (pour_point[0], pour_point[1]))

    # Delineate catchment
    catch = grid.catchment(x=x_snap, y=y_snap, fdir=fdir, xytype='coordinate')
    catch_arr = np.array(catch, dtype=np.float32)
    catch_arr[np.isnan(catch_arr)] = DEFAULT_NODATA

    # Conteo de celdas
    area_cells = np.sum(catch_arr == 1) if not np.all(np.isnan(catch_arr)) else 0
    if dtm.resolution:
        area_m2 = area_cells * dtm.resolution[0] * dtm.resolution[1]
        logger.info(f"Cuenca: {area_cells} celdas ({area_m2/10000:.2f} ha)")

    result = RasterLayer.from_array(
        catch_arr, dtm.bounds, epsg=dtm.crs_epsg,
        nodata=DEFAULT_NODATA, name="Cuenca"
    )
    result.transform = dtm.transform
    result.crs = dtm.crs
    return result


def extract_drainage_network(dtm: RasterLayer,
                              threshold: int = None) -> dict:
    """
    Extrae la red de drenaje como geometrías vectoriales.
    Devuelve un diccionario con geometrías GeoJSON-like.
    """
    threshold = threshold or DEFAULT_FLOW_ACC_THRESHOLD
    logger.info(f"Extrayendo red de drenaje (umbral={threshold})...")
    from pysheds.grid import Grid

    grid, dem = _prepare_dem(dtm)
    fdir = grid.flowdir(dem)
    acc = grid.accumulation(fdir)

    # Extraer red
    branches = grid.extract_river_network(fdir, acc > threshold)

    logger.info(f"Red de drenaje: {len(branches.get('features', []))} segmentos")
    return branches


def detect_ponding_zones(dtm: RasterLayer,
                          threshold: float = 0.1) -> RasterLayer:
    """
    Detecta zonas con potencial de encharcamiento.
    Compara el MDT original con el rellenado — la diferencia indica depresiones.
    """
    logger.info("Detectando zonas de encharcamiento...")
    from pysheds.grid import Grid

    grid, dem = _prepare_dem(dtm)

    original = dtm.get_band(0).copy().astype(np.float32)
    filled = np.array(dem, dtype=np.float32)

    # Diferencia: zonas donde se rellenó
    depth = filled - original
    depth[depth < threshold] = 0
    depth[np.isnan(original)] = DEFAULT_NODATA

    result = RasterLayer.from_array(
        depth, dtm.bounds, epsg=dtm.crs_epsg,
        nodata=DEFAULT_NODATA, name="Encharcamiento"
    )
    result.transform = dtm.transform
    result.crs = dtm.crs

    ponding_area = np.sum(depth > threshold)
    if dtm.resolution and ponding_area > 0:
        area_m2 = ponding_area * dtm.resolution[0] * dtm.resolution[1]
        logger.info(f"Zonas de encharcamiento: {area_m2:.0f} m²")

    return result


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _get_grid_and_path(dtm: RasterLayer):
    """Obtiene el Grid de pysheds y la ruta al raster."""
    from pysheds.grid import Grid
    import tempfile

    # pysheds trabaja mejor con archivos
    if dtm.file_path:
        return Grid.from_raster(dtm.file_path), dtm.file_path

    # Si no hay archivo, guardar temporalmente
    tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    tmp.close()
    dtm.to_geotiff(tmp.name)
    return Grid.from_raster(tmp.name), tmp.name


def _prepare_dem(dtm: RasterLayer):
    """Prepara el MDT para análisis hidrológico."""
    from pysheds.grid import Grid

    grid, path = _get_grid_and_path(dtm)
    dem = grid.read_raster(path)

    # Acondicionar
    pit_filled = grid.fill_pits(dem)
    flooded = grid.fill_depressions(pit_filled)
    inflated = grid.resolve_flats(flooded)

    return grid, inflated
