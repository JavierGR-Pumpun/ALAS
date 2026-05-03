"""
ALAS — Volume Tool
Modal flotante para la herramienta de cálculo de volumen.
Muestra vértices en tiempo real, permite definir Z de referencia y muestra resultados inline.
"""

import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFormLayout, QGroupBox, QListWidget, QListWidgetItem,
    QSizePolicy, QFrame, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.volume_tool")


class VolumeToolDialog(QDialog):
    """
    Modal flotante de la herramienta de volumen.
    - Se mantiene visible mientras el usuario hace clic en el viewport.
    - Permite configurar la cota Z de referencia.
    - Muestra la lista de vértices en tiempo real.
    - Al pulsar 'Calcular' o Enter con >= 3 vértices, muestra los resultados inline.
    """

    calculate_requested = pyqtSignal()
    clear_requested     = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool)
        self.setWindowTitle("Cálculo de Volumen")
        self.setMinimumWidth(320)
        self.setMaximumWidth(400)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        self._vertices: list[tuple] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- Instrucciones ---
        lbl_hint = QLabel(
            "Clic izquierdo para añadir vértices al polígono de cálculo.\n"
            "Define la cota Z de referencia y pulsa <b>Calcular</b> con ≥ 3 vértices."
        )
        lbl_hint.setWordWrap(True)
        lbl_hint.setObjectName("muted")
        lbl_hint.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(lbl_hint)

        # --- Configuración ---
        grp_config = QGroupBox("Configuración")
        config_form = QFormLayout(grp_config)
        self._z_ref_spin = QDoubleSpinBox()
        self._z_ref_spin.setRange(-10000, 10000)
        self._z_ref_spin.setDecimals(2)
        self._z_ref_spin.setValue(0.0)
        self._z_ref_spin.setSuffix(" m")
        config_form.addRow("Nivel de ref. (Z):", self._z_ref_spin)
        layout.addWidget(grp_config)

        # --- Lista de vértices ---
        grp_verts = QGroupBox("Vértices del Polígono")
        verts_layout = QVBoxLayout(grp_verts)
        verts_layout.setContentsMargins(6, 6, 6, 6)

        self._vertex_list = QListWidget()
        self._vertex_list.setMaximumHeight(160)
        self._vertex_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._vertex_list.setStyleSheet(
            "QListWidget { background: #12121f; border: none; font-size: 11px; }"
            "QListWidget::item { padding: 2px 4px; color: #c0c0d0; }"
        )
        verts_layout.addWidget(self._vertex_list)

        self._count_label = QLabel("0 vértices")
        self._count_label.setObjectName("muted")
        self._count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        verts_layout.addWidget(self._count_label)

        layout.addWidget(grp_verts)

        # --- Botones de acción ---
        btn_row = QHBoxLayout()

        self._btn_calc = QPushButton("Calcular")
        self._btn_calc.setObjectName("primary")
        self._btn_calc.setEnabled(False)
        self._btn_calc.clicked.connect(self._on_calculate_clicked)
        btn_row.addWidget(self._btn_calc)

        btn_undo = QPushButton("Deshacer")
        btn_undo.clicked.connect(self._on_undo)
        btn_row.addWidget(btn_undo)

        btn_clear = QPushButton("Limpiar")
        btn_clear.clicked.connect(self._on_clear)
        btn_row.addWidget(btn_clear)

        layout.addLayout(btn_row)

        # --- Separador ---
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a3d;")
        layout.addWidget(sep)

        # --- Panel de resultados ---
        self._results_group = QGroupBox("Resultados")
        results_form = QFormLayout(self._results_group)
        results_form.setSpacing(6)

        font_val = QFont()
        font_val.setBold(True)

        self._lbl_cut = QLabel("—")
        self._lbl_cut.setFont(font_val)
        self._lbl_fill = QLabel("—")
        self._lbl_fill.setFont(font_val)
        self._lbl_net = QLabel("—")
        self._lbl_net.setFont(font_val)
        self._lbl_area = QLabel("—")

        results_form.addRow("Corte (Desmonte):", self._lbl_cut)
        results_form.addRow("Relleno (Terraplén):", self._lbl_fill)
        results_form.addRow("Volumen Neto:", self._lbl_net)
        results_form.addRow("Área base:", self._lbl_area)

        self._results_group.setVisible(False)
        layout.addWidget(self._results_group)

        self._lbl_source = QLabel("")
        self._lbl_source.setObjectName("muted")
        self._lbl_source.setWordWrap(True)
        self._lbl_source.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lbl_source)

        # --- Botón cerrar ---
        btn_close = QPushButton(tr("dialog.close"))
        btn_close.clicked.connect(self._on_close)
        layout.addWidget(btn_close)

        layout.addStretch()
        self.adjustSize()

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def add_vertex(self, x: float, y: float, z: float):
        self._vertices.append((x, y, z))
        n = len(self._vertices)

        item = QListWidgetItem(f"  {n:>2}.  X={x:.2f}   Y={y:.2f}   Z={z:.2f}")
        item.setForeground(QColor("#a855f7"))
        self._vertex_list.addItem(item)
        self._vertex_list.scrollToBottom()

        self._count_label.setText(f"{n} vértice{'s' if n != 1 else ''}")
        self._btn_calc.setEnabled(n >= 3)

        if self._results_group.isVisible():
            self._results_group.setVisible(False)
            self._lbl_source.setText("")

    def get_vertices(self) -> list[tuple]:
        return list(self._vertices)
        
    def get_reference_z(self) -> float:
        return self._z_ref_spin.value()

    def show_results(self, cut_m3: float, fill_m3: float, net_m3: float, area_m2: float):
        self._lbl_cut.setText(f"{cut_m3:,.2f} m³")
        self._lbl_fill.setText(f"{fill_m3:,.2f} m³")
        self._lbl_net.setText(f"{net_m3:,.2f} m³")
        self._lbl_area.setText(f"{area_m2:,.2f} m²")

        self._lbl_source.setText("Volumen calculado usando el MDT activo y la cota Z de referencia.")
        self._results_group.setVisible(True)
        self.adjustSize()
        
    def show_error(self, message: str):
        self._results_group.setVisible(False)
        self._lbl_source.setText(message)
        self._lbl_source.setStyleSheet("color: #ef4444;")
        self.adjustSize()

    def reset(self):
        self._vertices.clear()
        self._vertex_list.clear()
        self._count_label.setText("0 vértices")
        self._btn_calc.setEnabled(False)
        self._results_group.setVisible(False)
        self._lbl_source.setText("")
        self._lbl_source.setStyleSheet("")
        self.adjustSize()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_calculate_clicked(self):
        if len(self._vertices) >= 3:
            self.calculate_requested.emit()

    def _on_undo(self):
        if not self._vertices:
            return
        self._vertices.pop()
        self._vertex_list.takeItem(self._vertex_list.count() - 1)
        n = len(self._vertices)
        self._count_label.setText(f"{n} vértice{'s' if n != 1 else ''}")
        self._btn_calc.setEnabled(n >= 3)
        self.clear_requested.emit()

    def _on_clear(self):
        self.reset()
        self.clear_requested.emit()

    def _on_close(self):
        self.reset()
        self.clear_requested.emit()
        self.hide()

    def closeEvent(self, event):
        self._on_close()
        event.ignore()
        self.hide()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._btn_calc.isEnabled():
                self._on_calculate_clicked()
        elif event.key() == Qt.Key.Key_Escape:
            self._on_close()
        else:
            super().keyPressEvent(event)
