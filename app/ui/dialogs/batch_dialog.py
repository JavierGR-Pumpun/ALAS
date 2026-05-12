"""
ALAS — Batch Processing Dialog
Configure and run a multi-step pipeline over a list of LAS/LAZ files.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QFileDialog,
    QMessageBox, QCheckBox, QComboBox, QDoubleSpinBox, QTabWidget,
    QWidget, QPlainTextEdit, QLineEdit, QAbstractItemView,
)


from app.config import SMRF_DEFAULTS, CSF_DEFAULTS, PMF_DEFAULTS, DEFAULT_DEM_RESOLUTION
from app.i18n import tr
from app.logger import get_logger
from app.processing.batch import BatchJob, BatchStep, BatchWorker

logger = get_logger("ui.batch_dialog")


class BatchProcessingDialog(QDialog):
    """Two-phase dialog: configure then run a batch job."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("batch.title"))
        self.setMinimumSize(820, 560)
        self._worker: BatchWorker | None = None
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        root = QVBoxLayout(self)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_config_tab(), tr("batch.title"))
        self._tabs.addTab(self._build_progress_tab(), tr("batch.progress_title"))
        self._tabs.setTabEnabled(1, False)
        root.addWidget(self._tabs)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_cancel = QPushButton(tr("dialog.cancel"))
        self._btn_cancel.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._btn_cancel)

        self._btn_run = QPushButton(tr("batch.run"))
        self._btn_run.setObjectName("primary")
        self._btn_run.clicked.connect(self._on_run)
        btn_row.addWidget(self._btn_run)

        root.addLayout(btn_row)

    # ── Config tab ────────────────────────────────────────────────────

    def _build_config_tab(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)

        # Left: file list  |  Right: pipeline steps
        h_split = QHBoxLayout()

        # ── Left: file list ───────────────────────────────────────────
        grp_files = QGroupBox(tr("batch.files"))
        vf = QVBoxLayout(grp_files)

        self._file_list = QListWidget()
        self._file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        vf.addWidget(self._file_list)

        btn_col = QVBoxLayout()
        btn_add = QPushButton(tr("batch.add_files"))
        btn_add.clicked.connect(self._add_files)
        btn_col.addWidget(btn_add)
        btn_folder = QPushButton(tr("batch.add_folder"))
        btn_folder.clicked.connect(self._add_folder)
        btn_col.addWidget(btn_folder)
        btn_remove = QPushButton(tr("batch.remove_selected"))
        btn_remove.clicked.connect(self._remove_selected)
        btn_col.addWidget(btn_remove)
        vf.addLayout(btn_col)

        h_split.addWidget(grp_files, stretch=1)

        # ── Right: steps (top) + output (bottom) ──────────────────────
        right = QVBoxLayout()

        steps_tabs = QTabWidget()
        steps_tabs.addTab(self._build_preprocess_step(), tr("batch.step_preprocess"))
        steps_tabs.addTab(self._build_classify_step(),   tr("batch.step_classify"))
        steps_tabs.addTab(self._build_dem_step(),        tr("batch.step_dem"))
        steps_tabs.addTab(self._build_export_step(),     tr("batch.step_export"))
        right.addWidget(steps_tabs, stretch=1)

        grp_out = QGroupBox(tr("batch.output_dir"))
        out_row = QHBoxLayout(grp_out)
        self._out_dir_edit = QLineEdit(tr("batch.no_output_dir"))
        self._out_dir_edit.setReadOnly(True)
        out_row.addWidget(self._out_dir_edit)
        btn_browse = QPushButton(tr("batch.browse"))
        btn_browse.clicked.connect(self._browse_output)
        out_row.addWidget(btn_browse)
        right.addWidget(grp_out)

        h_split.addLayout(right, stretch=1)

        root.addLayout(h_split)

        return w

    def _build_preprocess_step(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)

        self._pre_enabled = QCheckBox(tr("batch.enable_step"))
        self._pre_enabled.setChecked(False)
        vl.addWidget(self._pre_enabled)

        grp = QGroupBox(tr("batch.preprocess_options"))
        form = QFormLayout(grp)

        self._pre_noise = QCheckBox()
        self._pre_noise.setChecked(True)
        form.addRow(tr("batch.filter_noise"), self._pre_noise)

        self._pre_noise_method = QComboBox()
        self._pre_noise_method.addItem(tr("batch.noise_statistical"), "statistical")
        self._pre_noise_method.addItem(tr("batch.noise_radius"), "radius")
        form.addRow(tr("batch.noise_method"), self._pre_noise_method)

        self._pre_decimate = QCheckBox()
        self._pre_decimate.setChecked(False)
        form.addRow(tr("batch.decimate"), self._pre_decimate)

        self._pre_voxel = QDoubleSpinBox()
        self._pre_voxel.setRange(0.1, 10.0)
        self._pre_voxel.setValue(0.5)
        self._pre_voxel.setDecimals(1)
        self._pre_voxel.setSuffix(" m")
        form.addRow(tr("batch.voxel_size"), self._pre_voxel)

        self._pre_overlap = QCheckBox()
        self._pre_overlap.setChecked(False)
        form.addRow(tr("batch.remove_overlap"), self._pre_overlap)

        vl.addWidget(grp)
        vl.addStretch()
        return w

    def _build_classify_step(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)

        self._clf_enabled = QCheckBox(tr("batch.enable_step"))
        self._clf_enabled.setChecked(False)
        vl.addWidget(self._clf_enabled)

        grp = QGroupBox(tr("batch.classify_options"))
        form = QFormLayout(grp)

        self._clf_algo = QComboBox()
        self._clf_algo.addItem(tr("classify.smrf"), "smrf")
        self._clf_algo.addItem(tr("classify.csf"),  "csf")
        self._clf_algo.addItem(tr("classify.pmf"),  "pmf")
        self._clf_algo.currentIndexChanged.connect(self._on_clf_algo_changed)
        form.addRow(tr("classify.algorithm"), self._clf_algo)

        # SMRF
        self._clf_smrf_window = QDoubleSpinBox()
        self._clf_smrf_window.setRange(1, 100)
        self._clf_smrf_window.setValue(SMRF_DEFAULTS["window"])
        form.addRow(tr("classify.window"), self._clf_smrf_window)

        self._clf_smrf_slope = QDoubleSpinBox()
        self._clf_smrf_slope.setRange(0.01, 5.0)
        self._clf_smrf_slope.setValue(SMRF_DEFAULTS["slope"])
        self._clf_smrf_slope.setSingleStep(0.05)
        form.addRow(tr("classify.slope"), self._clf_smrf_slope)

        self._clf_smrf_threshold = QDoubleSpinBox()
        self._clf_smrf_threshold.setRange(0.01, 10.0)
        self._clf_smrf_threshold.setValue(SMRF_DEFAULTS["threshold"])
        form.addRow(tr("classify.threshold"), self._clf_smrf_threshold)

        # CSF (hidden by default)
        self._clf_csf_resolution = QDoubleSpinBox()
        self._clf_csf_resolution.setRange(0.1, 10.0)
        self._clf_csf_resolution.setValue(CSF_DEFAULTS["resolution"])
        self._clf_csf_res_row = (QLabel(tr("classify.resolution")), self._clf_csf_resolution)

        self._clf_csf_threshold = QDoubleSpinBox()
        self._clf_csf_threshold.setRange(0.01, 5.0)
        self._clf_csf_threshold.setValue(CSF_DEFAULTS["threshold"])
        self._clf_csf_thr_row = (QLabel(tr("classify.threshold")), self._clf_csf_threshold)

        # PMF (hidden by default)
        self._clf_pmf_window = QDoubleSpinBox()
        self._clf_pmf_window.setRange(1, 100)
        self._clf_pmf_window.setValue(PMF_DEFAULTS["max_window_size"])
        self._clf_pmf_win_row = (QLabel(tr("classify.max_window")), self._clf_pmf_window)

        self._clf_pmf_slope = QDoubleSpinBox()
        self._clf_pmf_slope.setRange(0.1, 10.0)
        self._clf_pmf_slope.setValue(PMF_DEFAULTS["slope"])
        self._clf_pmf_slp_row = (QLabel(tr("classify.slope")), self._clf_pmf_slope)

        # Add CSF/PMF rows to form and hide them
        for lbl, widget in [self._clf_csf_res_row, self._clf_csf_thr_row,
                             self._clf_pmf_win_row, self._clf_pmf_slp_row]:
            form.addRow(lbl, widget)
            lbl.hide()
            widget.hide()

        self._clf_veg = QCheckBox()
        self._clf_veg.setChecked(True)
        form.addRow(tr("classify.classify_veg"), self._clf_veg)

        vl.addWidget(grp)
        vl.addStretch()
        return w

    def _build_dem_step(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)

        self._dem_enabled = QCheckBox(tr("batch.enable_step"))
        self._dem_enabled.setChecked(False)
        vl.addWidget(self._dem_enabled)

        grp = QGroupBox(tr("batch.dem_options"))
        form = QFormLayout(grp)

        self._dem_dtm = QCheckBox()
        self._dem_dtm.setChecked(True)
        form.addRow("DTM", self._dem_dtm)

        self._dem_dsm = QCheckBox()
        self._dem_dsm.setChecked(False)
        form.addRow("DSM", self._dem_dsm)

        self._dem_chm = QCheckBox()
        self._dem_chm.setChecked(False)
        form.addRow("CHM", self._dem_chm)

        self._dem_resolution = QDoubleSpinBox()
        self._dem_resolution.setRange(0.1, 100.0)
        self._dem_resolution.setValue(DEFAULT_DEM_RESOLUTION)
        self._dem_resolution.setDecimals(1)
        self._dem_resolution.setSuffix(" m")
        form.addRow(tr("dem.resolution"), self._dem_resolution)

        self._dem_method = QComboBox()
        self._dem_method.addItem(tr("dem.method_idw"),     "idw")
        self._dem_method.addItem(tr("dem.method_tin"),     "tin")
        self._dem_method.addItem(tr("dem.method_nearest"), "nearest")
        form.addRow(tr("dem.interpolation"), self._dem_method)

        vl.addWidget(grp)
        vl.addStretch()
        return w

    def _build_export_step(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)

        self._exp_enabled = QCheckBox(tr("batch.enable_step"))
        self._exp_enabled.setChecked(True)
        vl.addWidget(self._exp_enabled)

        grp = QGroupBox(tr("batch.export_options"))
        form = QFormLayout(grp)

        self._exp_format = QComboBox()
        self._exp_format.addItem("LAZ", "laz")
        self._exp_format.addItem("LAS", "las")
        form.addRow(tr("export.format"), self._exp_format)

        vl.addWidget(grp)
        vl.addStretch()
        return w

    # ── Progress tab (CLI aesthetic) ──────────────────────────────────

    # One-Dark-ish palette
    C_BG       = "#0a0a0a"
    C_BG_DIM   = "#0f1216"
    C_BORDER   = "#1a1f26"
    C_FG       = "#d4d4d4"
    C_DIM      = "#5c6370"
    C_DIMMER   = "#3a3f46"
    C_CYAN     = "#56b6c2"
    C_GREEN    = "#98c379"
    C_RED      = "#e06c75"
    C_YELLOW   = "#e5c07b"
    C_BLUE     = "#61afef"
    C_MAGENTA  = "#c678dd"

    BAR_WIDTH  = 24
    SPINNER    = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def _build_progress_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background:{self.C_BG};")
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        mono = QFont("Menlo", 10)
        mono.setStyleHint(QFont.StyleHint.Monospace)

        # ── scrolling terminal ───────────────────────────────────────
        self._term = QPlainTextEdit()
        self._term.setReadOnly(True)
        self._term.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._term.setFont(mono)
        self._term.setStyleSheet(
            "QPlainTextEdit {"
            f"  background:{self.C_BG};"
            f"  color:{self.C_FG};"
            "  border:none;"
            "  padding:10px 14px 6px 14px;"
            "  selection-background-color:#2a3a4a;"
            "}"
            "QScrollBar:vertical { background:#0a0a0a; width:10px; }"
            f"QScrollBar::handle:vertical {{ background:{self.C_DIMMER}; border-radius:3px; }}"
            "QScrollBar::add-line, QScrollBar::sub-line { height:0; }"
        )
        vl.addWidget(self._term, stretch=1)

        # ── status line (a label, drawn as ASCII status bar) ─────────
        self._status_line = QLabel()
        self._status_line.setFont(mono)
        self._status_line.setTextFormat(Qt.TextFormat.RichText)
        self._status_line.setStyleSheet(
            f"background:{self.C_BG_DIM};"
            f"color:{self.C_FG};"
            f"border-top:1px solid {self.C_BORDER};"
            "padding:8px 14px;"
        )
        vl.addWidget(self._status_line)

        # Per-run state
        self._total_files: int = 0
        self._done_count:  int = 0
        self._step_block: int | None = None   # block index of in-place step line
        self._head_block: int | None = None   # block index of "▸ [n/N] name" line
        self._spin_idx:   int = 0
        self._file_t0:    float = 0.0
        self._batch_t0:   float = 0.0

        self._update_status(0, 0, "idle")
        return w

    # ── terminal output helpers ───────────────────────────────────────

    def _emit(self, text: str, color: str | None = None) -> int:
        """Append a line at the end and return its block number."""
        fmt = QTextCharFormat()
        if color:
            fmt.setForeground(QColor(color))
        cur = self._term.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        cur.insertText(text + "\n", fmt)
        self._term.setTextCursor(cur)
        self._term.ensureCursorVisible()
        return self._term.document().blockCount() - 2

    def _replace_block(self, block_no: int, text: str, color: str):
        block = self._term.document().findBlockByNumber(block_no)
        if not block.isValid():
            return
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        c = QTextCursor(block)
        c.select(QTextCursor.SelectionType.BlockUnderCursor)
        # BlockUnderCursor includes the preceding newline; reinsert it
        c.insertText(("\n" if block_no > 0 else "") + text, fmt)

    def _ascii_bar(self, pct: int, width: int | None = None) -> str:
        width = width or self.BAR_WIDTH
        pct = max(0, min(100, pct))
        filled = int(width * pct / 100)
        return "█" * filled + "░" * (width - filled)

    def _spinner_char(self) -> str:
        ch = self.SPINNER[self._spin_idx % len(self.SPINNER)]
        self._spin_idx += 1
        return ch

    def _update_status(self, done: int, total: int, state: str):
        """Render the bottom status bar (rich text in QLabel)."""
        pct  = int(done / total * 100) if total else 0
        bar  = self._ascii_bar(pct, 32)
        sep  = f"<span style='color:{self.C_DIMMER}'>│</span>"
        bar_color = self.C_GREEN if (total and done == total) else self.C_CYAN
        files_txt = (
            f"<span style='color:{self.C_DIM}'>files</span> "
            f"<span style='color:{self.C_FG}'>{done}/{total}</span>"
        )
        bar_txt = (
            f"<span style='color:{bar_color}'>{bar}</span> "
            f"<span style='color:{self.C_FG}'>{pct:3d}%</span>"
        )
        state_color = {
            "idle":     self.C_DIM,
            "running":  self.C_BLUE,
            "done":     self.C_GREEN,
            "errors":   self.C_YELLOW,
        }.get(state, self.C_DIM)
        state_txt = f"<span style='color:{state_color}'>● {state}</span>"
        self._status_line.setText(
            f"&nbsp;{files_txt}&nbsp;&nbsp;{sep}&nbsp;&nbsp;{bar_txt}"
            f"&nbsp;&nbsp;{sep}&nbsp;&nbsp;{state_txt}"
        )

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, tr("batch.add_files"), "",
            "LAS/LAZ (*.las *.laz);;All files (*)"
        )
        for p in paths:
            self._add_path(Path(p))

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, tr("batch.add_folder"))
        if not folder:
            return
        files = list(Path(folder).glob("*.las")) + list(Path(folder).glob("*.laz"))
        if not files:
            QMessageBox.information(self, tr("batch.title"), tr("batch.no_files_in_folder"))
            return
        for f in sorted(files):
            self._add_path(f)

    def _add_path(self, path: Path):
        for i in range(self._file_list.count()):
            if self._file_list.item(i).data(Qt.ItemDataRole.UserRole) == str(path):
                return
        item = QListWidgetItem(path.name)
        item.setData(Qt.ItemDataRole.UserRole, str(path))
        item.setToolTip(str(path))
        self._file_list.addItem(item)

    def _remove_selected(self):
        for item in self._file_list.selectedItems():
            self._file_list.takeItem(self._file_list.row(item))

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, tr("batch.output_dir"))
        if folder:
            self._out_dir_edit.setText(folder)

    def _on_clf_algo_changed(self, _idx: int):
        algo = self._clf_algo.currentData()
        smrf_widgets = [self._clf_smrf_window, self._clf_smrf_slope, self._clf_smrf_threshold]
        csf_pairs = [self._clf_csf_res_row, self._clf_csf_thr_row]
        pmf_pairs = [self._clf_pmf_win_row, self._clf_pmf_slp_row]

        for w in smrf_widgets:
            w.setVisible(algo == "smrf")
        for lbl, widget in csf_pairs:
            lbl.setVisible(algo == "csf")
            widget.setVisible(algo == "csf")
        for lbl, widget in pmf_pairs:
            lbl.setVisible(algo == "pmf")
            widget.setVisible(algo == "pmf")

    def _on_cancel(self):
        if self._worker is not None:
            self._worker.cancel()
        self.reject()

    def _on_run(self):
        # Validate
        if self._file_list.count() == 0:
            QMessageBox.warning(self, tr("batch.title"), tr("batch.no_files"))
            return

        out_dir_text = self._out_dir_edit.text()
        if out_dir_text == tr("batch.no_output_dir") or not out_dir_text:
            QMessageBox.warning(self, tr("batch.title"), tr("batch.no_output_dir_warn"))
            return

        steps = self._collect_steps()
        if not steps:
            QMessageBox.warning(self, tr("batch.title"), tr("batch.no_steps"))
            return

        files = [
            Path(self._file_list.item(i).data(Qt.ItemDataRole.UserRole))
            for i in range(self._file_list.count())
        ]
        job = BatchJob(
            file_list=files,
            steps=steps,
            output_dir=Path(out_dir_text),
        )

        self._prepare_progress_table(files)
        self._tabs.setTabEnabled(1, True)
        self._tabs.setCurrentIndex(1)
        self._btn_run.setEnabled(False)

        self._worker = BatchWorker(job)
        self._worker.signals.file_started.connect(self._on_file_started)
        self._worker.signals.file_progress.connect(self._on_file_progress)
        self._worker.signals.file_done.connect(self._on_file_done)
        self._worker.signals.all_done.connect(self._on_all_done)
        QThreadPool.globalInstance().start(self._worker)

    # ------------------------------------------------------------------
    # Progress helpers
    # ------------------------------------------------------------------

    def _prepare_progress_table(self, files: list[Path]):
        import datetime, time
        self._total_files = len(files)
        self._done_count  = 0
        self._step_block  = None
        self._head_block  = None
        self._spin_idx    = 0
        self._batch_t0    = time.time()

        self._term.clear()

        ts = datetime.datetime.now().strftime("%H:%M:%S")
        # Header banner
        self._emit("",                                                   self.C_DIM)
        self._emit("  ╭─────────────────────────────────────────────╮",  self.C_BORDER)
        self._emit(f"  │  alas-batch  ·  {len(files):>3} files  ·  {ts}     │",
                                                                         self.C_FG)
        self._emit("  ╰─────────────────────────────────────────────╯",  self.C_BORDER)
        self._emit("",                                                   self.C_DIM)

        self._update_status(0, len(files), "running")

    def _on_file_started(self, idx: int, name: str):
        import time
        self._file_t0 = time.time()
        n = idx + 1
        # Header line for this file (in cyan), tracked so we can finalise later
        head = f"  ▸ [{n}/{self._total_files}]  {name}"
        self._head_block = self._emit(head, self.C_CYAN)
        # Reserve an empty step line right below; it gets updated in place
        self._step_block = self._emit("", self.C_BLUE)

    def _on_file_progress(self, _idx: int, pct: int, msg: str):
        msg_clean = msg.rstrip("…").rstrip(".").lower()
        spin      = self._spinner_char()
        bar       = self._ascii_bar(pct)
        line      = f"      {spin}  {msg_clean:<22.22s} [{bar}] {pct:3d}%"
        if self._step_block is not None:
            self._replace_block(self._step_block, line, self.C_BLUE)
            self._term.ensureCursorVisible()
        else:
            self._step_block = self._emit(line, self.C_BLUE)

    def _on_file_done(self, _idx: int, success: bool, message: str):
        import time
        elapsed = time.time() - self._file_t0

        # Finalise the step line in place
        if self._step_block is not None:
            if success:
                bar  = self._ascii_bar(100)
                line = f"      ✓  {'done':<22.22s} [{bar}] 100%"
                self._replace_block(self._step_block, line, self.C_GREEN)
            else:
                line = f"      ✗  {message[:60]}"
                self._replace_block(self._step_block, line, self.C_RED)
            self._step_block = None

        # Append a tidy summary line below
        if success:
            self._emit(f"        └─ ok in {elapsed:.1f}s", self.C_DIMMER)
        else:
            self._emit(f"        └─ failed after {elapsed:.1f}s", self.C_DIMMER)
        self._emit("", self.C_DIM)

        self._done_count += 1
        state = "running" if self._done_count < self._total_files else "done"
        self._update_status(self._done_count, self._total_files, state)

    def _on_all_done(self, succeeded: int, failed: int):
        import time
        self._worker = None
        self._btn_run.setEnabled(True)
        total = succeeded + failed
        elapsed = time.time() - self._batch_t0

        self._emit("  " + "─" * 47, self.C_BORDER)
        if failed == 0:
            self._emit(
                f"  ✓ batch finished  {succeeded}/{total} ok  in {elapsed:.1f}s",
                self.C_GREEN,
            )
        else:
            self._emit(
                f"  ! batch finished  {succeeded}/{total} ok, "
                f"{failed} failed  in {elapsed:.1f}s",
                self.C_YELLOW,
            )
        self._emit("", self.C_DIM)

        self._update_status(self._done_count, self._total_files,
                            "done" if failed == 0 else "errors")

        msg = tr("batch.done_msg").format(succeeded, total)
        if failed:
            msg += "\n" + tr("batch.done_errors").format(failed)
        QMessageBox.information(self, tr("batch.title"), msg)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _collect_steps(self) -> list[BatchStep]:
        steps = []

        if self._pre_enabled.isChecked():
            steps.append(BatchStep(
                step_type="preprocess",
                params={
                    "filter_noise":  self._pre_noise.isChecked(),
                    "noise_method":  self._pre_noise_method.currentData(),
                    "decimate":      self._pre_decimate.isChecked(),
                    "voxel_size":    self._pre_voxel.value(),
                    "handle_overlap": self._pre_overlap.isChecked(),
                },
            ))

        if self._clf_enabled.isChecked():
            algo = self._clf_algo.currentData()
            p: dict = {"algorithm": algo, "classify_above_ground": self._clf_veg.isChecked()}
            if algo == "smrf":
                p.update(window=self._clf_smrf_window.value(),
                         slope=self._clf_smrf_slope.value(),
                         threshold=self._clf_smrf_threshold.value())
            elif algo == "csf":
                p.update(resolution=self._clf_csf_resolution.value(),
                         threshold=self._clf_csf_threshold.value())
            elif algo == "pmf":
                p.update(max_window_size=self._clf_pmf_window.value(),
                         slope=self._clf_pmf_slope.value())
            steps.append(BatchStep(step_type="classify", params=p))

        if self._dem_enabled.isChecked():
            dem_types = []
            if self._dem_dtm.isChecked(): dem_types.append("dtm")
            if self._dem_dsm.isChecked(): dem_types.append("dsm")
            if self._dem_chm.isChecked(): dem_types.append("chm")
            if dem_types:
                steps.append(BatchStep(
                    step_type="dem",
                    params={
                        "dem_types":     dem_types,
                        "resolution":    self._dem_resolution.value(),
                        "interpolation": self._dem_method.currentData(),
                    },
                ))

        if self._exp_enabled.isChecked():
            steps.append(BatchStep(
                step_type="export",
                params={"format": self._exp_format.currentData()},
            ))

        return steps
