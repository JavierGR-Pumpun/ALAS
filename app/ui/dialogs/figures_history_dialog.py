"""
ALAS — Figures History Dialog
Modal that lists every geometric figure placed on the point cloud, with
type, center, parameters and timestamp. Same visual language as the
measurements history dialog.
"""

from __future__ import annotations
import datetime
from typing import List, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSplitter, QTextEdit, QFrame, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from app.i18n import tr
from app.logger import get_logger
from app.ui.viewport.figures_tool import type_label, params_summary

logger = get_logger("ui.figures_history")


class FigureEntry:
    _counter = 0

    def __init__(self, ftype: str, center: tuple, params: dict):
        FigureEntry._counter += 1
        self.id = FigureEntry._counter
        self.ftype = ftype
        self.center = tuple(float(c) for c in center)
        self.params = dict(params)
        self.ts = datetime.datetime.now()
        self.actor_name = f"_figure_{self.id}"

    @property
    def timestamp_str(self) -> str:
        return self.ts.strftime("%H:%M:%S")

    def detail_text(self) -> str:
        sep = "-" * 44
        cx, cy, cz = self.center
        lines = [
            sep,
            f"  #{self.id}  {type_label(self.ftype)}   {self.ts.strftime('%d/%m/%Y %H:%M:%S')}",
            sep,
            f"  {tr('fig.col_center').ljust(18)}: ({cx:.3f}, {cy:.3f}, {cz:.3f})",
            f"  {tr('fig.col_params').ljust(18)}: {params_summary(self.ftype, self.params)}",
        ]
        return "\n".join(lines)


