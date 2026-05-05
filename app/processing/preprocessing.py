"""
ALAS — Preprocessing
Fusion, filtrado de ruido, reproyeccion y decimado de nubes de puntos.
"""

import json
import numpy as np
import tempfile
import os
from pathlib import Path
from typing import Optional

from app.core.point_cloud import PointCloudData
from app.logger import get_logger

logger = get_logger("processing.preprocessing")


def _get_ascii_tmpdir() -> Path:
    """Devuelve un directorio temporal con ruta ASCII garantizada (Mac/Win/Linux)."""
    tmp_dir = Path(os.environ.get("TMPDIR", tempfile.gettempdir()))
    try:
        str(tmp_dir).encode("ascii")
        return tmp_dir
    except UnicodeEncodeError:
        fallback = Path("/tmp") if os.name != "nt" else Path("C:/Temp")
        fallback.mkdir(exist_ok=True)
        return fallback


def filter_noise(pc: PointCloudData, method: str = "statistical",
                 k: int = 8, multiplier: float = 2.0) -> PointCloudData:
    """
    Filtra puntos de ruido (outliers).
    method: 'statistical' (SOR) o 'radius'
    """
    logger.info(f"Filtrando ruido ({method}, k={k}, mult={multiplier})")

    # Usamos numpy SOR directamente — el PDAL filters.outlier reclasifica
    # todos los puntos ignorando el 'where', destruyendo Overlap y otras clases
    result = _numpy_sor(pc, k, multiplier)

    logger.info(
        f"Ruido filtrado: {pc.point_count:,} -> {result.point_count:,} "
        f"({pc.point_count - result.point_count:,} eliminados)"
    )
    return result


def _pdal_filter_noise_sor(pc: PointCloudData, k: int,
                            multiplier: float) -> PointCloudData:
    """Filtrado SOR usando PDAL pipeline."""
    import pdal

    tmp_dir = _get_ascii_tmpdir()
    uid = id(pc)
    tmp_in  = tmp_dir / f"alas_sor_in_{uid}.las"
    tmp_out = tmp_dir / f"alas_sor_out_{uid}.las"

    try:
        pc.to_file(str(tmp_in), compress=False)

        pipeline_json = json.dumps([
            {"type": "readers.las", "filename": tmp_in.as_posix()},
            {
                "type": "filters.outlier",
                "method": "statistical",
                "mean_k": k,
                "multiplier": multiplier,
                # Solo actuar sobre puntos sin clasificar, respetar Ground,
                # Vegetation, Building, Overlap (clase 12), etc.
                "where": "Classification == 0 || Classification == 1",
            },
            {
                "type": "filters.range",
                # Excluir solo clase 7 (noise marcado por PDAL), conservar todo lo demas
                "limits": "Classification![7:7]",
            },
            {"type": "writers.las", "filename": tmp_out.as_posix()},
        ], ensure_ascii=True)

        # Guardia: verificar que el JSON es ASCII puro antes de pasarlo a PDAL
        pipeline_json.encode("ascii")

        pipeline = pdal.Pipeline(pipeline_json)
        pipeline.execute()

        result = PointCloudData.from_file(str(tmp_out))
        result.name = f"{pc.name}_filtered"
        result.crs_wkt = pc.crs_wkt
        result.crs_epsg = pc.crs_epsg
        return result

    finally:
        tmp_in.unlink(missing_ok=True)
        tmp_out.unlink(missing_ok=True)


