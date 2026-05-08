"""
ALAS — About Dialog
Displays project README with version info and tech stack.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTextBrowser
)
from PyQt6.QtCore import Qt

from app.config import APP_NAME, APP_FULL_NAME, APP_VERSION, ROOT_DIR
from app.i18n import tr


def _read_readme() -> str:
    readme_path = ROOT_DIR / "README.md"
    try:
        return readme_path.read_text(encoding="utf-8")
    except Exception:
        return f"# {APP_NAME}\n\n{APP_FULL_NAME}\n\nVersion {APP_VERSION}"


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("dialog.about_title"))
        self.setMinimumSize(600, 520)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 16)
        root.setSpacing(0)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        self._browser.setMarkdown(_read_readme())
        root.addWidget(self._browser)

        # Close button
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(16, 0, 16, 0)
        btn_row.addStretch()
        close_btn = QPushButton(tr("dialog.close"))
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)