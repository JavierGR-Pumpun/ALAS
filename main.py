"""
ALAS — Aerial LiDAR Analysis Software
Punto de entrada principal de la aplicación.

conda env create -f environment.yml || conda env update -f environment.yml; conda run -n alas python main.py
"""
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PDAL_DRIVER_PATH"] = ""   # fuerza PDAL a no buscar plugins con rutas non-ASCII
os.environ["LC_ALL"] = "C"            # locale ASCII puro — funciona en Mac, Linux y WSL
os.environ["LANG"] = "C"

import sys
from pathlib import Path

# Asegurar que el directorio raíz está en el path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def main():
    """Inicia la aplicación ALAS."""
    # Importar Qt antes que nada
    from PyQt6.QtWidgets import QApplication, QSplashScreen
    from PyQt6.QtGui import QPixmap, QFont, QColor, QPainter
    from PyQt6.QtCore import Qt, QTimer, QCoreApplication

    # --- Performance and Graphics fixes for Windows ---
    if sys.platform == "win32":
        # Forzar el uso de OpenGL de escritorio en lugar de ANGLE (Direct3D)
        # Esto es vital para que VTK/PyVista funcione con aceleración real en Windows
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        
        # Variables de entorno adicionales para asegurar el backend de OpenGL
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

    # Fondo gradiente
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

    # --- Splash update ---
    splash.showMessage(
        "Cargando módulos...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
        QColor("#c0c0d0")
    )
    app.processEvents()

    # --- Create main window ---
    from app.ui.main_window import MainWindow
    window = MainWindow()

    splash.showMessage(
        "Listo",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
        QColor("#555555")
    )
    app.processEvents()

    # --- Show window, close splash ---
    QTimer.singleShot(800, lambda: _show_window(window, splash))

    sys.exit(app.exec())


def _show_window(window, splash):
    """Muestra la ventana principal y cierra el splash."""
    window.show()
    splash.finish(window)


if __name__ == "__main__":
    main()
