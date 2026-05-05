"""
ALAS — Analysis Dialog
Diálogo unificado de análisis con pestañas: geomorfología, hidrología, vegetación, multitemporal.
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
    """Ventana para mostrar resultados hidrológicos como imágenes con leyendas."""

    def __init__(self, results: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Resultados Hidrológicos")
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

                grp = QGroupBox(f"Resultado: {layer_type}")
                grp_layout = QVBoxLayout(grp)
                
                # Imagen
                lbl_img = QLabel()
                lbl_img.setPixmap(pixmap)
                lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
                grp_layout.addWidget(lbl_img)

                # Leyenda según tipo
                legend_text = self._get_legend_text(layer_type, raster_layer)
                lbl_legend = QLabel(legend_text)
                lbl_legend.setTextFormat(Qt.TextFormat.RichText)
                lbl_legend.setStyleSheet("color: #999; font-size: 11px; margin-top: 10px;")
                lbl_legend.setWordWrap(True)
                grp_layout.addWidget(lbl_legend)
                
                layout.addWidget(grp)

            except Exception as e:
                logger.error(f"Error renderizando {layer_type}: {e}")

        layout.addStretch()
        scroll.setWidget(container)
        self.setCentralWidget(scroll)

    @staticmethod
    def _get_legend_text(layer_type: str, raster_layer=None) -> str:
        """Devuelve el texto de leyenda según el tipo de análisis."""
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
                    f"<b>Escorrentía por Precipitaciones — {rainfall_mm_h} mm/h</b><br>"
                    f"• <span style='color: #e8f4fd; {sq}'>■</span> Débil (&lt; 1 mm/h) | "
                    f"<span style='color: #2196f3; {sq}'>■</span> Moderado (1–10 mm/h) | "
                    f"<span style='color: #0d47a1; {sq}'>■</span> Fuerte (10–50 mm/h) | "
                    f"<span style='color: #1a237e; {sq}'>■</span> Extremo (&gt; 50 mm/h)<br>"
                    f"• Escala 1–150 mm/h."
                )

        legends = {
            "flow_direction": (
                "<b>Dirección de Flujo (D8):</b><br>"
                "• <span style='color: #1f77b4; {sq}'>■</span> Este (1) | "
                "<span style='color: #ff7f0e; {sq}'>■</span> Sureste (2) | "
                "<span style='color: #2ca02c; {sq}'>■</span> Sur (4) | "
                "<span style='color: #d62728; {sq}'>■</span> Suroeste (8) | "
                "<span style='color: #9467bd; {sq}'>■</span> Oeste (16) | "
                "<span style='color: #8c564b; {sq}'>■</span> Noroeste (32) | "
                "<span style='color: #e377c2; {sq}'>■</span> Norte (64) | "
                "<span style='color: #7f7f7f; {sq}'>■</span> Noreste (128)"
            ),
            "flow_accumulation": (
                "<b>Acumulación de Flujo:</b><br>"
                "• <span style='color: #dddddd; {sq}'>■</span> (Bajo) → "
                "<span style='color: #3a79e0; {sq}'>■</span> (Medio)→ "
                "<span style='color: #001f3f; {sq}'>■</span> (Alto)<br>"
                "• Células con valor < 1 → Transparentes"
            ),
            "ponding": (
                "<b>Zonas de Encharcamiento:</b><br>"
                "• Profundidad: <span style='color: #d2b48c; {sq}'>■</span> (Alta) → "
                "<span style='color: #2ca02c; {sq}'>■</span> (Media) → "
                "<span style='color: #1f77b4; {sq}'>■</span> (Baja) → "
                "<span style='color: #000080; {sq}'>■</span> (Muy Baja)<br>"
                "• Células con profundidad = 0 → Transparentes<br>"
            ),
            "rainfall_runoff": (
                "<b>Escorrentía por Precipitaciones (m³/h):</b><br>"
                "• <span style='color: #e8f4fd; {sq}'>■</span> (Bajo) → "
                "<span style='color: #2196f3; {sq}'>■</span> (Medio) → "
                "<span style='color: #0d47a1; {sq}'>■</span> (Alto) → "
                "<span style='color: #1a237e; {sq}'>■</span> (Muy Alto)<br>"
                "• Escala logarítmica. Células sin flujo → Transparentes"
            )
        }
        text = legends.get(layer_type, "Sin información de leyenda disponible")
        return text.replace("{sq}", sq)


class AnalysisDialog(QDialog):
    """Diálogo de análisis con pestañas."""

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
        self._tabs.addTab(self._geomorph_tab, "Geomorfología")

        # Hydrology tab
        self._hydro_tab = self._build_hydrology_tab()
        self._tabs.addTab(self._hydro_tab, "Hidrología")

        # Vegetation tab
        self._veg_tab = self._build_vegetation_tab()
        self._tabs.addTab(self._veg_tab, "Vegetación")

        # Multitemporal tab
        self._multi_tab = self._build_multitemporal_tab()
        self._tabs.addTab(self._multi_tab, "Multitemporal")

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
        """Crea un combo con las capas raster disponibles."""
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
            combo.addItem("(No hay capas raster)", -1)
        else:
            combo.setCurrentIndex(new_index)

    def _update_combos(self, *args):
        """Actualiza todos los combos cuando cambian las capas."""
        if not hasattr(self, "_geo_raster"):
            return
        self._populate_combo(self._geo_raster)
        self._populate_combo(self._hydro_raster)
        self._populate_combo(self._veg_raster)
        self._populate_combo(self._multi_before)
        self._populate_combo(self._multi_after)

    # ------------------------------------------------------------------
    # Geomorphology Tab
    # ------------------------------------------------------------------

    def _build_geomorphology_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Source raster
        grp_src = QGroupBox("Raster de entrada (MDT)")
        form_src = QFormLayout(grp_src)
        self._geo_raster = self._get_raster_combo()
        form_src.addRow("MDT", self._geo_raster)
        layout.addWidget(grp_src)

        # Analysis checkboxes
        grp_anal = QGroupBox("Análisis a ejecutar")
        vl = QVBoxLayout(grp_anal)
        self._chk_slope = QCheckBox("Pendiente (slope)")
        self._chk_slope.setChecked(True)
        vl.addWidget(self._chk_slope)
        self._chk_aspect = QCheckBox("Orientación (aspect)")
        self._chk_aspect.setChecked(True)
        vl.addWidget(self._chk_aspect)
        self._chk_curvature = QCheckBox("Curvatura")
        vl.addWidget(self._chk_curvature)
        self._chk_roughness = QCheckBox("Rugosidad (TRI)")
        vl.addWidget(self._chk_roughness)
        self._chk_hillshade = QCheckBox("Sombreado (hillshade)")
        self._chk_hillshade.setChecked(True)
        vl.addWidget(self._chk_hillshade)
        self._chk_morpho = QCheckBox("Clasificación morfométrica")
        vl.addWidget(self._chk_morpho)
        layout.addWidget(grp_anal)

        # Hillshade params
        grp_hs = QGroupBox("Parámetros de sombreado")
        form_hs = QFormLayout(grp_hs)
        self._hs_azimuth = QDoubleSpinBox()
        self._hs_azimuth.setRange(0, 360)
        self._hs_azimuth.setValue(315)
        self._hs_azimuth.setSuffix("°")
        form_hs.addRow("Azimut solar", self._hs_azimuth)
        self._hs_altitude = QDoubleSpinBox()
        self._hs_altitude.setRange(1, 90)
        self._hs_altitude.setValue(45)
        self._hs_altitude.setSuffix("°")
        form_hs.addRow("Altitud solar", self._hs_altitude)
        layout.addWidget(grp_hs)

        # Run button
        btn_run = QPushButton("▶ Ejecutar análisis geomorfológico")
        btn_run.setObjectName("primary")
        btn_run.clicked.connect(self._run_geomorphology)
        layout.addWidget(btn_run)

        layout.addStretch()
        return tab

    def _run_geomorphology(self):
        idx = self._geo_raster.currentData()
        if idx is None or idx < 0:
            QMessageBox.warning(self, "Aviso", "Selecciona un MDT primero.")
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

            QMessageBox.information(self, "Completado", "Análisis geomorfológico completado.")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ------------------------------------------------------------------
    # Hydrology Tab
    # ------------------------------------------------------------------

    def _build_hydrology_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        grp_src = QGroupBox("Raster de entrada (MDT)")
        form_src = QFormLayout(grp_src)
        self._hydro_raster = self._get_raster_combo()
        form_src.addRow("MDT", self._hydro_raster)
        layout.addWidget(grp_src)

        grp_anal = QGroupBox("Análisis a ejecutar")
        vl = QVBoxLayout(grp_anal)
        self._chk_flow_dir = QCheckBox("Dirección de flujo")
        self._chk_flow_dir.setChecked(True)
        vl.addWidget(self._chk_flow_dir)
        self._chk_flow_acc = QCheckBox("Acumulación de flujo")
        self._chk_flow_acc.setChecked(True)
        vl.addWidget(self._chk_flow_acc)
        self._chk_ponding = QCheckBox("Zonas de encharcamiento")
        vl.addWidget(self._chk_ponding)
        self._chk_rainfall = QCheckBox("Simulación de precipitaciones")
        vl.addWidget(self._chk_rainfall)
        layout.addWidget(grp_anal)

        grp_params = QGroupBox("Parámetros")
        form_p = QFormLayout(grp_params)
        self._drainage_threshold = QSpinBox()
        self._drainage_threshold.setRange(10, 100000)
        self._drainage_threshold.setValue(1000)
        form_p.addRow("Umbral red drenaje", self._drainage_threshold)
        self._rainfall_intensity = QDoubleSpinBox()
        self._rainfall_intensity.setRange(0.1, 1000.0)
        self._rainfall_intensity.setValue(10.0)
        self._rainfall_intensity.setDecimals(1)
        self._rainfall_intensity.setSuffix(" mm/h")
        form_p.addRow("Intensidad precipitación", self._rainfall_intensity)
        layout.addWidget(grp_params)

        # Botones
        btn_run = QPushButton("▶ Ejecutar análisis hidrológico")
        btn_run.setObjectName("primary")
        btn_run.clicked.connect(self._run_hydrology)
        layout.addWidget(btn_run)

        self._btn_view_results = QPushButton("Ver resultados")
        self._btn_view_results.setEnabled(False)
        self._btn_view_results.clicked.connect(self._show_hydro_results)
        layout.addWidget(self._btn_view_results)

        self._btn_hydro_history = QPushButton("Historial")
        self._btn_hydro_history.clicked.connect(self._show_hydro_history)
        layout.addWidget(self._btn_hydro_history)

        layout.addStretch()
        return tab

    def _show_hydro_results(self):
        """Muestra la ventana con resultados hidrológicos."""
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
        """Muestra un modal con el historial de análisis hidrológicos y permite abrirlos."""
        main_window = self.parent()
        history = getattr(main_window, "_hydro_history", [])
        if not history:
            QMessageBox.information(self, "Historial", "No hay análisis hidrológicos en el historial.")
            return

        if hasattr(main_window, "_hydro_history_dialog") and main_window._hydro_history_dialog is not None:
            try:
                main_window._hydro_history_dialog.close()
            except RuntimeError:
                pass
                
        dlg = QDialog(self)
        dlg.setWindowTitle("Historial de Análisis Hidrológicos")
        dlg.setMinimumSize(400, 300)
        dlg.setWindowFlags(Qt.WindowType.Window)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        main_window._hydro_history_dialog = dlg
        
        l = QVBoxLayout(dlg)
        
        list_widget = QListWidget()
        for idx, item in enumerate(history):
            text = f"[{item['timestamp']}] MDT: {item['layer']} ({len(item['results'])} capas)"
            lw_item = QListWidgetItem(text)
            lw_item.setData(Qt.ItemDataRole.UserRole, idx)
            list_widget.addItem(lw_item)
            
        l.addWidget(list_widget)
        
        btn_open = QPushButton("Abrir resultados seleccionados")
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
            QMessageBox.warning(self, "Aviso", "Selecciona un MDT primero.")
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
                QMessageBox.information(self, "Completado", "Análisis hidrológico completado.\nPresiona 'Ver resultados' para ver las imágenes.")
            else:
                QMessageBox.warning(self, "Aviso", "No se seleccionó ningún análisis.")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            logger.error(f"Error en análisis hidrológico: {e}", exc_info=True)


    # ------------------------------------------------------------------
    # Vegetation Tab
    # ------------------------------------------------------------------

    def _build_vegetation_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        grp_src = QGroupBox("Raster de entrada (CHM)")
        form_src = QFormLayout(grp_src)
        self._veg_raster = self._get_raster_combo()
        form_src.addRow("CHM", self._veg_raster)
        layout.addWidget(grp_src)

        grp_params = QGroupBox("Parámetros")
        form_p = QFormLayout(grp_params)

        self._min_tree_height = QDoubleSpinBox()
        self._min_tree_height.setRange(0.5, 50.0)
        self._min_tree_height.setValue(2.0)
        self._min_tree_height.setSuffix(" m")
        form_p.addRow("Altura mín. árbol", self._min_tree_height)

        self._crown_window = QSpinBox()
        self._crown_window.setRange(3, 21)
        self._crown_window.setValue(5)
        self._crown_window.setSuffix(" px")
        form_p.addRow("Ventana detección", self._crown_window)

        self._density_cell = QDoubleSpinBox()
        self._density_cell.setRange(1, 100)
        self._density_cell.setValue(10)
        self._density_cell.setSuffix(" m")
        form_p.addRow("Celda densidad", self._density_cell)

        layout.addWidget(grp_params)

        grp_anal = QGroupBox("Análisis")
        vl = QVBoxLayout(grp_anal)
        self._chk_tree_detect = QCheckBox("Detectar árboles individuales")
        self._chk_tree_detect.setChecked(True)
        vl.addWidget(self._chk_tree_detect)
        self._chk_crown_seg = QCheckBox("Segmentar copas (watershed)")
        vl.addWidget(self._chk_crown_seg)
        self._chk_density = QCheckBox("Mapa de densidad")
        vl.addWidget(self._chk_density)
        layout.addWidget(grp_anal)

        btn_run = QPushButton("▶ Ejecutar análisis de vegetación")
        btn_run.setObjectName("primary")
        btn_run.clicked.connect(self._run_vegetation)
        layout.addWidget(btn_run)

        layout.addStretch()
        return tab

    def _run_vegetation(self):
        idx = self._veg_raster.currentData()
        if idx is None or idx < 0:
            QMessageBox.warning(self, "Aviso", "Selecciona un CHM primero.")
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
                logger.info(f"Detectados {len(tree_tops)} árboles")

            if self._chk_crown_seg.isChecked() and tree_tops is not None:
                labels, height_map = segment_crowns(chm, tree_tops)
                crown_rl = build_crown_raster(chm, height_map, labels)
                self.layer_manager.add_layer(crown_rl)

            if self._chk_density.isChecked():
                result = density_map(chm, self._density_cell.value())
                self.layer_manager.add_layer(result)

            msg = "Análisis de vegetación completado."
            if tree_tops is not None:
                msg += f"\nÁrboles detectados: {len(tree_tops)}"
            QMessageBox.information(self, "Completado", msg)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ------------------------------------------------------------------
    # Multitemporal Tab
    # ------------------------------------------------------------------

    def _build_multitemporal_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        grp_src = QGroupBox("Rasters de entrada")
        form_src = QFormLayout(grp_src)
        self._multi_before = self._get_raster_combo()
        form_src.addRow("DEM anterior", self._multi_before)
        self._multi_after = self._get_raster_combo()
        form_src.addRow("DEM posterior", self._multi_after)
        layout.addWidget(grp_src)

        grp_params = QGroupBox("Parámetros")
        form_p = QFormLayout(grp_params)
        self._dod_threshold = QDoubleSpinBox()
        self._dod_threshold.setRange(0.01, 10.0)
        self._dod_threshold.setValue(0.3)
        self._dod_threshold.setSuffix(" m")
        form_p.addRow("Umbral cambio", self._dod_threshold)
        layout.addWidget(grp_params)

        grp_anal = QGroupBox("Análisis")
        vl = QVBoxLayout(grp_anal)
        self._chk_dod = QCheckBox("Diferencia de DEMs (DoD)")
        self._chk_dod.setChecked(True)
        vl.addWidget(self._chk_dod)
        self._chk_change_class = QCheckBox("Clasificar cambios")
        self._chk_change_class.setChecked(True)
        vl.addWidget(self._chk_change_class)
        self._chk_deforest = QCheckBox("Detectar deforestación (requiere CHMs)")
        vl.addWidget(self._chk_deforest)
        layout.addWidget(grp_anal)

        btn_run = QPushButton("▶ Ejecutar análisis multitemporal")
        btn_run.setObjectName("primary")
        btn_run.clicked.connect(self._run_multitemporal)
        layout.addWidget(btn_run)

        layout.addStretch()
        return tab

    def _run_multitemporal(self):
        idx_before = self._multi_before.currentData()
        idx_after = self._multi_after.currentData()

        if idx_before is None or idx_before < 0 or idx_after is None or idx_after < 0:
            QMessageBox.warning(self, "Aviso", "Selecciona ambos rasters.")
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

            QMessageBox.information(self, "Completado", "Análisis multitemporal completado.")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
