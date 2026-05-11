"""
ALAS — Base Analysis Tab
Shared base class and history-dialog helper used by every analysis tab widget.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QMessageBox,
    QDialog, QHBoxLayout, QListWidget, QListWidgetItem,
    QFileDialog, QInputDialog, QMainWindow,
)
from PyQt6.QtCore import Qt, QThreadPool

from app.core.layer_manager import LayerManager
from app.core.raster_layer import RasterLayer
from app.i18n import tr
from app.logger import get_logger
from app.processing.workers import ProcessingWorker
from app.ui.widgets import LoadingOverlay

logger = get_logger("ui.analysis_tab")


# ---------------------------------------------------------------------------
# History dialog (shared by all tabs)
# ---------------------------------------------------------------------------

def show_history_dialog(
    parent_widget: QWidget,
    main_window: QMainWindow,
    *,
    history_attr: str,
    tab_type: str,
    history_dialog_attr: str,
    pdf_title_key: str,
    source_label_key: str,
    results_window_class,
):
    """
    Build and display the history dialog for any analysis tab.

    Parameters
    ----------
    parent_widget        : the tab widget (used as dialog parent)
    main_window          : top-level QMainWindow that owns the history list
    history_attr         : name of the list attribute on main_window
    tab_type             : 'geomorphology' | 'hydrology' | 'vegetation' | 'multitemporal'
    history_dialog_attr  : name of the open-dialog tracker attribute on main_window
    pdf_title_key        : i18n key for the PDF title
    source_label_key     : i18n key for the source-layer metadata label
    results_window_class : AnalysisResultsWindow subclass to open results in
    """
    history = getattr(main_window, history_attr, [])
    if not history:
        QMessageBox.information(
            parent_widget,
            tr(f"{tab_type}.history"),
            tr(f"{tab_type}.no_history"),
        )
        return

    existing = getattr(main_window, history_dialog_attr, None)
    if existing is not None:
        try:
            existing.close()
        except RuntimeError:
            pass

    dlg = QDialog(parent_widget)
    dlg.setWindowTitle(tr(f"{tab_type}.history_title"))
    dlg.setMinimumSize(400, 300)
    dlg.setWindowFlags(Qt.WindowType.Window)
    dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    setattr(main_window, history_dialog_attr, dlg)

    layout = QVBoxLayout(dlg)

    list_widget = QListWidget()
    for i, item in enumerate(history):
        n = len(item["results"])
        text = (
            f"[{item['timestamp']}] {tr(source_label_key)} {item['layer']} "
            f"({n} {tr('analysis.history_layers')})"
        )
        lw_item = QListWidgetItem(text)
        lw_item.setData(Qt.ItemDataRole.UserRole, i)
        list_widget.addItem(lw_item)
    layout.addWidget(list_widget)

    btn_row = QHBoxLayout()

    # Open
    btn_open = QPushButton(tr("analysis.view_results"))

    def on_open():
        sel = list_widget.currentItem()
        if not sel:
            return
        idx = sel.data(Qt.ItemDataRole.UserRole)
        res = history[idx]["results"]
        win = results_window_class(res, main_window)
        win.setWindowFlags(Qt.WindowType.Window)
        win.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        attr = f"_{tab_type}_result_windows"
        if not hasattr(main_window, attr):
            setattr(main_window, attr, [])
        getattr(main_window, attr).append(win)
        win.show()

    btn_open.clicked.connect(on_open)
    btn_row.addWidget(btn_open)

    # Export PDF
    btn_pdf = QPushButton(tr("hydro.export_pdf"))

    def on_export_pdf():
        sel = list_widget.currentItem()
        if not sel:
            return
        idx = sel.data(Qt.ItemDataRole.UserRole)
        item = history[idx]
        res = item["results"]

        path, _ = QFileDialog.getSaveFileName(
            dlg,
            tr("export.dialog_title"),
            f"{tab_type}_analysis_{item['timestamp'].replace(':', '-')}.pdf",
            f"{tr('export.files_filter')} (*.pdf)",
        )
        if not path:
            return

        from app.processing.exporters import export_pdf_report

        metadata = {
            tr(source_label_key): item["layer"],
            tr("hydro.timestamp"): item["timestamp"],
            tr("analysis.history_layers"): str(len(res)),
        }
        stats = _collect_statistics(res)
        analysis_results, _tmp = results_window_class.render_for_pdf(res)
        export_pdf_report(tr(pdf_title_key), metadata, stats, [], path,
                          analysis_results=analysis_results)
        QMessageBox.information(
            dlg, tr("export.success"), f"{tr('export.exported_message')} {path}"
        )

    btn_pdf.clicked.connect(on_export_pdf)
    btn_row.addWidget(btn_pdf)

    # Save to reports
    btn_save = QPushButton(tr("hydro.save_to_reports"))

    def on_save():
        sel = list_widget.currentItem()
        if not sel:
            return
        user = getattr(main_window, "_current_user", None)
        if user is None:
            QMessageBox.warning(dlg, tr("reports.title"), tr("reports.no_user"))
            return

        idx = sel.data(Qt.ItemDataRole.UserRole)
        item = history[idx]
        res = item["results"]

        title, ok = QInputDialog.getText(
            dlg,
            tr("reports.title_input"),
            tr("reports.save_title_prompt"),
            text=f"{tr(pdf_title_key)} {item['timestamp']}",
        )
        if not ok or not title.strip():
            return

        import pathlib
        reports_dir = pathlib.Path.home() / ".alas" / "reports" / str(user.id)
        reports_dir.mkdir(parents=True, exist_ok=True)
        safe_ts = item["timestamp"].replace(":", "-")
        pdf_path = reports_dir / f"{tab_type}_{safe_ts}.pdf"

        from app.processing.exporters import export_pdf_report

        metadata = {
            tr(source_label_key): item["layer"],
            tr("hydro.timestamp"): item["timestamp"],
            tr("analysis.history_layers"): str(len(res)),
        }
        stats = _collect_statistics(res)
        analysis_results, _tmp = results_window_class.render_for_pdf(res)

        try:
            export_pdf_report(title.strip(), metadata, stats, [], str(pdf_path),
                              analysis_results=analysis_results)
        except Exception as e:
            QMessageBox.critical(dlg, tr("reports.title"), str(e))
            return

        from app.auth.reports_service import save_report

        result = save_report(user.id, title.strip(), str(pdf_path))
        if isinstance(result, str):
            QMessageBox.critical(dlg, tr("reports.title"), tr("reports.error_save"))
            return

        QMessageBox.information(dlg, tr("reports.saved"), tr("reports.saved_msg"))

    btn_save.clicked.connect(on_save)
    btn_row.addWidget(btn_save)

    layout.addLayout(btn_row)
    dlg.show()
    dlg.raise_()
    dlg.activateWindow()


def _collect_statistics(results: dict) -> dict:
    stats = {}
    for layer_type, raster_layer in results.items():
        if hasattr(raster_layer, "statistics"):
            for key, value in raster_layer.statistics().items():
                stats[f"{layer_type} - {key}"] = value
    return stats


# ---------------------------------------------------------------------------
# Base tab widget
# ---------------------------------------------------------------------------

class BaseAnalysisTab(QWidget):
    """
    Abstract base for all four analysis tab widgets.

    Subclasses must implement:
        TAB_TYPE          : str  — used for i18n keys and history attr names
        _build_ui()       : build all child widgets; called from __init__
        _get_run_btn()    : return the primary run QPushButton
        _get_view_btn()   : return the "View Results" QPushButton
        _get_hist_btn()   : return the "History" QPushButton
        _run()            : slot connected to the run button
        _show_history()   : slot connected to the history button
    """

    TAB_TYPE: str = ""

    def __init__(self, layer_manager: LayerManager, main_window: QMainWindow, parent=None):
        super().__init__(parent)
        self.layer_manager = layer_manager
        self.main_window = main_window
        self._loading_overlay = LoadingOverlay(self)
        self._loading_overlay.hide()
        self._build_ui()

    # ------------------------------------------------------------------
    # Subclass interface
    # ------------------------------------------------------------------

    def _build_ui(self):
        raise NotImplementedError

    def _get_run_btn(self) -> QPushButton:
        raise NotImplementedError

    def _get_view_btn(self) -> QPushButton:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _show_loading(self):
        self._get_run_btn().setEnabled(False)
        self._loading_overlay.show_loading()

    def _hide_loading(self):
        self._loading_overlay.hide_loading()
        self._get_run_btn().setEnabled(True)

    def _run_worker(self, compute_fn, result_slot, extra_error_fn=None):
        def on_error(e):
            self._hide_loading()
            QMessageBox.critical(self, tr("crs.error"), e)
            if extra_error_fn:
                extra_error_fn(e)

        worker = ProcessingWorker(compute_fn)
        worker.signals.result.connect(result_slot)
        worker.signals.error.connect(on_error)
        worker.signals.finished.connect(self._hide_loading)
        QThreadPool.globalInstance().start(worker)

    def _append_history(self, layer_name: str, results: dict):
        import datetime
        attr = f"_{self.TAB_TYPE}_history"
        if not hasattr(self.main_window, attr):
            setattr(self.main_window, attr, [])
        getattr(self.main_window, attr).append({
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
            "layer": layer_name,
            "results": results,
        })

    def _open_results_window(self, results: dict, results_window_class):
        win = results_window_class(results, self.main_window)
        win.setWindowFlags(Qt.WindowType.Window)
        win.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        attr = f"_{self.TAB_TYPE}_result_windows"
        if not hasattr(self.main_window, attr):
            setattr(self.main_window, attr, [])
        getattr(self.main_window, attr).append(win)
        win.show()