"""
ALAS — Animated Flythrough Recorder
Records an orbiting flythrough of selected layers and exports to MP4.

THREADING NOTE: VTK/OpenGL screenshot() MUST run on the main thread.
Frame capture is driven by QTimer (main thread). Encoding runs in a
separate QThread after all frames are collected.
"""

import os
import json
import tempfile
import math
from datetime import datetime
from pathlib import Path

PRESETS_DIR = Path.home() / ".alas" / "flythrough_presets"

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QFileDialog,
    QMessageBox, QSpinBox, QDoubleSpinBox, QProgressBar, QLineEdit,
    QComboBox, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QSizePolicy, QScrollArea, QWidget, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor

from app.core.layer_manager import LayerManager
from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.flythrough_dialog")


# ---------------------------------------------------------------------------
# Encoder worker
# ---------------------------------------------------------------------------

class EncoderWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error    = pyqtSignal(str)

    def __init__(self, frame_paths, fps, output_path, tmp_dir):
        super().__init__()
        self._frame_paths = frame_paths
        self._fps         = fps
        self._output_path = output_path
        self._tmp_dir     = tmp_dir

    def run(self):
        try:
            import imageio
        except ImportError:
            self.error.emit("imageio not found.\nInstall: pip install imageio[ffmpeg]")
            return
        try:
            writer = imageio.get_writer(
                self._output_path,
                format="ffmpeg",
                fps=self._fps,
                codec="libx264",
                output_params=["-pix_fmt", "yuv420p", "-crf", "18"],
            )
            n = len(self._frame_paths)
            for i, fp in enumerate(self._frame_paths):
                writer.append_data(imageio.imread(fp))
                self.progress.emit(int((i + 1) / n * 100))
            writer.close()
        except Exception as exc:
            self._cleanup()
            self.error.emit(f"Encoding error: {exc}")
            return
        self._cleanup()
        self.finished.emit(self._output_path)

    def _cleanup(self):
        for fp in self._frame_paths:
            try:
                os.remove(fp)
            except OSError:
                pass
        try:
            os.rmdir(self._tmp_dir)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Path builder
# ---------------------------------------------------------------------------

