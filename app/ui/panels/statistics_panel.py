"""
ALAS — Statistics Panel
Panel de estadísticas con histograma y resumen numérico.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout, QScrollArea
)
from PyQt6.QtCore import Qt

from app.core.layer_manager import LayerManager
from app.core.point_cloud import PointCloudData
from app.core.raster_layer import RasterLayer
from app.i18n import tr


class StatisticsPanel(QWidget):
    """Panel que muestra estadísticas de la capa activa."""

    def __init__(self, layer_manager: LayerManager, parent=None):
        super().__init__(parent)
        self.layer_manager = layer_manager
        self._setup_ui()
        self.layer_manager.active_layer_changed.connect(self._update)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._content = QWidget()
        self._layout = QVBoxLayout(self._content)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._content)
        layout.addWidget(scroll)

        self._placeholder = QLabel("Sin datos estadísticos")
        self._placeholder.setObjectName("muted")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._placeholder)

    def _update(self, index: int):
        self._clear()
        entry = self.layer_manager.get_entry(index)
        if entry is None:
            return

        if entry.is_point_cloud:
            self._show_pc_stats(entry.layer)
        elif entry.is_raster:
            self._show_raster_stats(entry.layer)

    def _clear(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _show_pc_stats(self, pc: PointCloudData):
        title = QLabel(f"{pc.name}")
        title.setObjectName("subheading")
        self._layout.addWidget(title)

        stats = pc.height_stats()
        if stats:
            grp = QGroupBox("Altura (Z)")
            form = QFormLayout(grp)
            form.addRow("Mínimo", QLabel(f"{stats['min']:.2f} m"))
            form.addRow("Máximo", QLabel(f"{stats['max']:.2f} m"))
            form.addRow("Media", QLabel(f"{stats['mean']:.2f} m"))
            form.addRow("Mediana", QLabel(f"{stats['median']:.2f} m"))
            form.addRow("Desv. est.", QLabel(f"{stats['std']:.2f} m"))
            form.addRow("Rango", QLabel(f"{stats['max'] - stats['min']:.2f} m"))
            self._layout.addWidget(grp)

        grp_gen = QGroupBox("General")
        form_g = QFormLayout(grp_gen)
        form_g.addRow("Total puntos", QLabel(f"{pc.point_count:,}"))
        if pc.bounds:
            b = pc.bounds
            area = (b[3] - b[0]) * (b[4] - b[1])
            density = pc.point_count / area if area > 0 else 0
            form_g.addRow("Área XY", QLabel(f"{area:,.1f} m²"))
            form_g.addRow("Densidad", QLabel(f"{density:.1f} pts/m²"))
        self._layout.addWidget(grp_gen)

        self._layout.addStretch()

    def _show_raster_stats(self, rl: RasterLayer):
        title = QLabel(f"{rl.name}")
        title.setObjectName("subheading")
        self._layout.addWidget(title)

        stats = rl.statistics()
        if stats:
            grp = QGroupBox("Valores")
            form = QFormLayout(grp)
            form.addRow("Mínimo", QLabel(f"{stats['min']:.4f}"))
            form.addRow("Máximo", QLabel(f"{stats['max']:.4f}"))
            form.addRow("Media", QLabel(f"{stats['mean']:.4f}"))
            form.addRow("Mediana", QLabel(f"{stats['median']:.4f}"))
            form.addRow("Desv. est.", QLabel(f"{stats['std']:.4f}"))
            self._layout.addWidget(grp)

        grp_gen = QGroupBox("General")
        form_g = QFormLayout(grp_gen)
        form_g.addRow("Tamaño", QLabel(f"{rl.width} × {rl.height} px"))
        if rl.resolution:
            form_g.addRow("Resolución", QLabel(f"{rl.resolution[0]:.3f} m"))
        if rl.bounds:
            b = rl.bounds
            area = (b[2] - b[0]) * (b[3] - b[1])
            form_g.addRow("Área", QLabel(f"{area:,.1f} m²"))
        self._layout.addWidget(grp_gen)

        self._layout.addStretch()
