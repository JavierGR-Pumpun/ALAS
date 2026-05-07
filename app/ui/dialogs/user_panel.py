"""
ALAS — User Panel Dialog
Shows logged-in user info and a logout button.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QPixmap, QPainterPath

from app.i18n import tr


def _initials_pixmap(full_name: str, size: int = 56) -> QPixmap:
    parts = full_name.strip().split()
    initials = (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()

    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)

    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.fillPath(path, QColor("#333348"))

    painter.setPen(QColor("#c0c0e0"))
    painter.setFont(QFont("Segoe UI", size // 3, QFont.Weight.Bold))
    painter.drawText(0, 0, size, size, Qt.AlignmentFlag.AlignCenter, initials)
    painter.end()
    return px


class UserPanelDialog(QDialog):
    """
    Centered modal showing user profile info and a logout button.
    Emits logout_requested when the user clicks Log out.
    """

    logout_requested = pyqtSignal()

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self._user = user
        self.setWindowTitle(tr("auth.my_account"))
        self.setFixedWidth(340)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self._build_ui()

    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(0)

        # Avatar + name
        header = QHBoxLayout()
        header.setSpacing(16)

        avatar = QLabel()
        avatar.setPixmap(_initials_pixmap(self._user.full_name, 56))
        avatar.setFixedSize(56, 56)
        header.addWidget(avatar)

        name_col = QVBoxLayout()
        name_col.setSpacing(4)

        name_lbl = QLabel(self._user.full_name)
        name_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        name_col.addWidget(name_lbl)

        email_lbl = QLabel(self._user.email)
        email_lbl.setObjectName("muted")
        name_col.addWidget(email_lbl)

        header.addLayout(name_col)
        header.addStretch()
        root.addLayout(header)

        root.addSpacing(20)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #222222; border: none;")
        root.addWidget(div)

        root.addSpacing(16)

        # Info rows
        phone_text = self._user.phone or "—"
        self._add_row(root, tr("auth.phone"), phone_text)

        since = self._user.created_at
        if hasattr(since, "strftime"):
            since_str = since.strftime("%d/%m/%Y")
        else:
            since_str = str(since)[:10]
        self._add_row(root, tr("auth.member_since"), since_str)

        root.addSpacing(20)

        # Logout
        btn = QPushButton(tr("auth.logout"))
        btn.setFixedHeight(36)
        btn.setObjectName("danger")
        btn.clicked.connect(self._on_logout)
        root.addWidget(btn)

    def _add_row(self, layout, key: str, value: str):
        row = QHBoxLayout()
        row.setSpacing(8)
        k = QLabel(key)
        k.setObjectName("muted")
        v = QLabel(value)
        row.addWidget(k)
        row.addStretch()
        row.addWidget(v)
        layout.addLayout(row)
        layout.addSpacing(8)

    def _on_logout(self):
        self.accept()
        self.logout_requested.emit()
