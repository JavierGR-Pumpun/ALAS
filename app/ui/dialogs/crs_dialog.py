"""
ALAS — CRS Dialog
Diálogo para reproyección de coordenadas.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLineEdit, QSpinBox, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt

from app.core.point_cloud import PointCloudData
from app.processing.preprocessing import reproject
from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.crs_dialog")


class CRSDialog(QDialog):
    """Diálogo de reproyección CRS."""

    def __init__(self, point_cloud: PointCloudData, parent=None):
        super().__init__(parent)
        self.pc = point_cloud
        self.setWindowTitle(tr("action.reproject"))
        self.setMinimumSize(400, 300)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Current CRS
        grp_current = QGroupBox("CRS actual")
        form_c = QFormLayout(grp_current)

        current_epsg = self.pc.crs_epsg or "Desconocido"
        self._current_label = QLabel(f"EPSG:{current_epsg}")
        self._current_label.setStyleSheet("color: #a855f7; font-weight: 600;")
        form_c.addRow("Sistema actual", self._current_label)

        layout.addWidget(grp_current)

        # Source EPSG (editable si no hay CRS)
        grp_source = QGroupBox("EPSG de origen")
        form_s = QFormLayout(grp_source)

        self._source_epsg = QSpinBox()
        self._source_epsg.setRange(1000, 99999)
        self._source_epsg.setValue(self.pc.crs_epsg or 25830)
        form_s.addRow("EPSG origen", self._source_epsg)
        layout.addWidget(grp_source)

        # Target EPSG
        grp_target = QGroupBox("EPSG de destino")
        form_t = QFormLayout(grp_target)

        self._target_epsg = QSpinBox()
        self._target_epsg.setRange(1000, 99999)
        self._target_epsg.setValue(25830)
        form_t.addRow("EPSG destino", self._target_epsg)

        # Common CRS shortcuts
        common_label = QLabel(
            "Comunes: 4326 (WGS84) | 25830 (ETRS89 UTM 30N) | "
            "25829 (UTM 29N) | 32630 (WGS84 UTM 30N)"
        )
        common_label.setObjectName("muted")
        common_label.setWordWrap(True)
        form_t.addRow("", common_label)

        layout.addWidget(grp_target)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton(tr("dialog.cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_reproject = QPushButton("Reproyectar")
        btn_reproject.setObjectName("primary")
        btn_reproject.clicked.connect(self._do_reproject)
        btn_layout.addWidget(btn_reproject)

        layout.addLayout(btn_layout)

    def _do_reproject(self):
        source = self._source_epsg.value()
        target = self._target_epsg.value()

        if source == target:
            QMessageBox.information(self, "Info", "Origen y destino son iguales.")
            return

        try:
            result = reproject(self.pc, source, target)

            # Update in-place
            self.pc.xyz = result.xyz
            self.pc.crs_epsg = result.crs_epsg
            self.pc.crs_wkt = result.crs_wkt
            self.pc.name = result.name

            QMessageBox.information(
                self, "Completado",
                f"Reproyectado de EPSG:{source} a EPSG:{target}"
            )
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
