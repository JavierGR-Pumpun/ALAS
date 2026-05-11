"""
ALAS — Loading Overlay Widget
Displays a spinner overlay during heavy processing tasks.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QColor

from app.ui.assets.waitingspinnerwidget import QtWaitingSpinner


class LoadingOverlay(QWidget):
    """Semi-transparent overlay with QtWaitingSpinner animation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("loading_overlay")

        if parent:
            parent.installEventFilter(self)

        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
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

        self._spinner = QtWaitingSpinner(
            self,
            centerOnParent=False,
            disableParentWhenSpinning=False,
        )
        self._spinner.setColor(QColor("#ffffff"))
        self._spinner.setRoundness(100.0)
        self._spinner.setNumberOfLines(12)
        self._spinner.setLineLength(12)
        self._spinner.setLineWidth(3)
        self._spinner.setInnerRadius(10)
        self._spinner.setRevolutionsPerSecond(1.5)
        self._spinner.setTrailFadePercentage(70.0)

        layout.addWidget(self._spinner, alignment=Qt.AlignmentFlag.AlignCenter)

    def eventFilter(self, obj, event):
        if obj == self.parent() and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.parent().rect())
        return super().eventFilter(obj, event)

    def show_loading(self):
        if self.parent():
            self.setGeometry(self.parent().rect())
        self._spinner.start()
        self.raise_()
        self.show()

    def hide_loading(self):
        self._spinner.stop()
        self.hide()

    def showEvent(self, event):
        if self.parent():
            self.setGeometry(self.parent().rect())
        super().showEvent(event)
