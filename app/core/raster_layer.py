"""
ALAS — RasterLayer
Wrapper sobre rasterio para capas raster georreferenciadas.
"""

import numpy as np
from pathlib import Path
from typing import Optional, Tuple, Dict
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS

from app.config import DEFAULT_NODATA, DEFAULT_GEOTIFF_COMPRESS
from app.logger import get_logger

logger = get_logger("core.raster_layer")


class RasterLayer:
    """
    Wrapper para datos raster georreferenciados.
    Almacena array NumPy 2D + metadatos de georreferenciación.
    """

    def __init__(self):
        self.data: Optional[np.ndarray] = None       # (rows, cols) or (bands, rows, cols)
        self.transform = None                        # rasterio Affine transform
        self.crs: Optional[CRS] = None               # rasterio CRS
        self.nodata: float = DEFAULT_NODATA
        self.file_path: Optional[str] = None
        self.name: str = "Sin nombre"
        self.band_names: list = []
        self.dtype = np.float32

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_loaded(self) -> bool:
        return self.data is not None

    @property
    def shape(self) -> Optional[Tuple[int, ...]]:
        if self.data is None:
            return None
        return self.data.shape

    @property
    def height(self) -> int:
        if self.data is None:
            return 0
        return self.data.shape[-2]

    @property
    def width(self) -> int:
        if self.data is None:
            return 0
        return self.data.shape[-1]

    @property
    def band_count(self) -> int:
        if self.data is None:
            return 0
        if self.data.ndim == 2:
            return 1
        return self.data.shape[0]

    @property
    def resolution(self) -> Optional[Tuple[float, float]]:
        if self.transform is None:
            return None
        return (abs(self.transform.a), abs(self.transform.e))

    @property
    def bounds(self) -> Optional[Tuple[float, float, float, float]]:
        """Devuelve (xmin, ymin, xmax, ymax)."""
        if self.transform is None or self.data is None:
            return None
        left = self.transform.c
        top = self.transform.f
        right = left + self.width * self.transform.a
        bottom = top + self.height * self.transform.e
        return (min(left, right), min(top, bottom),
                max(left, right), max(top, bottom))

    @property
    def crs_epsg(self) -> Optional[int]:
        if self.crs is None:
            return None
        try:
            return self.crs.to_epsg()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    @classmethod
    def from_file(cls, path: str) -> "RasterLayer":
        """Lee un archivo raster (GeoTIFF) y devuelve RasterLayer."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        logger.info(f"Leyendo raster: {path.name}")

        rl = cls()
        rl.file_path = str(path)
        rl.name = path.stem

        with rasterio.open(str(path)) as src:
            rl.data = src.read().astype(np.float32)
            if rl.data.shape[0] == 1:
                rl.data = rl.data[0]  # Squeeze single band
            rl.transform = src.transform
            rl.crs = src.crs
            rl.nodata = src.nodata if src.nodata is not None else DEFAULT_NODATA
            rl.dtype = src.dtypes[0]
            rl.band_names = [src.descriptions[i] or f"Band {i+1}"
                             for i in range(src.count)]

        logger.info(
            f"Raster cargado: {rl.width}x{rl.height} | "
            f"CRS: EPSG:{rl.crs_epsg or '?'} | "
            f"Resolución: {rl.resolution}"
        )
        return rl

    def to_geotiff(self, path: str, compress: str = None):
        """Exporta como GeoTIFF."""
        if self.data is None:
            raise ValueError("No hay datos para exportar.")

        compress = compress or DEFAULT_GEOTIFF_COMPRESS
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        write_data = self.data
        if write_data.ndim == 2:
            write_data = write_data[np.newaxis, :, :]  # Add band dimension

        count = write_data.shape[0]
        height = write_data.shape[1]
        width = write_data.shape[2]

        logger.info(f"Exportando GeoTIFF: {path.name} ({width}x{height}, {count} bandas)")

        with rasterio.open(
            str(path), "w",
            driver="GTiff",
            height=height,
            width=width,
            count=count,
            dtype=write_data.dtype,
            crs=self.crs,
            transform=self.transform,
            nodata=self.nodata,
            compress=compress,
        ) as dst:
            for i in range(count):
                dst.write(write_data[i], i + 1)
                if i < len(self.band_names):
                    dst.set_band_description(i + 1, self.band_names[i])

        logger.info(f"GeoTIFF guardado: {path}")

    # ------------------------------------------------------------------
    # Factory: from numpy array + bounds
    # ------------------------------------------------------------------

    @classmethod
    def from_array(cls, data: np.ndarray,
                   bounds: Tuple[float, float, float, float],
                   epsg: int = None,
                   nodata: float = None,
                   name: str = "raster") -> "RasterLayer":
        """
        Crea un RasterLayer desde un array NumPy y extensión geográfica.
        bounds: (xmin, ymin, xmax, ymax)
        """
        rl = cls()
        rl.data = data.astype(np.float32)
        rl.name = name
        rl.nodata = nodata if nodata is not None else DEFAULT_NODATA

        xmin, ymin, xmax, ymax = bounds
        if data.ndim == 2:
            rows, cols = data.shape
        else:
            _, rows, cols = data.shape

        rl.transform = from_bounds(xmin, ymin, xmax, ymax, cols, rows)

        if epsg is not None:
            rl.crs = CRS.from_epsg(epsg)

        return rl

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def statistics(self) -> Dict[str, float]:
        """Estadísticas básicas del raster (ignorando nodata)."""
        if self.data is None:
            return {}
        arr = self.data
        if arr.ndim > 2:
            arr = arr[0]  # First band

        valid = arr[arr != self.nodata]
        if len(valid) == 0:
            return {"min": 0, "max": 0, "mean": 0, "std": 0}

        return {
            "min": float(np.nanmin(valid)),
            "max": float(np.nanmax(valid)),
            "mean": float(np.nanmean(valid)),
            "std": float(np.nanstd(valid)),
            "median": float(np.nanmedian(valid)),
        }

    def get_band(self, band: int = 0) -> np.ndarray:
        """Devuelve una banda como array 2D."""
        if self.data is None:
            raise ValueError("No hay datos.")
        if self.data.ndim == 2:
            return self.data
        return self.data[band]
