"""
ALAS — Vegetation Analysis
CHM, detección de árboles, segmentación de copas, estadísticas de dosel.
"""

import numpy as np
from typing import Optional, Tuple, List, Dict
from scipy import ndimage

from app.core.raster_layer import RasterLayer
from app.config import (
    DEFAULT_NODATA, DEFAULT_MIN_TREE_HEIGHT,
    DEFAULT_CROWN_WINDOW, DEFAULT_CANOPY_CELL_SIZE
)
from app.logger import get_logger

logger = get_logger("processing.vegetation")


def detect_tree_tops(chm: RasterLayer, min_height: float = None,
                      window_size: int = None) -> np.ndarray:
    """
    Detecta copas de árboles como máximos locales en el CHM.
    Devuelve array (N, 3) con coordenadas [x, y, height].
    """
    min_height = min_height or DEFAULT_MIN_TREE_HEIGHT
    window_size = window_size or DEFAULT_CROWN_WINDOW

    logger.info(f"Detectando árboles (min_h={min_height}m, ventana={window_size}px)")

    data = chm.get_band(0).copy()
    data[data == chm.nodata] = 0

    # Máximos locales
    local_max = ndimage.maximum_filter(data, size=window_size)
    is_peak = (data == local_max) & (data >= min_height)

    # Coordenadas de los picos
    rows, cols = np.where(is_peak)
    heights = data[rows, cols]

    # Convertir pixel coords a geo coords
    if chm.transform:
        xs = chm.transform.c + cols * chm.transform.a + chm.transform.a / 2
        ys = chm.transform.f + rows * chm.transform.e + chm.transform.e / 2
    elif chm.bounds:
        xmin, ymin, xmax, ymax = chm.bounds
        xs = xmin + cols * (xmax - xmin) / data.shape[1]
        ys = ymax - rows * (ymax - ymin) / data.shape[0]
    else:
        xs = cols.astype(float)
        ys = rows.astype(float)

    tree_tops = np.column_stack([xs, ys, heights])

    logger.info(f"Detectados {len(tree_tops)} árboles (h: {heights.min():.1f} - {heights.max():.1f} m)")
    return tree_tops


def segment_crowns(chm: RasterLayer, tree_tops: np.ndarray,
                    method: str = "watershed") -> np.ndarray:
    """
    Segmenta copas individuales usando watershed.
    Devuelve un raster de etiquetas (cada árbol = un ID).
    """
    logger.info(f"Segmentando copas ({method})...")
    from skimage.segmentation import watershed
    from skimage.feature import peak_local_max

    data = chm.get_band(0).copy()
    data[data == chm.nodata] = 0

    # Crear marcadores desde tree_tops
    markers = np.zeros_like(data, dtype=np.int32)

    if chm.transform:
        for i, (x, y, h) in enumerate(tree_tops):
            col = int((x - chm.transform.c) / chm.transform.a)
            row = int((y - chm.transform.f) / chm.transform.e)
            if 0 <= row < data.shape[0] and 0 <= col < data.shape[1]:
                markers[row, col] = i + 1
    elif chm.bounds:
        xmin, ymin, xmax, ymax = chm.bounds
        for i, (x, y, h) in enumerate(tree_tops):
            col = int((x - xmin) / (xmax - xmin) * data.shape[1])
            row = int((ymax - y) / (ymax - ymin) * data.shape[0])
            if 0 <= row < data.shape[0] and 0 <= col < data.shape[1]:
                markers[row, col] = i + 1

    # Watershed (invertir CHM para que las copas sean cuencas)
    mask = data > 0.5  # Solo zonas con vegetación
    labels = watershed(-data, markers=markers, mask=mask)

    n_trees = len(np.unique(labels)) - 1  # Excluir 0 (background)
    logger.info(f"Segmentadas {n_trees} copas individuales")

    return labels, data


