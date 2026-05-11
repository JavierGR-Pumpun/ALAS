"""
ALAS — Hydrology Analysis Tab
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QFormLayout, QDoubleSpinBox, QSpinBox,
    QCheckBox, QPushButton, QMessageBox,
)

from app.core.raster_layer import RasterLayer
from app.i18n import tr
from app.logger import get_logger

from .analysis_base import BaseAnalysisTab, show_history_dialog
from .results_window import AnalysisResultsWindow

logger = get_logger("ui.hydrology_tab")


# ---------------------------------------------------------------------------
# Results window
# ---------------------------------------------------------------------------

class HydrologyResultsWindow(AnalysisResultsWindow):
    TAB_TYPE = "hydrology"

    def _render_layer(self, layer_type: str, raster_layer):
        from app.rendering.hydro_renderer import HydroRenderer, array_to_qimage
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt
        renderer = HydroRenderer(raster_layer, layer_type)
        rgba = renderer.render()
        qimage = array_to_qimage(rgba)
        pixmap = QPixmap.fromImage(qimage)
        pixmap = pixmap.scaledToWidth(800, Qt.TransformationMode.SmoothTransformation)
        return rgba, qimage, pixmap

    def _get_legend_text(self, layer_type: str, raster_layer=None) -> str:
        sq = "font-size: 15px;"

        if layer_type == "rainfall_runoff" and raster_layer is not None:
            rainfall_mm_h = getattr(raster_layer, "rainfall_mm_h", None)
            data = raster_layer.data if hasattr(raster_layer, "data") else None
            if rainfall_mm_h is not None and data is not None:
                return (
                    f"<b>{tr('hydro.legend_runoff_title').format(rainfall_mm_h)}</b><br>"
                    f"• <span style='color:#e8f4fd;{sq}'>■</span> {tr('legend.weak')} (&lt;1 mm/h) | "
                    f"<span style='color:#2196f3;{sq}'>■</span> {tr('legend.moderate')} (1–10 mm/h) | "
                    f"<span style='color:#0d47a1;{sq}'>■</span> {tr('legend.strong')} (10–50 mm/h) | "
                    f"<span style='color:#1a237e;{sq}'>■</span> {tr('legend.extreme')} (&gt;50 mm/h)<br>"
                    f"• {tr('legend.scale')} 1–150 mm/h."
                )

        if layer_type == "flood_simulation" and raster_layer is not None:
            import numpy as np
            from app.config import DEFAULT_NODATA
            water_height = getattr(raster_layer, "flood_water_height", None)
            data = raster_layer.data if hasattr(raster_layer, "data") else None
            if water_height is not None and data is not None:
                arr = np.asarray(data, dtype=np.float32)
                if arr.ndim > 2:
                    arr = arr[0]
                valid = arr[(arr != DEFAULT_NODATA) & (arr > 0)]
                max_depth = float(np.max(valid)) if valid.size > 0 else 0.0
                flooded_cells = int(np.sum((arr != DEFAULT_NODATA) & (arr > 0)))
                return (
                    f"<b>{tr('hydro.legend_flood_title').format(water_height)}</b><br>"
                    f"• <span style='color:#aad4f5;{sq}'>■</span> {tr('legend.shallow')} (&lt;0.5 m) | "
                    f"<span style='color:#2196f3;{sq}'>■</span> {tr('legend.moderate')} (0.5–2 m) | "
                    f"<span style='color:#1565c0;{sq}'>■</span> {tr('legend.deep')} (2–5 m) | "
                    f"<span style='color:#000033;{sq}'>■</span> {tr('legend.very_deep')} (&gt;5 m)<br>"
                    f"• {tr('legend.flooded_cells')}: {flooded_cells} | {tr('legend.max_depth')}: {max_depth:.2f} m"
                )

        legends = {
            "flow_direction": (
                f"<b>{tr('hydro.legend_flow_direction')}</b><br>"
                f"• <span style='color:#1f77b4;{sq}'>■</span> {tr('legend.east')} (1) | "
                f"<span style='color:#ff7f0e;{sq}'>■</span> {tr('legend.southeast')} (2) | "
                f"<span style='color:#2ca02c;{sq}'>■</span> {tr('legend.south')} (4) | "
                f"<span style='color:#d62728;{sq}'>■</span> {tr('legend.southwest')} (8) | "
                f"<span style='color:#9467bd;{sq}'>■</span> {tr('legend.west')} (16) | "
                f"<span style='color:#8c564b;{sq}'>■</span> {tr('legend.northwest')} (32) | "
                f"<span style='color:#e377c2;{sq}'>■</span> {tr('legend.north')} (64) | "
                f"<span style='color:#7f7f7f;{sq}'>■</span> {tr('legend.northeast')} (128)"
            ),
            "flow_accumulation": (
                f"<b>{tr('hydro.legend_flow_accumulation')}</b><br>"
                f"• <span style='color:#dddddd;{sq}'>■</span> ({tr('legend.low')}) → "
                f"<span style='color:#3a79e0;{sq}'>■</span> ({tr('legend.medium')}) → "
                f"<span style='color:#001f3f;{sq}'>■</span> ({tr('legend.high')})<br>"
                "• Cells with value &lt; 1 → Transparent"
            ),
            "ponding": (
                f"<b>{tr('hydro.legend_ponding')}</b><br>"
                f"• <span style='color:#d2b48c;{sq}'>■</span> ({tr('legend.high')}) → "
                f"<span style='color:#2ca02c;{sq}'>■</span> ({tr('legend.medium')}) → "
                f"<span style='color:#1f77b4;{sq}'>■</span> ({tr('legend.low')}) → "
                f"<span style='color:#000080;{sq}'>■</span> ({tr('legend.very_high')})<br>"
                "• Cells with depth = 0 → Transparent"
            ),
            "rainfall_runoff": (
                f"<b>{tr('hydro.legend_rainfall')}</b><br>"
                f"• <span style='color:#e8f4fd;{sq}'>■</span> ({tr('legend.low')}) → "
                f"<span style='color:#2196f3;{sq}'>■</span> ({tr('legend.medium')}) → "
                f"<span style='color:#0d47a1;{sq}'>■</span> ({tr('legend.high')}) → "
                f"<span style='color:#1a237e;{sq}'>■</span> ({tr('legend.very_high')})<br>"
                "• Logarithmic scale. Cells without flow → Transparent"
            ),
        }
        return legends.get(layer_type, "No legend information available.")


# ---------------------------------------------------------------------------
# Tab widget
# ---------------------------------------------------------------------------

class HydrologyTab(BaseAnalysisTab):
    TAB_TYPE = "hydrology"

    def _build_ui(self):
        layout = QVBoxLayout(self)

        grp_src = QGroupBox(tr("analysis.input_raster_dem"))
        form_src = QFormLayout(grp_src)
        self._raster_combo = self._make_raster_combo()
        form_src.addRow(tr("analysis.dem"), self._raster_combo)
        layout.addWidget(grp_src)

        grp_anal = QGroupBox(tr("analysis.to_execute"))
        vl = QVBoxLayout(grp_anal)
        self._chk_flow_dir = QCheckBox(tr("hydro.flow_direction"))
        self._chk_flow_dir.setChecked(True)
        vl.addWidget(self._chk_flow_dir)
        self._chk_flow_acc = QCheckBox(tr("hydro.flow_accumulation"))
        self._chk_flow_acc.setChecked(True)
        vl.addWidget(self._chk_flow_acc)
        self._chk_ponding = QCheckBox(tr("hydro.ponding_zones"))
        vl.addWidget(self._chk_ponding)
        self._chk_rainfall = QCheckBox(tr("hydro.rainfall_simulation"))
        vl.addWidget(self._chk_rainfall)
        self._chk_flood = QCheckBox(tr("hydro.flood_simulation"))
        vl.addWidget(self._chk_flood)
        layout.addWidget(grp_anal)

        grp_params = QGroupBox(tr("analysis.parameters"))
        form_p = QFormLayout(grp_params)
        self._drainage_threshold = QSpinBox()
        self._drainage_threshold.setRange(10, 100000)
        self._drainage_threshold.setValue(1000)
        form_p.addRow(tr("hydro.drainage_threshold"), self._drainage_threshold)
        self._rainfall_intensity = QDoubleSpinBox()
        self._rainfall_intensity.setRange(0.1, 1000.0)
        self._rainfall_intensity.setValue(10.0)
        self._rainfall_intensity.setDecimals(1)
        self._rainfall_intensity.setSuffix(" mm/h")
        form_p.addRow(tr("hydro.rainfall_intensity"), self._rainfall_intensity)
        self._flood_water_height = QDoubleSpinBox()
        self._flood_water_height.setRange(-9999.0, 99999.0)
        self._flood_water_height.setDecimals(2)
        self._flood_water_height.setValue(10.0)
        self._flood_water_height.setSuffix(" m")
        form_p.addRow(tr("hydro.water_level"), self._flood_water_height)
        layout.addWidget(grp_params)

        self._btn_run = QPushButton(tr("hydro.execute"))
        self._btn_run.setObjectName("primary")
        self._btn_run.clicked.connect(self._run)
        layout.addWidget(self._btn_run)

        self._btn_view = QPushButton(tr("analysis.view_results"))
        self._btn_view.setEnabled(False)
        self._btn_view.clicked.connect(self._show_latest_results)
        layout.addWidget(self._btn_view)

        self._btn_history = QPushButton(tr("hydro.history"))
        self._btn_history.clicked.connect(self._show_history)
        layout.addWidget(self._btn_history)

        layout.addStretch()

    def _get_run_btn(self):
        return self._btn_run

    def _get_view_btn(self):
        return self._btn_view

    def _make_raster_combo(self):
        from PyQt6.QtWidgets import QComboBox
        combo = QComboBox()
        self._fill_combo(combo)
        return combo

    def _fill_combo(self, combo):
        current = combo.currentData()
        combo.clear()
        new_idx = 0
        for i, entry in enumerate(self.layer_manager.get_all_entries()):
            if entry.is_raster:
                combo.addItem(entry.name, i)
                if i == current:
                    new_idx = combo.count() - 1
        if combo.count() == 0:
            combo.addItem(tr("analysis.no_raster_layers"), -1)
        combo.setCurrentIndex(new_idx)

    def refresh_combos(self):
        self._fill_combo(self._raster_combo)

    def _run(self):
        idx = self._raster_combo.currentData()
        if idx is None or idx < 0:
            QMessageBox.warning(self, tr("dialog.confirm"), tr("analysis.warning_select_dem"))
            return

        dtm = self.layer_manager.get_layer(idx)
        if not isinstance(dtm, RasterLayer):
            return

        checks = dict(
            flow_dir=self._chk_flow_dir.isChecked(),
            flow_acc=self._chk_flow_acc.isChecked(),
            ponding=self._chk_ponding.isChecked(),
            rainfall=self._chk_rainfall.isChecked(),
            flood=self._chk_flood.isChecked(),
        )
        rainfall_intensity = self._rainfall_intensity.value()
        flood_water_height = self._flood_water_height.value()
        self._pending_layer_name = dtm.name

        def _compute():
            from app.processing.hydrology import (
                flow_direction, flow_accumulation, detect_ponding_zones,
                simulate_rainfall, simulate_flood,
            )
            results = {}
            if checks["flow_dir"]:
                results["flow_direction"] = flow_direction(dtm)
            if checks["flow_acc"]:
                results["flow_accumulation"] = flow_accumulation(dtm)
            if checks["ponding"]:
                results["ponding"] = detect_ponding_zones(dtm)
            if checks["rainfall"]:
                results["rainfall_runoff"] = simulate_rainfall(dtm, rainfall_mm_h=rainfall_intensity)
            if checks["flood"]:
                results["flood_simulation"] = simulate_flood(dtm, water_height=flood_water_height)
            return results

        self._show_loading()
        self._run_worker(
            _compute,
            self._on_result,
            extra_error_fn=lambda e: logger.error(f"Hydrology error: {e}"),
        )

    def _on_result(self, results: dict):
        if not results:
            QMessageBox.warning(self, tr("dialog.confirm"), tr("analysis.warning_no_analysis"))
            return
        if "flood_simulation" in results:
            self.layer_manager.add_layer(results["flood_simulation"])
        self._latest_results = results
        self._append_history(self._pending_layer_name, results)
        self._btn_view.setEnabled(True)
        QMessageBox.information(self, tr("dialog.confirm"), tr("analysis.completed_hydro"))

    def _show_latest_results(self):
        if hasattr(self, "_latest_results") and self._latest_results:
            self._open_results_window(self._latest_results, HydrologyResultsWindow)

    def _show_history(self):
        show_history_dialog(
            self,
            self.main_window,
            history_attr="_hydrology_history",
            tab_type="hydrology",
            history_dialog_attr="_hydro_history_dialog",
            pdf_title_key="hydro.pdf_title",
            source_label_key="analysis.history_dem",
            results_window_class=HydrologyResultsWindow,
        )