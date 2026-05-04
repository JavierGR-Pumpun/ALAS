"""
ALAS — Hydrology
Análisis hidrológico: cuencas, flujo, red de drenaje, encharcamiento.
"""

import numpy as np
import tempfile
import os
from typing import Optional, Tuple

# Compatibility patch for NumPy 2.x+: np.in1d fue eliminado, usar np.isin.
if not hasattr(np, "in1d"):
    def _in1d(ar1, ar2, assume_unique=False, invert=False):
        return np.isin(ar1, ar2, invert=invert)
    np.in1d = _in1d

from app.core.raster_layer import RasterLayer
from app.config import DEFAULT_NODATA, DEFAULT_FLOW_ACC_THRESHOLD
from app.logger import get_logger

logger = get_logger("processing.hydrology")


# ------------------------------------------------------------------
# Funciones públicas
# ------------------------------------------------------------------

def condition_dem(dtm: RasterLayer) -> RasterLayer:
    """
    Acondiciona el MDT para análisis hidrológico:
    relleno de pozos, depresiones y resolución de zonas planas.

    Returns:
        RasterLayer con el MDT condicionado.
    """
    logger.info("Acondicionando MDT para hidrología...")

    grid, path = _get_grid_and_path(dtm)
    dem = grid.read_raster(path)

    inflated = _condition_raw(grid, dem)

    result_arr = np.array(inflated, dtype=np.float32)
    result_arr[np.isnan(result_arr)] = DEFAULT_NODATA

    result = _build_result(result_arr, dtm, name="MDT_condicionado")
    logger.info("MDT acondicionado correctamente.")
    return result


def flow_direction(dtm: RasterLayer,
                   conditioned: Optional[RasterLayer] = None) -> RasterLayer:
    """
    Calcula la dirección de flujo (D8).

    Args:
        dtm: MDT original o ya condicionado.
        conditioned: Si se pasa un MDT ya condicionado, se usa directamente
                     para evitar re-procesar.

    Returns:
        RasterLayer con la dirección de flujo.
    """
    logger.info("Calculando dirección de flujo (D8)...")

    grid, dem = _prepare_dem(dtm, conditioned)
    fdir = grid.flowdir(dem)

    fdir_arr = np.array(fdir, dtype=np.float32)
    fdir_arr[np.isnan(fdir_arr)] = DEFAULT_NODATA

    logger.info("Dirección de flujo calculada.")
    return _build_result(fdir_arr, dtm, name="Dirección_flujo")


def flow_accumulation(dtm: RasterLayer,
                      conditioned: Optional[RasterLayer] = None) -> RasterLayer:
    """
    Calcula la acumulación de flujo.

    Args:
        dtm: MDT original.
        conditioned: MDT ya condicionado (opcional, evita re-procesar).

    Returns:
        RasterLayer con la acumulación de flujo.
    """
    logger.info("Calculando acumulación de flujo...")

    grid, dem = _prepare_dem(dtm, conditioned)
    fdir = grid.flowdir(dem)
    acc = grid.accumulation(fdir)

    acc_arr = np.array(acc, dtype=np.float32)
    acc_arr[np.isnan(acc_arr)] = DEFAULT_NODATA

    logger.info(f"Acumulación máxima: {np.nanmax(acc_arr):.0f} celdas")
    return _build_result(acc_arr, dtm, name="Acumulación_flujo")


def delineate_watershed(dtm: RasterLayer,
                         pour_point: Tuple[float, float],
                         snap_threshold: int = 100,
                         conditioned: Optional[RasterLayer] = None) -> RasterLayer:
    """
    Delimita una cuenca vertiente desde un punto de vertido.

    Args:
        dtm: MDT original.
        pour_point: (x, y) en coordenadas del raster (sistema de referencia del MDT).
        snap_threshold: Umbral mínimo de acumulación al que ajustar el punto de vertido.
        conditioned: MDT ya condicionado (opcional).

    Returns:
        RasterLayer con la máscara de la cuenca (1 = cuenca, 0/nodata = fuera).
    """
    logger.info(
        f"Delimitando cuenca desde ({pour_point[0]:.1f}, {pour_point[1]:.1f})"
    )

    grid, dem = _prepare_dem(dtm, conditioned)
    fdir = grid.flowdir(dem)
    acc = grid.accumulation(fdir)

    # snap_to_mask espera un array de forma (N, 2) con pares (x, y)
    xy = np.array([[pour_point[0], pour_point[1]]])
    snapped = grid.snap_to_mask(acc > snap_threshold, xy)
    x_snap, y_snap = float(snapped[0, 0]), float(snapped[0, 1])

    logger.info(f"Punto ajustado a alta acumulación: ({x_snap:.1f}, {y_snap:.1f})")

    catch = grid.catchment(x=x_snap, y=y_snap, fdir=fdir, xytype="coordinate")
    catch_arr = np.array(catch, dtype=np.float32)
    catch_arr[np.isnan(catch_arr)] = DEFAULT_NODATA

    area_cells = int(np.sum(catch_arr == 1))
    if dtm.resolution and area_cells > 0:
        area_m2 = area_cells * dtm.resolution[0] * dtm.resolution[1]
        logger.info(f"Cuenca: {area_cells} celdas ({area_m2 / 10_000:.2f} ha)")

    return _build_result(catch_arr, dtm, name="Cuenca")


