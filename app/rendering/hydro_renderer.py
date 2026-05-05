"""
ALAS — Hydro Renderer
Renderizado de resultados hidrológicos a imágenes RGBA y figuras Matplotlib.
"""

from __future__ import annotations

import numpy as np
from typing import Optional, Union
from matplotlib.colors import ListedColormap, LinearSegmentedColormap, LogNorm, Normalize
from matplotlib import cm
from PyQt6.QtGui import QImage

from app.config import DEFAULT_NODATA
from app.core.raster_layer import RasterLayer
from app.logger import get_logger

logger = get_logger("rendering.hydro_renderer")

_FLOW_DIRECTION_VALUES = [1, 2, 4, 8, 16, 32, 64, 128]
_FLOW_DIRECTION_LABELS = {
    1: "E",
    2: "SE",
    4: "S",
    8: "SW",
    16: "W",
    32: "NW",
    64: "N",
    128: "NE",
}
_FLOW_DIRECTION_COLORS = [
    (31, 119, 180),   # azul
    (255, 127, 14),   # naranja
    (44, 160, 44),    # verde
    (214, 39, 40),    # rojo
    (148, 103, 189),  # morado
    (140, 86, 75),    # marrón
    (227, 119, 194),  # rosa
    (127, 127, 127),  # gris
]
_WATERSHED_BINARY_COLOR = (41, 128, 185, 200)

_FLOW_DIRECTION_CMAP = ListedColormap([
    tuple(c / 255.0 for c in rgb) for rgb in _FLOW_DIRECTION_COLORS
], name="flow_direction")

_FLOW_ACC_CMAP = LinearSegmentedColormap.from_list(
    "hydro_flow_acc",
    ["#ffffff", "#3a79e0", "#001f3f"],
    N=256
)

_TERRAIN_CMAP = cm.get_cmap("terrain")

_ALLOWED_LAYER_TYPES = {
    "flow_direction",
    "flow_accumulation",
    "watershed",
    "ponding",
    "conditioned_dem",
    "rainfall_runoff",
}


