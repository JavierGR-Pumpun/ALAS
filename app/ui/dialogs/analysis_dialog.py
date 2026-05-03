"""
ALAS — Analysis Dialog
Diálogo unificado de análisis con pestañas: geomorfología, hidrología, vegetación, multitemporal.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QGroupBox,
    QFormLayout, QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox,
    QPushButton, QLabel, QMessageBox, QFileDialog,
    QWidget
)
from PyQt6.QtCore import Qt

from app.core.layer_manager import LayerManager
from app.core.raster_layer import RasterLayer
from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.analysis_dialog")


class AnalysisDialog(QDialog):
    """Diálogo de análisis con pestañas."""

    def __init__(self, initial_tab: str, layer_manager: LayerManager, parent=None):
        super().__init__(parent)
        self.layer_manager = layer_manager
        self.setWindowTitle(tr("menu.analysis"))
        self.setMinimumSize(550, 600)
        self._setup_ui(initial_tab)

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
        for i, entry in enumerate(self.layer_manager.get_all_entries()):
            if entry.is_raster:
                combo.addItem(entry.name, i)
        if combo.count() == 0:
            combo.addItem("(No hay capas raster)", -1)
        return combo

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
        layout.addWidget(grp_anal)

        grp_params = QGroupBox("Parámetros")
        form_p = QFormLayout(grp_params)
        self._drainage_threshold = QSpinBox()
        self._drainage_threshold.setRange(10, 100000)
        self._drainage_threshold.setValue(1000)
        form_p.addRow("Umbral red drenaje", self._drainage_threshold)
        layout.addWidget(grp_params)

        btn_run = QPushButton("▶ Ejecutar análisis hidrológico")
        btn_run.setObjectName("primary")
        btn_run.clicked.connect(self._run_hydrology)
        layout.addWidget(btn_run)

        layout.addStretch()
        return tab

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
                flow_direction, flow_accumulation, detect_ponding_zones
            )

            if self._chk_flow_dir.isChecked():
                result = flow_direction(dtm)
                self.layer_manager.add_layer(result)

            if self._chk_flow_acc.isChecked():
                result = flow_accumulation(dtm)
                self.layer_manager.add_layer(result)

            if self._chk_ponding.isChecked():
                result = detect_ponding_zones(dtm)
                self.layer_manager.add_layer(result)

            QMessageBox.information(self, "Completado", "Análisis hidrológico completado.")

        except Exception as e:

            QMessageBox.critical(self, "Error", str(e))

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
                detect_tree_tops, segment_crowns, density_map
            )

            tree_tops = None
            if self._chk_tree_detect.isChecked():
                tree_tops = detect_tree_tops(
                    chm, self._min_tree_height.value(), self._crown_window.value()
                )
                logger.info(f"Detectados {len(tree_tops)} árboles")

            if self._chk_crown_seg.isChecked() and tree_tops is not None:
                labels = segment_crowns(chm, tree_tops)
                # Guardar como raster
                crown_rl = RasterLayer.from_array(
                    labels.astype(float), chm.bounds,
                    epsg=chm.crs_epsg, name="Copas_segmentadas"
                )
                crown_rl.transform = chm.transform
                crown_rl.crs = chm.crs
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