def build_crown_raster(chm: RasterLayer,
                       height_map: np.ndarray,
                       labels: np.ndarray) -> RasterLayer:
    """
    Construye un raster de copas segmentadas.
    Cada píxel de copa toma la altura máxima de su segmento.
    """
    logger.info("Construyendo raster de copas segmentadas...")

    crown_data = np.full(labels.shape, chm.nodata, dtype=np.float32)
    unique_ids = np.unique(labels)
    unique_ids = unique_ids[unique_ids > 0]

    for tree_id in unique_ids:
        mask = labels == tree_id
        if not mask.any():
            continue
        crown_data[mask] = float(np.max(height_map[mask]))

    bounds = chm.bounds
    if bounds is None:
        raise ValueError("No se puede construir raster de copas sin bounds válidos.")

    result = RasterLayer.from_array(
        crown_data,
        bounds,
        epsg=chm.crs_epsg,
        nodata=chm.nodata,
        name="Copas_vegetación"
    )
    result.crs = chm.crs
    return result


def compute_canopy_stats(chm: RasterLayer,
                          labels: np.ndarray) -> List[Dict]:
    """
    Calcula estadísticas por copa segmentada.
    Devuelve lista de dicts con: id, x, y, max_height, mean_height, area_m2.
    """
    logger.info("Calculando estadísticas de copas...")

    data = chm.get_band(0).copy()
    data[data == chm.nodata] = 0

    res_x = chm.resolution[0] if chm.resolution else 1.0
    res_y = chm.resolution[1] if chm.resolution else 1.0
    cell_area = res_x * res_y

    unique_ids = np.unique(labels)
    unique_ids = unique_ids[unique_ids > 0]  # Excluir background

    stats = []
    for tree_id in unique_ids:
        mask = labels == tree_id
        heights = data[mask]

        if len(heights) == 0:
            continue

        # Centroide
        rows, cols = np.where(mask)
        mean_row = rows.mean()
        mean_col = cols.mean()

        if chm.transform:
            cx = chm.transform.c + mean_col * chm.transform.a
            cy = chm.transform.f + mean_row * chm.transform.e
        else:
            cx, cy = mean_col, mean_row

        stats.append({
            "id": int(tree_id),
            "x": float(cx),
            "y": float(cy),
            "max_height": float(heights.max()),
            "mean_height": float(heights.mean()),
            "area_m2": float(len(heights) * cell_area),
            "n_pixels": int(len(heights)),
        })

    logger.info(f"Estadísticas calculadas para {len(stats)} árboles")
    return stats


def density_map(chm: RasterLayer, cell_size: float = None) -> RasterLayer:
    """
    Genera mapa de densidad de vegetación.
    Porcentaje de cobertura del dosel por celda de tamaño configurable.
    """
    cell_size = cell_size or DEFAULT_CANOPY_CELL_SIZE
    logger.info(f"Calculando mapa de densidad (celda={cell_size}m)")

    data = chm.get_band(0).copy()
    data[data == chm.nodata] = 0

    res = chm.resolution[0] if chm.resolution else 1.0
    block_size = max(1, int(cell_size / res))

    rows, cols = data.shape
    out_rows = rows // block_size
    out_cols = cols // block_size

    density = np.zeros((out_rows, out_cols), dtype=np.float32)

    for r in range(out_rows):
        for c in range(out_cols):
            block = data[
                r * block_size: (r + 1) * block_size,
                c * block_size: (c + 1) * block_size
            ]
            total = block.size
            canopy = np.sum(block > DEFAULT_MIN_TREE_HEIGHT)
            density[r, c] = (canopy / total * 100) if total > 0 else 0

    bounds = chm.bounds
    if bounds:
        xmin, ymin, xmax, ymax = bounds
        new_xmax = xmin + out_cols * cell_size
        new_ymin = ymax - out_rows * cell_size
        bounds = (xmin, new_ymin, new_xmax, ymax)

    result = RasterLayer.from_array(
        density, bounds, epsg=chm.crs_epsg,
        nodata=DEFAULT_NODATA, name="Densidad_vegetación"
    )
    result.crs = chm.crs

    logger.info(f"Densidad media: {np.mean(density):.1f}%")
    return result
