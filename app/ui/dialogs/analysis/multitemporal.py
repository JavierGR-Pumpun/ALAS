"""
ALAS — Multitemporal Analysis Tab
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

logger = get_logger("ui.multitemporal_tab")


# ---------------------------------------------------------------------------
# Results window
# ---------------------------------------------------------------------------

class MultitemporalResultsWindow(AnalysisResultsWindow):
    TAB_TYPE = "multitemporal"

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
            "dod": (
                f"<b>{tr('analysis.dod')}</b><br>"
                f"• <span style='color:#d62728;{sq}'>■</span> {tr('legend.erosion')} (&lt;0 m) | "
                f"<span style='color:#f5f5f5;{sq}'>■</span> {tr('legend.stable')} (≈0 m) | "
                f"<span style='color:#1f77b4;{sq}'>■</span> {tr('legend.deposition')} (&gt;0 m)<br>"
                f"• Diverging colormap centred at 0. Threshold applied."
            ),
            "change_class": (
                f"<b>{tr('analysis.classify_changes')}</b><br>"
                f"• <span style='color:#d62728;{sq}'>■</span> {tr('legend.significant_erosion')} | "
                f"<span style='color:#cccccc;{sq}'>■</span> {tr('legend.stable')} | "
                f"<span style='color:#1f77b4;{sq}'>■</span> {tr('legend.significant_deposition')}"
            ),
            "deforestation": (
                f"<b>{tr('analysis.detect_deforest')}</b><br>"
                f"• <span style='color:#d62728;{sq}'>■</span> {tr('legend.deforested')} | "
                f"<span style='color:#2ca02c;{sq}'>■</span> {tr('legend.forest_gain')} | "
                f"<span style='color:#cccccc;{sq}'>■</span> {tr('legend.no_change')}"
            ),
        }
        return legends.get(layer_type, "No legend information available.")


# ---------------------------------------------------------------------------
# Tab widget
# ---------------------------------------------------------------------------

class MultitemporalTab(BaseAnalysisTab):
    TAB_TYPE = "multitemporal"

    def _build_ui(self):
        layout = QVBoxLayout(self)

        grp_src = QGroupBox(tr("analysis.input_rasters"))
        form_src = QFormLayout(grp_src)
        self._combo_before = self._make_raster_combo()
        form_src.addRow(tr("analysis.previous_dem"), self._combo_before)
        self._combo_after = self._make_raster_combo()
        form_src.addRow(tr("analysis.posterior_dem"), self._combo_after)
        layout.addWidget(grp_src)

        grp_params = QGroupBox(tr("analysis.parameters"))
        form_p = QFormLayout(grp_params)
        self._dod_threshold = QDoubleSpinBox()
        self._dod_threshold.setRange(0.01, 10.0)
        self._dod_threshold.setValue(0.3)
        self._dod_threshold.setSuffix(" m")
        form_p.addRow(tr("analysis.change_threshold"), self._dod_threshold)
        layout.addWidget(grp_params)

        grp_anal = QGroupBox(tr("analysis.analysis"))
        vl = QVBoxLayout(grp_anal)
        self._chk_dod = QCheckBox(tr("analysis.dod"))
        self._chk_dod.setChecked(True)
        vl.addWidget(self._chk_dod)
        self._chk_change_class = QCheckBox(tr("analysis.classify_changes"))
        self._chk_change_class.setChecked(True)
        vl.addWidget(self._chk_change_class)
        self._chk_deforest = QCheckBox(tr("analysis.detect_deforest"))
        vl.addWidget(self._chk_deforest)
        layout.addWidget(grp_anal)

        self._btn_run = QPushButton(tr("analysis.execute_multi"))
        self._btn_run.setObjectName("primary")
        self._btn_run.clicked.connect(self._run)
        layout.addWidget(self._btn_run)

        self._btn_view = QPushButton(tr("analysis.view_results"))
        self._btn_view.setEnabled(False)
        self._btn_view.clicked.connect(self._show_latest_results)
        layout.addWidget(self._btn_view)

        self._btn_history = QPushButton(tr("multitemporal.history"))
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
        self._fill_combo(self._combo_before)
        self._fill_combo(self._combo_after)

    def _run(self):
        idx_before = self._combo_before.currentData()
        idx_after = self._combo_after.currentData()

        if idx_before is None or idx_before < 0 or idx_after is None or idx_after < 0:
            QMessageBox.warning(self, tr("dialog.confirm"), tr("analysis.warning_select_both"))
            return
        if idx_before == idx_after:
            QMessageBox.warning(self, tr("dialog.confirm"), tr("analysis.warning_same_layer"))
            return

        before = self.layer_manager.get_layer(idx_before)
        after = self.layer_manager.get_layer(idx_after)
        if not isinstance(before, RasterLayer) or not isinstance(after, RasterLayer):
            return

        checks = dict(
            dod=self._chk_dod.isChecked(),
            change_class=self._chk_change_class.isChecked(),
            deforest=self._chk_deforest.isChecked(),
        )
        dod_threshold = self._dod_threshold.value()
        self._pending_layer_name = f"{before.name} → {after.name}"

        def _compute():
            from app.processing.multitemporal import (
                compute_dod, classify_changes, detect_deforestation,
            )
            results = {}
            dod = None
            if checks["dod"]:
                dod = compute_dod(before, after)
                results["dod"] = dod
            if checks["change_class"] and dod is not None:
                results["change_class"] = classify_changes(dod, dod_threshold)
            if checks["deforest"]:
                results["deforestation"] = detect_deforestation(before, after)
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
        QMessageBox.information(self, tr("dialog.confirm"), tr("analysis.completed_multi"))

    def _show_latest_results(self):
        if hasattr(self, "_latest_results") and self._latest_results:
            self._open_results_window(self._latest_results, MultitemporalResultsWindow)

    def _show_history(self):
        show_history_dialog(
            self,
            self.main_window,
            history_attr="_multitemporal_history",
            tab_type="multitemporal",
            history_dialog_attr="_multi_history_dialog",
            pdf_title_key="multitemporal.pdf_title",
            source_label_key="analysis.history_layers_pair",
            results_window_class=MultitemporalResultsWindow,
        )