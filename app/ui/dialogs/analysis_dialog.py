"""
ALAS — Analysis Dialog
Unified analysis dialog with tabs: geomorphology, hydrology, vegetation, multitemporal.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QGroupBox,
    QFormLayout, QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox,
    QPushButton, QLabel, QMessageBox, QFileDialog,
    QWidget, QScrollArea, QMainWindow, QListWidget, QListWidgetItem
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from app.core.layer_manager import LayerManager
from app.core.raster_layer import RasterLayer
from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.analysis_dialog")


class HydroResultsWindow(QMainWindow):
    """Window to display hydrological results as images with legends."""

    def __init__(self, results: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("analysis.hydro_results"))
        self.setMinimumSize(1000, 800)
        self._setup_ui(results)

    def _setup_ui(self, results: dict):
        from app.rendering.hydro_renderer import HydroRenderer, array_to_qimage

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)

        for layer_type, raster_layer in results.items():
            try:
                renderer = HydroRenderer(raster_layer, layer_type)
                rgba = renderer.render()
                qimage = array_to_qimage(rgba)
                pixmap = QPixmap.fromImage(qimage)
                pixmap = pixmap.scaledToWidth(800, Qt.TransformationMode.SmoothTransformation)

                grp = QGroupBox(tr("analysis.result").format(layer_type))
                grp_layout = QVBoxLayout(grp)
                
                # Image
                lbl_img = QLabel()
                lbl_img.setPixmap(pixmap)
                lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
                grp_layout.addWidget(lbl_img)

                # Legend according to type
                legend_text = self._get_legend_text(layer_type, raster_layer)
                lbl_legend = QLabel(legend_text)
                lbl_legend.setTextFormat(Qt.TextFormat.RichText)
                lbl_legend.setStyleSheet("color: #999; font-size: 11px; margin-top: 10px;")
                lbl_legend.setWordWrap(True)
                grp_layout.addWidget(lbl_legend)
                
                layout.addWidget(grp)

            except Exception as e:
                logger.error(f"Error rendering {layer_type}: {e}")

        layout.addStretch()
        scroll.setWidget(container)
        self.setCentralWidget(scroll)

    @staticmethod
    def _get_legend_text(layer_type: str, raster_layer=None) -> str:
        """Return the legend text according to the analysis type."""
        sq = "font-size: 15px;"

        if layer_type == "rainfall_runoff" and raster_layer is not None:
            import numpy as np
            rainfall_mm_h = getattr(raster_layer, "rainfall_mm_h", None)
            cell_area_m2 = getattr(raster_layer, "rainfall_cell_area_m2", 1.0)
            data = raster_layer.data if hasattr(raster_layer, "data") else None
            if rainfall_mm_h is not None and data is not None:
                from app.config import DEFAULT_NODATA
                arr = np.asarray(data, dtype=np.float32)
                if arr.ndim > 2:
                    arr = arr[0]
                return (
                    f"<b>{tr('hydro.legend_runoff_title').format(rainfall_mm_h)}</b><br>"
                    f"• <span style='color: #e8f4fd; {sq}'>■</span> {tr('legend.weak')} (&lt; 1 mm/h) | "
                    f"<span style='color: #2196f3; {sq}'>■</span> {tr('legend.moderate')} (1–10 mm/h) | "
                    f"<span style='color: #0d47a1; {sq}'>■</span> {tr('legend.strong')} (10–50 mm/h) | "
                    f"<span style='color: #1a237e; {sq}'>■</span> {tr('legend.extreme')} (&gt; 50 mm/h)<br>"
                    f"• {tr('legend.scale')} 1–150 mm/h."
                )

        if layer_type == "flood_simulation" and raster_layer is not None:
            water_height = getattr(raster_layer, "flood_water_height", None)
            import numpy as np
            data = raster_layer.data if hasattr(raster_layer, "data") else None
            if water_height is not None and data is not None:
                from app.config import DEFAULT_NODATA
                arr = np.asarray(data, dtype=np.float32)
                if arr.ndim > 2:
                    arr = arr[0]
                valid = arr[(arr != DEFAULT_NODATA) & (arr > 0)]
                max_depth = float(np.max(valid)) if valid.size > 0 else 0.0
                flooded_cells = int(np.sum((arr != DEFAULT_NODATA) & (arr > 0)))
                return (
                    f"<b>{tr('hydro.legend_flood_title').format(water_height)}</b><br>"
                    f"• <span style='color: #aad4f5; {sq}'>■</span> {tr('legend.shallow')} (&lt; 0.5 m) | "
                    f"<span style='color: #2196f3; {sq}'>■</span> {tr('legend.moderate')} (0.5–2 m) | "
                    f"<span style='color: #1565c0; {sq}'>■</span> {tr('legend.deep')} (2–5 m) | "
                    f"<span style='color: #000033; {sq}'>■</span> {tr('legend.very_deep')} (&gt; 5 m)<br>"
                    f"• {tr('legend.flooded_cells')}: {flooded_cells} | {tr('legend.max_depth')}: {max_depth:.2f} m"
                )

        legends = {
            "flow_direction": (
                f"<b>{tr('hydro.legend_flow_direction')}</b><br>"
                f"• <span style='color: #1f77b4; {sq}'>■</span> {tr('legend.east')} (1) | "
                f"<span style='color: #ff7f0e; {sq}'>■</span> {tr('legend.southeast')} (2) | "
                f"<span style='color: #2ca02c; {sq}'>■</span> {tr('legend.south')} (4) | "
                f"<span style='color: #d62728; {sq}'>■</span> {tr('legend.southwest')} (8) | "
                f"<span style='color: #9467bd; {sq}'>■</span> {tr('legend.west')} (16) | "
                f"<span style='color: #8c564b; {sq}'>■</span> {tr('legend.northwest')} (32) | "
                f"<span style='color: #e377c2; {sq}'>■</span> {tr('legend.north')} (64) | "
                f"<span style='color: #7f7f7f; {sq}'>■</span> {tr('legend.northeast')} (128)"
            ),
            "flow_accumulation": (
                f"<b>{tr('hydro.legend_flow_accumulation')}</b><br>"
                f"• <span style='color: #dddddd; {sq}'>■</span> ({tr('legend.low')}) → "
                f"<span style='color: #3a79e0; {sq}'>■</span> ({tr('legend.medium')})→ "
                f"<span style='color: #001f3f; {sq}'>■</span> ({tr('legend.high')})<br>"
                "• Cells with value < 1 → Transparent"
            ),
            "ponding": (
                f"<b>{tr('hydro.legend_ponding')}</b><br>"
                f"• Depth: <span style='color: #d2b48c; {sq}'>■</span> ({tr('legend.high')}) → "
                f"<span style='color: #2ca02c; {sq}'>■</span> ({tr('legend.medium')}) → "
                f"<span style='color: #1f77b4; {sq}'>■</span> ({tr('legend.low')}) → "
                f"<span style='color: #000080; {sq}'>■</span> ({tr('legend.very_high')})<br>"
                "• Cells with depth = 0 → Transparent<br>"
            ),
            "rainfall_runoff": (
                f"<b>{tr('hydro.legend_rainfall')}</b><br>"
                f"• <span style='color: #e8f4fd; {sq}'>■</span> ({tr('legend.low')}) → "
                f"<span style='color: #2196f3; {sq}'>■</span> ({tr('legend.medium')}) → "
                f"<span style='color: #0d47a1; {sq}'>■</span> ({tr('legend.high')}) → "
                f"<span style='color: #1a237e; {sq}'>■</span> ({tr('legend.very_high')})<br>"
                "• Logarithmic scale. Cells without flow → Transparent"
            )
        }
        text = legends.get(layer_type, "No legend information available")
        return text.replace("{sq}", sq)


class AnalysisDialog(QDialog):
    """Analysis dialog with tabs."""

    def __init__(self, initial_tab: str, layer_manager: LayerManager, parent=None):
        super().__init__(parent)
        self.layer_manager = layer_manager
        self.setWindowTitle(tr("menu.analysis"))
        self.setMinimumSize(550, 600)
        self._setup_ui(initial_tab)
        
        self.layer_manager.layer_added.connect(self._update_combos)
        self.layer_manager.layer_removed.connect(self._update_combos)

    def set_tab(self, tab_name: str):
        """Cambia a la pestaña indicada."""
        tab_map = {"geomorphology": 0, "hydrology": 1, "vegetation": 2, "multitemporal": 3}
        self._tabs.setCurrentIndex(tab_map.get(tab_name, 0))

    def _setup_ui(self, initial_tab: str):
        layout = QVBoxLayout(self)

        self._tabs = QTabWidget()

        # Geomorphology tab
        self._geomorph_tab = self._build_geomorphology_tab()
        self._tabs.addTab(self._geomorph_tab, tr("analysis.geomorphology"))

        # Hydrology tab
        self._hydro_tab = self._build_hydrology_tab()
        self._tabs.addTab(self._hydro_tab, tr("analysis.hydrology"))

        # Vegetation tab
        self._veg_tab = self._build_vegetation_tab()
        self._tabs.addTab(self._veg_tab, tr("analysis.vegetation"))

        # Multitemporal tab
        self._multi_tab = self._build_multitemporal_tab()
        self._tabs.addTab(self._multi_tab, tr("analysis.multitemporal"))

        layout.addWidget(self._tabs)

        # Set initial tab
        tab_map = {"geomorphology": 0, "hydrology": 1, "vegetation": 2, "multitemporal": 3}
        self._tabs.setCurrentIndex(tab_map.get(initial_tab, 0))

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton(tr("dialog.close"))
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def _get_raster_combo(self) -> QComboBox:
        """Create a combo with the available raster layers."""
        combo = QComboBox()
        self._populate_combo(combo)
        return combo

    def _populate_combo(self, combo: QComboBox):
        """Llena un combobox con las capas raster actuales, manteniendo la selección si es posible."""
        current_data = combo.currentData()
        combo.clear()
        
        # Encontrar nueva selección
        new_index = 0
        for i, entry in enumerate(self.layer_manager.get_all_entries()):
            if entry.is_raster:
                combo.addItem(entry.name, i)
                if i == current_data:
                    new_index = combo.count() - 1
                    
        if combo.count() == 0:
            combo.addItem(tr("analysis.no_raster_layers"), -1)
        return combo

    def _update_combos(self, *args):
        """Refresh all raster combo boxes when layers are added or removed."""
        for combo in (self._geo_raster, self._hydro_raster, self._veg_raster,
                      self._multi_before, self._multi_after):
            self._populate_combo(combo)

    # ------------------------------------------------------------------
    # Geomorphology Tab
    # ------------------------------------------------------------------

    def _build_geomorphology_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Source raster
        grp_src = QGroupBox(tr("analysis.input_raster_dem"))
        form_src = QFormLayout(grp_src)
        self._geo_raster = self._get_raster_combo()
        form_src.addRow(tr("analysis.dem"), self._geo_raster)
        layout.addWidget(grp_src)

        # Analysis checkboxes
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

        # Hillshade params
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

        # Run button
        btn_run = QPushButton(tr("analysis.execute_geomorph"))
        btn_run.setObjectName("primary")
        btn_run.clicked.connect(self._run_geomorphology)
        layout.addWidget(btn_run)

        layout.addStretch()
        return tab

    def _run_geomorphology(self):
        idx = self._geo_raster.currentData()
        if idx is None or idx < 0:
            QMessageBox.warning(self, tr("dialog.confirm"), tr("analysis.warning_select_dem"))
            return

        dtm = self.layer_manager.get_layer(idx)
        if not isinstance(dtm, RasterLayer):
            return

        try:
            from app.processing.geomorphology import (
                calculate_slope, calculate_aspect, calculate_curvature,
                calculate_roughness, calculate_hillshade, morphometric_classification
            )

            if self._chk_slope.isChecked():
                result = calculate_slope(dtm)
                self.layer_manager.add_layer(result)

            if self._chk_aspect.isChecked():
                result = calculate_aspect(dtm)
                self.layer_manager.add_layer(result)

            if self._chk_curvature.isChecked():
                result = calculate_curvature(dtm)
                self.layer_manager.add_layer(result)

            if self._chk_roughness.isChecked():
                result = calculate_roughness(dtm)
                self.layer_manager.add_layer(result)

            if self._chk_hillshade.isChecked():
                result = calculate_hillshade(
                    dtm, self._hs_azimuth.value(), self._hs_altitude.value()
                )
                self.layer_manager.add_layer(result)

            if self._chk_morpho.isChecked():
                result = morphometric_classification(dtm)
                self.layer_manager.add_layer(result)

            QMessageBox.information(self, tr("dialog.confirm"), tr("analysis.completed_geomorph"))

        except Exception as e:
            QMessageBox.critical(self, tr("crs.error"), str(e))

    # ------------------------------------------------------------------
    # Hydrology Tab
    # ------------------------------------------------------------------

    def _build_hydrology_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        grp_src = QGroupBox(tr("analysis.input_raster_dem"))
        form_src = QFormLayout(grp_src)
        self._hydro_raster = self._get_raster_combo()
        form_src.addRow(tr("analysis.dem"), self._hydro_raster)
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

        # Hydrological analysis buttons
        btn_run = QPushButton(tr("hydro.execute"))
        btn_run.setObjectName("primary")
        btn_run.clicked.connect(self._run_hydrology)
        layout.addWidget(btn_run)

        self._btn_view_results = QPushButton(tr("analysis.view_results"))
        self._btn_view_results.setEnabled(False)
        self._btn_view_results.clicked.connect(self._show_hydro_results)
        layout.addWidget(self._btn_view_results)

        self._btn_hydro_history = QPushButton(tr("hydro.history"))
        self._btn_hydro_history.clicked.connect(self._show_hydro_history)
        layout.addWidget(self._btn_hydro_history)

        layout.addStretch()
        return tab

    def _show_hydro_results(self):
        """Show the window with hydrological results."""
        if hasattr(self, "_hydro_results") and self._hydro_results:
            main_window = self.parent()
            results_window = HydroResultsWindow(self._hydro_results, main_window)
            results_window.setWindowFlags(Qt.WindowType.Window)
            results_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            
            if not hasattr(main_window, "_hydro_result_windows"):
                main_window._hydro_result_windows = []
            main_window._hydro_result_windows.append(results_window)
            
            self._results_window = results_window
            results_window.show()

    def _show_hydro_history(self):
        """Show a modal with the hydrological analysis history and allows opening them."""
        main_window = self.parent()
        history = getattr(main_window, "_hydro_history", [])
        if not history:
            QMessageBox.information(self, tr("hydro.history"), tr("hydro.no_history"))
            return

        if hasattr(main_window, "_hydro_history_dialog") and main_window._hydro_history_dialog is not None:
            try:
                main_window._hydro_history_dialog.close()
            except RuntimeError:
                pass
                
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("hydro.history_title"))
        dlg.setMinimumSize(400, 300)
        dlg.setWindowFlags(Qt.WindowType.Window)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        main_window._hydro_history_dialog = dlg
        
        l = QVBoxLayout(dlg)
        
        list_widget = QListWidget()
        for idx, item in enumerate(history):
            text = f"[{item['timestamp']}] {tr('analysis.history_dem')} {item['layer']} ({len(item['results'])} {tr('analysis.history_layers')})"
            lw_item = QListWidgetItem(text)
            lw_item.setData(Qt.ItemDataRole.UserRole, idx)
            list_widget.addItem(lw_item)
            
        l.addWidget(list_widget)
        
        btn_open = QPushButton(tr("analysis.view_results"))
        def on_open():
            selected = list_widget.currentItem()
            if selected:
                idx = selected.data(Qt.ItemDataRole.UserRole)
                res = history[idx]["results"]
                
                results_window = HydroResultsWindow(res, main_window)
                results_window.setWindowFlags(Qt.WindowType.Window)
                results_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
                
                if not hasattr(main_window, "_hydro_result_windows"):
                    main_window._hydro_result_windows = []
                main_window._hydro_result_windows.append(results_window)
                results_window.show()
                
        btn_open.clicked.connect(on_open)
        l.addWidget(btn_open)
        
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _run_hydrology(self):
        idx = self._hydro_raster.currentData()
        if idx is None or idx < 0:
            QMessageBox.warning(self, tr("dialog.confirm"), tr("analysis.warning_select_dem"))
            return

        dtm = self.layer_manager.get_layer(idx)
        if not isinstance(dtm, RasterLayer):
            return

        try:
            from app.processing.hydrology import (
                flow_direction, flow_accumulation, detect_ponding_zones, simulate_rainfall
            )

            results = {}

            if self._chk_flow_dir.isChecked():
                result = flow_direction(dtm)
                results["flow_direction"] = result

            if self._chk_flow_acc.isChecked():
                result = flow_accumulation(dtm)
                results["flow_accumulation"] = result

            if self._chk_ponding.isChecked():
                result = detect_ponding_zones(dtm)
                results["ponding"] = result

            if self._chk_rainfall.isChecked():
                result = simulate_rainfall(dtm, rainfall_mm_h=self._rainfall_intensity.value())
                results["rainfall_runoff"] = result

            if self._chk_flood.isChecked():
                from app.processing.hydrology import simulate_flood
                result = simulate_flood(dtm, water_height=self._flood_water_height.value())
                results["flood_simulation"] = result
                self.layer_manager.add_layer(result)

            if results:
                self._hydro_results = results
                
                import datetime
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                main_window = self.parent()
                if not hasattr(main_window, "_hydro_history"):
                    main_window._hydro_history = []
                main_window._hydro_history.append({
                    "timestamp": timestamp,
                    "layer": dtm.name,
                    "results": results
                })

                self._btn_view_results.setEnabled(True)
                QMessageBox.information(self, tr("dialog.confirm"), tr("analysis.completed_hydro"))
            else:
                QMessageBox.warning(self, tr("dialog.confirm"), tr("analysis.warning_no_analysis"))

        except Exception as e:
            QMessageBox.critical(self, tr("crs.error"), str(e))
            logger.error(f"Error in hydrological analysis: {e}", exc_info=True)


    # ------------------------------------------------------------------
    # Vegetation Tab
    # ------------------------------------------------------------------

    def _build_vegetation_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        grp_src = QGroupBox(tr("analysis.input_raster_chm"))
        form_src = QFormLayout(grp_src)
        self._veg_raster = self._get_raster_combo()
        form_src.addRow(tr("analysis.chm"), self._veg_raster)
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

        btn_run = QPushButton(tr("analysis.execute_veg"))
        btn_run.setObjectName("primary")
        btn_run.clicked.connect(self._run_vegetation)
        layout.addWidget(btn_run)

        layout.addStretch()
        return tab

    def _run_vegetation(self):
        idx = self._veg_raster.currentData()
        if idx is None or idx < 0:
            QMessageBox.warning(self, tr("dialog.confirm"), tr("analysis.warning_select_chm"))
            return

        chm = self.layer_manager.get_layer(idx)
        if not isinstance(chm, RasterLayer):
            return

        try:
            from app.processing.vegetation import (
                detect_tree_tops, segment_crowns, build_crown_raster, density_map
            )

            tree_tops = None
            if self._chk_tree_detect.isChecked():
                tree_tops = detect_tree_tops(
                    chm, self._min_tree_height.value(), self._crown_window.value()
                )
                logger.info(f"Detected {len(tree_tops)} trees")

            if self._chk_crown_seg.isChecked() and tree_tops is not None:
                labels, height_map = segment_crowns(chm, tree_tops)
                crown_rl = build_crown_raster(chm, height_map, labels)
                self.layer_manager.add_layer(crown_rl)

            if self._chk_density.isChecked():
                result = density_map(chm, self._density_cell.value())
                self.layer_manager.add_layer(result)

            msg = tr("analysis.completed_veg")
            if tree_tops is not None:
                msg += f"\n{tr('analysis.trees_detected').format(len(tree_tops))}"
            QMessageBox.information(self, tr("dialog.confirm"), msg)

        except Exception as e:
            QMessageBox.critical(self, tr("crs.error"), str(e))

    # ------------------------------------------------------------------
    # Multitemporal Tab
    # ------------------------------------------------------------------

    def _build_multitemporal_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        grp_src = QGroupBox(tr("analysis.input_rasters"))
        form_src = QFormLayout(grp_src)
        self._multi_before = self._get_raster_combo()
        form_src.addRow(tr("analysis.previous_dem"), self._multi_before)
        self._multi_after = self._get_raster_combo()
        form_src.addRow(tr("analysis.posterior_dem"), self._multi_after)
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

        btn_run = QPushButton(tr("analysis.execute_multi"))
        btn_run.setObjectName("primary")
        btn_run.clicked.connect(self._run_multitemporal)
        layout.addWidget(btn_run)

        layout.addStretch()
        return tab

    def _run_multitemporal(self):
        idx_before = self._multi_before.currentData()
        idx_after = self._multi_after.currentData()

        if idx_before is None or idx_before < 0 or idx_after is None or idx_after < 0:
            QMessageBox.warning(self, tr("dialog.confirm"), tr("analysis.warning_select_both"))
            return

        before = self.layer_manager.get_layer(idx_before)
        after = self.layer_manager.get_layer(idx_after)

        if not isinstance(before, RasterLayer) or not isinstance(after, RasterLayer):
            return

        try:
            from app.processing.multitemporal import (
                compute_dod, classify_changes, detect_deforestation
            )

            dod = None
            if self._chk_dod.isChecked():
                dod = compute_dod(before, after)
                self.layer_manager.add_layer(dod)

            if self._chk_change_class.isChecked() and dod is not None:
                changes = classify_changes(dod, self._dod_threshold.value())
                self.layer_manager.add_layer(changes)

            if self._chk_deforest.isChecked():
                deforest = detect_deforestation(before, after)
                self.layer_manager.add_layer(deforest)

            QMessageBox.information(self, tr("dialog.confirm"), tr("analysis.completed_multi"))

        except Exception as e:
            QMessageBox.critical(self, tr("crs.error"), str(e))
