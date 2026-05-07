"""
ALAS — Area Tool
Modal flotante para la herramienta de medición de área.
Muestra vértices en tiempo real y resultados inline.
"""

import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFormLayout, QGroupBox, QListWidget, QListWidgetItem,
    QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.area_tool")


class AreaToolDialog(QDialog):
    """
    Modal flotante de la herramienta de área.
    - Se mantiene visible mientras el usuario hace clic en el viewport.
    - Muestra la lista de vértices en tiempo real.
    - Al pulsar 'Calcular' o Enter con ≥3 vértices, muestra los resultados inline.
    - Emite calculate_requested cuando el usuario quiere calcular.
    - Emite clear_requested cuando el usuario cancela/limpia.
    """

    calculate_requested = pyqtSignal()   # El main_window ejecuta el cálculo
    clear_requested     = pyqtSignal()   # El main_window limpia el viewport
    undo_requested      = pyqtSignal(list)  # El main_window redibuja con vértices restantes

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool)  # Tool = flotante, no bloquea
        self.setWindowTitle(tr("action.area"))
        self.setMinimumWidth(320)
        self.setMaximumWidth(400)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        self._vertices: list[tuple] = []
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- Instrucciones ---
        lbl_hint = QLabel(
            "Clic izquierdo para añadir vértices al polígono.\n"
            "Pulsa <b>Calcular</b> con ≥ 3 vértices."
        )
        lbl_hint.setWordWrap(True)
        lbl_hint.setObjectName("muted")
        lbl_hint.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(lbl_hint)

        # --- Lista de vértices ---
        grp_verts = QGroupBox("Vértices")
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

        # Contador
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

        # --- Panel de resultados (oculto hasta calcular) ---
        self._results_group = QGroupBox("Resultados")
        results_form = QFormLayout(self._results_group)
        results_form.setSpacing(6)

        font_val = QFont()
        font_val.setBold(True)

        self._lbl_plan   = QLabel("—")
        self._lbl_plan.setFont(font_val)
        self._lbl_plan_ha = QLabel("—")
        self._lbl_plan_ha.setFont(font_val)
        self._lbl_surf   = QLabel("—")
        self._lbl_surf.setFont(font_val)
        self._lbl_perim  = QLabel("—")
        self._lbl_perim.setFont(font_val)
        self._lbl_verts  = QLabel("—")

        results_form.addRow("Área planimétrica:",  self._lbl_plan)
        results_form.addRow("",                    self._lbl_plan_ha)
        results_form.addRow("Área superficial:",   self._lbl_surf)
        results_form.addRow("Perímetro 2D:",       self._lbl_perim)
        results_form.addRow("Vértices:",           self._lbl_verts)

        self._results_group.setVisible(False)
        layout.addWidget(self._results_group)

        # --- Aviso de fuente de datos ---
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
    # Public API — llamado desde main_window
    # ------------------------------------------------------------------

    def add_vertex(self, x: float, y: float, z: float):
        """Añade un vértice y actualiza la UI."""
        self._vertices.append((x, y, z))
        n = len(self._vertices)

        item = QListWidgetItem(f"  {n:>2}.  X={x:.2f}   Y={y:.2f}   Z={z:.2f}")
        item.setForeground(QColor("#a855f7"))
        self._vertex_list.addItem(item)
        self._vertex_list.scrollToBottom()

        self._count_label.setText(f"{n} vértice{'s' if n != 1 else ''}")
        self._btn_calc.setEnabled(n >= 3)

        # Resetear resultados si añaden más vértices tras calcular
        if self._results_group.isVisible():
            self._results_group.setVisible(False)
            self._lbl_source.setText("")

        logger.debug(f"Vértice {n} añadido: ({x:.2f}, {y:.2f}, {z:.2f})")

    def get_vertices(self) -> list[tuple]:
        """Devuelve la lista de vértices [(x, y, z), ...]."""
        return list(self._vertices)

    def show_results(self, plan_m2: float, surf_m2: float,
                     perimeter_m: float, used_raster: bool):
        """Muestra los resultados en el panel inline."""
        self._lbl_plan.setText(f"{plan_m2:,.2f} m²")
        self._lbl_plan_ha.setText(f"({plan_m2 / 10000:,.4f} ha)")
        self._lbl_surf.setText(
            f"{surf_m2:,.2f} m²" if used_raster else "— (sin MDT)"
        )
        self._lbl_perim.setText(f"{perimeter_m:,.2f} m")
        self._lbl_verts.setText(str(len(self._vertices)))

        if used_raster:
            self._lbl_source.setText("Área superficial calculada usando el MDT activo.")
        else:
            self._lbl_source.setText(
                "No hay MDT cargado. Sólo área planimétrica (Shoelace)."
            )

        self._results_group.setVisible(True)
        self.adjustSize()

    def reset(self):
        """Limpia vértices y resultados."""
        self._vertices.clear()
        self._vertex_list.clear()
        self._count_label.setText("0 vértices")
        self._btn_calc.setEnabled(False)
        self._results_group.setVisible(False)
        self._lbl_source.setText("")
        self._lbl_plan.setText("—")
        self._lbl_plan_ha.setText("—")
        self._lbl_surf.setText("—")
        self._lbl_perim.setText("—")
        self._lbl_verts.setText("—")
        self.adjustSize()

    # ------------------------------------------------------------------
    # Slots internos
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
        self.undo_requested.emit(list(self._vertices))

    def _on_clear(self):
        self.reset()
        self.clear_requested.emit()

    def _on_close(self):
        self.hide()
        self.reset()
        self.clear_requested.emit()

    # Evitar que cerrar la ventana destruya el diálogo
    def closeEvent(self, event):
        event.ignore()   # No destruir, solo ocultar
        self._on_close()

    # Enter cuando el foco está en el diálogo
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._btn_calc.isEnabled():
                self._on_calculate_clicked()
        elif event.key() == Qt.Key.Key_Escape:
            self._on_close()
        else:
            super().keyPressEvent(event)
