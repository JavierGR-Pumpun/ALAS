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


# Model output index → ASPRS LAS class code (from checkpoint config class_mapping inverse)
_AI_CLASS_TO_ASPRS = {0: 2, 1: 3, 2: 4, 3: 5, 4: 6, 5: 7}
_AI_CLASS_NAMES    = ["Ground", "Low Veg", "Med Veg", "High Veg", "Building", "Noise"]


def _build_ai_model(cfg: dict):
    """Reconstruct the PointNet encoder-decoder from checkpoint config."""
    import torch.nn as nn

    num_features = cfg.get("num_features", 6)
    num_classes  = cfg.get("num_classes",  6)
    latent_dim   = cfg.get("latent_dim",   256)

    class _ConvBlock(nn.Module):
        def __init__(self, in_ch, out_ch):
            super().__init__()
            self.block = nn.Sequential(
                nn.Conv1d(in_ch, out_ch, 1),
                nn.BatchNorm1d(out_ch, track_running_stats=False),
                nn.ReLU(inplace=True),
            )
        def forward(self, x):
            return self.block(x)

    class _PointNetClassifier(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = nn.ModuleList([
                _ConvBlock(num_features, 64),
                _ConvBlock(64, 128),
                _ConvBlock(128, latent_dim),
            ])
            self.decoder = nn.ModuleList([
                _ConvBlock(latent_dim * 2, latent_dim),
                _ConvBlock(latent_dim, 128),
                _ConvBlock(128, 64),
                nn.Conv1d(64, num_classes, 1),
            ])

        def forward(self, x):          # x: (B, num_features, N)
            for enc in self.encoder:
                x = enc(x)             # → (B, latent_dim, N)
            # Global context: max-pool over points, expand back
            g = x.max(dim=2, keepdim=True)[0].expand(-1, -1, x.shape[2])
            x = torch.cat([x, g], dim=1)   # (B, latent_dim*2, N)
            for dec in self.decoder:
                x = dec(x)
            return x                   # (B, num_classes, N)

    return _PointNetClassifier()


def classify_ai(pc: PointCloudData, model_path: str,
                batch_size: int = 65536) -> np.ndarray:
    """
    Full-scene AI classification using classifier_best.pt.

    Input features (6, per-point, normalized to [0,1]):
        x, y, z, intensity, return_number, number_of_returns
    Output: ASPRS codes 2–7 (Ground / Lo-Med-Hi Veg / Building / Noise).
    """
    try:
        import torch
    except ImportError:
        raise ImportError(
            "PyTorch is required for AI classification. Install with: pip install torch"
        )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"AI classification — device: {device}")

    model_file = Path(model_path)
    if not model_file.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    ckpt  = torch.load(str(model_file), map_location=device, weights_only=False)
    cfg   = ckpt.get("config", {})
    model = _build_ai_model(cfg)
    model.load_state_dict(ckpt["model_state_dict"], strict=False)
    model.to(device).eval()
    logger.info(f"Model loaded — epoch {ckpt.get('epoch')}, val_f1 {ckpt.get('val_f1')}")

    n = pc.point_count

    # ── Feature extraction ─────────────────────────────────────────────────
    xyz = pc.xyz.astype(np.float32)
    xyz_norm = (xyz - xyz.min(axis=0)) / np.maximum(xyz.max(axis=0) - xyz.min(axis=0), 1e-8)

    intens  = (pc.intensity.astype(np.float32) / 65535.0
               if pc.intensity is not None else np.zeros(n, np.float32))
    ret_num = (pc.return_number.astype(np.float32) / 7.0
               if pc.return_number is not None else np.full(n, 1/7, np.float32))
    num_ret = (pc.number_of_returns.astype(np.float32) / 7.0
               if pc.number_of_returns is not None else np.full(n, 1/7, np.float32))

    # (N, 6) — will be transposed to (6, N) per batch
    features = np.column_stack([xyz_norm, intens, ret_num, num_ret])

    # ── Batch inference ────────────────────────────────────────────────────
    raw_preds = np.zeros(n, dtype=np.int64)
    with torch.no_grad():
        for start in range(0, n, batch_size):
            end   = min(start + batch_size, n)
            chunk = features[start:end]                         # (chunk_n, 6)
            # Conv1d expects (B, C, L) → (1, 6, chunk_n)
            x     = torch.tensor(chunk.T[np.newaxis], dtype=torch.float32).to(device)
            out   = model(x)                                    # (1, 6, chunk_n)
            raw_preds[start:end] = out.squeeze(0).argmax(dim=0).cpu().numpy()
            if end % (batch_size * 10) == 0 or end == n:
                logger.info(f"  {end:,}/{n:,} points ({end / n * 100:.0f}%)")

    # ── Map model classes → ASPRS codes ────────────────────────────────────
    classification = np.ones(n, dtype=np.uint8)
    for model_cls, asprs in _AI_CLASS_TO_ASPRS.items():
        mask = raw_preds == model_cls
        classification[mask] = asprs
        count = int(mask.sum())
        logger.info(f"  {_AI_CLASS_NAMES[model_cls]}: {count:,} ({count / n * 100:.1f}%)")

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