class HydroRenderer:
    """Renderizador de capas hidrológicas a RGBA y figuras."""

    def __init__(self, layer: Union[RasterLayer, np.ndarray], layer_type: str):
        self.layer_type = layer_type
        self._source_layer = layer
        self.array = self._extract_array(layer)
        self.nodata = self._extract_nodata(layer)

    def render(self) -> np.ndarray:
        """Devuelve un array RGBA uint8 listo para mostrar en PyQt."""
        if self.layer_type not in _ALLOWED_LAYER_TYPES:
            raise ValueError(f"Tipo de capa no válido: {self.layer_type}")

        if self.layer_type == "flow_direction":
            rgba = self._render_flow_direction()
        elif self.layer_type == "flow_accumulation":
            rgba = self._render_flow_accumulation()
        elif self.layer_type == "watershed":
            rgba = self._render_watershed()
        elif self.layer_type == "ponding":
            rgba = self._render_ponding()
        elif self.layer_type == "conditioned_dem":
            rgba = self._render_conditioned_dem()
        elif self.layer_type == "rainfall_runoff":
            rgba = self._render_rainfall_runoff()
        else:
            raise ValueError(f"Tipo de capa no soportado: {self.layer_type}")

        return rgba

    @staticmethod
    def _extract_array(layer: Union[RasterLayer, np.ndarray]) -> np.ndarray:
        if isinstance(layer, RasterLayer):
            if layer.data is None:
                raise ValueError("RasterLayer sin datos.")
            data = layer.data
        elif isinstance(layer, np.ndarray):
            data = layer
        elif hasattr(layer, "data"):
            data = getattr(layer, "data")
        elif hasattr(layer, "array"):
            data = getattr(layer, "array")
        elif hasattr(layer, "values"):
            data = getattr(layer, "values")
        else:
            raise TypeError("La capa debe ser RasterLayer o np.ndarray.")

        arr = np.asarray(data, dtype=np.float32)
        if arr.ndim > 2:
            arr = arr[0]
        return arr

    @staticmethod
    def _extract_nodata(layer: Union[RasterLayer, np.ndarray]) -> float:
        if isinstance(layer, RasterLayer):
            return layer.nodata
        return DEFAULT_NODATA

    def _mask_nodata(self, arr: np.ndarray) -> np.ndarray:
        mask = np.isnan(arr) | (arr == self.nodata)
        return mask

    def _build_rgba(self, base_rgba: np.ndarray, mask: np.ndarray) -> np.ndarray:
        rgba = np.asarray(base_rgba, dtype=np.float32)
        if rgba.ndim != 3 or rgba.shape[2] != 4:
            raise ValueError("La imagen debe tener forma (H, W, 4).")
        rgba = np.clip(rgba * 255.0, 0, 255).astype(np.uint8)
        rgba[mask] = np.array([0, 0, 0, 0], dtype=np.uint8)
        return rgba

    def _render_flow_direction(self) -> np.ndarray:
        data = self.array
        if data.ndim != 2:
            raise ValueError("flow_direction espera un array 2D.")

        mask = self._mask_nodata(data)
        index = np.full(data.shape, -1, dtype=np.int32)
        for idx, value in enumerate(_FLOW_DIRECTION_VALUES):
            index[data == value] = idx

        rgba = _FLOW_DIRECTION_CMAP(index)
        rgba[..., 3] = np.where(mask, 0.0, 1.0)
        return self._build_rgba(rgba, mask)

    def _render_flow_accumulation(self) -> np.ndarray:
        data = self.array.astype(np.float32)
        mask = self._mask_nodata(data) | (data < 1.0)
        shaded = np.full((*data.shape, 4), 0.0, dtype=np.float32)

        valid = ~mask
        if np.any(valid):
            data_vis = data.copy()
            data_vis[data_vis < 1.0] = np.nan
            vmax = float(np.nanpercentile(data_vis[valid], 99.5)) if np.any(valid) else 1.0
            vmin = 1.0
            norm = LogNorm(vmin=vmin, vmax=max(vmax, vmin))
            cmap = _FLOW_ACC_CMAP
            rgba = cmap(norm(data_vis))
            shaded[valid] = rgba[valid]
            shaded[mask, 3] = 0.0
        return self._build_rgba(shaded, mask)

    def _render_watershed(self) -> np.ndarray:
        data = self.array
        mask = self._mask_nodata(data) | (data == 0)
        unique = np.unique(data[~mask]) if np.any(~mask) else np.array([], dtype=data.dtype)

        if unique.size == 1 and unique[0] == 1:
            rgba = np.zeros((*data.shape, 4), dtype=np.float32)
            rgba[data == 1] = np.array(_WATERSHED_BINARY_COLOR, dtype=np.float32) / 255.0
            rgba[data == 1, 3] = _WATERSHED_BINARY_COLOR[3] / 255.0
            rgba[mask] = 0.0
            return self._build_rgba(rgba, mask)

        cmap = cm.get_cmap("tab20", lut=max(1, len(unique)))
        rgba = np.zeros((*data.shape, 4), dtype=np.float32)
        for idx, value in enumerate(unique):
            rgba[data == value] = cmap(idx)
        rgba[mask] = 0.0
        return self._build_rgba(rgba, mask)

    def _render_ponding(self) -> np.ndarray:
        data = self.array.astype(np.float32)
        mask = self._mask_nodata(data)
        zero_mask = (data == 0) & ~mask
        valid = (~mask) & (~zero_mask)

        rgba = np.zeros((*data.shape, 4), dtype=np.float32)
        if np.any(valid):
            nonzero = data[valid]
            vmax = float(np.percentile(nonzero, 98)) if nonzero.size else 1.0
            norm = Normalize(vmin=0.0, vmax=max(vmax, 0.0))
            cmap = _TERRAIN_CMAP
            rgba[valid] = cmap(norm(data[valid]))
        rgba[zero_mask] = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)
        rgba[mask] = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)
        return self._build_rgba(rgba, mask | zero_mask)

    def _render_rainfall_runoff(self) -> np.ndarray:
        data = self.array.astype(np.float32)
        mask = self._mask_nodata(data) | (data <= 0.0)
        valid = ~mask

        rgba = np.zeros((*data.shape, 4), dtype=np.float32)
        if np.any(valid):
            rainfall_mm_h = getattr(self._source_layer, "rainfall_mm_h", None)

            if rainfall_mm_h is not None:
                cell_area_m2 = getattr(self._source_layer, "rainfall_cell_area_m2", 1.0)
                total_cells = int(np.sum(valid))
                # Fixed scale 1-150 mm/h so colour intensity is always comparable.
                vmin = float((1.0 / 1000.0) * cell_area_m2 * total_cells * 0.001)
                vmax = float((150.0 / 1000.0) * cell_area_m2 * total_cells)
            else:
                vmax = float(np.nanpercentile(data[valid], 99.5))
                vmin = float(np.nanmin(data[valid]))

            norm = LogNorm(vmin=max(vmin, 1e-9), vmax=max(vmax, vmin + 1e-9))
            cmap = LinearSegmentedColormap.from_list(
                "rainfall_runoff",
                ["#e8f4fd", "#2196f3", "#0d47a1", "#1a237e"],
                N=256
            )
            rgba[valid] = cmap(norm(data[valid]))
        rgba[mask] = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)
        return self._build_rgba(rgba, mask)

    def _render_conditioned_dem(self) -> np.ndarray:
        data = self.array.astype(np.float32)
        mask = self._mask_nodata(data)

        rgba = np.zeros((*data.shape, 4), dtype=np.float32)
        if np.any(~mask):
            valid = ~mask
            vmin = float(np.nanmin(data[valid]))
            vmax = float(np.nanmax(data[valid]))
            norm = Normalize(vmin=vmin, vmax=max(vmax, vmin))
            rgba[valid] = _TERRAIN_CMAP(norm(data[valid]))
        rgba[mask] = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)
        return self._build_rgba(rgba, mask)


def array_to_qimage(rgba: np.ndarray) -> QImage:
    """Convierte un array RGBA uint8 (H, W, 4) a QImage Format_RGBA8888."""
    if rgba.ndim != 3 or rgba.shape[2] != 4:
        raise ValueError("El array debe tener forma (H, W, 4).")
    if rgba.dtype != np.uint8:
        raise ValueError("El array debe ser uint8.")

    rgba = np.ascontiguousarray(rgba)
    height, width = rgba.shape[:2]
    bytes_per_line = width * 4
    return QImage(rgba.data, width, height, bytes_per_line, QImage.Format.Format_RGBA8888)
