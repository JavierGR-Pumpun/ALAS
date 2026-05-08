"""
ALAS — Export Dialog
Export dialog with format selection and options.
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
from app.log import log
from app.ui.widgets import LoadingOverlay
from app.processing.workers import ProcessingWorker

logger = get_logger("ui.export_dialog")


class ExportDialog(QDialog):
    """Export dialog."""

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
        grp_layer = QGroupBox(tr("export.layer_to_export"))
        form_l = QFormLayout(grp_layer)

        self._layer_combo = QComboBox()
        for i, entry in enumerate(self.layer_manager.get_all_entries()):
            label = f"{'☁' if entry.is_point_cloud else '▦'} {entry.name}"
            self._layer_combo.addItem(label, i)

        if preset_layer is not None:
            self._layer_combo.setCurrentIndex(preset_layer)

        self._layer_combo.currentIndexChanged.connect(self._on_layer_changed)
        form_l.addRow(tr("export.layer"), self._layer_combo)
        layout.addWidget(grp_layer)

        # Format selection
        grp_format = QGroupBox(tr("export.format"))
        form_f = QFormLayout(grp_format)

        self._format_combo = QComboBox()
        form_f.addRow(tr("export.format"), self._format_combo)
        layout.addWidget(grp_format)

        # Options
        grp_opts = QGroupBox(tr("export.options"))
        form_o = QFormLayout(grp_opts)

        self._compress = QCheckBox(tr("export.compression"))
        self._compress.setChecked(True)
        form_o.addRow("", self._compress)

        layout.addWidget(grp_opts)

        # PDF report
        grp_pdf = QGroupBox(tr("export.pdf_report"))
        form_pdf = QFormLayout(grp_pdf)
        self._gen_pdf = QCheckBox(tr("export.generate_pdf"))
        form_pdf.addRow("", self._gen_pdf)
        self._pdf_title = QLineEdit(tr("export.default_title"))
        form_pdf.addRow(tr("export.title"), self._pdf_title)
        layout.addWidget(grp_pdf)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton(tr("dialog.cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_export = QPushButton(tr("export.button"))
        btn_export.setObjectName("primary")
        btn_export.clicked.connect(self._export)
        btn_layout.addWidget(btn_export)

        layout.addLayout(btn_layout)

        # Initialize formats
        self._on_layer_changed(0)

        self._loading_overlay = LoadingOverlay(self)
        self._loading_overlay.hide()

    def _on_layer_changed(self, index: int):
        self._format_combo.clear()
        layer_idx = self._layer_combo.currentData()
        if layer_idx is None:
            return

        entry = self.layer_manager.get_entry(layer_idx)
        if entry is None:
            return

        if entry.is_point_cloud:
            self._format_combo.addItem(tr("export.laz_format"), "laz")
            self._format_combo.addItem(tr("export.las_format"), "las")
        elif entry.is_raster:
            self._format_combo.addItem(tr("export.geotiff_format"), "tif")
            self._format_combo.addItem(tr("export.obj_format"), "obj")

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
            self, tr("export.dialog_title"), f"{entry.name}{ext}",
            f"{tr('export.files_filter')} (*{ext})"
        )
        if not path:
            return

        gen_pdf = self._gen_pdf.isChecked()
        pdf_title = self._pdf_title.text()
        
        def _compute():
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
            if gen_pdf:
                pdf_path = Path(path).with_suffix(".pdf")
                stats = {}
                if entry.is_point_cloud:
                    stats = entry.layer.height_stats()
                elif entry.is_raster:
                    stats = entry.layer.statistics()

                metadata = {
                    tr("export.metadata_layer"): entry.name,
                    tr("export.metadata_format"): fmt.upper(),
                    tr("export.metadata_file"): str(path),
                }
                if entry.is_point_cloud:
                    metadata[tr("export.metadata_points")] = f"{entry.layer.point_count:,}"
                    if entry.layer.crs_epsg:
                        metadata[tr("export.metadata_crs")] = f"EPSG:{entry.layer.crs_epsg}"
                elif entry.is_raster:
                    metadata[tr("export.metadata_size")] = f"{entry.layer.width}×{entry.layer.height}"
                    if entry.layer.crs_epsg:
                        metadata[tr("export.metadata_crs")] = f"EPSG:{entry.layer.crs_epsg}"

                export_pdf_report(
                    pdf_title, metadata, stats, [], str(pdf_path)
                )
            return path
        
        self._loading_overlay.show_loading()
        
        worker = ProcessingWorker(_compute)
        worker.signals.result.connect(self._on_export_result)
        worker.signals.error.connect(self._on_export_error)
        worker.signals.finished.connect(lambda: self._loading_overlay.hide_loading())
        
        from PyQt6.QtCore import QThreadPool
        QThreadPool.globalInstance().start(worker)
    
    def _on_export_result(self, path):
        QMessageBox.information(self, tr("export.success"),
                                 f"{tr('export.exported_message')} {path}")
        self.accept()
    
    def _on_export_error(self, error_msg: str):
        QMessageBox.critical(self, tr("error.export_failed"), error_msg)
