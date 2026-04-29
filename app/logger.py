"""
ALAS — Logging
Sistema de logging con rotación de archivos y emisión de señales Qt.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from PyQt6.QtCore import QObject, pyqtSignal
from app.config import USER_CONFIG_DIR, APP_NAME


class LogSignalEmitter(QObject):
    """Emite señales Qt con cada mensaje de log."""
    log_message = pyqtSignal(str, str)  # (level, message)


class QtLogHandler(logging.Handler):
    """Handler que emite señales Qt."""
    def __init__(self, emitter: LogSignalEmitter):
        super().__init__()
        self.emitter = emitter

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self.emitter.log_message.emit(record.levelname, msg)
        except Exception:
            self.handleError(record)


_log_emitter = LogSignalEmitter()


def get_log_emitter() -> LogSignalEmitter:
    return _log_emitter


def setup_logging(level: int = logging.DEBUG) -> logging.Logger:
    log_dir = USER_CONFIG_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "alas.log"

    logger = logging.getLogger(APP_NAME)
    logger.setLevel(level)
    logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s.%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fmt_short = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt_short)
    logger.addHandler(console)

    fh = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    qt_handler = QtLogHandler(_log_emitter)
    qt_handler.setLevel(logging.INFO)
    qt_handler.setFormatter(fmt_short)
    logger.addHandler(qt_handler)

    logger.info("Logging inicializado")
    return logger


def get_logger(name: str = "") -> logging.Logger:
    base = APP_NAME
    if name:
        return logging.getLogger(f"{base}.{name}")
    return logging.getLogger(base)
