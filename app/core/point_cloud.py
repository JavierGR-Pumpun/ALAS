"""
ALAS — PointCloudData
Wrapper sobre laspy + NumPy para nubes de puntos LiDAR.
"""

import numpy as np
from pathlib import Path
from typing import Optional, Tuple, Dict, List
import laspy

from app.config import (
    ASPRS_COLORS, MAX_VIEWPORT_POINTS, VOXEL_DOWNSAMPLE_SIZE
)
from app.logger import get_logger

logger = get_logger("core.point_cloud")


class PointCloudData:
    """
    Clase envoltorio para datos de nubes de puntos LiDAR.
    Almacena arrays NumPy y metadatos de forma eficiente.
    """

    def __init__(self):
        self.xyz: Optional[np.ndarray] = None           # (N, 3) float64
        self.intensity: Optional[np.ndarray] = None      # (N,) uint16
        self.classification: Optional[np.ndarray] = None # (N,) uint8
        self.return_number: Optional[np.ndarray] = None  # (N,) uint8
        self.number_of_returns: Optional[np.ndarray] = None  # (N,) uint8
        self.rgb: Optional[np.ndarray] = None            # (N, 3) uint16
        self.gps_time: Optional[np.ndarray] = None       # (N,) float64

        # Metadata
        self.file_path: Optional[str] = None
        self.crs_wkt: Optional[str] = None
        self.crs_epsg: Optional[int] = None
        self.point_format: Optional[int] = None
        self.file_version: Optional[str] = None
        self.creation_date: Optional[str] = None
        self.extra_dims: Dict[str, np.ndarray] = {}

        # Name for layer panel
        self.name: str = "Sin nombre"

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def point_count(self) -> int:
        if self.xyz is None:
            return 0
        return self.xyz.shape[0]

    @property
    def bounds(self) -> Optional[Tuple[float, float, float, float, float, float]]:
        """Devuelve (xmin, ymin, zmin, xmax, ymax, zmax)."""
        if self.xyz is None or len(self.xyz) == 0:
            return None
        mins = self.xyz.min(axis=0)
        maxs = self.xyz.max(axis=0)
        return (mins[0], mins[1], mins[2], maxs[0], maxs[1], maxs[2])

    @property
    def centroid(self) -> Optional[np.ndarray]:
        if self.xyz is None:
            return None
        return self.xyz.mean(axis=0)

    @property
    def available_dimensions(self) -> List[str]:
        dims = ["x", "y", "z"]
        if self.intensity is not None:
            dims.append("intensity")
        if self.classification is not None:
            dims.append("classification")
        if self.return_number is not None:
            dims.append("return_number")
        if self.rgb is not None:
            dims.append("rgb")
        if self.gps_time is not None:
            dims.append("gps_time")
        dims.extend(self.extra_dims.keys())
        return dims

    @property
    def has_rgb(self) -> bool:
        return self.rgb is not None and len(self.rgb) > 0

    @property
    def unique_classifications(self) -> Optional[np.ndarray]:
        if self.classification is None:
            return None
        return np.unique(self.classification)

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    @classmethod
    def from_file(cls, path: str) -> "PointCloudData":
        """Lee un archivo LAS/LAZ y devuelve PointCloudData."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        logger.info(f"Leyendo nube de puntos: {path.name}")
        las = laspy.read(str(path))

        pc = cls()
        pc.file_path = str(path)
        pc.name = path.stem

        # Coordenadas
        pc.xyz = np.column_stack([
            las.x.astype(np.float64),
            las.y.astype(np.float64),
            las.z.astype(np.float64),
        ])

        # Intensidad
        if hasattr(las, "intensity"):
            pc.intensity = np.array(las.intensity, dtype=np.uint16)

        # Clasificación
        if hasattr(las, "classification"):
            pc.classification = np.array(las.classification, dtype=np.uint8)

        # Retornos
        if hasattr(las, "return_number"):
            pc.return_number = np.array(las.return_number, dtype=np.uint8)
        if hasattr(las, "number_of_returns"):
            pc.number_of_returns = np.array(las.number_of_returns, dtype=np.uint8)

        # RGB
        try:
            if hasattr(las, "red") and hasattr(las, "green") and hasattr(las, "blue"):
                pc.rgb = np.column_stack([
                    np.array(las.red, dtype=np.uint16),
                    np.array(las.green, dtype=np.uint16),
                    np.array(las.blue, dtype=np.uint16),
                ])
        except Exception:
            pass

        # GPS time
        if hasattr(las, "gps_time"):
            pc.gps_time = np.array(las.gps_time, dtype=np.float64)

        # CRS
        pc._extract_crs(las)

        # File info
        pc.point_format = las.header.point_format.id
        pc.file_version = f"{las.header.version.major}.{las.header.version.minor}"

        logger.info(
            f"Cargados {pc.point_count:,} puntos | "
            f"CRS: EPSG:{pc.crs_epsg or 'desconocido'} | "
            f"Formato: {pc.point_format}"
        )
        return pc

    def _extract_crs(self, las: laspy.LasData):
        """Extrae información CRS de los VLR del archivo LAS."""
        try:
            for vlr in las.vlrs:
                # WKT
                if vlr.record_id == 2112:
                    self.crs_wkt = vlr.record_data.decode("utf-8", errors="ignore").strip("\x00")
                    break
            # Intentar extraer EPSG del WKT
            if self.crs_wkt:
                self._parse_epsg_from_wkt(self.crs_wkt)
        except Exception as e:
            logger.debug(f"No se pudo extraer CRS: {e}")

        # Segundo intento: usar pyproj si hay WKT
        if self.crs_wkt and self.crs_epsg is None:
            try:
                from pyproj import CRS
                crs = CRS.from_wkt(self.crs_wkt)
                self.crs_epsg = crs.to_epsg()
            except Exception:
                pass

    def _parse_epsg_from_wkt(self, wkt: str):
        """Intenta extraer código EPSG del WKT."""
        import re
        match = re.search(r'AUTHORITY\["EPSG","(\d+)"\]', wkt)
        if match:
            self.crs_epsg = int(match.group(1))
            return
        match = re.search(r'"EPSG",(\d+)', wkt)
        if match:
            self.crs_epsg = int(match.group(1))

    def to_file(self, path: str, compress: bool = True):
        """Escribe la nube de puntos a LAS/LAZ."""
        if self.xyz is None:
            raise ValueError("No hay datos para guardar.")

        path = Path(path)
        logger.info(f"Guardando nube: {path.name} ({self.point_count:,} puntos)")

        # Determinar formato de punto
        point_format_id = self.point_format or 0
        if self.has_rgb and point_format_id < 2:
            point_format_id = 2

        header = laspy.LasHeader(point_format=point_format_id, version="1.4")

        # Escala y offset
        mins = self.xyz.min(axis=0)
        maxs = self.xyz.max(axis=0)
        ranges = maxs - mins
        header.offsets = mins
        header.scales = np.where(ranges > 0, ranges / (2**31 - 1), 0.001)

        las = laspy.LasData(header)
        las.x = self.xyz[:, 0]
        las.y = self.xyz[:, 1]
        las.z = self.xyz[:, 2]

        if self.intensity is not None:
            las.intensity = self.intensity
        if self.classification is not None:
            las.classification = self.classification
        if self.return_number is not None:
            las.return_number = self.return_number
        if self.number_of_returns is not None:
            las.number_of_returns = self.number_of_returns
        if self.has_rgb:
            las.red = self.rgb[:, 0]
            las.green = self.rgb[:, 1]
            las.blue = self.rgb[:, 2]

        # CRS como VLR WKT
        if self.crs_wkt:
            from laspy import VLR
            vlr = VLR("LASF_Projection", 2112,
                       self.crs_wkt.encode("utf-8"))
            las.vlrs.append(vlr)

        path.parent.mkdir(parents=True, exist_ok=True)
        if compress or path.suffix.lower() == ".laz":
            las.write(str(path), laz_backend=laspy.LazBackend.Lazrs)
        else:
            las.write(str(path))

        logger.info(f"Guardado completado: {path}")

    # ------------------------------------------------------------------
    # Subsetting
    # ------------------------------------------------------------------

    def subset(self, mask: np.ndarray) -> "PointCloudData":
        """Devuelve un nuevo PointCloudData con solo los puntos del mask."""
        pc = PointCloudData()
        pc.xyz = self.xyz[mask].copy()
        pc.name = f"{self.name}_subset"
        pc.crs_wkt = self.crs_wkt
        pc.crs_epsg = self.crs_epsg

        if self.intensity is not None:
            pc.intensity = self.intensity[mask].copy()
        if self.classification is not None:
            pc.classification = self.classification[mask].copy()
        if self.return_number is not None:
            pc.return_number = self.return_number[mask].copy()
        if self.number_of_returns is not None:
            pc.number_of_returns = self.number_of_returns[mask].copy()
        if self.has_rgb:
            pc.rgb = self.rgb[mask].copy()
        if self.gps_time is not None:
            pc.gps_time = self.gps_time[mask].copy()

        for dim_name, arr in self.extra_dims.items():
            pc.extra_dims[dim_name] = arr[mask].copy()

        return pc

    def get_ground_points(self) -> "PointCloudData":
        """Devuelve solo los puntos clasificados como suelo (class 2)."""
        if self.classification is None:
            raise ValueError("La nube no tiene clasificación.")
        mask = self.classification == 2
        pc = self.subset(mask)
        pc.name = f"{self.name}_ground"
        return pc

    def get_non_ground_points(self) -> "PointCloudData":
        """Devuelve puntos que no son suelo."""
        if self.classification is None:
            raise ValueError("La nube no tiene clasificación.")
        mask = self.classification != 2
        pc = self.subset(mask)
        pc.name = f"{self.name}_non_ground"
        return pc

    def get_first_returns(self) -> "PointCloudData":
        """Devuelve solo los primeros retornos."""
        if self.return_number is None:
            raise ValueError("La nube no tiene información de retornos.")
        mask = self.return_number == 1
        pc = self.subset(mask)
        pc.name = f"{self.name}_first_returns"
        return pc

    # ------------------------------------------------------------------
    # Decimation for visualization
    # ------------------------------------------------------------------

    def decimate_for_display(self, max_points: int = None,
                              voxel_size: float = None) -> "PointCloudData":
        """
        Decima la nube para visualización eficiente.
        Usa voxel downsampling o random sampling.
        """
        if max_points is None:
            max_points = MAX_VIEWPORT_POINTS
        if self.point_count <= max_points:
            return self

        if voxel_size is None:
            voxel_size = VOXEL_DOWNSAMPLE_SIZE

        logger.info(
            f"Decimando {self.point_count:,} → ~{max_points:,} puntos "
            f"(voxel={voxel_size}m)"
        )

        # Voxel grid downsampling via numpy
        coords = self.xyz
        voxel_indices = np.floor(coords / voxel_size).astype(np.int64)

        # Unique voxels — keep one random point per voxel
        _, unique_idx = np.unique(
            voxel_indices, axis=0, return_index=True
        )

        # Si aún hay demasiados, submuestrear aleatoriamente
        if len(unique_idx) > max_points:
            rng = np.random.default_rng(42)
            unique_idx = rng.choice(unique_idx, max_points, replace=False)

        unique_idx = np.sort(unique_idx)
        mask = np.zeros(self.point_count, dtype=bool)
        mask[unique_idx] = True

        result = self.subset(mask)
        result.name = f"{self.name}_display"
        logger.info(f"Decimado a {result.point_count:,} puntos")
        return result

    # ------------------------------------------------------------------
    # Classification stats
    # ------------------------------------------------------------------

    def classification_summary(self) -> Dict[int, int]:
        """Devuelve conteo de puntos por clase."""
        if self.classification is None:
            return {}
        classes, counts = np.unique(self.classification, return_counts=True)
        return dict(zip(classes.tolist(), counts.tolist()))

    def height_stats(self) -> Dict[str, float]:
        """Estadísticas básicas de altura (Z)."""
        if self.xyz is None:
            return {}
        z = self.xyz[:, 2]
        return {
            "min": float(z.min()),
            "max": float(z.max()),
            "mean": float(z.mean()),
            "std": float(z.std()),
            "median": float(np.median(z)),
        }

    # ------------------------------------------------------------------
    # Merge
    # ------------------------------------------------------------------

    @staticmethod
    def merge(clouds: List["PointCloudData"],
              name: str = "merged") -> "PointCloudData":
        """Fusiona múltiples nubes de puntos en una sola."""
        if not clouds:
            raise ValueError("No hay nubes para fusionar.")

        result = PointCloudData()
        result.name = name
        result.crs_wkt = clouds[0].crs_wkt
        result.crs_epsg = clouds[0].crs_epsg

        # Concatenar arrays
        xyz_list = [c.xyz for c in clouds if c.xyz is not None]
        result.xyz = np.vstack(xyz_list)

        # Intensidad
        int_list = [c.intensity for c in clouds if c.intensity is not None]
        if len(int_list) == len(clouds):
            result.intensity = np.concatenate(int_list)

        # Clasificación
        cls_list = [c.classification for c in clouds if c.classification is not None]
        if len(cls_list) == len(clouds):
            result.classification = np.concatenate(cls_list)

        # Retornos
        ret_list = [c.return_number for c in clouds if c.return_number is not None]
        if len(ret_list) == len(clouds):
            result.return_number = np.concatenate(ret_list)

        nor_list = [c.number_of_returns for c in clouds if c.number_of_returns is not None]
        if len(nor_list) == len(clouds):
            result.number_of_returns = np.concatenate(nor_list)

        # RGB
        rgb_list = [c.rgb for c in clouds if c.rgb is not None]
        if len(rgb_list) == len(clouds):
            result.rgb = np.vstack(rgb_list)

        logger.info(f"Fusionadas {len(clouds)} nubes → {result.point_count:,} puntos")
        return result
