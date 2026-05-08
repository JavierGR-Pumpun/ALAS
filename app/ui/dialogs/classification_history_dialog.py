"""
ALAS — Classification History Dialog
Modal showing the history of terrain classifications performed in the session.
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
from app.i18n import tr

logger = get_logger("ui.classification_history")

_ALGO_LABEL_KEY: Dict[str, str] = {
    "smrf": "class_hist.smrf",
    "csf": "class_hist.csf",
    "pmf": "class_hist.pmf",
    "ai": "class_hist.ai",
}

_CLASS_NAMES: Dict[int, str] = {
    0: "class_hist.unclassified",
    1: "class_hist.unclassified",
    2: "class_hist.ground",
    3: "class_hist.low_veg",
    4: "class_hist.med_veg",
    5: "class_hist.high_veg",
    6: "class_hist.building",
    7: "class_hist.noise",
}


def _get_algo_label(algo: str) -> str:
    key = _ALGO_LABEL_KEY.get(algo, "class_hist.unknown")
    return tr(key)


def _fmt(value: float, decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}"


class ClassificationEntry:
    """Encapsulates a stored classification."""

    _counter = 0

    def __init__(self, algo: str, data: Dict[str, Any]):
        ClassificationEntry._counter += 1
        self.id = ClassificationEntry._counter
        self.algo = algo
        self.data = data
        self.ts = datetime.datetime.now()

    @property
    def timestamp_str(self) -> str:
        return self.ts.strftime("%H:%M:%S")

    @property
    def algo_label(self) -> str:
        return _get_algo_label(self.algo)

    @property
    def summary(self) -> str:
        d = self.data
        total = d.get("total_points", 0)
        ground = d.get("ground_points", 0)
        pct = (ground / total * 100) if total > 0 else 0
        return f"{_fmt(ground, 0)} ground ({pct:.1f}%)"

    def detail_text(self) -> str:
        sep = "-" * 44
        lines = [
            sep,
            f"  #{self.id}  {self.algo_label}   {self.ts.strftime('%d/%m/%Y %H:%M:%S')}",
            sep,
        ]
        d = self.data

        def row(label: str, value: str, w: int = 20) -> str:
            return f"  {label.ljust(w)}: {value}"

        W = 20
        total = d.get("total_points", 0)
        lines.append(row(tr("class_hist.total_points"), _fmt(total, 0), W))
        lines.append("")

        for class_code in [2, 3, 4, 5, 6, 7, 0]:
            count = d.get(f"class_{class_code}", 0)
            if count > 0 or class_code == 2:
                pct = (count / total * 100) if total > 0 else 0
                class_name = tr(_CLASS_NAMES.get(class_code, "class_hist.unknown"))
                lines.append(row(class_name, f"{_fmt(count, 0)} ({pct:.1f}%)", W))

        if self.algo != "ai":
            lines.append("")
            lines.append(row(tr("class_hist.post_process"), 
                           tr("dialog.yes") if d.get("post_process", False) else tr("dialog.no"), W))

        if self.algo == "smrf":
            lines.append("")
            lines.append(row(tr("classify.window"), str(d.get("window", "-")), W))
            lines.append(row(tr("classify.slope"), str(d.get("slope", "-")), W))
            lines.append(row(tr("classify.threshold"), str(d.get("threshold", "-")), W))
        elif self.algo == "csf":
            lines.append("")
            lines.append(row(tr("classify.resolution"), str(d.get("resolution", "-")), W))
            lines.append(row(tr("classify.rigidity"), str(d.get("rigidness", "-")), W))
            lines.append(row(tr("classify.threshold"), str(d.get("threshold", "-")), W))
        elif self.algo == "pmf":
            lines.append("")
            lines.append(row(tr("classify.max_window"), str(d.get("max_window_size", "-")), W))
            lines.append(row(tr("classify.slope"), str(d.get("slope", "-")), W))
        elif self.algo == "ai":
            lines.append("")
            lines.append(row(tr("classify.model_path"), d.get("model_path", "-"), W))
            lines.append(row(tr("classify.batch_size"), str(d.get("batch_size", "-")), W))

        return "\n".join(lines)


class ClassificationHistoryDialog(QDialog):
    """
    Non-blocking modal with classification history for the session.
    Hides on close, never destroyed.
    """

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(tr("class_hist.title"))
        self.setMinimumSize(740, 500)
        self.resize(880, 560)
        self._entries: List[ClassificationEntry] = []
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(12)

        hdr = QHBoxLayout()
        hdr.setSpacing(0)

        title = QLabel(tr("class_hist.title"))
        title.setObjectName("hist_title")
        hdr.addWidget(title)
        hdr.addStretch()

        self._count_label = QLabel(tr("class_hist.count_zero"))
        self._count_label.setObjectName("count_label")
        hdr.addWidget(self._count_label)
        root.addLayout(hdr)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("divider")
        root.addWidget(sep)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        left_container = QFrame()
        left_container.setObjectName("panel")
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        col_header = QLabel(tr("class_hist.classifications"))
        col_header.setObjectName("section_label")
        left_layout.addWidget(col_header)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            tr("hist.col_id"), tr("hist.col_time"),
            tr("class_hist.col_algorithm"), tr("hist.col_result"),
        ])
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

        self._empty_label = QLabel(tr("class_hist.empty_message"))
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setObjectName("empty_label")
        left_layout.addWidget(self._empty_label)

        splitter.addWidget(left_container)

        right_container = QFrame()
        right_container.setObjectName("panel")
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        detail_header = QLabel(tr("hist.detail"))
        detail_header.setObjectName("section_label")
        right_layout.addWidget(detail_header)

        self._detail_text = QTextEdit()
        self._detail_text.setReadOnly(True)
        self._detail_text.setObjectName("detail_text")
        self._detail_text.setPlaceholderText(tr("class_hist.placeholder"))
        right_layout.addWidget(self._detail_text)

        splitter.addWidget(right_container)
        splitter.setSizes([480, 360])

        root.addWidget(splitter, 1)

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

        self._btn_clear = QPushButton(tr("hist.clear_history"))
        self._btn_clear.setObjectName("btn_danger")
        self._btn_clear.clicked.connect(self._clear_history)
        btn_row.addWidget(self._btn_clear)

        btn_close = QPushButton(tr("dialog.close"))
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
                background: #1c1010;
                color: #cc6666;
                border-color: #2a1414;
            }
            QPushButton#btn_danger:hover {
                background: #251515;
                color: #d97878;
                border-color: #321818;
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

    def add_classification(self, algo: str, data: Dict[str, Any]) -> ClassificationEntry:
        entry = ClassificationEntry(algo, data)
        self._entries.append(entry)
        self._add_row(entry)
        self._update_counter()
        logger.debug(f"Classification #{entry.id} ({algo}) saved to history")
        return entry

    def show_and_raise(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _add_row(self, entry: ClassificationEntry):
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setRowHeight(row, 34)

        fg = QColor("#c0c0c0")
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
        self._table.setItem(row, 2, cell(entry.algo_label))
        self._table.setItem(row, 3, cell(entry.summary))

        self._empty_label.setVisible(False)
        self._table.setVisible(True)
        self._table.scrollToBottom()

    def _update_counter(self):
        n = len(self._entries)
        if n == 1:
            self._count_label.setText(tr("class_hist.count_one"))
        else:
            self._count_label.setText(tr("class_hist.count").format(n))

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
            self, tr("hist.copied_title"),
            tr("hist.copied_message").format(len(self._entries))
        )

    def _clear_history(self):
        if not self._entries:
            return
        reply = QMessageBox.question(
            self, tr("hist.clear_confirm_title"),
            tr("hist.clear_confirm_message").format(len(self._entries)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Yes:
            ClassificationEntry._counter = 0
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
