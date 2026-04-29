"""
ALAS — Profile Tool
Herramienta interactiva de perfil topográfico con gráfico matplotlib.
"""

import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFormLayout, QDoubleSpinBox, QGroupBox
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from app.core.raster_layer import RasterLayer
from app.core.point_cloud import PointCloudData
from app.processing.measurements import extract_profile, extract_profile_from_cloud
from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.profile_tool")


class ProfileDialog(QDialog):
    """Diálogo de perfil topográfico con gráfico embebido."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("action.profile"))
        self.setMinimumSize(700, 500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Coordinate inputs
        grp_coords = QGroupBox("Coordenadas del perfil")
        form = QFormLayout(grp_coords)

        self._x1 = QDoubleSpinBox()
        self._x1.setRange(-1e8, 1e8)
        self._x1.setDecimals(2)
        form.addRow("X inicio", self._x1)

        self._y1 = QDoubleSpinBox()
        self._y1.setRange(-1e8, 1e8)
        self._y1.setDecimals(2)
        form.addRow("Y inicio", self._y1)

        self._x2 = QDoubleSpinBox()
        self._x2.setRange(-1e8, 1e8)
        self._x2.setDecimals(2)
        form.addRow("X fin", self._x2)

        self._y2 = QDoubleSpinBox()
        self._y2.setRange(-1e8, 1e8)
        self._y2.setDecimals(2)
        form.addRow("Y fin", self._y2)

        layout.addWidget(grp_coords)

        # Matplotlib canvas
        self._figure = Figure(figsize=(8, 4), facecolor='#1a1a2e')
        self._canvas = FigureCanvas(self._figure)
        self._ax = self._figure.add_subplot(111)
        self._style_axes()
        layout.addWidget(self._canvas)

        # Info label
        self._info = QLabel("")
        self._info.setObjectName("muted")
        layout.addWidget(self._info)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_close = QPushButton(tr("dialog.close"))
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def _style_axes(self):
        """Aplica estilo oscuro al gráfico."""
        self._ax.set_facecolor('#12121f')
        self._ax.tick_params(colors='#a0a0b0', labelsize=9)
        self._ax.spines['bottom'].set_color('#3a3a4d')
        self._ax.spines['left'].set_color('#3a3a4d')
        self._ax.spines['top'].set_visible(False)
        self._ax.spines['right'].set_visible(False)
        self._ax.set_xlabel("Distancia (m)", color='#c0c0d0', fontsize=10)
        self._ax.set_ylabel("Elevación (m)", color='#c0c0d0', fontsize=10)
        self._ax.grid(True, alpha=0.2, color='#3a3a4d')

    def plot_profile(self, distances: np.ndarray, elevations: np.ndarray,
                      title: str = "Perfil topográfico"):
        """Dibuja el perfil en el canvas."""
        self._ax.clear()
        self._style_axes()

        # Línea del perfil
        valid = ~np.isnan(elevations)
        self._ax.fill_between(
            distances[valid], elevations[valid],
            elevations[valid].min(),
            alpha=0.3, color='#7c3aed'
        )
        self._ax.plot(distances[valid], elevations[valid],
                       color='#a855f7', linewidth=2)

        self._ax.set_title(title, color='#e0e0e8', fontsize=12, pad=10)

        self._figure.tight_layout()
        self._canvas.draw()

        # Info
        valid_elev = elevations[valid]
        if len(valid_elev) > 0:
            self._info.setText(
                f"Distancia: {distances[-1]:.1f}m | "
                f"Z min: {valid_elev.min():.2f}m | "
                f"Z max: {valid_elev.max():.2f}m | "
                f"Desnivel: {valid_elev.max() - valid_elev.min():.2f}m"
            )

    def set_coordinates(self, x1, y1, x2, y2):
        """Establece las coordenadas desde selección en viewport."""
        self._x1.setValue(x1)
        self._y1.setValue(y1)
        self._x2.setValue(x2)
        self._y2.setValue(y2)