def extract_drainage_network(dtm: RasterLayer,
                              threshold: Optional[int] = None,
                              conditioned: Optional[RasterLayer] = None) -> dict:
    """
    Extrae la red de drenaje como geometrías vectoriales (GeoJSON-like).

    Args:
        dtm: MDT original.
        threshold: Umbral de acumulación para definir cauces.
        conditioned: MDT ya condicionado (opcional).

    Returns:
        Diccionario con FeatureCollection de segmentos de la red.
    """
    threshold = threshold or DEFAULT_FLOW_ACC_THRESHOLD
    logger.info(f"Extrayendo red de drenaje (umbral={threshold})...")

    grid, dem = _prepare_dem(dtm, conditioned)
    fdir = grid.flowdir(dem)
    acc = grid.accumulation(fdir)

    branches = grid.extract_river_network(fdir, acc > threshold)

    n_features = len(branches.get("features", []))
    logger.info(f"Red de drenaje: {n_features} segmentos extraídos.")
    return branches


def detect_ponding_zones(dtm: RasterLayer,
                          threshold: float = 0.1) -> RasterLayer:
    """
    Detecta zonas con potencial de encharcamiento.

    La diferencia entre el MDT rellenado y el original indica la profundidad
    de las depresiones. Se utiliza el MDT *sin* resolve_flats para conservar
    la magnitud real del relleno.

    Args:
        dtm: MDT original (sin acondicionar).
        threshold: Profundidad mínima (metros) para considerar encharcamiento.

    Returns:
        RasterLayer con la profundidad de encharcamiento potencial.
    """
    logger.info("Detectando zonas de encharcamiento...")

    grid, path = _get_grid_and_path(dtm)
    dem = grid.read_raster(path)

    # MDT original como array
    original = np.array(dem, dtype=np.float32)

    # Solo fill_pits + fill_depressions — NO resolve_flats, para preservar
    # la magnitud real de las depresiones rellenadas.
    pit_filled = grid.fill_pits(dem)
    filled = np.array(grid.fill_depressions(pit_filled), dtype=np.float32)

    # Profundidad de encharcamiento
    depth = filled - original

    # Aplicar nodata y umbral de forma consistente (>= threshold en ambos lados)
    nodata_mask = np.isnan(original) | (original == DEFAULT_NODATA)
    depth[nodata_mask] = DEFAULT_NODATA
    depth[~nodata_mask & (depth < threshold)] = 0.0

    result = _build_result(depth, dtm, name="Encharcamiento")

    ponding_cells = int(np.sum(depth[~nodata_mask] >= threshold))
    if dtm.resolution and ponding_cells > 0:
        area_m2 = ponding_cells * dtm.resolution[0] * dtm.resolution[1]
        logger.info(f"Zonas de encharcamiento: {ponding_cells} celdas ({area_m2:.0f} m²)")
    else:
        logger.info("No se detectaron zonas de encharcamiento significativas.")

    return result


# ------------------------------------------------------------------
# Helpers privados
# ------------------------------------------------------------------

def _get_grid_and_path(dtm: RasterLayer):
    """
    Obtiene el Grid de pysheds y la ruta al raster.

    pysheds trabaja internamente con archivos GeoTIFF.
    Si el RasterLayer no tiene ruta en disco, se escribe uno temporal.
    """
    from pysheds.grid import Grid

    if dtm.file_path and os.path.isfile(dtm.file_path):
        return Grid.from_raster(dtm.file_path), dtm.file_path

    # Escribir a archivo temporal
    tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    tmp.close()
    dtm.to_geotiff(tmp.name)
    logger.debug(f"MDT exportado a temporal: {tmp.name}")
    return Grid.from_raster(tmp.name), tmp.name


def _condition_raw(grid, dem):
    """
    Aplica el pipeline completo de acondicionamiento sobre un objeto dem de pysheds.

    Returns:
        dem acondicionado (pit_filled → flooded → inflated).
    """
    pit_filled = grid.fill_pits(dem)
    flooded = grid.fill_depressions(pit_filled)
    inflated = grid.resolve_flats(flooded)
    return inflated


def _prepare_dem(dtm: RasterLayer, conditioned: Optional[RasterLayer] = None):
    """
    Prepara el MDT para análisis hidrológico.

    Si se pasa un `conditioned` ya procesado, se usa directamente evitando
    recalcular el acondicionamiento. De lo contrario, se acondiciona el `dtm`.

    Returns:
        (grid, dem_condicionado) listos para calcular flowdir/accumulation.
    """
    from pysheds.grid import Grid

    source = conditioned if conditioned is not None else dtm
    grid, path = _get_grid_and_path(source)
    dem = grid.read_raster(path)

    if conditioned is None:
        dem = _condition_raw(grid, dem)

    return grid, dem


def _build_result(arr: np.ndarray, dtm: RasterLayer, name: str) -> RasterLayer:
    """
    Construye un RasterLayer de resultado copiando la georreferenciación del MDT origen.
    """
    result = RasterLayer.from_array(
        arr, dtm.bounds, epsg=dtm.crs_epsg,
        nodata=DEFAULT_NODATA, name=name
    )
    result.transform = dtm.transform
    result.crs = dtm.crs
    return result