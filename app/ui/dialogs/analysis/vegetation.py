"""
ALAS — Vegetation Analysis Tab
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

logger = get_logger("ui.vegetation_tab")


# ---------------------------------------------------------------------------
# Results window
# ---------------------------------------------------------------------------

class VegetationResultsWindow(AnalysisResultsWindow):
    TAB_TYPE = "vegetation"

    def _render_layer(self, layer_type: str, raster_layer):
        import numpy as np
        if layer_type == "tree_tops" and isinstance(raster_layer, np.ndarray):
            return self._render_tree_tops(raster_layer)
        return super()._render_layer(layer_type, raster_layer)

    def _render_tree_tops(self, tree_tops: "np.ndarray"):
        """Render tree top locations as a scatter image using matplotlib."""
        import numpy as np
        import matplotlib.pyplot as plt
        import io
        from PyQt6.QtGui import QImage, QPixmap
        from PyQt6.QtCore import Qt

        fig, ax = plt.subplots(figsize=(8, 6), facecolor="#1a1a2e")
        ax.set_facecolor("#1a1a2e")

        if len(tree_tops) > 0:
            xs, ys, heights = tree_tops[:, 0], tree_tops[:, 1], tree_tops[:, 2]
            sc = ax.scatter(xs, ys, c=heights, cmap="YlGn", s=6,
                            vmin=heights.min(), vmax=heights.max(), alpha=0.85)
            cbar = plt.colorbar(sc, ax=ax, pad=0.02)
            cbar.set_label("Height (m)", color="white", fontsize=9)
            cbar.ax.yaxis.set_tick_params(color="white")
            plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")

        ax.set_title(f"Tree Tops  (n={len(tree_tops)})", color="white", fontsize=11)
        ax.tick_params(colors="white", labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor("#444")
        plt.tight_layout(pad=0.4)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)
        data = buf.read()

        qimage = QImage.fromData(data)
        pixmap = QPixmap.fromImage(qimage)
        pixmap = pixmap.scaledToWidth(800, Qt.TransformationMode.SmoothTransformation)
        rgba = None
        return rgba, qimage, pixmap

    def _get_legend_text(self, layer_type: str, raster_layer=None) -> str:
        sq = "font-size: 15px;"
        legends = {
            "tree_tops": (
                f"<b>{tr('analysis.detect_trees')}</b><br>"
                f"• Each point represents a detected tree top<br>"
                f"• <span style='color:#ff0000;{sq}'>■</span> {tr('legend.high')} canopy | "
                f"<span style='color:#ffff00;{sq}'>■</span> {tr('legend.medium')} canopy | "
                f"<span style='color:#00cc00;{sq}'>■</span> {tr('legend.low')} canopy"
            ),
            "crown_raster": (
                f"<b>{tr('analysis.segment_crowns')}</b><br>"
                f"• Crown IDs cycle through the 20-color <b>tab20</b> palette:<br>"
                f"• <span style='color:#1f77b4;{sq}'>■</span>"
                f"<span style='color:#aec7e8;{sq}'>■</span>"
                f"<span style='color:#ff7f0e;{sq}'>■</span>"
                f"<span style='color:#ffbb78;{sq}'>■</span>"
                f"<span style='color:#2ca02c;{sq}'>■</span>"
                f"<span style='color:#98df8a;{sq}'>■</span>"
                f"<span style='color:#d62728;{sq}'>■</span>"
                f"<span style='color:#ff9896;{sq}'>■</span>"
                f"<span style='color:#9467bd;{sq}'>■</span>"
                f"<span style='color:#c5b0d5;{sq}'>■</span>"
                f"<span style='color:#8c564b;{sq}'>■</span>"
                f"<span style='color:#c49c94;{sq}'>■</span>"
                f"<span style='color:#e377c2;{sq}'>■</span>"
                f"<span style='color:#f7b6d2;{sq}'>■</span>"
                f"<span style='color:#7f7f7f;{sq}'>■</span>"
                f"<span style='color:#c7c7c7;{sq}'>■</span>"
                f"<span style='color:#bcbd22;{sq}'>■</span>"
                f"<span style='color:#dbdb8d;{sq}'>■</span>"
                f"<span style='color:#17becf;{sq}'>■</span>"
                f"<span style='color:#9edae5;{sq}'>■</span> (repeats for ID > 20)<br>"
                f"• Background (no crown) → Transparent"
            ),
            "density": (
                f"<b>{tr('analysis.density_map')}</b><br>"
                f"• <span style='color:#f7fcf5;{sq}'>■</span> ({tr('legend.low')}) → "
                f"<span style='color:#74c476;{sq}'>■</span> ({tr('legend.medium')}) → "
                f"<span style='color:#00441b;{sq}'>■</span> ({tr('legend.high')})<br>"
                f"• Trees per grid cell. Cell size defined by density cell parameter."
            ),
        }
        return legends.get(layer_type, "No legend information available.")


# ---------------------------------------------------------------------------
# Tab widget
# ---------------------------------------------------------------------------

class VegetationTab(BaseAnalysisTab):
    TAB_TYPE = "vegetation"

    def _build_ui(self):
        layout = QVBoxLayout(self)

        grp_src = QGroupBox(tr("analysis.input_raster_chm"))
        form_src = QFormLayout(grp_src)
        self._raster_combo = self._make_raster_combo()
        form_src.addRow(tr("analysis.chm"), self._raster_combo)
        layout.addWidget(grp_src)

        grp_params = QGroupBox(tr("analysis.parameters"))
        form_p = QFormLayout(grp_params)
        self._min_tree_height = QDoubleSpinBox()
        self._min_tree_height.setRange(0.5, 50.0)
        self._min_tree_height.setValue(2.0)
        self._min_tree_height.setSuffix(" m")
        form_p.addRow(tr("analysis.min_tree_height"), self._min_tree_height)
        self._crown_window = QSpinBox()
        self._crown_window.setRange(3, 21)
        self._crown_window.setValue(5)
        self._crown_window.setSuffix(" px")
        form_p.addRow(tr("analysis.detection_window"), self._crown_window)
        self._density_cell = QDoubleSpinBox()
        self._density_cell.setRange(1, 100)
        self._density_cell.setValue(10)
        self._density_cell.setSuffix(" m")
        form_p.addRow(tr("analysis.density_cell"), self._density_cell)
        layout.addWidget(grp_params)

        grp_anal = QGroupBox(tr("analysis.analysis"))
        vl = QVBoxLayout(grp_anal)
        self._chk_tree_detect = QCheckBox(tr("analysis.detect_trees"))
        self._chk_tree_detect.setChecked(True)
        vl.addWidget(self._chk_tree_detect)
        self._chk_crown_seg = QCheckBox(tr("analysis.segment_crowns"))
        vl.addWidget(self._chk_crown_seg)
        self._chk_density = QCheckBox(tr("analysis.density_map"))
        vl.addWidget(self._chk_density)
        layout.addWidget(grp_anal)

        self._btn_run = QPushButton(tr("analysis.execute_veg"))
        self._btn_run.setObjectName("primary")
        self._btn_run.clicked.connect(self._run)
        layout.addWidget(self._btn_run)

        self._btn_view = QPushButton(tr("analysis.view_results"))
        self._btn_view.setEnabled(False)
        self._btn_view.clicked.connect(self._show_latest_results)
        layout.addWidget(self._btn_view)

        self._btn_history = QPushButton(tr("vegetation.history"))
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
            QMessageBox.warning(self, tr("dialog.confirm"), tr("analysis.warning_select_chm"))
            return

        chm = self.layer_manager.get_layer(idx)
        if not isinstance(chm, RasterLayer):
            return

        checks = dict(
            tree_detect=self._chk_tree_detect.isChecked(),
            crown_seg=self._chk_crown_seg.isChecked(),
            density=self._chk_density.isChecked(),
        )
        min_tree_height = self._min_tree_height.value()
        crown_window = self._crown_window.value()
        density_cell = self._density_cell.value()
        self._pending_layer_name = chm.name

        def _compute():
            from app.processing.vegetation import (
                detect_tree_tops, segment_crowns, build_crown_raster, density_map,
            )
            results = {}
            tree_tops = None
            if checks["tree_detect"]:
                tree_tops = detect_tree_tops(chm, min_tree_height, crown_window)
                logger.info(f"Detected {len(tree_tops)} trees")
                results["tree_tops"] = tree_tops
            if checks["crown_seg"] and tree_tops is not None:
                labels, height_map = segment_crowns(chm, tree_tops)
                results["crown_raster"] = build_crown_raster(chm, height_map, labels)
            if checks["density"]:
                results["density"] = density_map(chm, density_cell)
            return results, tree_tops

        self._show_loading()
        self._run_worker(_compute, self._on_result)

    def _on_result(self, payload):
        results, tree_tops = payload
        for key, layer in results.items():
            if key != "tree_tops" and isinstance(layer, RasterLayer):
                self.layer_manager.add_layer(layer)
        self._latest_results = results
        self._append_history(self._pending_layer_name, results)
        self._btn_view.setEnabled(True)
        msg = tr("analysis.completed_veg")
        if tree_tops is not None:
            msg += f"\n{tr('analysis.trees_detected').format(len(tree_tops))}"
        QMessageBox.information(self, tr("dialog.confirm"), msg)

    def _show_latest_results(self):
        if hasattr(self, "_latest_results") and self._latest_results:
            self._open_results_window(self._latest_results, VegetationResultsWindow)

    def _show_history(self):
        show_history_dialog(
            self,
            self.main_window,
            history_attr="_vegetation_history",
            tab_type="vegetation",
            history_dialog_attr="_veg_history_dialog",
            pdf_title_key="vegetation.pdf_title",
            source_label_key="analysis.history_chm",
            results_window_class=VegetationResultsWindow,
        )