def _numpy_sor(pc: PointCloudData, k: int, multiplier: float) -> PointCloudData:
    """SOR simple con numpy + scipy (sin PDAL)."""
    from scipy.spatial import cKDTree

    tree = cKDTree(pc.xyz)
    distances, _ = tree.query(pc.xyz, k=k + 1)
    mean_dists = distances[:, 1:].mean(axis=1)  # Excluir distancia a si mismo

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

    logger.info(f"Reproyectando EPSG:{source_epsg} -> EPSG:{target_epsg}")

    tmp_dir = _get_ascii_tmpdir()
    uid = id(pc)
    tmp_in  = tmp_dir / f"alas_reproj_in_{uid}.las"
    tmp_out = tmp_dir / f"alas_reproj_out_{uid}.las"

    try:
        pc.to_file(str(tmp_in), compress=False)

        pipeline_json = json.dumps([
            {"type": "readers.las", "filename": tmp_in.as_posix()},
            {
                "type": "filters.reprojection",
                "in_srs": f"EPSG:{source_epsg}",
                "out_srs": f"EPSG:{target_epsg}",
            },
            {"type": "writers.las", "filename": tmp_out.as_posix()},
        ], ensure_ascii=True)

        pipeline_json.encode("ascii")

        pipeline = pdal.Pipeline(pipeline_json)
        pipeline.execute()

        result = PointCloudData.from_file(str(tmp_out))
        result.name = f"{pc.name}_epsg{target_epsg}"
        result.crs_epsg = target_epsg
        try:
            from pyproj import CRS
            result.crs_wkt = CRS.from_epsg(target_epsg).to_wkt()
        except Exception:
            pass
        return result

    finally:
        tmp_in.unlink(missing_ok=True)
        tmp_out.unlink(missing_ok=True)


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
        if target_count is None:
            target_count = pc.point_count // 2
        rng = np.random.default_rng(42)
        indices = rng.choice(pc.point_count, min(target_count, pc.point_count), replace=False)
        mask = np.zeros(pc.point_count, dtype=bool)
        mask[indices] = True
        result = pc.subset(mask)

    result.name = f"{pc.name}_decimated"
    logger.info(f"Decimado: {pc.point_count:,} -> {result.point_count:,}")
    return result


def merge_tiles(clouds: list) -> PointCloudData:
    """Fusiona multiples nubes de puntos."""
    return PointCloudData.merge(clouds, "merged")

def handle_overlap(pc: PointCloudData, strategy: str = "auto") -> PointCloudData:
    """
    Gestiona puntos de Overlap (clase 12) según el tipo de sensor.
    
    strategy:
        'auto'   — decide según sensor_type
        'remove' — elimina directamente
        'dedup'  — voxel deduplication
        'keep'   — no hace nada
    """
    if pc.classification is None:
        return pc

    overlap_count = int(np.sum(pc.classification == 12))
    if overlap_count == 0:
        logger.info("No hay puntos de Overlap (clase 12)")
        return pc

    overlap_pct = overlap_count / pc.point_count * 100
    logger.info(f"Overlap detectado: {overlap_count:,} puntos ({overlap_pct:.1f}%)")

    if strategy == "auto":
        sensor = pc.sensor_type
        if sensor in ("uav", "mls"):
            strategy = "remove"
        elif sensor in ("tls", "bathymetric"):
            strategy = "keep"
        elif sensor == "aerial":
            # Aéreo: si densidad alta (>3 pts/m²) eliminar, si baja dedup
            bounds = pc.bounds
            if bounds:
                area = (bounds[3] - bounds[0]) * (bounds[4] - bounds[1])
                density = pc.point_count / area if area > 0 else 0
                strategy = "remove" if density > 3.0 else "dedup"
            else:
                strategy = "remove"
        else:
            strategy = "dedup"  # unknown: conservador
        logger.info(f"Sensor '{pc.sensor_type}' → estrategia overlap: {strategy}")

    if strategy == "keep":
        logger.info("Overlap conservado sin cambios")
        return pc

    elif strategy == "remove":
        mask = pc.classification != 12
        result = pc.subset(mask)
        result.name = f"{pc.name}_no_overlap"
        logger.info(f"Overlap eliminado: {overlap_count:,} puntos")
        return result

    elif strategy == "dedup":
        # Separar overlap del resto
        overlap_mask = pc.classification == 12
        non_overlap = pc.subset(~overlap_mask)
        overlap_pc = pc.subset(overlap_mask)

        # Voxel dedup solo sobre los overlap
        bounds = pc.bounds
        if bounds:
            area = (bounds[3] - bounds[0]) * (bounds[4] - bounds[1])
            density = overlap_count / area if area > 0 else 0
            # Tamaño de voxel adaptativo según densidad
            voxel_size = max(0.1, min(0.5, 1.0 / density ** 0.5)) if density > 0 else 0.25
        else:
            voxel_size = 0.25

        deduped = overlap_pc.decimate_for_display(voxel_size=voxel_size)
        # Mantener clase 12 — no reclasificar, solo reducir densidad
        result = PointCloudData.merge([non_overlap, deduped], f"{pc.name}_deduped")
        result.crs_wkt = pc.crs_wkt
        result.crs_epsg = pc.crs_epsg
        removed = overlap_count - int(np.sum(deduped.classification == 12))
        logger.info(f"Overlap dedup: {overlap_count:,} → {np.sum(deduped.classification == 12):,} puntos ({removed:,} eliminados)")
        return result

    return pc