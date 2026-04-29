"""
ALAS — Measurement Tools
Herramientas de medición interactivas en el viewport.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFormLayout, QGroupBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt

from app.processing.measurements import measure_3d_distance, calculate_volume
from app.core.raster_layer import RasterLayer
from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.measurement_tools")


class DistanceDialog(QDialog):
    """Diálogo de medición de distancia."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("action.distance"))
        self.setMinimumSize(350, 350)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        grp_a = QGroupBox("Punto A")
        form_a = QFormLayout(grp_a)
        self._ax = QDoubleSpinBox(); self._ax.setRange(-1e8, 1e8); self._ax.setDecimals(3)
        self._ay = QDoubleSpinBox(); self._ay.setRange(-1e8, 1e8); self._ay.setDecimals(3)
        self._az = QDoubleSpinBox(); self._az.setRange(-1e8, 1e8); self._az.setDecimals(3)
        form_a.addRow("X", self._ax)
        form_a.addRow("Y", self._ay)
        form_a.addRow("Z", self._az)
        layout.addWidget(grp_a)

        grp_b = QGroupBox("Punto B")
        form_b = QFormLayout(grp_b)
        self._bx = QDoubleSpinBox(); self._bx.setRange(-1e8, 1e8); self._bx.setDecimals(3)
        self._by = QDoubleSpinBox(); self._by.setRange(-1e8, 1e8); self._by.setDecimals(3)
        self._bz = QDoubleSpinBox(); self._bz.setRange(-1e8, 1e8); self._bz.setDecimals(3)
        form_b.addRow("X", self._bx)
        form_b.addRow("Y", self._by)
        form_b.addRow("Z", self._bz)
        layout.addWidget(grp_b)

        # Calculate button
        btn_calc = QPushButton("Calcular")
        btn_calc.setObjectName("primary")
        btn_calc.clicked.connect(self._calculate)
        layout.addWidget(btn_calc)

        # Results
        self._results = QGroupBox("Resultados")
        self._results_form = QFormLayout(self._results)
        self._dist_3d = QLabel("—")
        self._dist_2d = QLabel("—")
        self._dz = QLabel("—")
        self._slope = QLabel("—")
        self._results_form.addRow("Distancia 3D", self._dist_3d)
        self._results_form.addRow("Distancia 2D", self._dist_2d)
        self._results_form.addRow("Desnivel", self._dz)
        self._results_form.addRow("Pendiente", self._slope)
        layout.addWidget(self._results)

        layout.addStretch()

        btn_close = QPushButton(tr("dialog.close"))
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _calculate(self):
        a = (self._ax.value(), self._ay.value(), self._az.value())
        b = (self._bx.value(), self._by.value(), self._bz.value())

        result = measure_3d_distance(a, b)

        self._dist_3d.setText(f"{result['distance_3d']:.3f} m")
        self._dist_2d.setText(f"{result['distance_2d']:.3f} m")
        self._dz.setText(f"{result['dz']:.3f} m")
        self._slope.setText(
            f"{result['slope_degrees']:.1f}° "
            f"({result['slope_percent']:.1f}%)"
        )


class VolumeDialog(QDialog):
    """Diálogo de cálculo de volumen."""

    def __init__(self, raster: RasterLayer = None, parent=None):
        super().__init__(parent)
        self.raster = raster
        self.setWindowTitle(tr("action.volume"))
        self.setMinimumSize(400, 300)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        grp = QGroupBox("Parámetros")
        form = QFormLayout(grp)

        self._ref_z = QDoubleSpinBox()
        self._ref_z.setRange(-1e6, 1e6)
        self._ref_z.setDecimals(2)
        self._ref_z.setSuffix(" m")
        form.addRow("Z referencia", self._ref_z)
        layout.addWidget(grp)

        btn_calc = QPushButton("Calcular volumen")
        btn_calc.setObjectName("primary")
        btn_calc.clicked.connect(self._calculate)
        layout.addWidget(btn_calc)

        self._results = QGroupBox("Resultados")
        self._rf = QFormLayout(self._results)
        self._cut = QLabel("—")
        self._fill = QLabel("—")
        self._net = QLabel("—")
        self._area = QLabel("—")
        self._rf.addRow("Corte", self._cut)
        self._rf.addRow("Relleno", self._fill)
        self._rf.addRow("Neto", self._net)
        self._rf.addRow("Área", self._area)
        layout.addWidget(self._results)

        layout.addStretch()

        btn_close = QPushButton(tr("dialog.close"))
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _calculate(self):
        if self.raster is None:
            return

        result = calculate_volume(self.raster, self._ref_z.value())

        self._cut.setText(f"{result['cut_volume_m3']:,.1f} m³")
        self._fill.setText(f"{result['fill_volume_m3']:,.1f} m³")
        self._net.setText(f"{result['net_volume_m3']:,.1f} m³")
        self._area.setText(f"{result['area_m2']:,.1f} m²")
