"""
ALAS — Processing Workers
Base classes para ejecutar tareas pesadas en hilos separados.
"""

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot


class ProcessingWorkerSignals(QObject):
    """Señales emitidas por los workers de procesamiento."""
    started = pyqtSignal()
    progress = pyqtSignal(int)          # 0-100
    status = pyqtSignal(str)            # mensaje de estado
    result = pyqtSignal(object)         # resultado del procesamiento
    error = pyqtSignal(str)             # mensaje de error
    finished = pyqtSignal()


class ProcessingWorker(QRunnable):
    """Worker base para tareas de procesamiento en background."""

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = ProcessingWorkerSignals()
        self.setAutoDelete(True)

    @pyqtSlot()
    def run(self):
        self.signals.started.emit()
        try:
            result = self.func(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


class FileLoadWorker(ProcessingWorker):
    """Worker específico para carga de archivos."""

    def __init__(self, file_path: str, loader_func, **kwargs):
        super().__init__(loader_func, file_path, **kwargs)
        self.file_path = file_path


class ProgressCallback:
    """Callback para reportar progreso desde funciones de procesamiento."""

    def __init__(self, signals: ProcessingWorkerSignals = None):
        self.signals = signals

    def update(self, progress: int, message: str = ""):
        if self.signals:
            self.signals.progress.emit(progress)
            if message:
                self.signals.status.emit(message)

    def __call__(self, progress: int, message: str = ""):
        self.update(progress, message)
