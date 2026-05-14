"""
ALAS — Geometric Figures Tool
Floating modal: pick a figure type, adjust its parameters via sliders, then
click in the viewport to place it. In edit mode, also exposes X/Y/Z coordinate
fields so the user can reposition the figure by typing exact values.
"""

from __future__ import annotations
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel,
    QPushButton, QComboBox, QSlider, QLineEdit, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDoubleValidator

from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.figures_tool")


FIGURE_TYPES = ["cube", "sphere", "cylinder", "cone", "plane"]

_SCALE = 10        # 1 tick = 0.1 m
_MIN_M = 0.1
_MAX_M = 200.0


def type_label(ftype: str) -> str:
    return tr(f"fig.type_{ftype}")


def params_summary(ftype: str, params: dict) -> str:
    if ftype == "cube":
        return f"size={params.get('size', 0):.1f} m"
    if ftype == "sphere":
        return f"r={params.get('radius', 0):.1f} m"
    if ftype in ("cylinder", "cone"):
        return f"r={params.get('radius', 0):.1f} m, h={params.get('height', 0):.1f} m"
    if ftype == "plane":
        return f"{params.get('size_x', 0):.1f} × {params.get('size_y', 0):.1f} m"
    return "-"


def _to_tick(metres: float) -> int:
    return max(int(_MIN_M * _SCALE),
               min(int(_MAX_M * _SCALE), round(metres * _SCALE)))


def _to_metres(tick: int) -> float:
    return tick / _SCALE


class _SliderRow:
    """Horizontal slider + editable line-edit that stay in sync."""

    def __init__(self, label_text: str, default_m: float):
        self.label = QLabel(label_text)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(int(_MIN_M * _SCALE), int(_MAX_M * _SCALE))
        self.slider.setValue(_to_tick(default_m))
        self.slider.setTickInterval(_SCALE)

        self.edit = QLineEdit(f"{default_m:.1f}")
        self.edit.setFixedWidth(64)
        self.edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.edit.setValidator(QDoubleValidator(_MIN_M, _MAX_M, 1))
        self.edit.setPlaceholderText("m")

        self._updating = False
        self.slider.valueChanged.connect(self._slider_to_edit)
        self.edit.editingFinished.connect(self._edit_to_slider)

    def _slider_to_edit(self, tick: int):
        if self._updating:
            return
        self._updating = True
        self.edit.setText(f"{_to_metres(tick):.1f}")
        self._updating = False

    def _edit_to_slider(self):
        if self._updating:
            return
        try:
            v = float(self.edit.text().replace(",", "."))
        except ValueError:
            return
        v = max(_MIN_M, min(_MAX_M, v))
        self._updating = True
        self.slider.setValue(_to_tick(v))
        self.edit.setText(f"{v:.1f}")
        self._updating = False

    def value(self) -> float:
        return _to_metres(self.slider.value())

    def set_value(self, metres: float):
        self._updating = True
        self.slider.setValue(_to_tick(metres))
        self.edit.setText(f"{metres:.1f}")
        self._updating = False

    def set_visible(self, on: bool):
        self.label.setVisible(on)
        self.slider.setVisible(on)
        self.edit.setVisible(on)


def _coord_edit(value: float = 0.0) -> QLineEdit:
    """A free-range coordinate line-edit (no slider — coords can be huge/negative)."""
    e = QLineEdit(f"{value:.3f}")
    e.setAlignment(Qt.AlignmentFlag.AlignRight)
    e.setValidator(QDoubleValidator(-1e9, 1e9, 3))
    return e


