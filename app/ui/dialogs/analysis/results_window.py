"""
ALAS — Analysis Results Window
Base results window shared by all analysis tabs.
Each tab subclasses this and overrides _get_legend_text() and _render_layer().
"""

from __future__ import annotations

import os
import re
import tempfile

import numpy as np

from PyQt6.QtWidgets import (
    QMainWindow, QScrollArea, QWidget, QVBoxLayout, QGroupBox, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.analysis_results_window")


class AnalysisResultsWindow(QMainWindow):
    """
    Base window that renders a dict of {layer_type: RasterLayer} results
    as images with legend captions and per-layer statistics.

    Subclasses override:
        TAB_TYPE          — used for the window title i18n key
        _render_layer()   — returns (rgba, qimage, pixmap) for one layer
        _get_legend_text()— returns HTML legend string for one layer
    """

    TAB_TYPE: str = ""

    def __init__(self, results: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr(f"analysis.{self.TAB_TYPE}_results"))
        self.setMinimumSize(1000, 800)
        self._setup_ui(results)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self, results: dict):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)

        for layer_type, raster_layer in results.items():
            grp = QGroupBox(tr("analysis.result").format(layer_type.replace("_", " ").title()))
            grp_layout = QVBoxLayout(grp)

            # Image
            try:
                _, _, pixmap = self._render_layer(layer_type, raster_layer)

                lbl_img = QLabel()
                lbl_img.setPixmap(pixmap)
                lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
                grp_layout.addWidget(lbl_img)

            except Exception as e:
                logger.error(f"Error rendering {layer_type}: {e}", exc_info=True)
                lbl_err = QLabel(f"⚠ {e}")
                lbl_err.setStyleSheet("color: #e74c3c; padding: 8px;")
                lbl_err.setWordWrap(True)
                grp_layout.addWidget(lbl_err)

            # Legend
            try:
                legend_html = self._get_legend_text(layer_type, raster_layer)
                lbl_legend = QLabel(legend_html)
                lbl_legend.setTextFormat(Qt.TextFormat.RichText)
                lbl_legend.setStyleSheet("color: #999; font-size: 11px; margin-top: 10px;")
                lbl_legend.setWordWrap(True)
                grp_layout.addWidget(lbl_legend)
            except Exception as e:
                logger.warning(f"Legend error {layer_type}: {e}")

            # Per-layer statistics
            stats = self._collect_layer_stats(layer_type, raster_layer)
            if stats:
                stats_header = QLabel(f"<b>{tr('analysis.layer_statistics')}</b>")
                stats_header.setStyleSheet("margin-top: 8px; font-size: 11px;")
                grp_layout.addWidget(stats_header)

                tbl = QTableWidget(len(stats), 2)
                tbl.setHorizontalHeaderLabels(["Metric", "Value"])
                tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
                tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
                tbl.verticalHeader().setVisible(False)
                tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
                tbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                row_h = tbl.verticalHeader().defaultSectionSize()
                header_h = tbl.horizontalHeader().height()
                tbl.setFixedHeight(len(stats) * row_h + header_h + 2)

                for row, (k, v) in enumerate(stats.items()):
                    tbl.setItem(row, 0, QTableWidgetItem(str(k)))
                    val_str = f"{v:.4f}" if isinstance(v, float) else str(v)
                    tbl.setItem(row, 1, QTableWidgetItem(val_str))

                grp_layout.addWidget(tbl)

            layout.addWidget(grp)

        layout.addStretch()
        scroll.setWidget(container)
        self.setCentralWidget(scroll)

    # ------------------------------------------------------------------
    # Overridable interface
    # ------------------------------------------------------------------

    def _render_layer(self, layer_type: str, raster_layer):
        """
        Render raster_layer to (rgba_array, QImage, QPixmap).
        Default falls back to the hydro renderer then the generic renderer.
        """
        try:
            from app.rendering.hydro_renderer import HydroRenderer, array_to_qimage
            renderer = HydroRenderer(raster_layer, layer_type)
            rgba = renderer.render()
            qimage = array_to_qimage(rgba)
        except Exception:
            from app.rendering.generic_renderer import GenericRenderer, array_to_qimage
            renderer = GenericRenderer(raster_layer, layer_type)
            rgba = renderer.render()
            qimage = array_to_qimage(rgba)

        pixmap = QPixmap.fromImage(qimage)
        pixmap = pixmap.scaledToWidth(800, Qt.TransformationMode.SmoothTransformation)
        return rgba, qimage, pixmap

    def _get_legend_text(self, layer_type: str, raster_layer=None) -> str:
        """Return an HTML legend string. Override in each subclass."""
        return "No legend information available."

    # ------------------------------------------------------------------
    # Statistics helpers
    # ------------------------------------------------------------------

    def _collect_layer_stats(self, layer_type: str, raster_layer) -> dict:
        """Extract per-layer statistics for display."""
        stats = {}
        if hasattr(raster_layer, "statistics") and callable(raster_layer.statistics):
            try:
                stats = raster_layer.statistics()
            except Exception:
                pass
        elif isinstance(raster_layer, np.ndarray):
            # For point arrays like tree_tops (N, 3)
            try:
                arr = raster_layer
                if arr.ndim == 2 and arr.shape[1] == 3:
                    stats = {
                        "Count": int(len(arr)),
                        "Min height (m)": float(np.min(arr[:, 2])),
                        "Max height (m)": float(np.max(arr[:, 2])),
                        "Mean height (m)": float(np.mean(arr[:, 2])),
                    }
            except Exception:
                pass
        return stats

    # ------------------------------------------------------------------
    # PDF rendering helper
    # ------------------------------------------------------------------

    @classmethod
    def render_for_pdf(cls, results: dict) -> tuple:
        """
        Render all layers to temp PNG files for PDF export.
        Returns (pdf_data_dict, temp_dir_path).
        pdf_data_dict: {layer_type: {'image': path|None, 'legend': str, 'stats': dict}}
        """
        temp_dir = tempfile.mkdtemp(prefix="alas_pdf_")
        pdf_data = {}

        # Create a real (invisible) instance with empty results so we can call
        # _render_layer / _get_legend_text without Qt widget state issues.
        helper = cls.__new__(cls)
        try:
            QMainWindow.__init__(helper, None)
        except Exception:
            pass

        for layer_type, raster_layer in results.items():
            img_path = None
            try:
                _, _, pixmap = helper._render_layer(layer_type, raster_layer)
                img_path = os.path.join(temp_dir, f"{layer_type}.png")
                if not pixmap.save(img_path, "PNG"):
                    logger.warning(f"Failed to save PNG for {layer_type}")
                    img_path = None
            except Exception as e:
                logger.warning(f"Cannot render {layer_type} for PDF: {e}")

            stats = {}
            try:
                stats = helper._collect_layer_stats(layer_type, raster_layer)
            except Exception:
                pass

            legend = ""
            try:
                raw = helper._get_legend_text(layer_type, raster_layer)
                legend = re.sub(r"<[^>]+>", "", raw)
            except Exception:
                pass

            pdf_data[layer_type] = {"image": img_path, "legend": legend, "stats": stats}

        try:
            helper.deleteLater()
        except Exception:
            pass

        return pdf_data, temp_dir
