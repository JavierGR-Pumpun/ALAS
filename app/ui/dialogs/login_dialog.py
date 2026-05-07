"""
ALAS — Login / Register Dialog
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.login_dialog")


class LoginDialog(QDialog):
    """Modal login/register gate. self.user and self.session_token are set on accept()."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user = None
        self.session_token = None

        self.setWindowTitle("ALAS")
        self.setFixedSize(420, 500)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        self._build_ui()

    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(0)

        title = QLabel("ALAS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        title.setObjectName("heading")
        root.addWidget(title)

        sub = QLabel("Aerial LiDAR Analysis Software")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setObjectName("muted")
        root.addWidget(sub)

        root.addSpacing(24)

        self._tabs = QTabWidget()
        root.addWidget(self._tabs)

        self._build_login_tab()
        self._build_register_tab()

    def _field(self, placeholder: str, password: bool = False) -> QLineEdit:
        w = QLineEdit()
        w.setPlaceholderText(placeholder)
        if password:
            w.setEchoMode(QLineEdit.EchoMode.Password)
        w.setFixedHeight(38)
        return w

    def _build_login_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(10)

        self._login_email = self._field(tr("auth.email"))
        self._login_password = self._field(tr("auth.password"), password=True)
        layout.addWidget(self._login_email)
        layout.addWidget(self._login_password)

        self._remember_me = QCheckBox(tr("auth.remember_me"))
        layout.addWidget(self._remember_me)

        layout.addSpacing(4)

        self._login_error = QLabel("")
        self._login_error.setObjectName("errorLabel")
        self._login_error.setWordWrap(True)
        self._login_error.setVisible(False)
        layout.addWidget(self._login_error)

        btn = QPushButton(tr("auth.login"))
        btn.setFixedHeight(40)
        btn.setObjectName("primary")
        btn.clicked.connect(self._do_login)
        layout.addWidget(btn)

        layout.addStretch()
        self._tabs.addTab(tab, tr("auth.login"))

    def _build_register_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(10)

        self._reg_name = self._field(tr("auth.full_name"))
        self._reg_email = self._field(tr("auth.email"))
        self._reg_phone = self._field(tr("auth.phone"))
        self._reg_password = self._field(tr("auth.password"), password=True)
        self._reg_confirm = self._field(tr("auth.confirm_password"), password=True)

        for w in (self._reg_name, self._reg_email, self._reg_phone,
                  self._reg_password, self._reg_confirm):
            layout.addWidget(w)

        self._reg_error = QLabel("")
        self._reg_error.setObjectName("errorLabel")
        self._reg_error.setWordWrap(True)
        self._reg_error.setVisible(False)
        layout.addWidget(self._reg_error)

        btn = QPushButton(tr("auth.register"))
        btn.setFixedHeight(40)
        btn.setObjectName("primary")
        btn.clicked.connect(self._do_register)
        layout.addWidget(btn)

        layout.addStretch()
        self._tabs.addTab(tab, tr("auth.register"))

    # ------------------------------------------------------------------

    def _do_login(self):
        from app.auth.service import login as auth_login

        self._login_error.setVisible(False)
        email = self._login_email.text().strip()
        password = self._login_password.text()

        if not email or not password:
            self._show_error(self._login_error, tr("auth.error_fill_all_fields"))
            return

        result = auth_login(email, password, remember_me=self._remember_me.isChecked())
        if isinstance(result, str):
            self._show_error(self._login_error, tr(result))
            return

        self.user, self.session_token = result
        logger.info(f"Login OK: {email}")
        self.accept()

    def _do_register(self):
        from app.auth.service import register as auth_register

        self._reg_error.setVisible(False)
        name = self._reg_name.text().strip()
        email = self._reg_email.text().strip()
        phone = self._reg_phone.text().strip()
        password = self._reg_password.text()
        confirm = self._reg_confirm.text()

        if not name or not email or not password or not confirm:
            self._show_error(self._reg_error, tr("auth.error_fill_all_fields"))
            return
        if password != confirm:
            self._show_error(self._reg_error, tr("auth.error_passwords_no_match"))
            return
        if len(password) < 8:
            self._show_error(self._reg_error, tr("auth.error_password_too_short"))
            return

        result = auth_register(name, email, phone, password)
        if isinstance(result, str):
            self._show_error(self._reg_error, tr(result))
            return

        self.user = result
        self.session_token = None
        logger.info(f"Register OK: {email}")
        self.accept()

    def _show_error(self, label: QLabel, message: str):
        label.setText(message)
        label.setVisible(True)
