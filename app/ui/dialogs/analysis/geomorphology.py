"""
ALAS — Geomorphology Analysis Tab
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QFormLayout, QDoubleSpinBox,
    QCheckBox, QPushButton, QMessageBox,
)

from app.core.raster_layer import RasterLayer
from app.i18n import tr
from app.logger import get_logger

from .analysis_base import BaseAnalysisTab, show_history_dialog
from .results_window import AnalysisResultsWindow

logger = get_logger("ui.geomorphology_tab")


# ---------------------------------------------------------------------------
# Results window
# ---------------------------------------------------------------------------

class GeomorphologyResultsWindow(AnalysisResultsWindow):
    TAB_TYPE = "geomorphology"

    def _render_layer(self, layer_type: str, raster_layer):
        from app.rendering.generic_renderer import GenericRenderer, array_to_qimage
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt
        renderer = GenericRenderer(raster_layer, layer_type)
        rgba = renderer.render()
        qimage = array_to_qimage(rgba)
        pixmap = QPixmap.fromImage(qimage)
        pixmap = pixmap.scaledToWidth(800, Qt.TransformationMode.SmoothTransformation)
        return rgba, qimage, pixmap

    def _get_legend_text(self, layer_type: str, raster_layer=None) -> str:
        sq = "font-size: 15px;"
        legends = {
            "slope": (
                f"<b>{tr('analysis.slope')}</b><br>"
                f"• <span style='color:#ffffcc;{sq}'>■</span> {tr('legend.flat')} (0–5°) | "
                f"<span style='color:#fd8d3c;{sq}'>■</span> {tr('legend.moderate')} (5–20°) | "
                f"<span style='color:#e31a1c;{sq}'>■</span> {tr('legend.steep')} (20–45°) | "
                f"<span style='color:#800026;{sq}'>■</span> {tr('legend.very_steep')} (&gt;45°)"
            ),
            "aspect": (
                f"<b>{tr('analysis.aspect')}</b><br>"
                f"• <span style='color:#1f77b4;{sq}'>■</span> {tr('legend.north')} (0°/360°) | "
                f"<span style='color:#ff7f0e;{sq}'>■</span> {tr('legend.east')} (90°) | "
                f"<span style='color:#2ca02c;{sq}'>■</span> {tr('legend.south')} (180°) | "
                f"<span style='color:#d62728;{sq}'>■</span> {tr('legend.west')} (270°)<br>"
                f"• Full circular colormap (HSV). Flat areas → Gray"
            ),
            "curvature": (
                f"<b>{tr('analysis.curvature')}</b><br>"
                f"• <span style='color:#d62728;{sq}'>■</span> {tr('legend.concave')} (&lt;0) | "
                f"<span style='color:#f5f5f5;{sq}'>■</span> {tr('legend.flat')} (≈0) | "
                f"<span style='color:#1f77b4;{sq}'>■</span> {tr('legend.convex')} (&gt;0)<br>"
                f"• Diverging colormap centred at 0"
            ),
            "roughness": (
                f"<b>{tr('analysis.roughness')}</b><br>"
                f"• <span style='color:#f7fcf5;{sq}'>■</span> ({tr('legend.low')}) → "
                f"<span style='color:#41ab5d;{sq}'>■</span> ({tr('legend.medium')}) → "
                f"<span style='color:#00441b;{sq}'>■</span> ({tr('legend.high')})"
            ),
            "hillshade": (
                f"<b>{tr('analysis.hillshade')}</b><br>"
                f"• <span style='color:#000000;{sq}'>■</span> {tr('legend.shadow')} (0) → "
                f"<span style='color:#ffffff;{sq}'>■</span> {tr('legend.lit')} (255)<br>"
                f"• Grayscale. Sun position defined by azimuth and altitude."
            ),
            "morpho": (
                f"<b>{tr('analysis.morpho_class')}</b><br>"
                f"• <span style='color:#1f77b4;{sq}'>■</span> {tr('legend.valley')} | "
                f"<span style='color:#aec7e8;{sq}'>■</span> {tr('legend.footslope')} | "
                f"<span style='color:#ffbb78;{sq}'>■</span> {tr('legend.backslope')} | "
                f"<span style='color:#d62728;{sq}'>■</span> {tr('legend.summit')}"
            ),
        }
        return legends.get(layer_type, "No legend information available.")


# ---------------------------------------------------------------------------
# Tab widget
# ---------------------------------------------------------------------------

class GeomorphologyTab(BaseAnalysisTab):
    TAB_TYPE = "geomorphology"

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Source raster
        grp_src = QGroupBox(tr("analysis.input_raster_dem"))
        form_src = QFormLayout(grp_src)
        self._raster_combo = self._make_raster_combo()
        form_src.addRow(tr("analysis.dem"), self._raster_combo)
        layout.addWidget(grp_src)

        # Analyses to execute
        grp_anal = QGroupBox(tr("analysis.to_execute"))
        vl = QVBoxLayout(grp_anal)
        self._chk_slope = QCheckBox(tr("analysis.slope"))
        self._chk_slope.setChecked(True)
        vl.addWidget(self._chk_slope)
        self._chk_aspect = QCheckBox(tr("analysis.aspect"))
        self._chk_aspect.setChecked(True)
        vl.addWidget(self._chk_aspect)
        self._chk_curvature = QCheckBox(tr("analysis.curvature"))
        vl.addWidget(self._chk_curvature)
        self._chk_roughness = QCheckBox(tr("analysis.roughness"))
        vl.addWidget(self._chk_roughness)
        self._chk_hillshade = QCheckBox(tr("analysis.hillshade"))
        self._chk_hillshade.setChecked(True)
        vl.addWidget(self._chk_hillshade)
        self._chk_morpho = QCheckBox(tr("analysis.morpho_class"))
        vl.addWidget(self._chk_morpho)
        layout.addWidget(grp_anal)

        # Hillshade parameters
        grp_hs = QGroupBox(tr("analysis.parameters"))
        form_hs = QFormLayout(grp_hs)
        self._hs_azimuth = QDoubleSpinBox()
        self._hs_azimuth.setRange(0, 360)
        self._hs_azimuth.setValue(315)
        self._hs_azimuth.setSuffix("°")
        form_hs.addRow(tr("analysis.azimuth"), self._hs_azimuth)
        self._hs_altitude = QDoubleSpinBox()
        self._hs_altitude.setRange(1, 90)
        self._hs_altitude.setValue(45)
        self._hs_altitude.setSuffix("°")
        form_hs.addRow(tr("analysis.altitude"), self._hs_altitude)
        layout.addWidget(grp_hs)

        # Action buttons
        self._btn_run = QPushButton(tr("analysis.execute_geomorph"))
        self._btn_run.setObjectName("primary")
        self._btn_run.clicked.connect(self._run)
        layout.addWidget(self._btn_run)

        self._btn_view = QPushButton(tr("analysis.view_results"))
        self._btn_view.setEnabled(False)
        self._btn_view.clicked.connect(self._show_latest_results)
        layout.addWidget(self._btn_view)

        self._btn_history = QPushButton(tr("geomorphology.history"))
        self._btn_history.clicked.connect(self._show_history)
        layout.addWidget(self._btn_history)

        layout.addStretch()

    # BaseAnalysisTab interface
    def _get_run_btn(self) -> QPushButton:
        return self._btn_run

    def _get_view_btn(self) -> QPushButton:
        return self._btn_view

    # ------------------------------------------------------------------
    # Combo helpers (raster combo scoped to this tab)
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Run logic
    # ------------------------------------------------------------------

    def _run(self):
        idx = self._raster_combo.currentData()
        if idx is None or idx < 0:
            QMessageBox.warning(self, tr("dialog.confirm"), tr("analysis.warning_select_dem"))
            return

        dtm = self.layer_manager.get_layer(idx)
        if not isinstance(dtm, RasterLayer):
            return

        checks = dict(
            slope=self._chk_slope.isChecked(),
            aspect=self._chk_aspect.isChecked(),
            curvature=self._chk_curvature.isChecked(),
            roughness=self._chk_roughness.isChecked(),
            hillshade=self._chk_hillshade.isChecked(),
            morpho=self._chk_morpho.isChecked(),
        )
        azimuth = self._hs_azimuth.value()
        altitude = self._hs_altitude.value()
        self._pending_layer_name = dtm.name

        def _compute():
            from app.processing.geomorphology import (
                calculate_slope, calculate_aspect, calculate_curvature,
                calculate_roughness, calculate_hillshade, morphometric_classification,
            )
            results = {}
            if checks["slope"]:
                results["slope"] = calculate_slope(dtm)
            if checks["aspect"]:
                results["aspect"] = calculate_aspect(dtm)
            if checks["curvature"]:
                results["curvature"] = calculate_curvature(dtm)
            if checks["roughness"]:
                results["roughness"] = calculate_roughness(dtm)
            if checks["hillshade"]:
                results["hillshade"] = calculate_hillshade(dtm, azimuth, altitude)
            if checks["morpho"]:
                results["morpho"] = morphometric_classification(dtm)
            return results

        self._show_loading()
        self._run_worker(_compute, self._on_result)

    def _on_result(self, results: dict):
        if not results:
            QMessageBox.warning(self, tr("dialog.confirm"), tr("analysis.warning_no_analysis"))
            return
        for layer in results.values():
            self.layer_manager.add_layer(layer)
        self._latest_results = results
        self._append_history(self._pending_layer_name, results)
        self._btn_view.setEnabled(True)
        QMessageBox.information(self, tr("dialog.confirm"), tr("analysis.completed_geomorph"))

    def _show_latest_results(self):
        if hasattr(self, "_latest_results") and self._latest_results:
            self._open_results_window(self._latest_results, GeomorphologyResultsWindow)

    def _show_history(self):
        show_history_dialog(
            self,
            self.main_window,
            history_attr="_geomorphology_history",
            tab_type="geomorphology",
            history_dialog_attr="_geo_history_dialog",
            pdf_title_key="geomorphology.pdf_title",
            source_label_key="analysis.history_dem",
            results_window_class=GeomorphologyResultsWindow,
        )