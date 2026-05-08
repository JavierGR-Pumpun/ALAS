"""
ALAS — Classification Dialog
Dialog to configure and execute terrain classification.
"""

import numpy as np
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QComboBox, QDoubleSpinBox, QSpinBox, QPushButton, QLabel,
    QMessageBox, QLineEdit, QFileDialog, QCheckBox, QApplication
)
from PyQt6.QtCore import Qt

from app.core.point_cloud import PointCloudData
from app.processing.classification import (
    classify_ground_smrf, classify_ground_csf, classify_ground_pmf,
    classify_above_ground, classify_ai,
)
from app.config import SMRF_DEFAULTS, CSF_DEFAULTS, PMF_DEFAULTS, MODELS_DIR
from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.classification_dialog")

_DEFAULT_MODEL = str(MODELS_DIR / "classifier_best.pt")


class ClassificationDialog(QDialog):
    """Terrain classification configuration dialog."""

    def __init__(self, point_cloud: PointCloudData, parent=None):
        super().__init__(parent)
        self.pc = point_cloud
        self._result = None
        self._classification_data = None
        self.setWindowTitle(tr("action.classify"))
        self.setMinimumSize(450, 500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Info
        info = QLabel(f"{tr('classify.cloud_info')} {self.pc.name} ({self.pc.point_count:,} points)")
        info.setObjectName("subheading")
        layout.addWidget(info)

        # Algorithm selection
        grp_algo = QGroupBox(tr("classify.algorithm"))
        form_algo = QFormLayout(grp_algo)

        self._algo_combo = QComboBox()
        self._algo_combo.addItem(tr("classify.smrf"), "smrf")
        self._algo_combo.addItem(tr("classify.csf"),  "csf")
        self._algo_combo.addItem(tr("classify.pmf"),  "pmf")
        self._algo_combo.addItem(tr("classify.ai"),   "ai")
        self._algo_combo.currentIndexChanged.connect(self._on_algo_changed)
        form_algo.addRow(tr("classify.algorithm"), self._algo_combo)
        layout.addWidget(grp_algo)

        # ── SMRF parameters ───────────────────────────────────────────────
        self._grp_smrf = QGroupBox(tr("classify.smrf_params"))
        form_smrf = QFormLayout(self._grp_smrf)

        self._smrf_window = QDoubleSpinBox()
        self._smrf_window.setRange(1, 100)
        self._smrf_window.setValue(SMRF_DEFAULTS["window"])
        self._smrf_window.setDecimals(1)
        form_smrf.addRow(tr("classify.window"), self._smrf_window)

        self._smrf_slope = QDoubleSpinBox()
        self._smrf_slope.setRange(0.01, 5.0)
        self._smrf_slope.setValue(SMRF_DEFAULTS["slope"])
        self._smrf_slope.setDecimals(2)
        self._smrf_slope.setSingleStep(0.05)
        form_smrf.addRow(tr("classify.slope"), self._smrf_slope)

        self._smrf_threshold = QDoubleSpinBox()
        self._smrf_threshold.setRange(0.01, 10.0)
        self._smrf_threshold.setValue(SMRF_DEFAULTS["threshold"])
        self._smrf_threshold.setDecimals(2)
        form_smrf.addRow(tr("classify.threshold"), self._smrf_threshold)

        layout.addWidget(self._grp_smrf)

        # ── CSF parameters ────────────────────────────────────────────────
        self._grp_csf = QGroupBox(tr("classify.csf_params"))
        form_csf = QFormLayout(self._grp_csf)

        self._csf_resolution = QDoubleSpinBox()
        self._csf_resolution.setRange(0.1, 10.0)
        self._csf_resolution.setValue(CSF_DEFAULTS["resolution"])
        self._csf_resolution.setDecimals(1)
        form_csf.addRow(tr("classify.resolution"), self._csf_resolution)

        self._csf_rigidness = QSpinBox()
        self._csf_rigidness.setRange(1, 3)
        self._csf_rigidness.setValue(CSF_DEFAULTS["rigidness"])
        form_csf.addRow(tr("classify.rigidity"), self._csf_rigidness)

        self._csf_threshold = QDoubleSpinBox()
        self._csf_threshold.setRange(0.01, 5.0)
        self._csf_threshold.setValue(CSF_DEFAULTS["threshold"])
        self._csf_threshold.setDecimals(2)
        form_csf.addRow(tr("classify.threshold"), self._csf_threshold)

        layout.addWidget(self._grp_csf)
        self._grp_csf.hide()

        # ── PMF parameters ────────────────────────────────────────────────
        self._grp_pmf = QGroupBox(tr("classify.pmf_params"))
        form_pmf = QFormLayout(self._grp_pmf)

        self._pmf_max_window = QDoubleSpinBox()
        self._pmf_max_window.setRange(1, 100)
        self._pmf_max_window.setValue(PMF_DEFAULTS["max_window_size"])
        form_pmf.addRow(tr("classify.max_window"), self._pmf_max_window)

        self._pmf_slope = QDoubleSpinBox()
        self._pmf_slope.setRange(0.1, 10.0)
        self._pmf_slope.setValue(PMF_DEFAULTS["slope"])
        form_pmf.addRow(tr("classify.slope"), self._pmf_slope)

        layout.addWidget(self._grp_pmf)
        self._grp_pmf.hide()

        # ── AI parameters ─────────────────────────────────────────────────
        self._grp_ai = QGroupBox(tr("classify.ai_params"))
        form_ai = QFormLayout(self._grp_ai)

        # Model path row: line edit + browse button
        path_row = QHBoxLayout()
        self._ai_model_path = QLineEdit()
        self._ai_model_path.setPlaceholderText(_DEFAULT_MODEL)
        if Path(_DEFAULT_MODEL).exists():
            self._ai_model_path.setText(_DEFAULT_MODEL)
        path_row.addWidget(self._ai_model_path)

        btn_browse = QPushButton(tr("classify.browse"))
        btn_browse.setFixedWidth(90)
        btn_browse.clicked.connect(self._browse_model)
        path_row.addWidget(btn_browse)

        path_widget = QLabel()  # dummy widget to host the layout in the form
        path_widget.setLayout(path_row)
        path_widget.setContentsMargins(0, 0, 0, 0)
        form_ai.addRow(tr("classify.model_path"), path_widget)

        self._ai_batch_size = QSpinBox()
        self._ai_batch_size.setRange(1024, 1_048_576)
        self._ai_batch_size.setValue(65536)
        self._ai_batch_size.setSingleStep(8192)
        form_ai.addRow(tr("classify.batch_size"), self._ai_batch_size)

        ai_info = QLabel(tr("classify.ai_info"))
        ai_info.setObjectName("muted")
        ai_info.setWordWrap(True)
        form_ai.addRow("", ai_info)

        layout.addWidget(self._grp_ai)
        self._grp_ai.hide()

        # ── Post-processing checkbox ──────────────────────────────────────
        self._classify_above = QCheckBox(tr("classify.classify_veg"))
        self._classify_above.setChecked(True)
        layout.addWidget(self._classify_above)

        layout.addStretch()

        # ── Buttons ───────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_clear = QPushButton(tr("classify.clear_button"))
        btn_clear.clicked.connect(self._clear_classification)
        btn_layout.addWidget(btn_clear)

        btn_cancel = QPushButton(tr("dialog.cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_run = QPushButton(tr("dialog.apply"))
        btn_run.setObjectName("primary")
        btn_run.clicked.connect(self._run_classification)
        btn_layout.addWidget(btn_run)

        layout.addLayout(btn_layout)

    # ------------------------------------------------------------------

    def _on_algo_changed(self, _index: int):
        algo = self._algo_combo.currentData()
        self._grp_smrf.setVisible(algo == "smrf")
        self._grp_csf.setVisible(algo == "csf")
        self._grp_pmf.setVisible(algo == "pmf")
        self._grp_ai.setVisible(algo == "ai")
        # AI handles all classes itself — post-ground step is irrelevant
        self._classify_above.setVisible(algo != "ai")
        self.adjustSize()

    def _browse_model(self):
        start_dir = str(MODELS_DIR) if MODELS_DIR.exists() else ""
        path, _ = QFileDialog.getOpenFileName(
            self, tr("classify.model_path"), start_dir,
            "PyTorch model (*.pt *.pth);;All files (*)"
        )
        if path:
            self._ai_model_path.setText(path)

    def _run_classification(self):
        algo = self._algo_combo.currentData()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if algo == "smrf":
                self._result = classify_ground_smrf(
                    self.pc,
                    window=self._smrf_window.value(),
                    slope=self._smrf_slope.value(),
                    threshold=self._smrf_threshold.value(),
                )
                self._classification_data = {
                    "window": self._smrf_window.value(),
                    "slope": self._smrf_slope.value(),
                    "threshold": self._smrf_threshold.value(),
                }
            elif algo == "csf":
                self._result = classify_ground_csf(
                    self.pc,
                    resolution=self._csf_resolution.value(),
                    rigidness=self._csf_rigidness.value(),
                    threshold=self._csf_threshold.value(),
                )
                self._classification_data = {
                    "resolution": self._csf_resolution.value(),
                    "rigidness": self._csf_rigidness.value(),
                    "threshold": self._csf_threshold.value(),
                }
            elif algo == "pmf":
                self._result = classify_ground_pmf(
                    self.pc,
                    max_window_size=self._pmf_max_window.value(),
                    slope=self._pmf_slope.value(),
                )
                self._classification_data = {
                    "max_window_size": self._pmf_max_window.value(),
                    "slope": self._pmf_slope.value(),
                }
            elif algo == "ai":
                model_path = self._ai_model_path.text().strip()
                if not model_path:
                    model_path = _DEFAULT_MODEL
                if not Path(model_path).exists():
                    QApplication.restoreOverrideCursor()
                    QMessageBox.critical(
                        self, tr("error.processing_failed"),
                        f"{tr('classify.model_not_found')}\n{model_path}"
                    )
                    return
                self._result = classify_ai(
                    self.pc,
                    model_path=model_path,
                    batch_size=self._ai_batch_size.value(),
                )
                self._classification_data = {
                    "model_path": model_path,
                    "batch_size": self._ai_batch_size.value(),
                }

            post_process = False
            if algo != "ai" and self._classify_above.isChecked() and self._result is not None:
                self.pc.classification = self._result
                self._result = classify_above_ground(self.pc)
                post_process = True

            if self._classification_data is not None:
                self._classification_data["post_process"] = post_process
                self._classification_data["algorithm"] = algo
                self._classification_data["total_points"] = self.pc.point_count
                for class_code in range(8):
                    count = int(np.sum(self._result == class_code))
                    self._classification_data[f"class_{class_code}"] = count
                self._classification_data["ground_points"] = int(np.sum(self._result == 2))

            self.accept()

        except ImportError as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, tr("error.processing_failed"), tr("classify.error_torch"))
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, tr("error.processing_failed"), str(e))
        else:
            QApplication.restoreOverrideCursor()

    def _clear_classification(self):
        if self.pc.classification is None:
            QMessageBox.information(self, tr("dialog.confirm"), tr("classify.info_no_class"))
            return
        reply = QMessageBox.question(
            self, tr("classify.confirm_clear"),
            tr("classify.confirm_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.pc.classification[:] = 1
            self._result = self.pc.classification.copy()
            self.accept()

    def get_result(self):
        return self._result

    def get_classification_data(self):
        return self._classification_data
