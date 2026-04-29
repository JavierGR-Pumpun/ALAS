"""
ALAS — Import Dialog
Diálogo de importación con opciones de CRS y decimado.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QCheckBox, QSpinBox, QDoubleSpinBox, QPushButton, QLabel
)
from PyQt6.QtCore import Qt

from app.i18n import tr


class ImportDialog(QDialog):
    """Diálogo de opciones de importación."""

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setWindowTitle("Opciones de importación")
        self.setMinimumSize(400, 300)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(f"Archivo: {self.file_path}")
        info.setWordWrap(True)
        layout.addWidget(info)

        # CRS override
        grp_crs = QGroupBox("Sistema de coordenadas")
        form_crs = QFormLayout(grp_crs)

        self._override_crs = QCheckBox("Asignar CRS manualmente")
        form_crs.addRow("", self._override_crs)

        self._epsg_override = QSpinBox()
        self._epsg_override.setRange(1000, 99999)
        self._epsg_override.setValue(25830)
        self._epsg_override.setEnabled(False)
        self._override_crs.toggled.connect(self._epsg_override.setEnabled)
        form_crs.addRow("EPSG", self._epsg_override)
        layout.addWidget(grp_crs)

        # Decimation
        grp_dec = QGroupBox("Decimado en importación")
        form_dec = QFormLayout(grp_dec)

        self._decimate = QCheckBox("Decimar al importar")
        form_dec.addRow("", self._decimate)

        self._voxel_size = QDoubleSpinBox()
        self._voxel_size.setRange(0.01, 100.0)
        self._voxel_size.setValue(0.5)
        self._voxel_size.setSuffix(" m")
        self._voxel_size.setEnabled(False)
        self._decimate.toggled.connect(self._voxel_size.setEnabled)
        form_dec.addRow("Tamaño voxel", self._voxel_size)
        layout.addWidget(grp_dec)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton(tr("dialog.cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_ok = QPushButton(tr("dialog.ok"))
        btn_ok.setObjectName("primary")
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_ok)

        layout.addLayout(btn_layout)

    def get_options(self) -> dict:
        return {
            "override_crs": self._override_crs.isChecked(),
            "epsg": self._epsg_override.value() if self._override_crs.isChecked() else None,
            "decimate": self._decimate.isChecked(),
            "voxel_size": self._voxel_size.value() if self._decimate.isChecked() else None,
        }
