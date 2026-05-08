"""
ALAS — User Panel Dialog
Shows logged-in user info, subscription/plan details, and a logout button.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QPixmap, QPainterPath

from app.i18n import tr
from app.auth import service as auth_service


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


_STATUS_COLOR = {
    "active":   "#4caf82",
    "trialing": "#7b9fe0",
    "lifetime": "#c0a060",
    "past_due": "#e07b7b",
    "canceled": "#888888",
    "unpaid":   "#e07b7b",
}

_BILLING_KEY = {
    "monthly":  "auth.billing_monthly",
    "annual":   "auth.billing_annual",
    "lifetime": "auth.billing_lifetime",
}

_STATUS_KEY = {
    "trialing": "auth.status_trialing",
    "active":   "auth.status_active",
    "past_due": "auth.status_past_due",
    "canceled": "auth.status_canceled",
    "unpaid":   "auth.status_unpaid",
    "lifetime": "auth.status_lifetime",
}


class UserPanelDialog(QDialog):
    """
    Centered modal showing user profile info and a logout button.
    Emits logout_requested when the user clicks Log out.
    """

    logout_requested = pyqtSignal()

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self._user = user
        self._sub = auth_service.get_subscription(user.id)
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
        root.addWidget(self._divider())
        root.addSpacing(16)

        # Account info
        phone_text = self._user.phone or "—"
        self._add_row(root, tr("auth.phone"), phone_text)

        since = self._user.created_at
        since_str = since.strftime("%d/%m/%Y") if hasattr(since, "strftime") else str(since)[:10]
        self._add_row(root, tr("auth.member_since"), since_str)

        root.addSpacing(16)
        root.addWidget(self._divider())
        root.addSpacing(16)

        # Subscription section
        self._build_subscription(root)

        root.addSpacing(20)

        # Logout
        btn = QPushButton(tr("auth.logout"))
        btn.setFixedHeight(36)
        btn.setObjectName("danger")
        btn.clicked.connect(self._on_logout)
        root.addWidget(btn)

    def _build_subscription(self, layout):
        sub = self._sub

        if sub is None:
            lbl = QLabel(tr("auth.no_subscription"))
            lbl.setObjectName("muted")
            layout.addWidget(lbl)
            layout.addSpacing(8)
            return

        # Plan name + status badge on the same row
        plan_row = QHBoxLayout()
        plan_row.setSpacing(8)

        plan_key = QLabel(tr("auth.plan"))
        plan_key.setObjectName("muted")
        plan_row.addWidget(plan_key)
        plan_row.addStretch()

        plan_name = QLabel(sub.plan_name)
        plan_name.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        plan_row.addWidget(plan_name)

        status_lbl = QLabel(tr(_STATUS_KEY.get(sub.status, sub.status)))
        color = _STATUS_COLOR.get(sub.status, "#888888")
        status_lbl.setStyleSheet(
            f"color: {color}; background: {color}22; border-radius: 4px;"
            "padding: 1px 6px; font-size: 10px;"
        )
        plan_row.addWidget(status_lbl)
        layout.addLayout(plan_row)
        layout.addSpacing(8)

        # Billing period
        billing_label = tr(_BILLING_KEY.get(sub.billing_period, sub.billing_period))
        self._add_row(layout, tr("auth.billing_period"), billing_label)

        # Trial / renewal / expiry date
        if sub.status == "trialing" and sub.trial_ends_at:
            date_str = sub.trial_ends_at.strftime("%d/%m/%Y")
            self._add_row(layout, tr("auth.trial_ends"), date_str)
        elif sub.status == "canceled" and sub.current_period_end:
            date_str = sub.current_period_end.strftime("%d/%m/%Y")
            self._add_row(layout, tr("auth.expires_on"), date_str)
        elif sub.current_period_end and sub.billing_period != "lifetime":
            date_str = sub.current_period_end.strftime("%d/%m/%Y")
            self._add_row(layout, tr("auth.renews_on"), date_str)

    def _divider(self) -> QFrame:
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #222222; border: none;")
        return div

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
