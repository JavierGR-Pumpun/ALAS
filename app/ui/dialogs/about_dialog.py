"""
ALAS — About Dialog
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt

from app.config import APP_NAME, APP_FULL_NAME, APP_VERSION
from app.i18n import tr


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("dialog.about_title"))
        self.setFixedSize(400, 250)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(APP_NAME)
        title.setObjectName("heading")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel(APP_FULL_NAME)
        subtitle.setObjectName("subheading")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        version = QLabel(f"Versión {APP_VERSION}")
        version.setObjectName("muted")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        desc = QLabel(tr("dialog.about_text"))
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        stack = QLabel("Python • PyQt6 • PyVista • PDAL • rasterio • richdem • pysheds")
        stack.setObjectName("muted")
        stack.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stack.setWordWrap(True)
        layout.addWidget(stack)

        btn = QPushButton(tr("dialog.close"))
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