def _scene_bounds(actors):
    bounds_list = []
    for actor in actors:
        try:
            b = actor.GetBounds()
            if all(abs(v) < 1e15 for v in b):
                bounds_list.append(b)
        except Exception:
            pass
    if not bounds_list:
        return None
    xmin = min(b[0] for b in bounds_list)
    xmax = max(b[1] for b in bounds_list)
    ymin = min(b[2] for b in bounds_list)
    ymax = max(b[3] for b in bounds_list)
    zmin = min(b[4] for b in bounds_list)
    zmax = max(b[5] for b in bounds_list)
    center = ((xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2)
    auto_radius = max(xmax - xmin, ymax - ymin, zmax - zmin) * 0.75
    return center, max(auto_radius, 1.0)


def _ease_inout(t):
    """Smooth-step ease in/out (t in [0,1])."""
    return t * t * (3 - 2 * t)


def _build_full_path(center_xyz, segments, start_angle_deg, fps):
    """
    Build the complete camera path from a list of segment dicts:
      {
        'duration': float (seconds),
        'radius':   float,
        'elevation': float (degrees),
        'orbits':   float,
        'clockwise': bool,
        'ease':      bool,
      }
    Returns list of (position, focal, view_up).
    """
    cx, cy, cz = center_xyz
    path = []
    current_angle = math.radians(start_angle_deg)

    for seg in segments:
        n_frames   = max(1, round(seg["duration"] * fps))
        radius     = seg["radius"]
        elev_rad   = math.radians(seg["elevation"])
        total_spin = 2 * math.pi * seg["orbits"]
        if seg["clockwise"]:
            total_spin = -total_spin

        for i in range(n_frames):
            t = i / max(n_frames - 1, 1)
            if seg["ease"]:
                t = _ease_inout(t)
            angle = current_angle + total_spin * t
            x = cx + radius * math.cos(angle) * math.cos(elev_rad)
            y = cy + radius * math.sin(angle) * math.cos(elev_rad)
            z = cz + radius * math.sin(elev_rad)
            path.append(((x, y, z), (cx, cy, cz), (0.0, 0.0, 1.0)))

        # next segment starts where this one ended
        current_angle += total_spin

    return path


# ---------------------------------------------------------------------------
# Segment table row defaults
# ---------------------------------------------------------------------------

_SEG_DEFAULTS = {
    "duration":  5.0,
    "radius":    100.0,
    "elevation": 30.0,
    "orbits":    1.0,
    "clockwise": False,
    "ease":      True,
}


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

class FlythroughDialog(QDialog):

    # column indices in the segments table
    _COL_DUR  = 0
    _COL_RAD  = 1
    _COL_ELEV = 2
    _COL_ORB  = 3
    _COL_CW   = 4
    _COL_EASE = 5

    def __init__(self, layer_manager: LayerManager, viewport, parent=None):
        super().__init__(parent)
        self._layer_manager    = layer_manager
        self._viewport         = viewport
        self._encoder          = None
        self._saved_visibility: dict = {}

        self._capture_timer = None
        self._camera_path   = []
        self._frame_idx     = 0
        self._frame_paths   = []
        self._tmp_dir       = None
        self._capture_fps   = 24
        self._capture_res   = (1920, 1080)
        self._output_path   = ""
        self._cancelled     = False
        self._auto_radius   = 100.0   # filled when recording starts

        self.setWindowTitle(tr("flythrough.title"))
        self.setMinimumWidth(620)
        self.setMinimumHeight(680)
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(8)
        scroll.setWidget(inner)
        root.addWidget(scroll)

        # ---- Presets ----
        grp_preset = QGroupBox(tr("flythrough.presets"))
        preset_row = QHBoxLayout(grp_preset)
        self._preset_combo = QComboBox()
        self._preset_combo.setMinimumWidth(180)
        self._preset_combo.setPlaceholderText(tr("flythrough.preset_placeholder"))
        preset_row.addWidget(self._preset_combo, stretch=1)
        load_btn = QPushButton(tr("flythrough.preset_load"))
        load_btn.clicked.connect(self._load_preset)
        preset_row.addWidget(load_btn)
        save_btn = QPushButton(tr("flythrough.preset_save"))
        save_btn.clicked.connect(self._save_preset)
        preset_row.addWidget(save_btn)
        del_btn_p = QPushButton(tr("flythrough.preset_delete"))
        del_btn_p.clicked.connect(self._delete_preset)
        preset_row.addWidget(del_btn_p)
        layout.addWidget(grp_preset)
        self._refresh_preset_list()

        # ---- Layer selection ----
        grp_layers = QGroupBox(tr("flythrough.layers"))
        vl = QVBoxLayout(grp_layers)
        self._layer_list = QListWidget()
        self._layer_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self._layer_list.setMaximumHeight(120)
        for entry in self._layer_manager.get_all_entries():
            icon = "☁" if entry.is_point_cloud else "▦"
            item = QListWidgetItem(f"{icon} {entry.name}")
            item.setData(Qt.ItemDataRole.UserRole, entry.name)
            item.setSelected(entry.visible)
            self._layer_list.addItem(item)
        vl.addWidget(self._layer_list)
        hint = QLabel(tr("flythrough.layers_hint"))
        hint.setStyleSheet("color: gray; font-size: 11px;")
        vl.addWidget(hint)
        layout.addWidget(grp_layers)

        # ---- Global camera settings ----
        grp_cam = QGroupBox(tr("flythrough.camera_global"))
        form_cam = QFormLayout(grp_cam)

        self._start_angle = QDoubleSpinBox()
        self._start_angle.setRange(0, 359.9)
        self._start_angle.setValue(0)
        self._start_angle.setSuffix("°")
        self._start_angle.setToolTip(tr("flythrough.tip_start_angle"))
        form_cam.addRow(tr("flythrough.start_angle"), self._start_angle)

        self._center_z_offset = QDoubleSpinBox()
        self._center_z_offset.setRange(-9999, 9999)
        self._center_z_offset.setValue(0)
        self._center_z_offset.setSingleStep(1)
        self._center_z_offset.setDecimals(2)
        self._center_z_offset.setToolTip(tr("flythrough.tip_center_z"))
        form_cam.addRow(tr("flythrough.center_z_offset"), self._center_z_offset)

        # Auto-radius toggle
        rad_row = QHBoxLayout()
        self._auto_radius_chk = QCheckBox(tr("flythrough.auto_radius"))
        self._auto_radius_chk.setChecked(True)
        self._auto_radius_chk.toggled.connect(self._on_auto_radius_toggled)
        rad_row.addWidget(self._auto_radius_chk)
        self._global_radius = QDoubleSpinBox()
        self._global_radius.setRange(0.1, 1e7)
        self._global_radius.setValue(100)
        self._global_radius.setSingleStep(10)
        self._global_radius.setDecimals(2)
        self._global_radius.setEnabled(False)
        self._global_radius.setToolTip(tr("flythrough.tip_global_radius"))
        rad_row.addWidget(self._global_radius)
        form_cam.addRow(tr("flythrough.distance"), rad_row)

        layout.addWidget(grp_cam)

        # ---- Orbit segments table ----
        grp_seg = QGroupBox(tr("flythrough.segments"))
        seg_layout = QVBoxLayout(grp_seg)

        hint2 = QLabel(tr("flythrough.segments_hint"))
        hint2.setStyleSheet("color: gray; font-size: 11px;")
        hint2.setWordWrap(True)
        seg_layout.addWidget(hint2)

        self._seg_table = QTableWidget(0, 6)
        self._seg_table.setHorizontalHeaderLabels([
            tr("flythrough.col_duration"),
            tr("flythrough.col_radius"),
            tr("flythrough.col_elevation"),
            tr("flythrough.col_orbits"),
            tr("flythrough.col_clockwise"),
            tr("flythrough.col_ease"),
        ])
        hdr = self._seg_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._seg_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._seg_table.setMinimumHeight(160)
        seg_layout.addWidget(self._seg_table)

        seg_btns = QHBoxLayout()
        add_btn = QPushButton(tr("flythrough.seg_add"))
        add_btn.clicked.connect(self._add_segment)
        seg_btns.addWidget(add_btn)
        dup_btn = QPushButton(tr("flythrough.seg_duplicate"))
        dup_btn.clicked.connect(self._duplicate_segment)
        seg_btns.addWidget(dup_btn)
        del_btn = QPushButton(tr("flythrough.seg_remove"))
        del_btn.clicked.connect(self._remove_segment)
        seg_btns.addWidget(del_btn)
        seg_btns.addStretch()
        seg_layout.addLayout(seg_btns)
        layout.addWidget(grp_seg)

        # Add one default segment
        self._add_segment()

        # ---- Video settings ----
        grp_vid = QGroupBox(tr("flythrough.video"))
        form2 = QFormLayout(grp_vid)
        self._fps = QSpinBox()
        self._fps.setRange(10, 60)
        self._fps.setValue(24)
        self._fps.setSuffix(" fps")
        form2.addRow(tr("flythrough.fps"), self._fps)
        self._resolution = QComboBox()
        self._resolution.addItems(["1280×720", "1920×1080", "2560×1440", "3840×2160"])
        self._resolution.setCurrentIndex(1)
        form2.addRow(tr("flythrough.resolution"), self._resolution)
        layout.addWidget(grp_vid)

        # ---- Output ----
        grp_out = QGroupBox(tr("flythrough.output"))
        hl = QHBoxLayout(grp_out)
        self._path_edit = QLineEdit()
        default_name = f"flythrough_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        self._path_edit.setText(os.path.join(os.path.expanduser("~"), default_name))
        self._path_edit.setPlaceholderText(tr("flythrough.output_placeholder"))
        hl.addWidget(self._path_edit)
        browse_btn = QPushButton(tr("classify.browse"))
        browse_btn.clicked.connect(self._browse_output)
        hl.addWidget(browse_btn)
        layout.addWidget(grp_out)

        # ---- Progress ----
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        root.addWidget(self._progress)
        self._status_label = QLabel("")
        self._status_label.setVisible(False)
        root.addWidget(self._status_label)

        # ---- Buttons ----
        btn_row = QHBoxLayout()
        self._record_btn = QPushButton(tr("flythrough.record"))
        self._record_btn.setDefault(True)
        self._record_btn.clicked.connect(self._start_recording)
        btn_row.addWidget(self._record_btn)
        self._cancel_btn = QPushButton(tr("dialog.cancel"))
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._cancel_btn)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Segment table helpers
    # ------------------------------------------------------------------

    def _add_segment(self, values: dict = None):
        v = values or dict(_SEG_DEFAULTS)
        row = self._seg_table.rowCount()
        self._seg_table.insertRow(row)
        self._set_seg_row(row, v)

    def _set_seg_row(self, row, v):
        def spin(val, lo, hi, step=0.1, dec=1, suffix=""):
            w = QDoubleSpinBox()
            w.setRange(lo, hi)
            w.setSingleStep(step)
            w.setDecimals(dec)
            w.setValue(val)
            if suffix:
                w.setSuffix(suffix)
            w.setFrame(False)
            return w

        def chk(val):
            w = QCheckBox()
            w.setChecked(val)
            wrapper = QWidget()
            lay = QHBoxLayout(wrapper)
            lay.addWidget(w)
            lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.setContentsMargins(0, 0, 0, 0)
            return wrapper, w

        self._seg_table.setCellWidget(row, self._COL_DUR,  spin(v["duration"],  0.5, 300, 0.5, 1, " s"))
        self._seg_table.setCellWidget(row, self._COL_RAD,  spin(v["radius"],    0.1, 1e7, 10,  2, ""))
        self._seg_table.setCellWidget(row, self._COL_ELEV, spin(v["elevation"], 1,   89,  5,   1, "°"))
        self._seg_table.setCellWidget(row, self._COL_ORB,  spin(v["orbits"],   -10,  10,  0.25,2, "×"))

        cw_wrap, self._cw_w = chk(v["clockwise"])
        self._seg_table.setCellWidget(row, self._COL_CW, cw_wrap)

        ease_wrap, self._ease_w = chk(v["ease"])
        self._seg_table.setCellWidget(row, self._COL_EASE, ease_wrap)

    def _get_seg_row(self, row) -> dict:
        def spin_val(col):
            w = self._seg_table.cellWidget(row, col)
            return w.value() if w else 0.0

        def chk_val(col):
            wrapper = self._seg_table.cellWidget(row, col)
            if wrapper is None:
                return False
            chkbox = wrapper.findChild(QCheckBox)
            return chkbox.isChecked() if chkbox else False

        return {
            "duration":  spin_val(self._COL_DUR),
            "radius":    spin_val(self._COL_RAD),
            "elevation": spin_val(self._COL_ELEV),
            "orbits":    spin_val(self._COL_ORB),
            "clockwise": chk_val(self._COL_CW),
            "ease":      chk_val(self._COL_EASE),
        }

    def _duplicate_segment(self):
        rows = sorted({i.row() for i in self._seg_table.selectedItems()})
        if not rows:
            rows = [self._seg_table.rowCount() - 1]
        for r in rows:
            self._add_segment(self._get_seg_row(r))

    def _remove_segment(self):
        rows = sorted({i.row() for i in self._seg_table.selectedItems()}, reverse=True)
        for r in rows:
            self._seg_table.removeRow(r)
        if self._seg_table.rowCount() == 0:
            self._add_segment()

    def _on_auto_radius_toggled(self, checked: bool):
        self._global_radius.setEnabled(not checked)

    # ------------------------------------------------------------------
    # Presets
    # ------------------------------------------------------------------

    def _preset_path(self, name: str) -> Path:
        return PRESETS_DIR / f"{name}.json"

    def _refresh_preset_list(self):
        self._preset_combo.clear()
        PRESETS_DIR.mkdir(parents=True, exist_ok=True)
        names = sorted(p.stem for p in PRESETS_DIR.glob("*.json"))
        for name in names:
            self._preset_combo.addItem(name)

    def _current_settings(self) -> dict:
        return {
            "start_angle":    self._start_angle.value(),
            "center_z_offset": self._center_z_offset.value(),
            "auto_radius":    self._auto_radius_chk.isChecked(),
            "global_radius":  self._global_radius.value(),
            "fps":            self._fps.value(),
            "resolution":     self._resolution.currentText(),
            "segments":       self._collect_segments(),
        }

    def _apply_settings(self, data: dict):
        self._start_angle.setValue(data.get("start_angle", 0))
        self._center_z_offset.setValue(data.get("center_z_offset", 0))
        auto = data.get("auto_radius", True)
        self._auto_radius_chk.setChecked(auto)
        self._global_radius.setEnabled(not auto)
        self._global_radius.setValue(data.get("global_radius", 100))
        self._fps.setValue(data.get("fps", 24))
        res = data.get("resolution", "1920×1080")
        idx = self._resolution.findText(res)
        if idx >= 0:
            self._resolution.setCurrentIndex(idx)
        # Rebuild segments table
        while self._seg_table.rowCount():
            self._seg_table.removeRow(0)
        for seg in data.get("segments", [_SEG_DEFAULTS]):
            self._add_segment(seg)

    def _save_preset(self):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, tr("flythrough.preset_save"), tr("flythrough.preset_name_prompt"),
            text=self._preset_combo.currentText() or "",
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        # Sanitise: remove path separators
        name = name.replace("/", "-").replace("\\", "-")
        PRESETS_DIR.mkdir(parents=True, exist_ok=True)
        path = self._preset_path(name)
        path.write_text(json.dumps(self._current_settings(), indent=2), encoding="utf-8")
        logger.info(f"Flythrough preset saved: {path}")
        self._refresh_preset_list()
        idx = self._preset_combo.findText(name)
        if idx >= 0:
            self._preset_combo.setCurrentIndex(idx)

    def _load_preset(self):
        name = self._preset_combo.currentText()
        if not name:
            return
        path = self._preset_path(name)
        if not path.exists():
            QMessageBox.warning(self, tr("flythrough.title"), tr("flythrough.preset_not_found"))
            self._refresh_preset_list()
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            QMessageBox.critical(self, tr("flythrough.title"), f"{tr('error.processing_failed')}: {exc}")
            return
        self._apply_settings(data)
        logger.info(f"Flythrough preset loaded: {name}")

    def _delete_preset(self):
        name = self._preset_combo.currentText()
        if not name:
            return
        reply = QMessageBox.question(
            self, tr("flythrough.preset_delete"),
            tr("flythrough.preset_delete_confirm").format(name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        path = self._preset_path(name)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        self._refresh_preset_list()
        logger.info(f"Flythrough preset deleted: {name}")

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def _browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, tr("flythrough.save_as"), "", "MP4 Video (*.mp4)"
        )
        if path:
            if not path.lower().endswith(".mp4"):
                path += ".mp4"
            self._path_edit.setText(path)

    def _selected_names(self):
        return {
            item.data(Qt.ItemDataRole.UserRole)
            for item in self._layer_list.selectedItems()
        }

    def _collect_segments(self):
        segs = []
        for r in range(self._seg_table.rowCount()):
            segs.append(self._get_seg_row(r))
        return segs

    def _start_recording(self):
        selected = self._selected_names()
        if not selected:
            QMessageBox.warning(self, tr("flythrough.title"), tr("flythrough.no_layers"))
            return

        self._output_path = self._path_edit.text().strip()
        if not self._output_path:
            QMessageBox.warning(self, tr("flythrough.title"), tr("flythrough.no_output"))
            return

        actor_map = self._viewport._current_actors
        selected_actors = [actor_map[n] for n in selected if n in actor_map]
        if not selected_actors:
            QMessageBox.warning(self, tr("flythrough.title"), tr("flythrough.no_actors"))
            return

        result = _scene_bounds(selected_actors)
        if result is None:
            QMessageBox.warning(self, tr("flythrough.title"), tr("flythrough.no_actors"))
            return
        center, auto_radius = result

        # Apply center Z offset
        cx, cy, cz = center
        cz += self._center_z_offset.value()
        center = (cx, cy, cz)

        # Radius: auto or manual
        base_radius = auto_radius if self._auto_radius_chk.isChecked() else self._global_radius.value()

        # Patch each segment: if auto-radius, scale segment radius relative to base
        segments = self._collect_segments()
        if self._auto_radius_chk.isChecked():
            # Use auto radius as the default for all segments that weren't changed
            # (segments keep their own radius values as multipliers when auto is on)
            for seg in segments:
                seg["radius"] = base_radius * (seg["radius"] / _SEG_DEFAULTS["radius"])
        # else: segments use their absolute radius values as-is

        self._capture_fps = self._fps.value()
        res_text = self._resolution.currentText()
        w, h = (int(v) for v in res_text.replace("×", "x").split("x"))
        self._capture_res = (w, h)

        self._camera_path = _build_full_path(
            center, segments,
            self._start_angle.value(),
            self._capture_fps,
        )

        if not self._camera_path:
            QMessageBox.warning(self, tr("flythrough.title"), tr("flythrough.no_actors"))
            return

        # Isolate layers
        self._saved_visibility = {}
        for entry in self._layer_manager.get_all_entries():
            self._saved_visibility[entry.name] = entry.visible
            self._viewport.set_layer_visibility(entry.name, entry.name in selected)

        self._tmp_dir     = tempfile.mkdtemp(prefix="alas_flythrough_")
        self._frame_paths = []
        self._frame_idx   = 0
        self._cancelled   = False

        self._record_btn.setEnabled(False)
        self._cancel_btn.setText(tr("flythrough.stop"))
        self._progress.setRange(0, len(self._camera_path))
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._status_label.setText(
            tr("flythrough.capturing_n").format(len(self._camera_path))
        )
        self._status_label.setVisible(True)

        self._capture_timer = QTimer(self)
        self._capture_timer.setInterval(0)
        self._capture_timer.timeout.connect(self._capture_next_frame)
        self._capture_timer.start()

    # ------------------------------------------------------------------
    # Frame capture (main thread)
    # ------------------------------------------------------------------

    def _capture_next_frame(self):
        if self._cancelled or self._frame_idx >= len(self._camera_path):
            self._capture_timer.stop()
            if self._cancelled:
                self._abort_capture()
            else:
                self._start_encoding()
            return

        pos, focal, up = self._camera_path[self._frame_idx]
        plotter = self._viewport.plotter
        plotter.camera_position = [pos, focal, up]
        plotter.reset_camera_clipping_range()
        plotter.render()

        frame_path = os.path.join(self._tmp_dir, f"frame_{self._frame_idx:05d}.png")
        plotter.screenshot(frame_path, window_size=self._capture_res)
        self._frame_paths.append(frame_path)
        self._frame_idx += 1
        self._progress.setValue(self._frame_idx)

    # ------------------------------------------------------------------
    # Encoding
    # ------------------------------------------------------------------

    def _start_encoding(self):
        self._status_label.setText(tr("flythrough.encoding"))
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._encoder = EncoderWorker(
            self._frame_paths, self._capture_fps,
            self._output_path, self._tmp_dir,
        )
        self._encoder.progress.connect(self._progress.setValue)
        self._encoder.finished.connect(self._on_finished)
        self._encoder.error.connect(self._on_error)
        self._encoder.start()

    # ------------------------------------------------------------------
    # Finish / error / cancel
    # ------------------------------------------------------------------

    def _restore_visibility(self):
        for entry in self._layer_manager.get_all_entries():
            wanted = self._saved_visibility.get(entry.name, entry.visible)
            self._viewport.set_layer_visibility(entry.name, wanted)
        self._saved_visibility = {}

    def _reset_ui(self):
        self._record_btn.setEnabled(True)
        self._cancel_btn.setText(tr("dialog.cancel"))
        self._progress.setVisible(False)
        self._status_label.setVisible(False)

    def _abort_capture(self):
        for fp in self._frame_paths:
            try:
                os.remove(fp)
            except OSError:
                pass
        try:
            os.rmdir(self._tmp_dir)
        except OSError:
            pass
        self._restore_visibility()
        self._reset_ui()

    def _on_finished(self, path):
        self._restore_visibility()
        self._progress.setValue(100)
        self._status_label.setText(tr("flythrough.done"))
        self._record_btn.setEnabled(True)
        self._cancel_btn.setText(tr("dialog.cancel"))
        logger.info(f"Flythrough exported: {path}")
        QMessageBox.information(
            self, tr("flythrough.title"),
            tr("flythrough.success").format(path),
        )

    def _on_error(self, msg):
        self._restore_visibility()
        self._reset_ui()
        logger.error(f"Flythrough error: {msg}")
        QMessageBox.critical(self, tr("flythrough.title"), msg)

    def _on_cancel(self):
        if self._capture_timer and self._capture_timer.isActive():
            self._cancelled = True
            return
        if self._encoder and self._encoder.isRunning():
            self._encoder.wait()
            self._restore_visibility()
        self.reject()

    def closeEvent(self, event):
        if self._capture_timer and self._capture_timer.isActive():
            self._capture_timer.stop()
            self._abort_capture()
        if self._encoder and self._encoder.isRunning():
            self._encoder.wait()
            self._restore_visibility()
        super().closeEvent(event)
