"""
ALAS — Properties Panel
Panel de propiedades de la capa activa (metadatos, estadísticas).
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QGroupBox, QScrollArea
)
from PyQt6.QtCore import Qt
from typing import Optional

from app.core.layer_manager import LayerManager, LayerEntry
from app.core.point_cloud import PointCloudData
from app.core.raster_layer import RasterLayer
from app.config import ASPRS_CLASSIFICATION
from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.properties_panel")


class PropertiesPanel(QWidget):
    """Panel que muestra metadatos y estadísticas de la capa activa."""

    def __init__(self, layer_manager: LayerManager, parent=None):
        super().__init__(parent)
        self.layer_manager = layer_manager
        self._setup_ui()
        self.layer_manager.active_layer_changed.connect(self._on_active_changed)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._content)
        main_layout.addWidget(scroll)

        # Placeholder
        self._placeholder = QLabel("Selecciona una capa para ver sus propiedades")
        self._placeholder.setObjectName("muted")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setWordWrap(True)
        self._content_layout.addWidget(self._placeholder)

    def _on_active_changed(self, index: int):
        entry = self.layer_manager.get_entry(index)
        self._clear_content()
        if entry is None:
            self._show_placeholder()
            return
        if entry.is_point_cloud:
            self._show_point_cloud_props(entry.layer)
        else:
            self._show_raster_props(entry.layer)

    def _clear_content(self):
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _show_placeholder(self):
        lbl = QLabel("Selecciona una capa para ver sus propiedades")
        lbl.setObjectName("muted")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        self._content_layout.addWidget(lbl)

    def _show_point_cloud_props(self, pc: PointCloudData):
        # --- Info general ---
        grp_info = QGroupBox("Información general")
        form = QFormLayout(grp_info)
        form.addRow(tr("prop.filename"), QLabel(pc.file_path or "—"))
        form.addRow(tr("prop.point_count"), QLabel(f"{pc.point_count:,}"))
        form.addRow("Formato LAS", QLabel(f"v{pc.file_version or '?'} (formato {pc.point_format or '?'})"))
        form.addRow(tr("prop.crs"), QLabel(
            f"EPSG:{pc.crs_epsg}" if pc.crs_epsg else tr("status.no_crs")
        ))
        self._content_layout.addWidget(grp_info)

        # --- Extensión ---
        bounds = pc.bounds
        if bounds:
            grp_bounds = QGroupBox(tr("prop.bounds"))
            form_b = QFormLayout(grp_bounds)
            form_b.addRow("X", QLabel(f"{bounds[0]:.2f} — {bounds[3]:.2f}"))
            form_b.addRow("Y", QLabel(f"{bounds[1]:.2f} — {bounds[4]:.2f}"))
            form_b.addRow("Z", QLabel(f"{bounds[2]:.2f} — {bounds[5]:.2f}"))
            self._content_layout.addWidget(grp_bounds)

        # --- Estadísticas de altura ---
        stats = pc.height_stats()
        if stats:
            grp_z = QGroupBox("Estadísticas Z (m)")
            form_z = QFormLayout(grp_z)
            form_z.addRow(tr("prop.min"), QLabel(f"{stats['min']:.2f}"))
            form_z.addRow(tr("prop.max"), QLabel(f"{stats['max']:.2f}"))
            form_z.addRow(tr("prop.mean"), QLabel(f"{stats['mean']:.2f}"))
            form_z.addRow("Desv. estándar", QLabel(f"{stats['std']:.2f}"))
            self._content_layout.addWidget(grp_z)

        # --- Clasificación ---
        cls_summary = pc.classification_summary()
        if cls_summary:
            grp_cls = QGroupBox("Clasificación")
            form_c = QFormLayout(grp_cls)
            total = sum(cls_summary.values())
            for code, count in sorted(cls_summary.items()):
                name = ASPRS_CLASSIFICATION.get(code, f"Clase {code}")
                pct = (count / total * 100) if total > 0 else 0
                form_c.addRow(name, QLabel(f"{count:,} ({pct:.1f}%)"))
            self._content_layout.addWidget(grp_cls)

        # --- Dimensiones disponibles ---
        grp_dims = QGroupBox("Dimensiones disponibles")
        form_d = QFormLayout(grp_dims)
        dims = pc.available_dimensions
        form_d.addRow("Campos", QLabel(", ".join(dims)))
        self._content_layout.addWidget(grp_dims)

        self._content_layout.addStretch()

    def _show_raster_props(self, rl: RasterLayer):
        # --- Info general ---
        grp_info = QGroupBox("Información general")
        form = QFormLayout(grp_info)
        form.addRow(tr("prop.filename"), QLabel(rl.file_path or "—"))
        form.addRow("Tamaño", QLabel(f"{rl.width} × {rl.height} px"))
        form.addRow(tr("prop.bands"), QLabel(str(rl.band_count)))
        form.addRow(tr("prop.resolution"), QLabel(
            f"{rl.resolution[0]:.3f} × {rl.resolution[1]:.3f} m" if rl.resolution else "—"
        ))
        form.addRow(tr("prop.crs"), QLabel(
            f"EPSG:{rl.crs_epsg}" if rl.crs_epsg else tr("status.no_crs")
        ))
        form.addRow(tr("prop.nodata"), QLabel(str(rl.nodata)))
        self._content_layout.addWidget(grp_info)

        # --- Extensión ---
        bounds = rl.bounds
        if bounds:
            grp_bounds = QGroupBox(tr("prop.bounds"))
            form_b = QFormLayout(grp_bounds)
            form_b.addRow("X", QLabel(f"{bounds[0]:.2f} — {bounds[2]:.2f}"))
            form_b.addRow("Y", QLabel(f"{bounds[1]:.2f} — {bounds[3]:.2f}"))
            self._content_layout.addWidget(grp_bounds)

        # --- Estadísticas ---
        stats = rl.statistics()
        if stats:
            grp_stats = QGroupBox(tr("panel.statistics"))
            form_s = QFormLayout(grp_stats)
            form_s.addRow(tr("prop.min"), QLabel(f"{stats['min']:.4f}"))
            form_s.addRow(tr("prop.max"), QLabel(f"{stats['max']:.4f}"))
            form_s.addRow(tr("prop.mean"), QLabel(f"{stats['mean']:.4f}"))
            form_s.addRow("Desv. estándar", QLabel(f"{stats['std']:.4f}"))
            self._content_layout.addWidget(grp_stats)

        self._content_layout.addStretch()
