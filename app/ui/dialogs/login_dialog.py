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

        self._login_btn = QPushButton(tr("auth.login"))
        self._login_btn.setFixedHeight(40)
        self._login_btn.setObjectName("primary")
        self._login_btn.clicked.connect(self._do_login)
        layout.addWidget(self._login_btn)

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

        self._register_btn = QPushButton(tr("auth.register"))
        self._register_btn.setFixedHeight(40)
        self._register_btn.setObjectName("primary")
        self._register_btn.clicked.connect(self._do_register)
        layout.addWidget(self._register_btn)

        layout.addStretch()
        self._tabs.addTab(tab, tr("auth.register"))

    # ------------------------------------------------------------------

    def _set_login_enabled(self, enabled: bool):
        self._login_email.setEnabled(enabled)
        self._login_password.setEnabled(enabled)
        self._remember_me.setEnabled(enabled)
        self._login_btn.setEnabled(enabled)

    def _set_register_enabled(self, enabled: bool):
        self._reg_name.setEnabled(enabled)
        self._reg_email.setEnabled(enabled)
        self._reg_phone.setEnabled(enabled)
        self._reg_password.setEnabled(enabled)
        self._reg_confirm.setEnabled(enabled)
        self._register_btn.setEnabled(enabled)

    def _do_login(self):
        from app.auth.service import login as auth_login
        from app.processing.workers import ProcessingWorker
        from PyQt6.QtCore import QThreadPool

        self._login_error.setVisible(False)
        email = self._login_email.text().strip()
        password = self._login_password.text()

        if not email or not password:
            self._show_error(self._login_error, tr("auth.error_fill_all_fields"))
            return

        remember_me = self._remember_me.isChecked()
        self._set_login_enabled(False)

        def _do():
            return auth_login(email, password, remember_me=remember_me)

        def _on_result(result):
            if isinstance(result, str):
                self._show_error(self._login_error, tr(result))
                self._set_login_enabled(True)
                return
            self.user, self.session_token = result
            logger.info(f"Login OK: {email}")
            self.accept()

        def _on_error(e):
            self._show_error(self._login_error, str(e))
            self._set_login_enabled(True)

        worker = ProcessingWorker(_do)
        worker.signals.result.connect(_on_result)
        worker.signals.error.connect(_on_error)
        QThreadPool.globalInstance().start(worker)

    def _do_register(self):
        from app.auth.service import register as auth_register
        from app.processing.workers import ProcessingWorker
        from PyQt6.QtCore import QThreadPool

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

        self._set_register_enabled(False)

        def _do():
            return auth_register(name, email, phone, password)

        def _on_result(result):
            if isinstance(result, str):
                self._show_error(self._reg_error, tr(result))
                self._set_register_enabled(True)
                return
            self.user = result
            self.session_token = None
            logger.info(f"Register OK: {email}")
            self.accept()

        def _on_error(e):
            self._show_error(self._reg_error, str(e))
            self._set_register_enabled(True)

        worker = ProcessingWorker(_do)
        worker.signals.result.connect(_on_result)
        worker.signals.error.connect(_on_error)
        QThreadPool.globalInstance().start(worker)

    def _show_error(self, label: QLabel, message: str):
        label.setText(message)
        label.setVisible(True)
