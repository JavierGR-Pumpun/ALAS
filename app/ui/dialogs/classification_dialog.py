"""
ALAS — Classification Dialog
Diálogo para configurar y ejecutar clasificación de terreno.
"""

import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QComboBox, QDoubleSpinBox, QSpinBox, QPushButton, QLabel,
    QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt

from app.core.point_cloud import PointCloudData
from app.processing.classification import (
    classify_ground_smrf, classify_ground_csf, classify_ground_pmf,
    classify_above_ground
)
from app.config import SMRF_DEFAULTS, CSF_DEFAULTS, PMF_DEFAULTS
from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.classification_dialog")


class ClassificationDialog(QDialog):
    """Diálogo de configuración de clasificación de terreno."""

    def __init__(self, point_cloud: PointCloudData, parent=None):
        super().__init__(parent)
        self.pc = point_cloud
        self._result = None
        self.setWindowTitle(tr("action.classify"))
        self.setMinimumSize(450, 500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Info
        info = QLabel(f"Nube: {self.pc.name} ({self.pc.point_count:,} puntos)")
        info.setObjectName("subheading")
        layout.addWidget(info)

        # Algorithm selection
        grp_algo = QGroupBox("Algoritmo")
        form_algo = QFormLayout(grp_algo)

        self._algo_combo = QComboBox()
        self._algo_combo.addItem("SMRF (Simple Morphological Filter)", "smrf")
        self._algo_combo.addItem("CSF (Cloth Simulation Filter)", "csf")
        self._algo_combo.addItem("PMF (Progressive Morphological Filter)", "pmf")
        self._algo_combo.currentIndexChanged.connect(self._on_algo_changed)
        form_algo.addRow("Algoritmo", self._algo_combo)
        layout.addWidget(grp_algo)

        # SMRF parameters
        self._grp_smrf = QGroupBox("Parámetros SMRF")
        form_smrf = QFormLayout(self._grp_smrf)

        self._smrf_window = QDoubleSpinBox()
        self._smrf_window.setRange(1, 100)
        self._smrf_window.setValue(SMRF_DEFAULTS["window"])
        self._smrf_window.setDecimals(1)
        form_smrf.addRow("Ventana (m)", self._smrf_window)

        self._smrf_slope = QDoubleSpinBox()
        self._smrf_slope.setRange(0.01, 5.0)
        self._smrf_slope.setValue(SMRF_DEFAULTS["slope"])
        self._smrf_slope.setDecimals(2)
        self._smrf_slope.setSingleStep(0.05)
        form_smrf.addRow("Pendiente", self._smrf_slope)

        self._smrf_threshold = QDoubleSpinBox()
        self._smrf_threshold.setRange(0.01, 10.0)
        self._smrf_threshold.setValue(SMRF_DEFAULTS["threshold"])
        self._smrf_threshold.setDecimals(2)
        form_smrf.addRow("Umbral (m)", self._smrf_threshold)

        layout.addWidget(self._grp_smrf)

        # CSF parameters
        self._grp_csf = QGroupBox("Parámetros CSF")
        form_csf = QFormLayout(self._grp_csf)

        self._csf_resolution = QDoubleSpinBox()
        self._csf_resolution.setRange(0.1, 10.0)
        self._csf_resolution.setValue(CSF_DEFAULTS["resolution"])
        self._csf_resolution.setDecimals(1)
        form_csf.addRow("Resolución (m)", self._csf_resolution)

        self._csf_rigidness = QSpinBox()
        self._csf_rigidness.setRange(1, 3)
        self._csf_rigidness.setValue(CSF_DEFAULTS["rigidness"])
        form_csf.addRow("Rigidez (1-3)", self._csf_rigidness)

        self._csf_threshold = QDoubleSpinBox()
        self._csf_threshold.setRange(0.01, 5.0)
        self._csf_threshold.setValue(CSF_DEFAULTS["threshold"])
        self._csf_threshold.setDecimals(2)
        form_csf.addRow("Umbral (m)", self._csf_threshold)

        layout.addWidget(self._grp_csf)
        self._grp_csf.hide()

        # PMF parameters
        self._grp_pmf = QGroupBox("Parámetros PMF")
        form_pmf = QFormLayout(self._grp_pmf)

        self._pmf_max_window = QDoubleSpinBox()
        self._pmf_max_window.setRange(1, 100)
        self._pmf_max_window.setValue(PMF_DEFAULTS["max_window_size"])
        form_pmf.addRow("Ventana máx. (m)", self._pmf_max_window)

        self._pmf_slope = QDoubleSpinBox()
        self._pmf_slope.setRange(0.1, 10.0)
        self._pmf_slope.setValue(PMF_DEFAULTS["slope"])
        form_pmf.addRow("Pendiente", self._pmf_slope)

        layout.addWidget(self._grp_pmf)
        self._grp_pmf.hide()

        # Classify above ground checkbox
        from PyQt6.QtWidgets import QCheckBox
        self._classify_above = QCheckBox("Clasificar vegetación y edificios (post-suelo)")
        self._classify_above.setChecked(True)
        layout.addWidget(self._classify_above)

        # Progress
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton(tr("dialog.cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_run = QPushButton(tr("dialog.apply"))
        btn_run.setObjectName("primary")
        btn_run.clicked.connect(self._run_classification)
        btn_layout.addWidget(btn_run)

        layout.addLayout(btn_layout)

    def _on_algo_changed(self, index: int):
        algo = self._algo_combo.currentData()
        self._grp_smrf.setVisible(algo == "smrf")
        self._grp_csf.setVisible(algo == "csf")
        self._grp_pmf.setVisible(algo == "pmf")

    def _run_classification(self):
        algo = self._algo_combo.currentData()
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)  # Indeterminate

        try:
            if algo == "smrf":
                self._result = classify_ground_smrf(
                    self.pc,
                    window=self._smrf_window.value(),
                    slope=self._smrf_slope.value(),
                    threshold=self._smrf_threshold.value(),
                )
            elif algo == "csf":
                self._result = classify_ground_csf(
                    self.pc,
                    resolution=self._csf_resolution.value(),
                    rigidness=self._csf_rigidness.value(),
                    threshold=self._csf_threshold.value(),
                )
            elif algo == "pmf":
                self._result = classify_ground_pmf(
                    self.pc,
                    max_window_size=self._pmf_max_window.value(),
                    slope=self._pmf_slope.value(),
                )

            # Clasificar sobre suelo
            if self._classify_above.isChecked() and self._result is not None:
                self.pc.classification = self._result
                self._result = classify_above_ground(self.pc)

            self._progress.setRange(0, 100)
            self._progress.setValue(100)
            self.accept()

        except Exception as e:
            self._progress.setVisible(False)
            QMessageBox.critical(self, tr("error.processing_failed"), str(e))

    def get_result(self):
        return self._result