class FiguresToolDialog(QDialog):
    """
    Floating tool dialog for placing / editing geometric figures.

    Modes
    -----
    - Place mode (default): Place button arms a world-pick; figure is created on
      click.  Emits ``place_requested(ftype, params)``.
    - Edit mode: loaded via ``load_figure()``.  Exposes X/Y/Z coordinate fields
      so the user can reposition the figure precisely.  Emits
      ``update_requested(figure_id, ftype, center, params)`` on Apply.
      Stays in edit mode until the user clicks Cancel.
    """

    place_requested  = pyqtSignal(str, dict)                  # ftype, params
    update_requested = pyqtSignal(int, str, tuple, dict)      # id, ftype, center, params

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool)
        self.setWindowTitle(tr("fig.title"))
        self.setMinimumWidth(380)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        self._edit_id: Optional[int] = None
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self._hint = QLabel(tr("fig.instructions"))
        self._hint.setWordWrap(True)
        self._hint.setObjectName("muted")
        self._hint.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self._hint)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a3d;")
        layout.addWidget(sep)

        # --- Parameters group ---
        self._grp_params = QGroupBox(tr("fig.parameters"))
        form_params = QFormLayout(self._grp_params)
        form_params.setSpacing(8)

        self._type_combo = QComboBox()
        for t in FIGURE_TYPES:
            self._type_combo.addItem(type_label(t), t)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        form_params.addRow(tr("fig.type"), self._type_combo)

        self._r_size   = _SliderRow(tr("fig.size"),   1.0)
        self._r_radius = _SliderRow(tr("fig.radius"), 1.0)
        self._r_height = _SliderRow(tr("fig.height"), 2.0)
        self._r_size_x = _SliderRow(tr("fig.size_x"), 2.0)
        self._r_size_y = _SliderRow(tr("fig.size_y"), 2.0)

        for r in (self._r_size, self._r_radius, self._r_height,
                  self._r_size_x, self._r_size_y):
            row_w = QHBoxLayout()
            row_w.addWidget(r.slider, 1)
            row_w.addWidget(r.edit)
            form_params.addRow(r.label, row_w)

        layout.addWidget(self._grp_params)

        # --- Position group (edit mode only) ---
        self._grp_pos = QGroupBox(tr("fig.position"))
        form_pos = QFormLayout(self._grp_pos)
        form_pos.setSpacing(8)

        self._edit_x = _coord_edit(0.0)
        self._edit_y = _coord_edit(0.0)
        self._edit_z = _coord_edit(0.0)
        form_pos.addRow("X", self._edit_x)
        form_pos.addRow("Y", self._edit_y)
        form_pos.addRow("Z", self._edit_z)

        self._grp_pos.setVisible(False)
        layout.addWidget(self._grp_pos)

        # --- Buttons ---
        btn_row = QHBoxLayout()
        self._btn_action = QPushButton(tr("fig.place"))
        self._btn_action.clicked.connect(self._on_action_clicked)
        btn_row.addWidget(self._btn_action)

        self._btn_cancel_edit = QPushButton(tr("fig.cancel_edit"))
        self._btn_cancel_edit.setVisible(False)
        self._btn_cancel_edit.clicked.connect(self._exit_edit_mode)
        btn_row.addWidget(self._btn_cancel_edit)

        btn_close = QPushButton(tr("dialog.close"))
        btn_close.clicked.connect(self.hide)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        self._on_type_changed(0)
        self.adjustSize()

    # ------------------------------------------------------------------
    # Parameter visibility
    # ------------------------------------------------------------------

    def _current_type(self) -> str:
        return self._type_combo.currentData()

    def _on_type_changed(self, _index: int):
        ftype = self._current_type()
        visible_map = {
            "cube":     {"size"},
            "sphere":   {"radius"},
            "cylinder": {"radius", "height"},
            "cone":     {"radius", "height"},
            "plane":    {"size_x", "size_y"},
        }
        visible = visible_map.get(ftype, set())
        self._r_size.set_visible("size" in visible)
        self._r_radius.set_visible("radius" in visible)
        self._r_height.set_visible("height" in visible)
        self._r_size_x.set_visible("size_x" in visible)
        self._r_size_y.set_visible("size_y" in visible)
        self.adjustSize()

    def _current_params(self) -> dict:
        ftype = self._current_type()
        if ftype == "cube":
            return {"size": self._r_size.value()}
        if ftype == "sphere":
            return {"radius": self._r_radius.value()}
        if ftype in ("cylinder", "cone"):
            return {"radius": self._r_radius.value(), "height": self._r_height.value()}
        if ftype == "plane":
            return {"size_x": self._r_size_x.value(), "size_y": self._r_size_y.value()}
        return {}

    def _current_center(self) -> tuple:
        def _f(edit: QLineEdit) -> float:
            try:
                return float(edit.text().replace(",", "."))
            except ValueError:
                return 0.0
        return (_f(self._edit_x), _f(self._edit_y), _f(self._edit_z))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_figure(self, figure_id: int, ftype: str, center: tuple, params: dict):
        """Switch to edit mode, pre-loaded with the figure's current state."""
        self._edit_id = figure_id

        idx = FIGURE_TYPES.index(ftype) if ftype in FIGURE_TYPES else 0
        self._type_combo.blockSignals(True)
        self._type_combo.setCurrentIndex(idx)
        self._type_combo.blockSignals(False)
        self._on_type_changed(idx)

        if "size"   in params: self._r_size.set_value(params["size"])
        if "radius" in params: self._r_radius.set_value(params["radius"])
        if "height" in params: self._r_height.set_value(params["height"])
        if "size_x" in params: self._r_size_x.set_value(params["size_x"])
        if "size_y" in params: self._r_size_y.set_value(params["size_y"])

        cx, cy, cz = (float(v) for v in center)
        self._edit_x.setText(f"{cx:.3f}")
        self._edit_y.setText(f"{cy:.3f}")
        self._edit_z.setText(f"{cz:.3f}")

        self._type_combo.setEnabled(False)
        self._grp_pos.setVisible(True)
        self._btn_action.setText(tr("fig.apply_changes"))
        self._btn_cancel_edit.setVisible(True)
        self._hint.setText(tr("fig.edit_instructions"))
        self.adjustSize()

    def update_center_display(self, center: tuple):
        """Refresh the coordinate fields after an external move (drag)."""
        if self._edit_id is None:
            return
        cx, cy, cz = (float(v) for v in center)
        self._edit_x.setText(f"{cx:.3f}")
        self._edit_y.setText(f"{cy:.3f}")
        self._edit_z.setText(f"{cz:.3f}")

    def _exit_edit_mode(self):
        self._edit_id = None
        self._type_combo.setEnabled(True)
        self._grp_pos.setVisible(False)
        self._btn_action.setText(tr("fig.place"))
        self._btn_cancel_edit.setVisible(False)
        self._hint.setText(tr("fig.instructions"))
        self.adjustSize()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_action_clicked(self):
        if self._edit_id is not None:
            self.update_requested.emit(
                self._edit_id,
                self._current_type(),
                self._current_center(),
                self._current_params(),
            )
        else:
            self.place_requested.emit(self._current_type(), self._current_params())

    def closeEvent(self, event):
        event.ignore()
        self.hide()
