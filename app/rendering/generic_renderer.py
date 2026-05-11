"""
ALAS — Generic Renderer
Universal raster renderer for geomorphology, vegetation, and multitemporal layers.
"""
from __future__ import annotations

import numpy as np
from matplotlib.colors import Normalize, LinearSegmentedColormap, ListedColormap
from matplotlib import cm
from PyQt6.QtGui import QImage

from app.config import DEFAULT_NODATA
from app.core.raster_layer import RasterLayer

_CMAPS: dict = {
    # Geomorphology
    "slope": LinearSegmentedColormap.from_list(
        "slope", ["#ffffcc", "#fd8d3c", "#e31a1c", "#800026"], N=256
    ),
    "aspect": cm.get_cmap("hsv"),
    "curvature": cm.get_cmap("RdBu_r"),
    "roughness": LinearSegmentedColormap.from_list(
        "roughness", ["#f7fcf5", "#41ab5d", "#00441b"], N=256
    ),
    "hillshade": cm.get_cmap("gray"),
    "morpho": cm.get_cmap("tab10"),
    # Multitemporal
    "dod": cm.get_cmap("RdBu"),
    "change_class": ListedColormap(["#d62728", "#cccccc", "#1f77b4"]),
    "deforestation": ListedColormap(["#cccccc", "#d62728", "#2ca02c"]),
    # Vegetation
    "crown_raster": cm.get_cmap("tab20"),
    "density": LinearSegmentedColormap.from_list(
        "density", ["#f7fcf5", "#74c476", "#00441b"], N=256
    ),
}

_DIVERGING = {"curvature", "dod"}
_ASPECT = {"aspect"}
_CATEGORICAL = {"morpho", "change_class", "deforestation", "crown_raster"}


class GenericRenderer:
    """Fallback renderer for all layer types not handled by HydroRenderer."""

    def __init__(self, layer, layer_type: str):
        self.layer_type = layer_type
        self._source = layer
        self.array = self._extract_array(layer)
        self.nodata = self._extract_nodata(layer)

    @staticmethod
    def _extract_array(layer) -> np.ndarray:
        if isinstance(layer, np.ndarray):
            arr = layer
        elif isinstance(layer, RasterLayer):
            arr = layer.data if layer.data is not None else np.zeros((1, 1), dtype=np.float32)
        elif hasattr(layer, "data"):
            arr = layer.data
        else:
            raise TypeError(f"Cannot extract array from {type(layer).__name__}")
        arr = np.asarray(arr, dtype=np.float32)
        if arr.ndim > 2:
            arr = arr[0]
        elif arr.ndim < 2:
            arr = arr.reshape(1, -1)
        return arr

    @staticmethod
    def _extract_nodata(layer) -> float:
        if hasattr(layer, "nodata"):
            return float(layer.nodata)
        return DEFAULT_NODATA

    def render(self) -> np.ndarray:
        arr = self.array
        nodata = self.nodata
        mask = np.isnan(arr) | (arr == nodata)
        valid = ~mask

        cmap = _CMAPS.get(self.layer_type, cm.get_cmap("viridis"))
        rgba = np.zeros((*arr.shape, 4), dtype=np.float32)

        if np.any(valid):
            vals = arr[valid]
            if self.layer_type in _DIVERGING:
                vmax = float(np.nanpercentile(np.abs(vals), 98))
                norm = Normalize(vmin=-max(vmax, 1e-6), vmax=max(vmax, 1e-6))
            elif self.layer_type in _ASPECT:
                norm = Normalize(vmin=0.0, vmax=360.0)
            elif self.layer_type in _CATEGORICAL:
                vmin = float(np.nanmin(vals))
                vmax = float(np.nanmax(vals))
                norm = Normalize(vmin=vmin, vmax=max(vmax, vmin + 1.0))
            else:
                p2 = float(np.nanpercentile(vals, 2))
                p98 = float(np.nanpercentile(vals, 98))
                norm = Normalize(vmin=p2, vmax=max(p98, p2 + 1e-6))

            rgba[valid] = cmap(norm(arr[valid]))

            if self.layer_type in _ASPECT:
                flat = valid & (arr == -1)
                rgba[flat] = [0.5, 0.5, 0.5, 1.0]

        rgba[mask] = 0.0
        return np.clip(rgba * 255.0, 0, 255).astype(np.uint8)


def array_to_qimage(rgba: np.ndarray) -> QImage:
    if rgba.dtype != np.uint8:
        rgba = np.clip(rgba, 0, 255).astype(np.uint8)
    rgba = np.ascontiguousarray(rgba)
    h, w = rgba.shape[:2]
    return QImage(rgba.data, w, h, w * 4, QImage.Format.Format_RGBA8888)
