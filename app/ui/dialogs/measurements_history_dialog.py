"""
ALAS — Measurements History Dialog
Modal que muestra el historial completo de medidas realizadas en la sesion.
"""

from __future__ import annotations
import datetime
from typing import List, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSplitter, QTextEdit, QFrame, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

from app.logger import get_logger

logger = get_logger("ui.measurements_history")

# Tipo -> (etiqueta, color texto fila)
TYPE_META: Dict[str, tuple] = {
    "area":      ("Area",      "#c0c0c0"),
    "distancia": ("Distancia", "#c0c0c0"),
    "volumen":   ("Volumen",   "#c0c0c0"),
    "perfil":    ("Perfil",    "#c0c0c0"),
}


def _fmt(value: float, unit: str = "", decimals: int = 2) -> str:
    return f"{value:,.{decimals}f} {unit}".strip()


class MeasurementEntry:
    """Encapsula una medida almacenada."""

    _counter = 0

    def __init__(self, mtype: str, data: Dict[str, Any]):
        MeasurementEntry._counter += 1
        self.id    = MeasurementEntry._counter
        self.mtype = mtype
        self.data  = data
        self.ts    = datetime.datetime.now()

    @property
    def timestamp_str(self) -> str:
        return self.ts.strftime("%H:%M:%S")

    @property
    def type_label(self) -> str:
        label, _ = TYPE_META.get(self.mtype, ("Medida", "#c0c0c0"))
        return label

    @property
    def summary(self) -> str:
        d = self.data
        if self.mtype == "area":
            return _fmt(d.get("planimetric_area_m2", 0), "m2")
        if self.mtype == "distancia":
            return _fmt(d.get("distance_3d", 0), "m")
        if self.mtype == "volumen":
            return _fmt(d.get("net_volume_m3", 0), "m3")
        if self.mtype == "perfil":
            return f"{_fmt(d.get('length_m', 0), 'm')}  dZ={_fmt(d.get('dz_m', 0), 'm')}"
        return "-"

    def detail_text(self) -> str:
        sep = "-" * 44
        lines = [
            sep,
            f"  #{self.id}  {self.type_label}   {self.ts.strftime('%d/%m/%Y %H:%M:%S')}",
            sep,
        ]
        d = self.data
        if self.mtype == "area":
            lines += [
                f"  Area planimétrica : {_fmt(d.get('planimetric_area_m2', 0), 'm2')}",
                f"                      {_fmt(d.get('planimetric_area_m2', 0) / 10000, 'ha', 4)}",
                f"  Area superficial  : {_fmt(d.get('surface_area_m2', 0), 'm2') if d.get('used_raster') else '- (sin MDT)'}",
                f"  Perimetro 2D      : {_fmt(d.get('perimeter_m', 0), 'm')}",
                f"  Num. vertices     : {d.get('num_vertices', '-')}",
                f"  Fuente            : {'MDT' if d.get('used_raster') else 'Shoelace (sin MDT)'}",
            ]
            verts = d.get('vertices', [])
            if verts:
                lines.append("  Vértices:")
                for i, v in enumerate(verts[:10], 1):
                    lines.append(f"    {i:2}. ({v.get('x', 0):.3f}, {v.get('y', 0):.3f}, {v.get('z', 0):.3f})")
                if len(verts) > 10:
                    lines.append(f"    ... y {len(verts) - 10} más")
        elif self.mtype == "distancia":
            lines += [
                f"  Distancia 3D  : {_fmt(d.get('distance_3d', 0), 'm')}",
                f"  Distancia 2D  : {_fmt(d.get('distance_2d', 0), 'm')}",
                f"  Desnivel (dZ) : {_fmt(d.get('dz', 0), 'm')}",
                f"  Pendiente     : {_fmt(d.get('slope_degrees', 0), 'deg')} "
                f"({_fmt(d.get('slope_percent', 0), '%')})",
                f"  Punto A       : ({d.get('ax', 0):.3f}, {d.get('ay', 0):.3f}, {d.get('az', 0):.3f})",
                f"  Punto B       : ({d.get('bx', 0):.3f}, {d.get('by', 0):.3f}, {d.get('bz', 0):.3f})",
            ]
        elif self.mtype == "volumen":
            lines += [
                f"  Corte    : {_fmt(d.get('cut_volume_m3', 0), 'm3')}",
                f"  Relleno  : {_fmt(d.get('fill_volume_m3', 0), 'm3')}",
                f"  Neto     : {_fmt(d.get('net_volume_m3', 0), 'm3')}",
                f"  Area base: {_fmt(d.get('area_m2', 0), 'm2')}",
                f"  Z ref.   : {_fmt(d.get('reference_z', 0), 'm')}",
                f"  Num. vertices : {d.get('num_vertices', '-')}",
            ]
            verts = d.get('vertices', [])
            if verts:
                lines.append("  Vértices:")
                for i, v in enumerate(verts[:10], 1):
                    lines.append(f"    {i:2}. ({v.get('x', 0):.3f}, {v.get('y', 0):.3f}, {v.get('z', 0):.3f})")
                if len(verts) > 10:
                    lines.append(f"    ... y {len(verts) - 10} más")
        elif self.mtype == "perfil":
            lines += [
                f"  Longitud : {_fmt(d.get('length_m', 0), 'm')}",
                f"  Z min    : {_fmt(d.get('z_min', 0), 'm')}",
                f"  Z max    : {_fmt(d.get('z_max', 0), 'm')}",
                f"  dZ       : {_fmt(d.get('dz_m', 0), 'm')}",
            ]
        return "\n".join(lines)


