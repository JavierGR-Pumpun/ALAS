"""
ALAS — Aerial LiDAR Analysis Software
Main entry point of the application.

conda env create -f environment.yml || conda env update -f environment.yml; conda run -n alas python main.py
"""
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PDAL_DRIVER_PATH"] = ""   # force PDAL to not search for plugins with non-ASCII paths
os.environ["LC_ALL"] = "C"            # pure ASCII locale — works on Mac, Linux and WSL
os.environ["LANG"] = "C"

import sys
from pathlib import Path

# Ensure the root directory is in the path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def main():
    """Start the ALAS application."""
    # Import Qt first
    from PyQt6.QtWidgets import QApplication, QSplashScreen
    from PyQt6.QtGui import QPixmap, QFont, QColor, QPainter
    from PyQt6.QtCore import Qt, QTimer, QCoreApplication

    # --- Performance and Graphics fixes for Windows ---
    if sys.platform == "win32":
        # Force the use of desktop OpenGL instead of ANGLE (Direct3D)
        # This is vital for VTK/PyVista to work with real acceleration on Windows
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        
        # Additional environment variables to ensure the OpenGL backend
        os.environ["QSG_RHI_BACKEND"] = "opengl"
        os.environ["PYVISTA_OFF_SCREEN"] = "false"

    app = QApplication(sys.argv)
    app.setApplicationName("ALAS")
    app.setOrganizationName("ALAS Project")
    app.setApplicationVersion("1.0.0")

    # --- Splash Screen ---
    splash_pixmap = QPixmap(600, 380)
    splash_pixmap.fill(QColor("#000000"))

    painter = QPainter(splash_pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Gradient background
    from PyQt6.QtGui import QLinearGradient
    gradient = QLinearGradient(0, 0, 600, 380)
    gradient.setColorAt(0, QColor("#000000"))
    gradient.setColorAt(1, QColor("#050505"))
    painter.fillRect(splash_pixmap.rect(), gradient)

    # Accent line
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#555555"))
    painter.drawRect(0, 340, 600, 4)

    # Title
    font_title = QFont("Segoe UI", 48, QFont.Weight.Bold)
    painter.setFont(font_title)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(splash_pixmap.rect().adjusted(0, 60, 0, -100),
                     Qt.AlignmentFlag.AlignHCenter, "ALAS")

    # Subtitle
    font_sub = QFont("Segoe UI", 14)
    painter.setFont(font_sub)
    painter.setPen(QColor("#888888"))
    painter.drawText(splash_pixmap.rect().adjusted(0, 140, 0, -80),
                     Qt.AlignmentFlag.AlignHCenter,
                     "Aerial LiDAR Analysis Software")

    # Version
    font_ver = QFont("Segoe UI", 11)
    painter.setFont(font_ver)
    painter.setPen(QColor("#888898"))
    painter.drawText(splash_pixmap.rect().adjusted(0, 180, 0, -60),
                     Qt.AlignmentFlag.AlignHCenter,
                     "v1.0.0")


    painter.end()

    splash = QSplashScreen(splash_pixmap)
    splash.show()
    app.processEvents()

    # --- Apply dark theme ---
    from app.config import STYLES_DIR
    theme_path = STYLES_DIR / "dark_theme.qss"
    if theme_path.exists():
        with open(theme_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    # --- Setup logging ---
    from app.logger import setup_logging
    logger = setup_logging()

    # --- Apply saved language before any tr() calls ---
    from app.core.project import UserPreferences
    from app.i18n import set_language, tr
    _startup_prefs = UserPreferences()
    set_language(_startup_prefs.get("language", "es"))

    # --- Init DB (create tables if missing) ---
    from app.auth.db import init_db
    try:
        init_db()
    except Exception as _db_err:
        logger.warning(f"DB init skipped: {_db_err}")

    # --- Splash update ---
    splash.showMessage(
        tr("splash.loading_modules"),
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
        QColor("#c0c0d0")
    )
    app.processEvents()

    # --- Check saved session (skip login if token is still valid) ---
    from app.auth.service import verify_session
    _saved_token = _startup_prefs.get("session_token")
    _auto_user = verify_session(_saved_token) if _saved_token else None
    _session_token = _saved_token if _auto_user else None

    # --- Create main window (shows login modal on first paint if not authed) ---
    from app.ui.main_window import MainWindow
    window = MainWindow(user=_auto_user, session_token=_session_token)

    splash.showMessage(
        tr("splash.ready"),
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
        QColor("#555555")
    )
    app.processEvents()

    # --- Show window, close splash ---
    QTimer.singleShot(800, lambda: _show_window(window, splash))

    sys.exit(app.exec())


def _show_window(window, splash):
    """Show the main window and close the splash."""
    window.show()
    splash.finish(window)


if __name__ == "__main__":
    main()
