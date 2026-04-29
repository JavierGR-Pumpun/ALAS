"""
ALAS — Export Dialog
Diálogo de exportación con selección de formato y opciones.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QComboBox, QPushButton, QLabel, QFileDialog, QMessageBox,
    QCheckBox, QLineEdit
)
from PyQt6.QtCore import Qt
from pathlib import Path

from app.core.layer_manager import LayerManager
from app.core.point_cloud import PointCloudData
from app.core.raster_layer import RasterLayer
from app.processing.exporters import (
    export_point_cloud, export_geotiff, export_mesh_obj,
    raster_to_mesh, export_pdf_report
)
from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.export_dialog")


class ExportDialog(QDialog):
    """Diálogo de exportación."""

    def __init__(self, layer_manager: LayerManager, parent=None,
                 preset_layer: int = None):
        super().__init__(parent)
        self.layer_manager = layer_manager
        self.setWindowTitle(tr("action.export"))
        self.setMinimumSize(450, 400)
        self._setup_ui(preset_layer)

    def _setup_ui(self, preset_layer):
        layout = QVBoxLayout(self)

        # Layer selection
        grp_layer = QGroupBox("Capa a exportar")
        form_l = QFormLayout(grp_layer)

        self._layer_combo = QComboBox()
        for i, entry in enumerate(self.layer_manager.get_all_entries()):
            label = f"{'☁' if entry.is_point_cloud else '▦'} {entry.name}"
            self._layer_combo.addItem(label, i)

        if preset_layer is not None:
            self._layer_combo.setCurrentIndex(preset_layer)

        self._layer_combo.currentIndexChanged.connect(self._on_layer_changed)
        form_l.addRow("Capa", self._layer_combo)
        layout.addWidget(grp_layer)

        # Format selection
        grp_format = QGroupBox("Formato de exportación")
        form_f = QFormLayout(grp_format)

        self._format_combo = QComboBox()
        form_f.addRow("Formato", self._format_combo)
        layout.addWidget(grp_format)

        # Options
        grp_opts = QGroupBox("Opciones")
        form_o = QFormLayout(grp_opts)

        self._compress = QCheckBox("Compresión")
        self._compress.setChecked(True)
        form_o.addRow("", self._compress)

        layout.addWidget(grp_opts)

        # PDF report
        grp_pdf = QGroupBox("Reporte PDF")
        form_pdf = QFormLayout(grp_pdf)
        self._gen_pdf = QCheckBox("Generar reporte PDF con estadísticas")
        form_pdf.addRow("", self._gen_pdf)
        self._pdf_title = QLineEdit("Reporte ALAS")
        form_pdf.addRow("Título", self._pdf_title)
        layout.addWidget(grp_pdf)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton(tr("dialog.cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_export = QPushButton("💾 Exportar")
        btn_export.setObjectName("primary")
        btn_export.clicked.connect(self._export)
        btn_layout.addWidget(btn_export)

        layout.addLayout(btn_layout)

        # Initialize formats
        self._on_layer_changed(0)

    def _on_layer_changed(self, index: int):
        self._format_combo.clear()
        layer_idx = self._layer_combo.currentData()
        if layer_idx is None:
            return

        entry = self.layer_manager.get_entry(layer_idx)
        if entry is None:
            return

        if entry.is_point_cloud:
            self._format_combo.addItem("LAZ (comprimido)", "laz")
            self._format_combo.addItem("LAS (sin comprimir)", "las")
        elif entry.is_raster:
            self._format_combo.addItem("GeoTIFF (.tif)", "tif")
            self._format_combo.addItem("OBJ 3D (.obj)", "obj")

    def _export(self):
        layer_idx = self._layer_combo.currentData()
        if layer_idx is None:
            return

        entry = self.layer_manager.get_entry(layer_idx)
        if entry is None:
            return

        fmt = self._format_combo.currentData()
        ext = f".{fmt}"

        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar", f"{entry.name}{ext}",
            f"Archivos (*{ext})"
        )
        if not path:
            return

        try:
            if entry.is_point_cloud:
                export_point_cloud(entry.layer, path,
                                    compress=(fmt == "laz"))
            elif entry.is_raster:
                if fmt == "tif":
                    export_geotiff(entry.layer, path)
                elif fmt == "obj":
                    vertices, faces = raster_to_mesh(entry.layer)
                    export_mesh_obj(vertices, faces, path)

            # PDF report
            if self._gen_pdf.isChecked():
                pdf_path = Path(path).with_suffix(".pdf")
                stats = {}
                if entry.is_point_cloud:
                    stats = entry.layer.height_stats()
                elif entry.is_raster:
                    stats = entry.layer.statistics()

                metadata = {
                    "Capa": entry.name,
                    "Formato": fmt.upper(),
                    "Archivo exportado": str(path),
                }
                if entry.is_point_cloud:
                    metadata["Puntos"] = f"{entry.layer.point_count:,}"
                    if entry.layer.crs_epsg:
                        metadata["CRS"] = f"EPSG:{entry.layer.crs_epsg}"
                elif entry.is_raster:
                    metadata["Tamaño"] = f"{entry.layer.width}×{entry.layer.height}"
                    if entry.layer.crs_epsg:
                        metadata["CRS"] = f"EPSG:{entry.layer.crs_epsg}"

                export_pdf_report(
                    self._pdf_title.text(), metadata, stats, [], str(pdf_path)
                )

            QMessageBox.information(self, tr("success.exported"),
                                     f"Exportado: {path}")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, tr("error.export_failed"), str(e))
