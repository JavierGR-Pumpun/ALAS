"""
ALAS — Classification
Automatic terrain classification using PDAL (SMRF, CSF, PMF).
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
    Ground classification using SMRF (Simple Morphological Filter).
    Returns updated classification array.
    """
    params = {
        "window": window or SMRF_DEFAULTS["window"],
        "slope": slope or SMRF_DEFAULTS["slope"],
        "threshold": threshold or SMRF_DEFAULTS["threshold"],
        "scalar": scalar or SMRF_DEFAULTS["scalar"],
    }
    logger.info(f"Classifying ground (SMRF): {params}")
    return _run_ground_classification(pc, "filters.smrf", params)


def classify_ground_csf(pc: PointCloudData,
                         resolution: float = None,
                         threshold: float = None,
                         rigidness: int = None,
                         iterations: int = None) -> np.ndarray:
    """
    Ground classification using CSF (Cloth Simulation Filter).
    Returns updated classification array.
    """
    params = {
        "resolution": resolution or CSF_DEFAULTS["resolution"],
        "threshold": threshold or CSF_DEFAULTS["threshold"],
        "rigidness": rigidness or CSF_DEFAULTS["rigidness"],
        "iterations": iterations or CSF_DEFAULTS["iterations"],
    }
    logger.info(f"Classifying ground (CSF): {params}")
    return _run_ground_classification(pc, "filters.csf", params)


def classify_ground_pmf(pc: PointCloudData,
                         max_window_size: float = None,
                         slope: float = None,
                         initial_distance: float = None,
                         max_distance: float = None) -> np.ndarray:
    """
    Ground classification using PMF (Progressive Morphological Filter).
    Returns updated classification array.
    """
    params = {
        "max_window_size": max_window_size or PMF_DEFAULTS["max_window_size"],
        "slope": slope or PMF_DEFAULTS["slope"],
        "initial_distance": initial_distance or PMF_DEFAULTS["initial_distance"],
        "max_distance": max_distance or PMF_DEFAULTS["max_distance"],
    }
    logger.info(f"Classifying ground (PMF): {params}")
    return _run_ground_classification(pc, "filters.pmf", params)


def _run_ground_classification(pc: PointCloudData, filter_type: str,
                                params: dict) -> np.ndarray:
    """Executes a PDAL ground classification pipeline."""
    import pdal
    import os

    # Temporary directory with guaranteed ASCII path on Mac/Win/Linux
    tmp_dir = Path(os.environ.get("TMPDIR", tempfile.gettempdir()))
    # If the path has non-ASCII characters, fall back to /tmp (Mac/Linux) or C:\Temp (Win)
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

        # Serialize cleanly, escape any non-ASCII
        pipeline_json = json.dumps(pipeline_def, ensure_ascii=True)

        # Guard: fail before PDAL does
        pipeline_json.encode("ascii")

        pipeline = pdal.Pipeline(pipeline_json)
        count = pipeline.execute()
        logger.info(f"Classification completed: {count:,} points processed")

        result = PointCloudData.from_file(str(tmp_out))
        classification = result.classification
        if classification is None:
            raise ValueError("Classified file has no classification field")

        ground_count = np.sum(classification == 2)
        total = len(classification)
        pct = (ground_count / total * 100) if total > 0 else 0
        logger.info(f"Ground: {ground_count:,} points ({pct:.1f}%)")

        return classification

    finally:
        tmp_in.unlink(missing_ok=True)
        tmp_out.unlink(missing_ok=True)


def classify_above_ground(pc: PointCloudData) -> np.ndarray:
    """
    Classifies above-ground points into categories:
    low/medium/high vegetation and buildings.
    Requires ground to already be classified (class 2).
    """
    if pc.classification is None:
        raise ValueError("Cloud needs prior ground classification.")

    logger.info("Classifying above-ground points...")
    classification = pc.classification.copy()

    # Calculate height above ground
    ground_mask = classification == 2
    if not ground_mask.any():
        logger.warning("No classified ground points")
        return classification

    ground_z = pc.xyz[ground_mask, 2]
    ground_xy = pc.xyz[ground_mask, :2]

    # Simple interpolation: for each non-ground point, find the Z
    # of the nearest ground point
    from scipy.spatial import cKDTree

    ground_tree = cKDTree(ground_xy)
    non_ground_mask = ~ground_mask
    non_ground_xy = pc.xyz[non_ground_mask, :2]
    non_ground_z = pc.xyz[non_ground_mask, 2]

    _, indices = ground_tree.query(non_ground_xy, k=1)
    ground_z_at_points = ground_z[indices]
    height_above_ground = non_ground_z - ground_z_at_points

    # Classify by height
    ng_class = classification[non_ground_mask]

    # Only classify those that are class 1 (unclassified)
    unclassified = (ng_class == 0) | (ng_class == 1)

    low_veg = unclassified & (height_above_ground > 0) & (height_above_ground <= LOW_VEG_MAX_HEIGHT)
    med_veg = unclassified & (height_above_ground > LOW_VEG_MAX_HEIGHT) & (height_above_ground <= MEDIUM_VEG_MAX_HEIGHT)
    high_veg = unclassified & (height_above_ground > MEDIUM_VEG_MAX_HEIGHT) & (height_above_ground <= HIGH_VEG_MAX_HEIGHT)

    ng_class[low_veg] = 3   # Low vegetation
    ng_class[med_veg] = 4   # Medium vegetation
    ng_class[high_veg] = 5  # High vegetation

    classification[non_ground_mask] = ng_class

    # Log stats
    for code, name in [(3, "Low veg."), (4, "Med. veg."), (5, "High veg.")]:
        count = np.sum(classification == code)
        logger.info(f"  {name}: {count:,} points")

    return classification


def manual_reclassify(pc: PointCloudData, indices: np.ndarray,
                      new_class: int) -> np.ndarray:
    """Manually reclassifies a set of points."""
    if pc.classification is None:
        pc.classification = np.zeros(pc.point_count, dtype=np.uint8)

    classification = pc.classification.copy()
    classification[indices] = new_class
    logger.info(f"Reclassified {len(indices):,} points → class {new_class}")
    return classification