class MeasurementsHistoryDialog(QDialog):
    """
    Modal no bloqueante con el historial de medidas de la sesion.
    Se oculta al cerrar, nunca se destruye.
    """

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Historial de Medidas")
        self.setMinimumSize(740, 500)
        self.resize(880, 560)
        self._entries: List[MeasurementEntry] = []
        self._setup_ui()
        self._apply_style()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(12)

        # Header row
        hdr = QHBoxLayout()
        hdr.setSpacing(0)

        title = QLabel("Historial de Medidas")
        title.setObjectName("hist_title")
        hdr.addWidget(title)
        hdr.addStretch()

        self._count_label = QLabel("0 medidas")
        self._count_label.setObjectName("count_label")
        hdr.addWidget(self._count_label)
        root.addLayout(hdr)

        # Divider
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("divider")
        root.addWidget(sep)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # -- Left: table --
        left_container = QFrame()
        left_container.setObjectName("panel")
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        col_header = QLabel("MEDIDAS")
        col_header.setObjectName("section_label")
        left_layout.addWidget(col_header)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["#", "Hora", "Tipo", "Resultado"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(False)
        self._table.selectionModel().selectionChanged.connect(self._on_selection)
        left_layout.addWidget(self._table)

        self._empty_label = QLabel(
            "Sin medidas en esta sesion.\n\n"
            "Usa las herramientas del menu\nHerramientas para comenzar."
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setObjectName("empty_label")
        left_layout.addWidget(self._empty_label)

        splitter.addWidget(left_container)

        # -- Right: detail --
        right_container = QFrame()
        right_container.setObjectName("panel")
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        detail_header = QLabel("DETALLE")
        detail_header.setObjectName("section_label")
        right_layout.addWidget(detail_header)

        self._detail_text = QTextEdit()
        self._detail_text.setReadOnly(True)
        self._detail_text.setObjectName("detail_text")
        self._detail_text.setPlaceholderText("Selecciona una fila para ver el detalle.")
        right_layout.addWidget(self._detail_text)

        splitter.addWidget(right_container)
        splitter.setSizes([480, 360])

        root.addWidget(splitter, 1)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_copy = QPushButton("Copiar detalle")
        self._btn_copy.setEnabled(False)
        self._btn_copy.clicked.connect(self._copy_detail)
        btn_row.addWidget(self._btn_copy)

        self._btn_copy_all = QPushButton("Copiar todo")
        self._btn_copy_all.clicked.connect(self._copy_all)
        btn_row.addWidget(self._btn_copy_all)

        btn_row.addStretch()

        self._btn_clear = QPushButton("Limpiar historial")
        self._btn_clear.setObjectName("btn_danger")
        self._btn_clear.clicked.connect(self._clear_history)
        btn_row.addWidget(self._btn_clear)

        btn_close = QPushButton("Cerrar")
        btn_close.setObjectName("btn_close")
        btn_close.clicked.connect(self.hide)
        btn_row.addWidget(btn_close)

        root.addLayout(btn_row)

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background: #0a0a0a;
                color: #d0d0d0;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }

            QLabel#hist_title {
                font-size: 15px;
                font-weight: 600;
                color: #ffffff;
                letter-spacing: 0.3px;
            }

            QLabel#count_label {
                color: #555555;
                font-size: 11px;
                padding-top: 3px;
            }

            QFrame#divider {
                color: #1e1e1e;
                max-height: 1px;
            }

            QFrame#panel {
                background: #0e0e0e;
                border: 1px solid #1a1a1a;
                border-radius: 4px;
            }

            QLabel#section_label {
                color: #444444;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 8px 10px 6px 10px;
                border-bottom: 1px solid #1a1a1a;
            }

            QLabel#empty_label {
                color: #333333;
                font-size: 12px;
                line-height: 1.8;
                padding: 40px 20px;
            }

            QTableWidget {
                background: transparent;
                border: none;
                color: #b0b0b0;
                font-size: 12px;
                gridline-color: transparent;
                outline: none;
            }

            QTableWidget::item {
                padding: 7px 10px;
                border-bottom: 1px solid #141414;
                color: #b0b0b0;
            }

            QTableWidget::item:selected {
                background: #1a1a1a;
                color: #ffffff;
            }

            QHeaderView::section {
                background: #0e0e0e;
                color: #3a3a3a;
                border: none;
                border-bottom: 1px solid #1a1a1a;
                padding: 6px 10px;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.8px;
            }

            QScrollBar:vertical {
                background: #0a0a0a;
                width: 5px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: #252525;
                border-radius: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }

            QScrollBar:horizontal {
                background: #0a0a0a;
                height: 5px;
                border-radius: 2px;
            }
            QScrollBar::handle:horizontal {
                background: #252525;
                border-radius: 2px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }

            QTextEdit#detail_text {
                background: #080808;
                color: #909090;
                border: none;
                font-family: 'Consolas', 'Cascadia Code', monospace;
                font-size: 12px;
                padding: 10px;
                line-height: 1.6;
                selection-background-color: #202020;
            }

            QSplitter::handle {
                background: #1a1a1a;
            }

            QPushButton {
                background: #141414;
                color: #a0a0a0;
                border: 1px solid #1e1e1e;
                border-radius: 3px;
                padding: 6px 14px;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #1c1c1c;
                color: #d0d0d0;
                border-color: #2a2a2a;
            }
            QPushButton:pressed {
                background: #0e0e0e;
            }
            QPushButton:disabled {
                color: #2a2a2a;
                border-color: #141414;
            }

            QPushButton#btn_danger {
                background: #141414;
                color: #664444;
                border-color: #1e1e1e;
            }
            QPushButton#btn_danger:hover {
                background: #1c1010;
                color: #cc6666;
                border-color: #2a1414;
            }

            QPushButton#btn_close {
                background: #141414;
                color: #606060;
                border-color: #1e1e1e;
            }
            QPushButton#btn_close:hover {
                background: #1c1c1c;
                color: #ffffff;
            }
        """)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_measurement(self, mtype: str, data: Dict[str, Any]) -> MeasurementEntry:
        entry = MeasurementEntry(mtype, data)
        self._entries.append(entry)
        self._add_row(entry)
        self._update_counter()
        logger.debug(f"Medida #{entry.id} ({mtype}) guardada en historial")
        return entry

    def show_and_raise(self):
        self.show()
        self.raise_()
        self.activateWindow()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _add_row(self, entry: MeasurementEntry):
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setRowHeight(row, 34)

        _, fg_hex = TYPE_META.get(entry.mtype, ("Medida", "#c0c0c0"))
        fg = QColor(fg_hex)
        bg = QColor("#0e0e0e")

        def cell(text: str, align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter) -> QTableWidgetItem:
            item = QTableWidgetItem(text)
            item.setBackground(bg)
            item.setForeground(fg)
            item.setTextAlignment(align)
            return item

        center = Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter

        self._table.setItem(row, 0, cell(str(entry.id), center))
        self._table.setItem(row, 1, cell(entry.timestamp_str, center))
        self._table.setItem(row, 2, cell(entry.type_label))
        self._table.setItem(row, 3, cell(entry.summary))

        self._empty_label.setVisible(False)
        self._table.setVisible(True)
        self._table.scrollToBottom()

    def _update_counter(self):
        n = len(self._entries)
        self._count_label.setText(f"{n} medida{'s' if n != 1 else ''}")

    def _on_selection(self):
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            self._detail_text.clear()
            self._btn_copy.setEnabled(False)
            return
        row = rows[0].row()
        if row < len(self._entries):
            self._detail_text.setPlainText(self._entries[row].detail_text())
            self._btn_copy.setEnabled(True)

    def _copy_detail(self):
        text = self._detail_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _copy_all(self):
        if not self._entries:
            return
        all_text = "\n\n".join(e.detail_text() for e in self._entries)
        QApplication.clipboard().setText(all_text)
        QMessageBox.information(
            self, "Copiado",
            f"Se han copiado {len(self._entries)} medidas al portapapeles."
        )

    def _clear_history(self):
        if not self._entries:
            return
        reply = QMessageBox.question(
            self, "Limpiar historial",
            f"Eliminar las {len(self._entries)} medidas del historial?\n"
            "Esta accion no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Yes:
            MeasurementEntry._counter = 0
            self._entries.clear()
            self._table.setRowCount(0)
            self._detail_text.clear()
            self._btn_copy.setEnabled(False)
            self._empty_label.setVisible(True)
            self._table.setVisible(False)
            self._update_counter()

    def closeEvent(self, event):
        event.ignore()
        self.hide()