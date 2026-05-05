"""
ALAS — I/O Handler
Lectura y escritura de archivos LAS/LAZ con laspy y PDAL.
"""

import json
import numpy as np
from pathlib import Path
from typing import Optional, List

from app.core.point_cloud import PointCloudData
from app.logger import get_logger

logger = get_logger("processing.io")


def read_las(path: str) -> PointCloudData:
    """Lee un archivo LAS/LAZ usando laspy."""
    return PointCloudData.from_file(path)


def write_las(pc: PointCloudData, path: str, compress: bool = True):
    """Escribe un archivo LAS/LAZ."""
    pc.to_file(path, compress=compress)


def read_with_pdal(path: str, extra_stages: list = None) -> np.ndarray:
    """
    Lee un archivo usando un pipeline PDAL.
    Devuelve un array NumPy estructurado.
    """
    import pdal

    pipeline_stages = [{"type": "readers.las", "filename": str(path)}]
    if extra_stages:
        pipeline_stages.extend(extra_stages)

    pipeline_json = json.dumps(pipeline_stages)
    pipeline = pdal.Pipeline(pipeline_json)
    count = pipeline.execute()
    logger.info(f"PDAL procesó {count:,} puntos de {Path(path).name}")

    arrays = pipeline.arrays
    if arrays:
        return arrays[0]
    return np.array([])


def pdal_pipeline_execute(stages: list) -> np.ndarray:
    """
    Ejecuta un pipeline PDAL arbitrario.
    stages: lista de diccionarios de etapas PDAL.
    """
    import pdal

    pipeline_json = json.dumps(stages)
    pipeline = pdal.Pipeline(pipeline_json)
    count = pipeline.execute()
    logger.info(f"Pipeline PDAL ejecutado: {count:,} puntos")

    arrays = pipeline.arrays
    if arrays:
        return arrays[0]
    return np.array([])


def get_file_info(path: str) -> dict:
    """Obtiene información básica de un archivo LAS/LAZ sin leer todos los puntos."""
    import laspy

    with laspy.open(str(path)) as reader:
        header = reader.header
        # system_identifier puede ser bytes o str según versión de laspy
        sys_id = header.system_identifier
        if isinstance(sys_id, bytes):
            system_id = sys_id.decode('utf-8', errors='ignore').strip()
        else:
            system_id = str(sys_id).strip() if sys_id else None
        info = {
            "file": str(path),
            "version": f"{header.version.major}.{header.version.minor}",
            "point_format": header.point_format.id,
            "point_count": header.point_count,
            "system_identifier": system_id,
            "scale": list(header.scales),
            "offset": list(header.offsets),
            "mins": list(header.mins),
            "maxs": list(header.maxs),
        }
    return info


def merge_files(paths: List[str]) -> PointCloudData:
    """Fusiona múltiples archivos LAS/LAZ."""
    clouds = [PointCloudData.from_file(p) for p in paths]
    return PointCloudData.merge(clouds, "merged")
