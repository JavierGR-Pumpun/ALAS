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
            self._show_point_cloud_props(entry)
        else:
            self._show_raster_props(entry)

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

    def _get_file_size_str(self, file_path):
        if not file_path:
            return "—"
        import os
        if not os.path.exists(file_path):
            return "—"
        size_bytes = os.path.getsize(file_path)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def _show_point_cloud_props(self, entry: LayerEntry):
        pc = entry.layer
        # --- Cabecera ---
        header_lbl = QLabel(f"<h2>{entry.name}</h2><p style='color: #888;'>Nube de puntos</p>")
        header_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._content_layout.addWidget(header_lbl)

        # --- Info general ---
        grp_info = QGroupBox("Información general")
        form = QFormLayout(grp_info)
        form.addRow("<b>" + tr("prop.filename") + "</b>", QLabel(pc.file_path or "—"))
        form.addRow("<b>Tamaño archivo</b>", QLabel(self._get_file_size_str(pc.file_path)))
        form.addRow("<b>" + tr("prop.point_count") + "</b>", QLabel(f"{pc.point_count:,}"))
        form.addRow("<b>Formato LAS</b>", QLabel(f"v{pc.file_version or '?'} (formato {pc.point_format or '?'})"))
        
        lbl_sensor = QLabel(pc.system_identifier or "No especificado")
        lbl_sensor.setToolTip("Identificador del sensor/sistema LiDAR")
        form.addRow("<b>Sensor</b>", lbl_sensor)
        
        lbl_crs = QLabel(f"EPSG:{pc.crs_epsg}" if pc.crs_epsg else tr("status.no_crs"))
        lbl_crs.setToolTip("Sistema de Referencia de Coordenadas")
        form.addRow("<b>" + tr("prop.crs") + "</b>", lbl_crs)
        self._content_layout.addWidget(grp_info)

        # --- Extensión ---
        bounds = pc.bounds
        if bounds:
            grp_bounds = QGroupBox(tr("prop.bounds"))
            form_b = QFormLayout(grp_bounds)
            w = bounds[3] - bounds[0]
            h = bounds[4] - bounds[1]
            form_b.addRow("<b>X</b>", QLabel(f"{bounds[0]:.2f} m — {bounds[3]:.2f} m (Ancho: {w:.2f} m)"))
            form_b.addRow("<b>Y</b>", QLabel(f"{bounds[1]:.2f} m — {bounds[4]:.2f} m (Alto: {h:.2f} m)"))
            form_b.addRow("<b>Z</b>", QLabel(f"{bounds[2]:.2f} m — {bounds[5]:.2f} m"))
            self._content_layout.addWidget(grp_bounds)

        # --- Estadísticas de altura ---
        stats = pc.height_stats()
        if stats:
            grp_z = QGroupBox("Estadísticas Z")
            form_z = QFormLayout(grp_z)
            form_z.addRow("<b>" + tr("prop.min") + "</b>", QLabel(f"{stats['min']:.2f} m"))
            form_z.addRow("<b>" + tr("prop.max") + "</b>", QLabel(f"{stats['max']:.2f} m"))
            form_z.addRow("<b>" + tr("prop.mean") + "</b>", QLabel(f"{stats['mean']:.2f} m"))
            form_z.addRow("<b>Desv. estándar</b>", QLabel(f"{stats['std']:.2f} m"))
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
                form_c.addRow(f"<b>{name}</b>", QLabel(f"{count:,} ({pct:.1f}%)"))
            self._content_layout.addWidget(grp_cls)

        # --- Dimensiones disponibles ---
        grp_dims = QGroupBox("Dimensiones disponibles")
        form_d = QFormLayout(grp_dims)
        dims = pc.available_dimensions
        lbl_dims = QLabel(", ".join(dims))
        lbl_dims.setWordWrap(True)
        form_d.addRow("<b>Campos</b>", lbl_dims)
        self._content_layout.addWidget(grp_dims)

        self._content_layout.addStretch()

    def _show_raster_props(self, entry: LayerEntry):
        rl = entry.layer
        # --- Cabecera ---
        header_lbl = QLabel(f"<h2>{entry.name}</h2><p style='color: #888;'>Modelo Raster</p>")
        header_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._content_layout.addWidget(header_lbl)

        # --- Info general ---
        grp_info = QGroupBox("Información general")
        form = QFormLayout(grp_info)
        form.addRow("<b>" + tr("prop.filename") + "</b>", QLabel(rl.file_path or "—"))
        form.addRow("<b>Tamaño archivo</b>", QLabel(self._get_file_size_str(rl.file_path)))
        form.addRow("<b>Tamaño</b>", QLabel(f"{rl.width} × {rl.height} px"))
        form.addRow("<b>" + tr("prop.bands") + "</b>", QLabel(str(rl.band_count)))
        form.addRow("<b>" + tr("prop.resolution") + "</b>", QLabel(
            f"{rl.resolution[0]:.3f} × {rl.resolution[1]:.3f} m" if rl.resolution else "—"
        ))
        lbl_crs = QLabel(f"EPSG:{rl.crs_epsg}" if rl.crs_epsg else tr("status.no_crs"))
        lbl_crs.setToolTip("Sistema de Referencia de Coordenadas")
        form.addRow("<b>" + tr("prop.crs") + "</b>", lbl_crs)
        lbl_nodata = QLabel(str(rl.nodata))
        lbl_nodata.setToolTip("Valor usado para representar píxeles sin información")
        form.addRow("<b>" + tr("prop.nodata") + "</b>", lbl_nodata)
        self._content_layout.addWidget(grp_info)

        # --- Extensión ---
        bounds = rl.bounds
        if bounds:
            grp_bounds = QGroupBox(tr("prop.bounds"))
            form_b = QFormLayout(grp_bounds)
            w = bounds[2] - bounds[0]
            h = bounds[3] - bounds[1]
            form_b.addRow("<b>X</b>", QLabel(f"{bounds[0]:.2f} m — {bounds[2]:.2f} m (Ancho: {w:.2f} m)"))
            form_b.addRow("<b>Y</b>", QLabel(f"{bounds[1]:.2f} m — {bounds[3]:.2f} m (Alto: {h:.2f} m)"))
            self._content_layout.addWidget(grp_bounds)

        # --- Estadísticas ---
        stats = rl.statistics()
        if stats:
            grp_stats = QGroupBox(tr("panel.statistics"))
            form_s = QFormLayout(grp_stats)
            form_s.addRow("<b>" + tr("prop.min") + "</b>", QLabel(f"{stats['min']:.2f} m"))
            form_s.addRow("<b>" + tr("prop.max") + "</b>", QLabel(f"{stats['max']:.2f} m"))
            form_s.addRow("<b>" + tr("prop.mean") + "</b>", QLabel(f"{stats['mean']:.2f} m"))
            form_s.addRow("<b>Desv. estándar</b>", QLabel(f"{stats['std']:.2f} m"))
            self._content_layout.addWidget(grp_stats)

        self._content_layout.addStretch()
