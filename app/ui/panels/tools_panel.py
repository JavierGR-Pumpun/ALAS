"""
ALAS — Tools Panel
Panel de herramientas activas: tamaño de punto, colorización, configuración de vista.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QSlider, QComboBox,
    QPushButton, QLabel, QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.config import (
    COLORIZE_MODES, COLORIZE_HEIGHT, COLORIZE_INTENSITY,
    COLORIZE_CLASSIFICATION, COLORIZE_RETURN_NUMBER,
    COLORIZE_RGB, COLORIZE_SINGLE, DEFAULT_POINT_SIZE
)
from app.i18n import tr


class ToolsPanel(QWidget):
    """Panel de herramientas de visualización."""

    point_size_changed = pyqtSignal(float)
    colorize_mode_changed = pyqtSignal(str)
    view_reset_requested = pyqtSignal()
    view_top_requested = pyqtSignal()
    view_front_requested = pyqtSignal()
    view_side_requested = pyqtSignal()

    COLORIZE_LABELS = {
        COLORIZE_HEIGHT: "Altura (Z)",
        COLORIZE_INTENSITY: "Intensidad",
        COLORIZE_CLASSIFICATION: "Clasificación",
        COLORIZE_RETURN_NUMBER: "Nº Retorno",
        COLORIZE_RGB: "RGB Original",
        COLORIZE_SINGLE: "Color sólido",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Visualización ---
        grp_vis = QGroupBox("Visualización")
        form_vis = QFormLayout(grp_vis)

        # Point size slider
        self._point_size_label = QLabel(f"{DEFAULT_POINT_SIZE:.0f}")
        self._point_size_slider = QSlider(Qt.Orientation.Horizontal)
        self._point_size_slider.setRange(1, 20)
        self._point_size_slider.setValue(int(DEFAULT_POINT_SIZE))
        self._point_size_slider.valueChanged.connect(self._on_point_size)

        ps_row = QHBoxLayout()
        ps_row.addWidget(self._point_size_slider)
        ps_row.addWidget(self._point_size_label)
        form_vis.addRow("Tamaño punto", ps_row)

        # Colorize mode
        self._colorize_combo = QComboBox()
        for mode in COLORIZE_MODES:
            self._colorize_combo.addItem(self.COLORIZE_LABELS.get(mode, mode), mode)
        self._colorize_combo.currentIndexChanged.connect(self._on_colorize_changed)
        form_vis.addRow("Colorear por", self._colorize_combo)

        layout.addWidget(grp_vis)

        # --- Cámara ---
        grp_cam = QGroupBox("Cámara")
        cam_layout = QVBoxLayout(grp_cam)

        btn_row1 = QHBoxLayout()
        btn_reset = QPushButton("⟲ Reset")
        btn_reset.clicked.connect(self.view_reset_requested.emit)
        btn_top = QPushButton("⬆ Cenital")
        btn_top.clicked.connect(self.view_top_requested.emit)
        btn_row1.addWidget(btn_reset)
        btn_row1.addWidget(btn_top)
        cam_layout.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        btn_front = QPushButton("◻ Frontal")
        btn_front.clicked.connect(self.view_front_requested.emit)
        btn_side = QPushButton("◻ Lateral")
        btn_side.clicked.connect(self.view_side_requested.emit)
        btn_row2.addWidget(btn_front)
        btn_row2.addWidget(btn_side)
        cam_layout.addLayout(btn_row2)

        layout.addWidget(grp_cam)
        layout.addStretch()

    def _on_point_size(self, value: int):
        self._point_size_label.setText(str(value))
        self.point_size_changed.emit(float(value))

    def _on_colorize_changed(self, index: int):
        mode = self._colorize_combo.itemData(index)
        if mode:
            self.colorize_mode_changed.emit(mode)
