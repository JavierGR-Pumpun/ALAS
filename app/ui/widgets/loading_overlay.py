"""
ALAS — Loading Overlay Widget
Displays a loading GIF overlay during heavy processing tasks.
"""

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMovie
from pathlib import Path


class LoadingOverlay(QWidget):
    """Semi-transparent overlay with animated loading GIF."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("loading_overlay")
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        self.setStyleSheet("""
            #loading_overlay {
                background-color: rgba(0, 0, 0, 0.5);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        gif_path = Path(__file__).parent.parent / "assets" / "loading.gif"
        if gif_path.exists():
            self._movie = QMovie(str(gif_path))
            self._label.setMovie(self._movie)
        else:
            self._label.setText("Loading...")
            self._label.setStyleSheet("color: white; font-size: 24px;")

        layout.addWidget(self._label)

    def show_loading(self):
        """Show the loading overlay and start animation."""
        if self.parent():
            self.setGeometry(self.parent().rect())
        if hasattr(self, '_movie'):
            self._movie.start()
        self.raise_()
        self.show()

    def hide_loading(self):
        """Hide the loading overlay and stop animation."""
        if hasattr(self, '_movie'):
            self._movie.stop()
        self.hide()

    def showEvent(self, event):
        """Ensure overlay covers the entire parent widget when shown."""
        if self.parent():
            self.setGeometry(self.parent().rect())
        super().showEvent(event)

    def resizeEvent(self, event):
        """Ensure overlay covers the entire parent widget."""
        if self.parent():
            self.setGeometry(self.parent().rect())
        super().resizeEvent(event)