class FiguresHistoryDialog(QDialog):
    """Non-blocking modal listing every figure placement of the session."""

    remove_requested = pyqtSignal(int)        # figure id
    clear_all_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(tr("fig_hist.title"))
        self.setMinimumSize(740, 500)
        self.resize(880, 560)
        self._entries: List[FigureEntry] = []
        self._setup_ui()
        self._apply_style()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(12)

        hdr = QHBoxLayout()
        title = QLabel(tr("fig_hist.title"))
        title.setObjectName("hist_title")
        hdr.addWidget(title)
        hdr.addStretch()
        self._count_label = QLabel(tr("fig_hist.count_zero"))
        self._count_label.setObjectName("count_label")
        hdr.addWidget(self._count_label)
        root.addLayout(hdr)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("divider")
        root.addWidget(sep)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # --- left: table ---
        left = QFrame()
        left.setObjectName("panel")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        col_header = QLabel(tr("fig_hist.figures"))
        col_header.setObjectName("section_label")
        ll.addWidget(col_header)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            tr("fig.col_id"), tr("fig.col_time"), tr("fig.col_type"),
            tr("fig.col_center"), tr("fig.col_params"),
        ])
        h = self._table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(False)
        self._table.selectionModel().selectionChanged.connect(self._on_selection)
        ll.addWidget(self._table)

        self._empty_label = QLabel(tr("fig_hist.empty_message"))
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setObjectName("empty_label")
        ll.addWidget(self._empty_label)

        splitter.addWidget(left)

        # --- right: detail ---
        right = QFrame()
        right.setObjectName("panel")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        detail_header = QLabel(tr("fig_hist.detail"))
        detail_header.setObjectName("section_label")
        rl.addWidget(detail_header)

        self._detail_text = QTextEdit()
        self._detail_text.setReadOnly(True)
        self._detail_text.setObjectName("detail_text")
        self._detail_text.setPlaceholderText(tr("fig_hist.placeholder"))
        rl.addWidget(self._detail_text)

        splitter.addWidget(right)
        splitter.setSizes([480, 360])
        root.addWidget(splitter, 1)

        # --- actions ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_copy = QPushButton(tr("hist.copy_detail"))
        self._btn_copy.setEnabled(False)
        self._btn_copy.clicked.connect(self._copy_detail)
        btn_row.addWidget(self._btn_copy)

        self._btn_copy_all = QPushButton(tr("hist.copy_all"))
        self._btn_copy_all.clicked.connect(self._copy_all)
        btn_row.addWidget(self._btn_copy_all)

        btn_row.addStretch()

        self._btn_remove = QPushButton(tr("fig.remove_selected"))
        self._btn_remove.setEnabled(False)
        self._btn_remove.clicked.connect(self._on_remove)
        btn_row.addWidget(self._btn_remove)

        self._btn_clear = QPushButton(tr("fig.clear_all"))
        self._btn_clear.setObjectName("btn_danger")
        self._btn_clear.clicked.connect(self._on_clear)
        btn_row.addWidget(self._btn_clear)

        btn_close = QPushButton(tr("dialog.close"))
        btn_close.setObjectName("btn_close")
        btn_close.clicked.connect(self.hide)
        btn_row.addWidget(btn_close)
        root.addLayout(btn_row)

    def _apply_style(self):
        # Reuse the measurements-history palette verbatim for visual parity.
        self.setStyleSheet("""
            QDialog { background: #0a0a0a; color: #d0d0d0; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
            QLabel#hist_title { font-size: 15px; font-weight: 600; color: #ffffff; letter-spacing: 0.3px; }
            QLabel#count_label { color: #555555; font-size: 11px; padding-top: 3px; }
            QFrame#divider { color: #1e1e1e; max-height: 1px; }
            QFrame#panel { background: #0e0e0e; border: 1px solid #1a1a1a; border-radius: 4px; }
            QLabel#section_label { color: #444444; font-size: 10px; font-weight: 700; letter-spacing: 1px; padding: 8px 10px 6px 10px; border-bottom: 1px solid #1a1a1a; }
            QLabel#empty_label { color: #333333; font-size: 12px; padding: 40px 20px; }
            QTableWidget { background: transparent; border: none; color: #b0b0b0; font-size: 12px; outline: none; }
            QTableWidget::item { padding: 7px 10px; border-bottom: 1px solid #141414; color: #b0b0b0; }
            QTableWidget::item:selected { background: #1a1a1a; color: #ffffff; }
            QHeaderView::section { background: #0e0e0e; color: #3a3a3a; border: none; border-bottom: 1px solid #1a1a1a; padding: 6px 10px; font-size: 10px; font-weight: 700; letter-spacing: 0.8px; }
            QTextEdit#detail_text { background: #080808; color: #909090; border: none; font-family: 'Consolas', monospace; font-size: 12px; padding: 10px; }
            QSplitter::handle { background: #1a1a1a; }
            QPushButton { background: #141414; color: #a0a0a0; border: 1px solid #1e1e1e; border-radius: 3px; padding: 6px 14px; font-size: 12px; min-width: 80px; }
            QPushButton:hover { background: #1c1c1c; color: #d0d0d0; border-color: #2a2a2a; }
            QPushButton:disabled { color: #2a2a2a; border-color: #141414; }
            QPushButton#btn_danger { background: #1c1010; color: #cc6666; border-color: #2a1414; }
            QPushButton#btn_danger:hover { background: #251515; color: #d97878; border-color: #321818; }
            QPushButton#btn_close { background: #141414; color: #606060; border-color: #1e1e1e; }
            QPushButton#btn_close:hover { background: #1c1c1c; color: #ffffff; }
        """)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_figure(self, ftype: str, center: tuple, params: Dict[str, Any]) -> FigureEntry:
        entry = FigureEntry(ftype, center, params)
        self._entries.append(entry)
        self._append_row(entry)
        self._update_counter()
        return entry

    def update_entry(self, figure_id: int, new_params: dict):
        """Update the params of an existing entry and refresh its table row."""
        for entry in self._entries:
            if entry.id == figure_id:
                entry.params = dict(new_params)
                break
        self._rebuild_table()

    def update_entry_center(self, figure_id: int, new_center: tuple):
        """Update the center of an existing entry after a drag."""
        for entry in self._entries:
            if entry.id == figure_id:
                entry.center = tuple(float(c) for c in new_center)
                break
        self._rebuild_table()

    def remove_entry(self, figure_id: int):
        self._entries = [e for e in self._entries if e.id != figure_id]
        self._rebuild_table()
        self._update_counter()
        if not self._entries:
            self._detail_text.clear()
            self._btn_copy.setEnabled(False)
            self._btn_remove.setEnabled(False)

    def show_and_raise(self):
        self.show()
        self.raise_()
        self.activateWindow()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _append_row(self, entry: FigureEntry):
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setRowHeight(row, 34)
        cx, cy, cz = entry.center
        fg = QColor("#c0c0c0")
        bg = QColor("#0e0e0e")

        def cell(text: str, align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter):
            item = QTableWidgetItem(text)
            item.setBackground(bg)
            item.setForeground(fg)
            item.setTextAlignment(align)
            return item

        center = Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        self._table.setItem(row, 0, cell(str(entry.id), center))
        self._table.setItem(row, 1, cell(entry.timestamp_str, center))
        self._table.setItem(row, 2, cell(type_label(entry.ftype)))
        self._table.setItem(row, 3, cell(f"({cx:.2f}, {cy:.2f}, {cz:.2f})"))
        self._table.setItem(row, 4, cell(params_summary(entry.ftype, entry.params)))

        self._empty_label.setVisible(False)
        self._table.setVisible(True)
        self._table.scrollToBottom()

    def _rebuild_table(self):
        self._table.setRowCount(0)
        for e in self._entries:
            self._append_row(e)
        if not self._entries:
            self._empty_label.setVisible(True)
            self._table.setVisible(False)

    def _update_counter(self):
        n = len(self._entries)
        if n == 0:
            self._count_label.setText(tr("fig_hist.count_zero"))
        elif n == 1:
            self._count_label.setText(tr("fig_hist.count_one"))
        else:
            self._count_label.setText(tr("fig_hist.count").format(n))

    def _selected_entry(self) -> FigureEntry | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        if row >= len(self._entries):
            return None
        return self._entries[row]

    def _on_selection(self):
        entry = self._selected_entry()
        if entry is None:
            self._detail_text.clear()
            self._btn_copy.setEnabled(False)
            self._btn_remove.setEnabled(False)
            return
        self._detail_text.setPlainText(entry.detail_text())
        self._btn_copy.setEnabled(True)
        self._btn_remove.setEnabled(True)

    def _on_remove(self):
        entry = self._selected_entry()
        if entry is None:
            return
        self.remove_requested.emit(entry.id)
        self.remove_entry(entry.id)

    def _on_clear(self):
        if not self._entries:
            return
        reply = QMessageBox.question(
            self, tr("fig.clear_confirm_title"),
            tr("fig.clear_confirm_message"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        FigureEntry._counter = 0
        self._entries.clear()
        self._table.setRowCount(0)
        self._detail_text.clear()
        self._btn_copy.setEnabled(False)
        self._btn_remove.setEnabled(False)
        self._empty_label.setVisible(True)
        self._table.setVisible(False)
        self._update_counter()
        self.clear_all_requested.emit()

    def _copy_detail(self):
        text = self._detail_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _copy_all(self):
        if not self._entries:
            return
        QApplication.clipboard().setText("\n\n".join(e.detail_text() for e in self._entries))
        QMessageBox.information(
            self, tr("hist.copied_title"),
            tr("hist.copied_message").format(len(self._entries))
        )

    def closeEvent(self, event):
        event.ignore()
        self.hide()
