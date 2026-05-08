"""
ALAS — DEM Dialog
Dialog to configure and generate digital models (DTM/DSM/CHM).
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
from app.ui.widgets import LoadingOverlay
from app.processing.workers import ProcessingWorker

logger = get_logger("ui.dem_dialog")


class DEMDialog(QDialog):
    """Digital model generation dialog."""

    def __init__(self, point_cloud: PointCloudData, parent=None):
        super().__init__(parent)
        self.pc = point_cloud
        self._result = None
        self.setWindowTitle(tr("action.generate_dem"))
        self.setMinimumSize(400, 400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(f"{tr('dem.cloud')} {self.pc.name} ({self.pc.point_count:,} points)")
        info.setObjectName("subheading")
        layout.addWidget(info)

        # DEM type
        grp_type = QGroupBox(tr("dem.model_type"))
        form_type = QFormLayout(grp_type)

        self._type_combo = QComboBox()
        self._type_combo.addItem(tr("dem.dtm"), "dtm")
        self._type_combo.addItem(tr("dem.dsm"), "dsm")
        self._type_combo.addItem(tr("dem.chm"), "chm")
        self._type_combo.addItem(tr("dem.all"), "all")
        form_type.addRow(tr("dem.model"), self._type_combo)
        layout.addWidget(grp_type)

        # Parameters
        grp_params = QGroupBox(tr("dem.resolution"))
        form_params = QFormLayout(grp_params)

        self._resolution = QDoubleSpinBox()
        self._resolution.setRange(0.1, 100.0)
        self._resolution.setValue(DEFAULT_DEM_RESOLUTION)
        self._resolution.setDecimals(1)
        self._resolution.setSuffix(" m")
        form_params.addRow(tr("dem.resolution"), self._resolution)

        self._method_combo = QComboBox()
        self._method_combo.addItem(tr("dem.method_idw"), "idw")
        self._method_combo.addItem(tr("dem.method_tin"), "tin")
        self._method_combo.addItem(tr("dem.method_nearest"), "nearest")
        form_params.addRow(tr("dem.interpolation"), self._method_combo)

        self._power = QDoubleSpinBox()
        self._power.setRange(0.5, 5.0)
        self._power.setValue(DEFAULT_IDW_POWER)
        self._power.setDecimals(1)
        form_params.addRow(tr("dem.idw_power"), self._power)

        layout.addWidget(grp_params)

        # Auto-export
        self._auto_export = QCheckBox(tr("dem.auto_export"))
        self._auto_export.setChecked(False)
        layout.addWidget(self._auto_export)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton(tr("dialog.cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_generate = QPushButton(tr("dem.generate"))
        btn_generate.setObjectName("primary")
        btn_generate.clicked.connect(self._generate)
        btn_layout.addWidget(btn_generate)

        layout.addLayout(btn_layout)

        self._loading_overlay = LoadingOverlay(self)
        self._loading_overlay.hide()

    def _generate(self):
        dem_type = self._type_combo.currentData()
        resolution = self._resolution.value()
        method = self._method_combo.currentData()
        power = self._power.value()
        auto_export = self._auto_export.isChecked()

        def _compute():
            results = []
            if dem_type == "dtm":
                results.append(generate_dtm(self.pc, resolution, method, power))
            elif dem_type == "dsm":
                results.append(generate_dsm(self.pc, resolution, method))
            elif dem_type == "chm":
                dtm = generate_dtm(self.pc, resolution, method, power)
                dsm = generate_dsm(self.pc, resolution, method)
                results.append(generate_chm(dtm, dsm))
            elif dem_type == "all":
                dtm = generate_dtm(self.pc, resolution, method, power)
                dsm = generate_dsm(self.pc, resolution, method)
                chm = generate_chm(dtm, dsm)
                results.extend([dtm, dsm, chm])
            return results
        
        self._loading_overlay.show_loading()
        self._auto_export_flag = auto_export
        
        worker = ProcessingWorker(_compute)
        worker.signals.result.connect(self._on_generation_result)
        worker.signals.error.connect(self._on_generation_error)
        worker.signals.finished.connect(lambda: self._loading_overlay.hide_loading())
        
        from PyQt6.QtCore import QThreadPool
        QThreadPool.globalInstance().start(worker)
    
    def _on_generation_result(self, results):
        self._results = results
        
        # Auto-export
        if self._auto_export_flag and self._results:
            if len(self._results) == 1:
                path, _ = QFileDialog.getSaveFileName(
                    self, tr("dem.save_geotiff"), f"{self._results[0].name}.tif",
                    tr("dem.geotiff_filter")
                )
                if path:
                    self._results[0].to_geotiff(path)
            else:
                dir_path = QFileDialog.getExistingDirectory(
                    self, tr("dem.select_folder")
                )
                if dir_path:
                    import os
                    for res in self._results:
                        res.to_geotiff(os.path.join(dir_path, f"{res.name}.tif"))
        
        self.accept()
    
    def _on_generation_error(self, error_msg: str):
        QMessageBox.critical(self, tr("error.processing_failed"), error_msg)

    def get_results(self) -> list[RasterLayer]:
        return getattr(self, '_results', [])
