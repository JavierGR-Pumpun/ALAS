"""
ALAS — CRS Dialog
Dialog for coordinate reprojection.
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
    """CRS reprojection dialog."""

    def __init__(self, point_cloud: PointCloudData, parent=None):
        super().__init__(parent)
        self.pc = point_cloud
        self.setWindowTitle(tr("action.reproject"))
        self.setMinimumSize(400, 300)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Current CRS
        grp_current = QGroupBox(tr("crs.current"))
        form_c = QFormLayout(grp_current)

        current_epsg = self.pc.crs_epsg or "Unknown"
        self._current_label = QLabel(f"{tr('crs.epsg_prefix')}{current_epsg}")
        self._current_label.setStyleSheet("color: #a855f7; font-weight: 600;")
        form_c.addRow(tr("crs.current_system"), self._current_label)

        layout.addWidget(grp_current)

        # Source EPSG (editable if no CRS)
        grp_source = QGroupBox(tr("crs.source"))
        form_s = QFormLayout(grp_source)

        self._source_epsg = QSpinBox()
        self._source_epsg.setRange(1000, 99999)
        self._source_epsg.setValue(self.pc.crs_epsg or 25830)
        form_s.addRow(tr("crs.source_epsg"), self._source_epsg)
        layout.addWidget(grp_source)

        # Target EPSG
        grp_target = QGroupBox(tr("crs.target"))
        form_t = QFormLayout(grp_target)

        self._target_epsg = QSpinBox()
        self._target_epsg.setRange(1000, 99999)
        self._target_epsg.setValue(25830)
        form_t.addRow(tr("crs.target_epsg"), self._target_epsg)

        # Common CRS shortcuts
        common_label = QLabel(tr("crs.common"))
        common_label.setObjectName("muted")
        common_label.setWordWrap(True)
        form_t.addRow("", common_label)

        layout.addWidget(grp_target)

        layout.addStretch()

        self._processing_label = QLabel(tr("status.processing"))
        self._processing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._processing_label.setObjectName("muted")
        self._processing_label.setVisible(False)
        layout.addWidget(self._processing_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton(tr("dialog.cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        self._btn_reproject = QPushButton(tr("crs.reproject_button"))
        self._btn_reproject.setObjectName("primary")
        self._btn_reproject.clicked.connect(self._do_reproject)
        btn_layout.addWidget(self._btn_reproject)

        layout.addLayout(btn_layout)

    def _do_reproject(self):
        source = self._source_epsg.value()
        target = self._target_epsg.value()

        if source == target:
            QMessageBox.information(self, tr("crs.same_epsg"), tr("crs.same_epsg_msg"))
            return

        from app.processing.workers import ProcessingWorker
        from PyQt6.QtCore import QThreadPool

        self._btn_reproject.setEnabled(False)
        self._processing_label.setVisible(True)

        def _do():
            return reproject(self.pc, source, target)

        def _on_result(result):
            self.pc.xyz = result.xyz
            self.pc.crs_epsg = result.crs_epsg
            self.pc.crs_wkt = result.crs_wkt
            self.pc.name = result.name
            QMessageBox.information(
                self, tr("crs.completed"),
                tr("crs.reprojected").format(source, target)
            )
            self.accept()

        def _on_error(e):
            QMessageBox.critical(self, tr("crs.error"), e)
            self._btn_reproject.setEnabled(True)
            self._processing_label.setVisible(False)

        def _on_finished():
            self._btn_reproject.setEnabled(True)
            self._processing_label.setVisible(False)

        worker = ProcessingWorker(_do)
        worker.signals.result.connect(_on_result)
        worker.signals.error.connect(_on_error)
        worker.signals.finished.connect(_on_finished)
        QThreadPool.globalInstance().start(worker)
