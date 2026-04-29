"""
ALAS — Log Panel
Panel de registro de procesamiento con colores por nivel.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit, QPushButton, QHBoxLayout
from PyQt6.QtGui import QColor, QTextCharFormat
from PyQt6.QtCore import Qt

from app.logger import get_log_emitter


class LogPanel(QWidget):
    """Panel que muestra los mensajes de log en tiempo real."""

    LEVEL_COLORS = {
        "DEBUG": "#888898",
        "INFO": "#e0e0e8",
        "WARNING": "#f59e0b",
        "ERROR": "#ef4444",
        "CRITICAL": "#dc2626",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        get_log_emitter().log_message.connect(self._append_log)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setMaximumBlockCount(2000)
        layout.addWidget(self.text_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_clear = QPushButton("Limpiar")
        btn_clear.setFixedWidth(80)
        btn_clear.clicked.connect(self.text_edit.clear)
        btn_layout.addWidget(btn_clear)

        layout.addLayout(btn_layout)

    def _append_log(self, level: str, message: str):
        color = self.LEVEL_COLORS.get(level, "#e0e0e8")
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))

        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(message + "\n", fmt)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()
