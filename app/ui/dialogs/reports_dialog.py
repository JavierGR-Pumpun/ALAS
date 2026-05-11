"""
ALAS — Analysis Reports Dialog
Manage saved PDF analysis reports stored in NeonDB.
"""

from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFrame, QApplication, QMessageBox, QFileDialog, QInputDialog
)
from PyQt6.QtCore import Qt, QThreadPool

from PyQt6.QtGui import QColor

from app.logger import get_logger
from app.i18n import tr
from app.processing.workers import ProcessingWorker
from app.ui.widgets import LoadingOverlay

logger = get_logger("ui.reports_dialog")


def _open_pdf(path: str):
    """Open a PDF file with the system default viewer."""
    p = Path(path)
    if not p.exists():
        return False
    try:
        if sys.platform == "win32":
            os.startfile(str(p))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])
        return True
    except Exception as e:
        logger.error(f"Could not open PDF: {e}")
        return False


class ReportsDialog(QDialog):
    """Dialog for browsing, uploading, and managing saved analysis PDF reports."""

    def __init__(self, user, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self._user = user
        self.setWindowTitle(tr("reports.title"))
        self.setMinimumSize(780, 500)
        self.resize(920, 560)
        self._reports: List = []
        self._busy = False
        self._setup_ui()
        self._apply_style()
        self._loading_overlay = LoadingOverlay(self)
        self._load_reports()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        title = QLabel(tr("reports.title"))
        title.setObjectName("rpt_title")
        hdr.addWidget(title)
        hdr.addStretch()
        self._count_label = QLabel("")
        self._count_label.setObjectName("count_label")
        hdr.addWidget(self._count_label)
        root.addLayout(hdr)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("divider")
        root.addWidget(sep)

        # Table
        panel = QFrame()
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        col_label = QLabel(tr("reports.table_header"))
        col_label.setObjectName("section_label")
        panel_layout.addWidget(col_label)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            tr("reports.col_title"),
            tr("reports.col_file"),
            tr("reports.col_size"),
            tr("reports.col_date"),
            tr("reports.col_shared"),
        ])
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(False)
        self._table.selectionModel().selectionChanged.connect(self._on_selection)
        panel_layout.addWidget(self._table)

        self._empty_label = QLabel(tr("reports.empty"))
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setObjectName("empty_label")
        panel_layout.addWidget(self._empty_label)

        root.addWidget(panel, 1)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_upload = QPushButton(tr("reports.upload"))
        self._btn_upload.clicked.connect(self._upload_pdf)
        btn_row.addWidget(self._btn_upload)

        self._btn_view = QPushButton(tr("reports.view"))
        self._btn_view.setEnabled(False)
        self._btn_view.clicked.connect(self._view_report)
        btn_row.addWidget(self._btn_view)

        self._btn_share = QPushButton(tr("reports.share"))
        self._btn_share.setEnabled(False)
        self._btn_share.clicked.connect(self._toggle_share)
        btn_row.addWidget(self._btn_share)

        self._btn_delete = QPushButton(tr("reports.delete"))
        self._btn_delete.setObjectName("btn_danger")
        self._btn_delete.setEnabled(False)
        self._btn_delete.clicked.connect(self._delete_report)
        btn_row.addWidget(self._btn_delete)

        btn_row.addStretch()

        self._btn_refresh = QPushButton(tr("reports.refresh"))
        self._btn_refresh.clicked.connect(self._load_reports)
        btn_row.addWidget(self._btn_refresh)

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
            QLabel#rpt_title {
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
                background: #0a0a0a; width: 5px; border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: #252525; border-radius: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
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
            QPushButton:pressed { background: #0e0e0e; }
            QPushButton:disabled { color: #2a2a2a; border-color: #141414; }
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

    # ------------------------------------------------------------------
    # Threading helpers
    # ------------------------------------------------------------------

    def _set_busy(self, busy: bool):
        self._busy = busy
        self._btn_upload.setEnabled(not busy)
        self._btn_refresh.setEnabled(not busy)
        if busy:
            self._btn_view.setEnabled(False)
            self._btn_share.setEnabled(False)
            self._btn_delete.setEnabled(False)
            self._loading_overlay.show_loading()
        else:
            self._loading_overlay.hide_loading()
            self._on_selection()

    def _run_in_thread(self, func, on_result=None, on_error=None):
        worker = ProcessingWorker(func)
        if on_result:
            worker.signals.result.connect(on_result)
        if on_error:
            worker.signals.error.connect(on_error)
        QThreadPool.globalInstance().start(worker)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _load_reports(self):
        if not self._user or self._busy:
            return
        self._set_busy(True)
        self._count_label.setText(tr("reports.loading") if tr("reports.loading") != "reports.loading" else "…")

        user_id = self._user.id

        def fetch():
            from app.auth.reports_service import get_user_reports
            return get_user_reports(user_id)

        def on_result(reports):
            self._reports = reports
            self._rebuild_table()
            self._set_busy(False)

        def on_error(msg):
            logger.error(f"Load reports failed: {msg}")
            self._set_busy(False)

        self._run_in_thread(fetch, on_result=on_result, on_error=on_error)

    def _rebuild_table(self):
        self._table.setRowCount(0)
        has = bool(self._reports)
        self._empty_label.setVisible(not has)
        self._table.setVisible(has)

        fg = QColor("#c0c0c0")
        bg = QColor("#0e0e0e")

        def cell(text: str, align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter):
            item = QTableWidgetItem(text)
            item.setBackground(bg)
            item.setForeground(fg)
            item.setTextAlignment(align)
            return item

        center = Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter

        for r in self._reports:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setRowHeight(row, 34)
            self._table.setItem(row, 0, cell(r.title))
            self._table.setItem(row, 1, cell(r.filename))
            self._table.setItem(row, 2, cell(r.size_human, center))
            self._table.setItem(row, 3, cell(r.date_str, center))
            shared_text = tr("reports.yes") if r.is_shared() else tr("reports.no")
            shared_item = cell(shared_text, center)
            if r.is_shared():
                shared_item.setForeground(QColor("#66cc88"))
            self._table.setItem(row, 4, shared_item)

        n = len(self._reports)
        self._count_label.setText(f"{n} {tr('reports.count_suffix')}")
        self._on_selection()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _selected_report(self):
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        idx = rows[0].row()
        if idx < len(self._reports):
            return self._reports[idx]
        return None

    def _on_selection(self):
        report = self._selected_report()
        has = report is not None and not self._busy
        self._btn_view.setEnabled(has)
        self._btn_delete.setEnabled(has)
        self._btn_share.setEnabled(has)
        if has:
            self._btn_share.setText(
                tr("reports.unshare") if report.is_shared() else tr("reports.share")
            )

    def _upload_pdf(self):
        if not self._user:
            QMessageBox.warning(self, tr("reports.title"), tr("reports.no_user"))
            return

        path, _ = QFileDialog.getOpenFileName(
            self, tr("reports.upload_dialog_title"), "",
            f"PDF (*.pdf)"
        )
        if not path:
            return

        title, ok = QInputDialog.getText(
            self, tr("reports.title_input"), tr("reports.title_prompt"),
            text=Path(path).stem
        )
        if not ok or not title.strip():
            return

        dest = self._ensure_reports_dir() / Path(path).name
        import shutil
        shutil.copy2(path, dest)

        self._set_busy(True)
        user_id = self._user.id
        final_title = title.strip()
        dest_str = str(dest)

        def save():
            from app.auth.reports_service import save_report
            return save_report(user_id, final_title, dest_str)

        def on_result(result):
            self._set_busy(False)
            if isinstance(result, str):
                QMessageBox.critical(self, tr("reports.title"), tr("reports.error_save"))
                return
            self._load_reports()
            QMessageBox.information(self, tr("reports.saved"), tr("reports.saved_msg"))

        def on_error(msg):
            logger.error(f"Upload save failed: {msg}")
            self._set_busy(False)
            QMessageBox.critical(self, tr("reports.title"), tr("reports.error_save"))

        self._run_in_thread(save, on_result=on_result, on_error=on_error)

    def _view_report(self):
        report = self._selected_report()
        if not report:
            return
        if not Path(report.disk_path).exists():
            QMessageBox.warning(self, tr("reports.title"), tr("reports.file_missing"))
            return
        if not _open_pdf(report.disk_path):
            QMessageBox.warning(self, tr("reports.title"), tr("reports.file_missing"))

    def _toggle_share(self):
        report = self._selected_report()
        if not report or not self._user:
            return
        self._set_busy(True)
        report_id = report.id
        user_id = self._user.id

        def toggle():
            from app.auth.reports_service import toggle_share
            return toggle_share(report_id, user_id)

        def on_result(new_token):
            self._set_busy(False)
            if new_token is not None:
                msg = tr("reports.shared_msg").format(new_token)
                QApplication.clipboard().setText(new_token)
                QMessageBox.information(self, tr("reports.title"), msg)
            else:
                QMessageBox.information(self, tr("reports.title"), tr("reports.unshared_msg"))
            self._load_reports()

        def on_error(msg):
            logger.error(f"Toggle share failed: {msg}")
            self._set_busy(False)

        self._run_in_thread(toggle, on_result=on_result, on_error=on_error)

    def _delete_report(self):
        report = self._selected_report()
        if not report or not self._user:
            return
        reply = QMessageBox.question(
            self,
            tr("reports.confirm_delete"),
            tr("reports.confirm_delete_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._set_busy(True)
        report_id = report.id
        user_id = self._user.id

        def delete():
            from app.auth.reports_service import delete_report
            return delete_report(report_id, user_id)

        def on_result(ok):
            self._set_busy(False)
            if ok:
                self._load_reports()
            else:
                QMessageBox.critical(self, tr("reports.title"), tr("reports.error_save"))

        def on_error(msg):
            logger.error(f"Delete report failed: {msg}")
            self._set_busy(False)

        self._run_in_thread(delete, on_result=on_result, on_error=on_error)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_reports_dir(self) -> Path:
        d = Path.home() / ".alas" / "reports" / str(self._user.id)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def show_and_raise(self):
        self._load_reports()
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
