"""
ALAS — Loading Overlay Widget
Displays a loading GIF overlay during heavy processing tasks.
"""

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QMovie
from pathlib import Path


class LoadingOverlay(QWidget):
    """Semi-transparent overlay with animated loading GIF."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("loading_overlay")
        
        # Install event filter on parent to track its resizing
        if parent:
            parent.installEventFilter(self)
            
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        # Allow the widget to receive mouse events to block underlying widgets
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        # Required for styling a custom QWidget
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        self.setStyleSheet("""
            #loading_overlay {
                background-color: rgba(0, 0, 0, 160);
                border-radius: 0px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("background: transparent;")
        
        gif_path = Path(__file__).parent.parent / "assets" / "loading.gif"
        if gif_path.exists():
            self._movie = QMovie(str(gif_path))
            # Optional: handle GIF scaling if needed, but usually GIFs are fixed size
            self._label.setMovie(self._movie)
        else:
            self._label.setText("Loading...")
            self._label.setStyleSheet("color: white; font-size: 24px; font-weight: bold; background: transparent;")

        layout.addWidget(self._label)

    def eventFilter(self, obj, event):
        """Track parent resize events to stay full-screen within the parent."""
        if obj == self.parent() and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.parent().rect())
        return super().eventFilter(obj, event)

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
