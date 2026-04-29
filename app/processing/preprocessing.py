"""
ALAS — Preprocessing
Fusión, filtrado de ruido, reproyección y decimado de nubes de puntos.
"""

import json
import numpy as np
import tempfile
from pathlib import Path
from typing import Optional

from app.core.point_cloud import PointCloudData
from app.logger import get_logger

logger = get_logger("processing.preprocessing")


def filter_noise(pc: PointCloudData, method: str = "statistical",
                 k: int = 8, multiplier: float = 2.0) -> PointCloudData:
    """
    Filtra puntos de ruido (outliers).
    method: 'statistical' (SOR) o 'radius'
    """
    logger.info(f"Filtrando ruido ({method}, k={k}, mult={multiplier})")

    if method == "statistical":
        # Statistical Outlier Removal usando PDAL
        result = _pdal_filter_noise_sor(pc, k, multiplier)
    else:
        result = _numpy_sor(pc, k, multiplier)

    logger.info(
        f"Ruido filtrado: {pc.point_count:,} → {result.point_count:,} "
        f"({pc.point_count - result.point_count:,} eliminados)"
    )
    return result


def _pdal_filter_noise_sor(pc: PointCloudData, k: int,
                            multiplier: float) -> PointCloudData:
    """Filtrado SOR usando PDAL pipeline."""
    import pdal

    # Guardar temporalmente para PDAL
    tmp_in = tempfile.NamedTemporaryFile(suffix=".las", delete=False)
    tmp_out = tempfile.NamedTemporaryFile(suffix=".las", delete=False)
    tmp_in.close()
    tmp_out.close()

    try:
        pc.to_file(tmp_in.name, compress=False)

        pipeline_json = json.dumps([
            {"type": "readers.las", "filename": tmp_in.name},
            {
                "type": "filters.outlier",
                "method": "statistical",
                "mean_k": k,
                "multiplier": multiplier,
            },
            {
                "type": "filters.range",
                "limits": "Classification![7:7]",  # Excluir noise (class 7)
            },
            {"type": "writers.las", "filename": tmp_out.name},
        ])

        pipeline = pdal.Pipeline(pipeline_json)
        pipeline.execute()

        result = PointCloudData.from_file(tmp_out.name)
        result.name = f"{pc.name}_filtered"
        result.crs_wkt = pc.crs_wkt
        result.crs_epsg = pc.crs_epsg
        return result

    finally:
        Path(tmp_in.name).unlink(missing_ok=True)
        Path(tmp_out.name).unlink(missing_ok=True)


def _numpy_sor(pc: PointCloudData, k: int, multiplier: float) -> PointCloudData:
    """SOR simple con numpy + scipy (sin PDAL)."""
    from scipy.spatial import cKDTree

    tree = cKDTree(pc.xyz)
    distances, _ = tree.query(pc.xyz, k=k + 1)
    mean_dists = distances[:, 1:].mean(axis=1)  # Excluir distancia a sí mismo

    global_mean = mean_dists.mean()
    global_std = mean_dists.std()
    threshold = global_mean + multiplier * global_std

    mask = mean_dists < threshold
    result = pc.subset(mask)
    result.name = f"{pc.name}_filtered"
    return result


def reproject(pc: PointCloudData, source_epsg: int,
              target_epsg: int) -> PointCloudData:
    """Reproyecta una nube de puntos de un CRS a otro usando PDAL."""
    import pdal

    logger.info(f"Reproyectando EPSG:{source_epsg} → EPSG:{target_epsg}")

    tmp_in = tempfile.NamedTemporaryFile(suffix=".las", delete=False)
    tmp_out = tempfile.NamedTemporaryFile(suffix=".las", delete=False)
    tmp_in.close()
    tmp_out.close()

    try:
        pc.to_file(tmp_in.name, compress=False)

        pipeline_json = json.dumps([
            {"type": "readers.las", "filename": tmp_in.name},
            {
                "type": "filters.reprojection",
                "in_srs": f"EPSG:{source_epsg}",
                "out_srs": f"EPSG:{target_epsg}",
            },
            {"type": "writers.las", "filename": tmp_out.name},
        ])

        pipeline = pdal.Pipeline(pipeline_json)
        pipeline.execute()

        result = PointCloudData.from_file(tmp_out.name)
        result.name = f"{pc.name}_epsg{target_epsg}"
        result.crs_epsg = target_epsg
        try:
            from pyproj import CRS
            result.crs_wkt = CRS.from_epsg(target_epsg).to_wkt()
        except Exception:
            pass
        return result

    finally:
        Path(tmp_in.name).unlink(missing_ok=True)
        Path(tmp_out.name).unlink(missing_ok=True)


def decimate(pc: PointCloudData, method: str = "voxel",
             voxel_size: float = 0.5,
             target_count: int = None) -> PointCloudData:
    """
    Decima una nube de puntos.
    method: 'voxel' o 'random'
    """
    logger.info(f"Decimando ({method}, voxel={voxel_size}m)")

    if method == "voxel":
        result = pc.decimate_for_display(
            max_points=target_count or pc.point_count,
            voxel_size=voxel_size
        )
    else:
        # Random sampling
        if target_count is None:
            target_count = pc.point_count // 2
        rng = np.random.default_rng(42)
        indices = rng.choice(pc.point_count, min(target_count, pc.point_count), replace=False)
        mask = np.zeros(pc.point_count, dtype=bool)
        mask[indices] = True
        result = pc.subset(mask)

    result.name = f"{pc.name}_decimated"
    logger.info(f"Decimado: {pc.point_count:,} → {result.point_count:,}")
    return result


def merge_tiles(clouds: list) -> PointCloudData:
    """Fusiona múltiples nubes de puntos."""
    return PointCloudData.merge(clouds, "merged")
