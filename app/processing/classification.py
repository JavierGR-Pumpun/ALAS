"""
ALAS — Classification
Clasificación automática del terreno usando PDAL (SMRF, CSF, PMF).
"""

import json
import tempfile
import numpy as np
from pathlib import Path
from typing import Optional

from app.core.point_cloud import PointCloudData
from app.config import (
    SMRF_DEFAULTS, CSF_DEFAULTS, PMF_DEFAULTS,
    LOW_VEG_MAX_HEIGHT, MEDIUM_VEG_MAX_HEIGHT, HIGH_VEG_MAX_HEIGHT,
    BUILDING_MIN_HEIGHT
)
from app.logger import get_logger

logger = get_logger("processing.classification")


def classify_ground_smrf(pc: PointCloudData,
                          window: float = None,
                          slope: float = None,
                          threshold: float = None,
                          scalar: float = None) -> np.ndarray:
    """
    Clasificación de suelo usando SMRF (Simple Morphological Filter).
    Devuelve array de clasificación actualizado.
    """
    params = {
        "window": window or SMRF_DEFAULTS["window"],
        "slope": slope or SMRF_DEFAULTS["slope"],
        "threshold": threshold or SMRF_DEFAULTS["threshold"],
        "scalar": scalar or SMRF_DEFAULTS["scalar"],
    }
    logger.info(f"Clasificando suelo (SMRF): {params}")
    return _run_ground_classification(pc, "filters.smrf", params)


def classify_ground_csf(pc: PointCloudData,
                         resolution: float = None,
                         threshold: float = None,
                         rigidness: int = None,
                         iterations: int = None) -> np.ndarray:
    """
    Clasificación de suelo usando CSF (Cloth Simulation Filter).
    Devuelve array de clasificación actualizado.
    """
    params = {
        "resolution": resolution or CSF_DEFAULTS["resolution"],
        "threshold": threshold or CSF_DEFAULTS["threshold"],
        "rigidness": rigidness or CSF_DEFAULTS["rigidness"],
        "iterations": iterations or CSF_DEFAULTS["iterations"],
    }
    logger.info(f"Clasificando suelo (CSF): {params}")
    return _run_ground_classification(pc, "filters.csf", params)


def classify_ground_pmf(pc: PointCloudData,
                         max_window_size: float = None,
                         slope: float = None,
                         initial_distance: float = None,
                         max_distance: float = None) -> np.ndarray:
    """
    Clasificación de suelo usando PMF (Progressive Morphological Filter).
    Devuelve array de clasificación actualizado.
    """
    params = {
        "max_window_size": max_window_size or PMF_DEFAULTS["max_window_size"],
        "slope": slope or PMF_DEFAULTS["slope"],
        "initial_distance": initial_distance or PMF_DEFAULTS["initial_distance"],
        "max_distance": max_distance or PMF_DEFAULTS["max_distance"],
    }
    logger.info(f"Clasificando suelo (PMF): {params}")
    return _run_ground_classification(pc, "filters.pmf", params)


