"""
ALAS — DEM Dialog
Diálogo para configurar y generar modelos digitales (MDT/MDS/CHM).
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QComboBox, QDoubleSpinBox, QPushButton, QLabel,
    QFileDialog, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt

from app.core.point_cloud import PointCloudData
from app.core.raster_layer import RasterLayer
from app.processing.dem_generator import generate_dtm, generate_dsm, generate_chm
from app.config import DEFAULT_DEM_RESOLUTION, DEFAULT_IDW_POWER
from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.dem_dialog")


class DEMDialog(QDialog):
    """Diálogo de generación de modelos digitales."""

    def __init__(self, point_cloud: PointCloudData, parent=None):
        super().__init__(parent)
        self.pc = point_cloud
        self._result = None
        self.setWindowTitle(tr("action.generate_dem"))
        self.setMinimumSize(400, 400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(f"Nube: {self.pc.name} ({self.pc.point_count:,} puntos)")
        info.setObjectName("subheading")
        layout.addWidget(info)

        # DEM type
        grp_type = QGroupBox("Tipo de modelo")
        form_type = QFormLayout(grp_type)

        self._type_combo = QComboBox()
        self._type_combo.addItem(tr("dem.dtm"), "dtm")
        self._type_combo.addItem(tr("dem.dsm"), "dsm")
        self._type_combo.addItem(tr("dem.chm"), "chm")
        form_type.addRow("Modelo", self._type_combo)
        layout.addWidget(grp_type)

        # Parameters
        grp_params = QGroupBox("Parámetros")
        form_params = QFormLayout(grp_params)

        self._resolution = QDoubleSpinBox()
        self._resolution.setRange(0.1, 100.0)
        self._resolution.setValue(DEFAULT_DEM_RESOLUTION)
        self._resolution.setDecimals(1)
        self._resolution.setSuffix(" m")
        form_params.addRow("Resolución", self._resolution)

        self._method_combo = QComboBox()
        self._method_combo.addItem("IDW (Inverse Distance Weighting)", "idw")
        self._method_combo.addItem("TIN (Triangulación Delaunay)", "tin")
        self._method_combo.addItem("Vecino más cercano", "nearest")
        form_params.addRow("Interpolación", self._method_combo)

        self._power = QDoubleSpinBox()
        self._power.setRange(0.5, 5.0)
        self._power.setValue(DEFAULT_IDW_POWER)
        self._power.setDecimals(1)
        form_params.addRow("Potencia IDW", self._power)

        layout.addWidget(grp_params)

        # Auto-export
        self._auto_export = QCheckBox("Exportar automáticamente como GeoTIFF")
        self._auto_export.setChecked(False)
        layout.addWidget(self._auto_export)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton(tr("dialog.cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_generate = QPushButton("Generar")
        btn_generate.setObjectName("primary")
        btn_generate.clicked.connect(self._generate)
        btn_layout.addWidget(btn_generate)

        layout.addLayout(btn_layout)

    def _generate(self):
        dem_type = self._type_combo.currentData()
        resolution = self._resolution.value()
        method = self._method_combo.currentData()
        power = self._power.value()

        try:
            if dem_type == "dtm":
                self._result = generate_dtm(self.pc, resolution, method, power)
            elif dem_type == "dsm":
                self._result = generate_dsm(self.pc, resolution, method)
            elif dem_type == "chm":
                # Generar ambos y calcular diferencia
                dtm = generate_dtm(self.pc, resolution, method, power)
                dsm = generate_dsm(self.pc, resolution, method)
                self._result = generate_chm(dtm, dsm)

            # Auto-export
            if self._auto_export.isChecked() and self._result:
                path, _ = QFileDialog.getSaveFileName(
                    self, "Guardar GeoTIFF", f"{self._result.name}.tif",
                    "GeoTIFF (*.tif)"
                )
                if path:
                    self._result.to_geotiff(path)

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, tr("error.processing_failed"), str(e))

    def get_result(self) -> RasterLayer:
        return self._result
