"""
ALAS — Distance Tool
Modal flotante para la herramienta de medición de distancia.
Muestra los puntos A y B en tiempo real y resultados inline.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFormLayout, QGroupBox, QListWidget, QListWidgetItem,
    QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.distance_tool")


class DistanceToolDialog(QDialog):
    """
    Modal flotante de la herramienta de distancia.
    - Se mantiene visible mientras el usuario hace clic en el viewport.
    - Muestra los puntos A y B en tiempo real.
    - Al seleccionar el punto B, muestra los resultados inline.
    - Emite calculate_requested cuando se tienen dos puntos.
    - Emite clear_requested cuando el usuario cancela/limpia.
    """

    calculate_requested = pyqtSignal()   # El main_window ejecuta el cálculo
    clear_requested     = pyqtSignal()   # El main_window limpia el viewport

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool)  # Tool = flotante, no bloquea
        self.setWindowTitle(tr("action.distance"))
        self.setMinimumWidth(320)
        self.setMaximumWidth(400)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        self._points: list[tuple] = []
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- Instrucciones ---
        lbl_hint = QLabel(
            "Clic izquierdo para seleccionar el punto A, luego el punto B.\n"
            "Los resultados se mostrarán automáticamente."
        )
        lbl_hint.setWordWrap(True)
        lbl_hint.setObjectName("muted")
        lbl_hint.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(lbl_hint)

        # --- Lista de puntos ---
        grp_points = QGroupBox("Puntos")
        points_layout = QVBoxLayout(grp_points)
        points_layout.setContentsMargins(6, 6, 6, 6)

        self._point_list = QListWidget()
        self._point_list.setMaximumHeight(80)
        self._point_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._point_list.setStyleSheet(
            "QListWidget { background: #12121f; border: none; font-size: 11px; }"
            "QListWidget::item { padding: 2px 4px; color: #c0c0d0; }"
        )
        points_layout.addWidget(self._point_list)

        layout.addWidget(grp_points)

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

        self._lbl_dist_3d = QLabel("—")
        self._lbl_dist_3d.setFont(font_val)
        self._lbl_dist_2d = QLabel("—")
        self._lbl_dist_2d.setFont(font_val)
        self._lbl_dz = QLabel("—")
        self._lbl_dz.setFont(font_val)
        self._lbl_slope = QLabel("—")
        self._lbl_slope.setFont(font_val)

        results_form.addRow("Distancia 3D:", self._lbl_dist_3d)
        results_form.addRow("Distancia 2D:", self._lbl_dist_2d)
        results_form.addRow("Diferencia Z:", self._lbl_dz)
        results_form.addRow("Pendiente:", self._lbl_slope)

        self._results_group.setVisible(False)
        layout.addWidget(self._results_group)

        # --- Botones de acción ---
        btn_row = QHBoxLayout()

        btn_clear = QPushButton("Limpiar")
        btn_clear.clicked.connect(self._on_clear)
        btn_row.addWidget(btn_clear)

        layout.addLayout(btn_row)

        # --- Botón cerrar ---
        btn_close = QPushButton(tr("dialog.close"))
        btn_close.clicked.connect(self._on_close)
        layout.addWidget(btn_close)

        layout.addStretch()
        self.adjustSize()

    # ------------------------------------------------------------------
    # Public API — llamado desde main_window
    # ------------------------------------------------------------------

    def add_point(self, x: float, y: float, z: float, label: str):
        """Añade un punto (A o B) y actualiza la UI."""
        if len(self._points) >= 2:
            return  # Solo dos puntos
        self._points.append((x, y, z))

        item = QListWidgetItem(f"{label}: X={x:.2f}   Y={y:.2f}   Z={z:.2f}")
        item.setForeground(QColor("#a855f7"))
        self._point_list.addItem(item)

        if len(self._points) == 2:
            self.calculate_requested.emit()

        logger.debug(f"Punto {label} añadido: ({x:.2f}, {y:.2f}, {z:.2f})")

    def show_results(self, dist_3d: float, dist_2d: float, dz: float, slope_deg: float):
        """Muestra los resultados en el panel inline."""
        self._lbl_dist_3d.setText(f"{dist_3d:.3f} m")
        self._lbl_dist_2d.setText(f"{dist_2d:.3f} m")
        self._lbl_dz.setText(f"{dz:.3f} m")
        self._lbl_slope.setText(f"{slope_deg:.1f} °")

        self._results_group.setVisible(True)
        self.adjustSize()

    def get_points(self) -> list[tuple]:
        """Devuelve la lista de puntos [(x, y, z), ...]."""
        return list(self._points)

    def reset(self):
        """Limpia puntos y resultados."""
        self._points.clear()
        self._point_list.clear()
        self._results_group.setVisible(False)
        self.adjustSize()

    # ------------------------------------------------------------------
    # Slots internos
    # ------------------------------------------------------------------

    def _on_clear(self):
        self.reset()
        self.clear_requested.emit()

    def _on_close(self):
        self.hide()
        self.reset()
        self.clear_requested.emit()

    # Evitar que cerrar la ventana destruya el diálogo
    def closeEvent(self, event):
        self._on_close()
        event.ignore()   # No destruir, solo ocultar
        self.hide()

    # Enter o Escape
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._on_close()
        else:
            super().keyPressEvent(event)