def _run_ground_classification(pc: PointCloudData, filter_type: str,
                                params: dict) -> np.ndarray:
    """Ejecuta un pipeline PDAL de clasificacion de suelo."""
    import pdal
    import os

    # Directorio temporal garantizado ASCII en Mac/Win/Linux
    tmp_dir = Path(os.environ.get("TMPDIR", tempfile.gettempdir()))
    # Si la ruta tiene caracteres no-ASCII, caer a /tmp (Mac/Linux) o C:\Temp (Win)
    try:
        str(tmp_dir).encode("ascii")
    except UnicodeEncodeError:
        tmp_dir = Path("/tmp") if os.name != "nt" else Path("C:/Temp")
        tmp_dir.mkdir(exist_ok=True)

    uid = id(pc)
    tmp_in  = tmp_dir / f"alas_in_{uid}.las"
    tmp_out = tmp_dir / f"alas_out_{uid}.las"

    try:
        pc.to_file(str(tmp_in), compress=False)

        filter_stage = {"type": filter_type}
        filter_stage.update(params)

        pipeline_def = [
            {"type": "readers.las", "filename": tmp_in.as_posix()},
            filter_stage,
            {
                "type": "writers.las",
                "filename": tmp_out.as_posix(),
                "forward": "all",
            },
        ]

        # Serializar limpio, escapar cualquier non-ASCII
        pipeline_json = json.dumps(pipeline_def, ensure_ascii=True)

        # Guardia: reventar antes de que lo haga PDAL
        pipeline_json.encode("ascii")

        print(repr(pipeline_json[1580:1610]))

        pipeline = pdal.Pipeline(pipeline_json)
        count = pipeline.execute()
        logger.info(f"Clasificacion completada: {count:,} puntos procesados")

        result = PointCloudData.from_file(str(tmp_out))
        classification = result.classification

        ground_count = np.sum(classification == 2)
        total = len(classification)
        pct = (ground_count / total * 100) if total > 0 else 0
        logger.info(f"Suelo: {ground_count:,} puntos ({pct:.1f}%)")

        return classification

    finally:
        tmp_in.unlink(missing_ok=True)
        tmp_out.unlink(missing_ok=True)


def classify_above_ground(pc: PointCloudData) -> np.ndarray:
    """
    Clasifica puntos sobre el suelo en categorías:
    vegetación baja/media/alta y edificios.
    Requiere que el suelo ya esté clasificado (class 2).
    """
    if pc.classification is None:
        raise ValueError("La nube necesita clasificación previa de suelo.")

    logger.info("Clasificando puntos sobre el suelo...")
    classification = pc.classification.copy()

    # Calcular altura sobre el suelo
    ground_mask = classification == 2
    if not ground_mask.any():
        logger.warning("No hay puntos de suelo clasificados")
        return classification

    ground_z = pc.xyz[ground_mask, 2]
    ground_xy = pc.xyz[ground_mask, :2]

    # Interpolación simple: para cada punto no-suelo, encontrar el Z
    # del punto de suelo más cercano
    from scipy.spatial import cKDTree

    ground_tree = cKDTree(ground_xy)
    non_ground_mask = ~ground_mask
    non_ground_xy = pc.xyz[non_ground_mask, :2]
    non_ground_z = pc.xyz[non_ground_mask, 2]

    _, indices = ground_tree.query(non_ground_xy, k=1)
    ground_z_at_points = ground_z[indices]
    height_above_ground = non_ground_z - ground_z_at_points

    # Clasificar por altura
    ng_class = classification[non_ground_mask]

    # Solo clasificar los que son class 1 (sin clasificar)
    unclassified = (ng_class == 0) | (ng_class == 1)

    low_veg = unclassified & (height_above_ground > 0) & (height_above_ground <= LOW_VEG_MAX_HEIGHT)
    med_veg = unclassified & (height_above_ground > LOW_VEG_MAX_HEIGHT) & (height_above_ground <= MEDIUM_VEG_MAX_HEIGHT)
    high_veg = unclassified & (height_above_ground > MEDIUM_VEG_MAX_HEIGHT) & (height_above_ground <= HIGH_VEG_MAX_HEIGHT)

    ng_class[low_veg] = 3   # Low vegetation
    ng_class[med_veg] = 4   # Medium vegetation
    ng_class[high_veg] = 5  # High vegetation

    classification[non_ground_mask] = ng_class

    # Log stats
    for code, name in [(3, "Veg. baja"), (4, "Veg. media"), (5, "Veg. alta")]:
        count = np.sum(classification == code)
        logger.info(f"  {name}: {count:,} puntos")

    return classification


def manual_reclassify(pc: PointCloudData, indices: np.ndarray,
                      new_class: int) -> np.ndarray:
    """Reclasifica manualmente un conjunto de puntos."""
    if pc.classification is None:
        pc.classification = np.zeros(pc.point_count, dtype=np.uint8)

    classification = pc.classification.copy()
    classification[indices] = new_class
    logger.info(f"Reclasificados {len(indices):,} puntos → clase {new_class}")
    return classification
