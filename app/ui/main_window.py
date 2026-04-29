"""
ALAS — Main Window
Ventana principal: viewport 3D central, paneles dock, menú y toolbar.
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QFileDialog, QMessageBox,
    QProgressBar, QLabel, QWidget, QVBoxLayout, QApplication,
    QTabWidget, QMenuBar, QMenu, QToolBar, QStatusBar
)
from PyQt6.QtCore import Qt, QSize, QThreadPool, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QIcon

from app.core.project import Project, UserPreferences
from app.core.layer_manager import LayerManager
from app.core.point_cloud import PointCloudData
from app.core.raster_layer import RasterLayer
from app.ui.viewport.viewport_3d import Viewport3D
from app.ui.panels.layer_panel import LayerPanel
from app.ui.panels.properties_panel import PropertiesPanel
from app.ui.panels.tools_panel import ToolsPanel
from app.ui.panels.statistics_panel import StatisticsPanel
from app.ui.panels.log_panel import LogPanel
from app.processing.workers import FileLoadWorker, ProcessingWorkerSignals
from app.config import (
    APP_NAME, APP_FULL_NAME, APP_VERSION,
    POINT_CLOUD_FILTER, RASTER_FILTER, POINT_CLOUD_EXTENSIONS,
    RASTER_EXTENSIONS
)
from app.i18n import tr, set_language, get_language
from app.logger import get_logger

logger = get_logger("ui.main_window")


class MainWindow(QMainWindow):
    """Ventana principal de ALAS."""

    def __init__(self):
        super().__init__()

        # Core objects
        self.project = Project()
        self.preferences = UserPreferences()
        self.layer_manager = LayerManager(self)
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)

        # Apply saved language
        saved_lang = self.preferences.get("language", "es")
        set_language(saved_lang)

        # Setup UI
        self._setup_window()
        self._setup_viewport()
        self._setup_panels()
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_status_bar()
        self._connect_signals()

        # Restore geometry
        self._restore_state()

        logger.info(f"{APP_NAME} v{APP_VERSION} iniciado")

    # ==================================================================
    # Window setup
    # ==================================================================

    def _setup_window(self):
        self.setWindowTitle(f"{APP_NAME} — {APP_FULL_NAME}")
        self.setMinimumSize(1200, 800)
        self.resize(1600, 1000)
        self.setDockOptions(
            QMainWindow.DockOption.AllowTabbedDocks |
            QMainWindow.DockOption.AllowNestedDocks |
            QMainWindow.DockOption.AnimatedDocks
        )

    # ==================================================================
    # Viewport (central widget)
    # ==================================================================

    def _setup_viewport(self):
        self.viewport = Viewport3D(self)
        self.setCentralWidget(self.viewport)

    # ==================================================================
    # Dock Panels
    # ==================================================================

    def _setup_panels(self):
        # --- Left: Layers ---
        self.layer_panel = LayerPanel(self.layer_manager, self)
        dock_layers = QDockWidget(tr("panel.layers"), self)
        dock_layers.setWidget(self.layer_panel)
        dock_layers.setMinimumWidth(220)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock_layers)

        # --- Right: Properties + Tools (tabbed) ---
        right_tabs = QTabWidget()

        self.properties_panel = PropertiesPanel(self.layer_manager, self)
        right_tabs.addTab(self.properties_panel, tr("panel.properties"))

        self.tools_panel = ToolsPanel(self)
        right_tabs.addTab(self.tools_panel, tr("panel.tools"))

        self.statistics_panel = StatisticsPanel(self.layer_manager, self)
        right_tabs.addTab(self.statistics_panel, tr("panel.statistics"))

        dock_right = QDockWidget(tr("panel.properties"), self)
        dock_right.setWidget(right_tabs)
        dock_right.setMinimumWidth(280)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_right)

        # --- Bottom: Log ---
        self.log_panel = LogPanel(self)
        dock_log = QDockWidget(tr("panel.log"), self)
        dock_log.setWidget(self.log_panel)
        dock_log.setMaximumHeight(200)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock_log)

    # ==================================================================
    # Menu Bar
    # ==================================================================

    def _setup_menu_bar(self):
        menubar = self.menuBar()

        # --- Archivo ---
        menu_file = menubar.addMenu(tr("menu.file"))

        act_open = QAction(tr("action.open"), self)
        act_open.setShortcut(QKeySequence("Ctrl+O"))
        act_open.triggered.connect(self._open_file)
        menu_file.addAction(act_open)

        act_open_multi = QAction(tr("action.open_multiple"), self)
        act_open_multi.setShortcut(QKeySequence("Ctrl+Shift+O"))
        act_open_multi.triggered.connect(self._open_multiple_files)
        menu_file.addAction(act_open_multi)

        menu_file.addSeparator()

        act_save = QAction(tr("action.save_project"), self)
        act_save.setShortcut(QKeySequence("Ctrl+S"))
        act_save.triggered.connect(self._save_project)
        menu_file.addAction(act_save)

        act_load = QAction(tr("action.load_project"), self)
        act_load.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_load.triggered.connect(self._load_project)
        menu_file.addAction(act_load)

        menu_file.addSeparator()

        act_export = QAction(tr("action.export"), self)
        act_export.setShortcut(QKeySequence("Ctrl+E"))
        act_export.triggered.connect(self._show_export_dialog)
        menu_file.addAction(act_export)

        menu_file.addSeparator()

        act_exit = QAction(tr("action.exit"), self)
        act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(self.close)
        menu_file.addAction(act_exit)

        # --- Vista ---
        menu_view = menubar.addMenu(tr("menu.view"))

        act_reset = QAction(tr("action.reset_view"), self)
        act_reset.setShortcut(QKeySequence("R"))
        act_reset.triggered.connect(self.viewport.reset_camera)
        menu_view.addAction(act_reset)

        act_top = QAction(tr("action.top_view"), self)
        act_top.setShortcut(QKeySequence("T"))
        act_top.triggered.connect(self.viewport.set_view_top)
        menu_view.addAction(act_top)

        act_front = QAction(tr("action.front_view"), self)
        act_front.setShortcut(QKeySequence("F"))
        act_front.triggered.connect(self.viewport.set_view_front)
        menu_view.addAction(act_front)

        act_side = QAction(tr("action.side_view"), self)
        act_side.setShortcut(QKeySequence("S"))
        act_side.triggered.connect(self.viewport.set_view_side)
        menu_view.addAction(act_side)

        menu_view.addSeparator()

        # Language submenu
        menu_lang = menu_view.addMenu("🌐 Idioma / Language")
        act_es = QAction("Español", self)
        act_es.triggered.connect(lambda: self._change_language("es"))
        menu_lang.addAction(act_es)
        act_en = QAction("English", self)
        act_en.triggered.connect(lambda: self._change_language("en"))
        menu_lang.addAction(act_en)

        # --- Procesamiento ---
        menu_proc = menubar.addMenu(tr("menu.process"))

        act_classify = QAction(tr("action.classify"), self)
        act_classify.triggered.connect(self._show_classification_dialog)
        menu_proc.addAction(act_classify)

        act_dem = QAction(tr("action.generate_dem"), self)
        act_dem.triggered.connect(self._show_dem_dialog)
        menu_proc.addAction(act_dem)

        menu_proc.addSeparator()

        act_merge = QAction(tr("action.merge_tiles"), self)
        act_merge.triggered.connect(self._merge_tiles)
        menu_proc.addAction(act_merge)

        act_noise = QAction(tr("action.filter_noise"), self)
        act_noise.triggered.connect(self._filter_noise)
        menu_proc.addAction(act_noise)

        act_reproj = QAction(tr("action.reproject"), self)
        act_reproj.triggered.connect(self._show_reproject_dialog)
        menu_proc.addAction(act_reproj)

        act_decimate = QAction(tr("action.decimate"), self)
        act_decimate.triggered.connect(self._decimate_cloud)
        menu_proc.addAction(act_decimate)

        # --- Análisis ---
        menu_analysis = menubar.addMenu(tr("menu.analysis"))

        act_geomorph = QAction(tr("action.geomorphology"), self)
        act_geomorph.triggered.connect(self._show_geomorphology_dialog)
        menu_analysis.addAction(act_geomorph)

        act_hydro = QAction(tr("action.hydrology"), self)
        act_hydro.triggered.connect(self._show_hydrology_dialog)
        menu_analysis.addAction(act_hydro)

        act_veg = QAction(tr("action.vegetation"), self)
        act_veg.triggered.connect(self._show_vegetation_dialog)
        menu_analysis.addAction(act_veg)

        act_multi = QAction(tr("action.multitemporal"), self)
        act_multi.triggered.connect(self._show_multitemporal_dialog)
        menu_analysis.addAction(act_multi)

        # --- Herramientas ---
        menu_tools = menubar.addMenu(tr("menu.tools"))

        act_profile = QAction(tr("action.profile"), self)
        act_profile.triggered.connect(self._start_profile_tool)
        menu_tools.addAction(act_profile)

        act_dist = QAction(tr("action.distance"), self)
        act_dist.triggered.connect(self._start_distance_tool)
        menu_tools.addAction(act_dist)

        act_area = QAction(tr("action.area"), self)
        act_area.triggered.connect(self._start_area_tool)
        menu_tools.addAction(act_area)

        act_vol = QAction(tr("action.volume"), self)
        act_vol.triggered.connect(self._start_volume_tool)
        menu_tools.addAction(act_vol)

        # --- Ayuda ---
        menu_help = menubar.addMenu(tr("menu.help"))
        act_about = QAction(tr("dialog.about_title"), self)
        act_about.triggered.connect(self._show_about)
        menu_help.addAction(act_about)

    # ==================================================================
    # Toolbar
    # ==================================================================

    def _setup_toolbar(self):
        toolbar = QToolBar("Principal", self)
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # File actions
        toolbar.addAction("📂 " + tr("action.open").replace("...", ""), self._open_file)
        toolbar.addSeparator()

        # View actions
        toolbar.addAction("⟲ Reset", self.viewport.reset_camera)
        toolbar.addAction("⬆ Top", self.viewport.set_view_top)
        toolbar.addSeparator()

        # Processing actions
        toolbar.addAction("🏔 " + tr("action.classify").replace("...", ""), self._show_classification_dialog)
        toolbar.addAction("📐 DEM", self._show_dem_dialog)
        toolbar.addSeparator()

        # Analysis
        toolbar.addAction("📊 " + tr("action.geomorphology").replace("...", ""), self._show_geomorphology_dialog)
        toolbar.addAction("💧 " + tr("action.hydrology").replace("...", ""), self._show_hydrology_dialog)
        toolbar.addAction("🌲 " + tr("action.vegetation").replace("...", ""), self._show_vegetation_dialog)
        toolbar.addSeparator()

        # Tools
        toolbar.addAction("📏 " + tr("action.profile"), self._start_profile_tool)
        toolbar.addSeparator()

        # Export
        toolbar.addAction("💾 " + tr("action.export").replace("...", ""), self._show_export_dialog)

    # ==================================================================
    # Status Bar
    # ==================================================================

    def _setup_status_bar(self):
        self.statusBar().setStyleSheet("QStatusBar { font-size: 12px; }")

        self._status_label = QLabel(tr("status.ready"))
        self.statusBar().addWidget(self._status_label, 1)

        self._crs_label = QLabel(tr("status.no_crs"))
        self._crs_label.setStyleSheet("color: #a855f7; font-weight: 600;")
        self.statusBar().addPermanentWidget(self._crs_label)

        self._points_label = QLabel("0 " + tr("status.points"))
        self.statusBar().addPermanentWidget(self._points_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedWidth(200)
        self._progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self._progress_bar)

    def _update_status(self, message: str):
        self._status_label.setText(message)

    def _update_crs_display(self, epsg: int = None):
        if epsg:
            self._crs_label.setText(f"EPSG:{epsg}")
        else:
            self._crs_label.setText(tr("status.no_crs"))

    def _update_points_display(self):
        total = sum(
            e.layer.point_count for e in self.layer_manager.get_all_entries()
            if e.is_point_cloud
        )
        self._points_label.setText(f"{total:,} {tr('status.points')}")

    def _show_progress(self, visible: bool, value: int = 0):
        self._progress_bar.setVisible(visible)
        self._progress_bar.setValue(value)

    # ==================================================================
    # Signal connections
    # ==================================================================

    def _connect_signals(self):
        # Tools panel
        self.tools_panel.point_size_changed.connect(self.viewport.set_point_size)
        self.tools_panel.colorize_mode_changed.connect(self._on_colorize_mode_changed)
        self.tools_panel.view_reset_requested.connect(self.viewport.reset_camera)
        self.tools_panel.view_top_requested.connect(self.viewport.set_view_top)
        self.tools_panel.view_front_requested.connect(self.viewport.set_view_front)
        self.tools_panel.view_side_requested.connect(self.viewport.set_view_side)

        # Layer panel
        self.layer_panel.zoom_to_layer_requested.connect(self._zoom_to_layer)
        self.layer_panel.export_layer_requested.connect(self._export_layer)

        # Layer manager
        self.layer_manager.layer_added.connect(lambda _: self._update_points_display())
        self.layer_manager.layer_removed.connect(lambda _: self._update_points_display())
        self.layer_manager.layer_visibility_changed.connect(self._on_visibility_changed)
        self.layer_manager.active_layer_changed.connect(self._on_active_layer_changed)

    # ==================================================================
    # File operations
    # ==================================================================

    def _open_file(self):
        last_dir = self.preferences.get("last_import_dir", "")
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("action.open"), last_dir,
            f"{POINT_CLOUD_FILTER};;{RASTER_FILTER}"
        )
        if file_path:
            self._load_file(file_path)

    def _open_multiple_files(self):
        last_dir = self.preferences.get("last_import_dir", "")
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, tr("action.open_multiple"), last_dir,
            POINT_CLOUD_FILTER
        )
        for fp in file_paths:
            self._load_file(fp)

    def _load_file(self, file_path: str):
        self.preferences.set("last_import_dir", str(Path(file_path).parent))
        self.preferences.add_recent_file(file_path)

        ext = Path(file_path).suffix.lower()
        self._update_status(tr("status.loading"))
        self._show_progress(True)

        try:
            if ext in POINT_CLOUD_EXTENSIONS:
                pc = PointCloudData.from_file(file_path)
                idx = self.layer_manager.add_layer(pc)
                self.viewport.display_point_cloud(pc)
                self.viewport.reset_camera()

                # CRS handling: leer del archivo, recordar
                if pc.crs_epsg:
                    self._update_crs_display(pc.crs_epsg)
                    self.preferences.last_crs = pc.crs_epsg
                elif not pc.crs_epsg:
                    self._update_crs_display(None)
                    self._prompt_crs_assignment(pc)

            elif ext in RASTER_EXTENSIONS:
                rl = RasterLayer.from_file(file_path)
                self.layer_manager.add_layer(rl)
                self.viewport.display_raster_surface(rl)
                self.viewport.reset_camera()

                if rl.crs_epsg:
                    self._update_crs_display(rl.crs_epsg)

            self._update_status(tr("success.loaded"))
            self.project.loaded_files.append(file_path)

        except Exception as e:
            logger.error(f"Error cargando {file_path}: {e}")
            QMessageBox.critical(self, tr("error.processing_failed"), str(e))
            self._update_status(tr("status.ready"))
        finally:
            self._show_progress(False)

    def _prompt_crs_assignment(self, pc: PointCloudData):
        """Si el archivo no tiene CRS, preguntar al usuario."""
        from PyQt6.QtWidgets import QInputDialog
        last_crs = self.preferences.last_crs
        default_text = str(last_crs) if last_crs else "25830"

        epsg_str, ok = QInputDialog.getText(
            self, tr("prop.crs"),
            f"{tr('error.no_crs')}\n\nIntroduce el código EPSG:",
            text=default_text,
        )
        if ok and epsg_str.strip().isdigit():
            epsg = int(epsg_str.strip())
            pc.crs_epsg = epsg
            try:
                from pyproj import CRS
                pc.crs_wkt = CRS.from_epsg(epsg).to_wkt()
            except Exception:
                pass
            self._update_crs_display(epsg)
            self.preferences.last_crs = epsg

    # ==================================================================
    # Project operations
    # ==================================================================

    def _save_project(self):
        last_dir = self.preferences.get("last_export_dir", "")
        path, _ = QFileDialog.getSaveFileName(
            self, tr("action.save_project"), last_dir,
            "Proyecto ALAS (*.alas)"
        )
        if path:
            self.project.save(path)
            self._update_status("Proyecto guardado")

    def _load_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("action.load_project"), "",
            "Proyecto ALAS (*.alas)"
        )
        if path:
            try:
                self.project = Project.load(path)
                self._update_status("Proyecto cargado")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    # ==================================================================
    # Viewport interactions
    # ==================================================================

    def _on_colorize_mode_changed(self, mode: str):
        entry = self.layer_manager.active_layer
        if entry and entry.is_point_cloud:
            self.viewport.update_colorization(entry.layer, mode)

    def _on_visibility_changed(self, index: int, visible: bool):
        entry = self.layer_manager.get_entry(index)
        if entry:
            self.viewport.set_layer_visibility(entry.name, visible)

    def _on_active_layer_changed(self, index: int):
        entry = self.layer_manager.get_entry(index)
        if entry and entry.is_point_cloud:
            self._update_crs_display(entry.layer.crs_epsg)
        elif entry and entry.is_raster:
            self._update_crs_display(entry.layer.crs_epsg)

    def _zoom_to_layer(self, index: int):
        entry = self.layer_manager.get_entry(index)
        if entry:
            if entry.is_point_cloud:
                self.viewport.zoom_to_bounds(entry.layer.bounds)
            elif entry.is_raster:
                self.viewport.zoom_to_bounds(entry.layer.bounds)
            self.viewport.reset_camera()

    # ==================================================================
    # Processing actions (stubs — implemented in dialogs)
    # ==================================================================

    def _show_classification_dialog(self):
        from app.ui.dialogs.classification_dialog import ClassificationDialog
        entry = self.layer_manager.active_layer
        if not entry or not entry.is_point_cloud:
            QMessageBox.information(self, "Info", "Selecciona una nube de puntos primero.")
            return
        dlg = ClassificationDialog(entry.layer, self)
        if dlg.exec():
            result = dlg.get_result()
            if result is not None:
                entry.layer.classification = result
                self.viewport.update_colorization(entry.layer, "classification")
                self._update_status(tr("success.classification_done"))

    def _show_dem_dialog(self):
        from app.ui.dialogs.dem_dialog import DEMDialog
        entry = self.layer_manager.active_layer
        if not entry or not entry.is_point_cloud:
            QMessageBox.information(self, "Info", "Selecciona una nube de puntos primero.")
            return
        dlg = DEMDialog(entry.layer, self)
        if dlg.exec():
            raster = dlg.get_result()
            if raster is not None:
                self.layer_manager.add_layer(raster)
                self.viewport.display_raster_surface(raster)
                self._update_status(tr("success.dem_generated"))

    def _show_geomorphology_dialog(self):
        from app.ui.dialogs.analysis_dialog import AnalysisDialog
        dlg = AnalysisDialog("geomorphology", self.layer_manager, self)
        dlg.exec()

    def _show_hydrology_dialog(self):
        from app.ui.dialogs.analysis_dialog import AnalysisDialog
        dlg = AnalysisDialog("hydrology", self.layer_manager, self)
        dlg.exec()

    def _show_vegetation_dialog(self):
        from app.ui.dialogs.analysis_dialog import AnalysisDialog
        dlg = AnalysisDialog("vegetation", self.layer_manager, self)
        dlg.exec()

    def _show_multitemporal_dialog(self):
        from app.ui.dialogs.analysis_dialog import AnalysisDialog
        dlg = AnalysisDialog("multitemporal", self.layer_manager, self)
        dlg.exec()

    def _show_reproject_dialog(self):
        from app.ui.dialogs.crs_dialog import CRSDialog
        entry = self.layer_manager.active_layer
        if not entry or not entry.is_point_cloud:
            QMessageBox.information(self, "Info", "Selecciona una nube de puntos primero.")
            return
        dlg = CRSDialog(entry.layer, self)
        dlg.exec()

    def _merge_tiles(self):
        clouds = self.layer_manager.get_point_clouds()
        if len(clouds) < 2:
            QMessageBox.information(self, "Info", "Se necesitan al menos 2 nubes para fusionar.")
            return
        merged = PointCloudData.merge(clouds, "merged")
        self.layer_manager.add_layer(merged)
        self.viewport.display_point_cloud(merged)
        self.viewport.reset_camera()

    def _filter_noise(self):
        entry = self.layer_manager.active_layer
        if not entry or not entry.is_point_cloud:
            return
        from app.processing.preprocessing import filter_noise
        try:
            self._update_status(tr("status.processing"))
            result = filter_noise(entry.layer)
            idx = self.layer_manager.add_layer(result)
            self.viewport.display_point_cloud(result)
            self._update_status(tr("status.ready"))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _decimate_cloud(self):
        entry = self.layer_manager.active_layer
        if not entry or not entry.is_point_cloud:
            return
        from PyQt6.QtWidgets import QInputDialog
        voxel, ok = QInputDialog.getDouble(
            self, "Decimar", "Tamaño de voxel (m):", 0.5, 0.01, 100.0, 2
        )
        if ok:
            from app.processing.preprocessing import decimate
            result = decimate(entry.layer, voxel_size=voxel)
            self.layer_manager.add_layer(result)
            self.viewport.display_point_cloud(result)

    # --- Tools ---
    def _start_profile_tool(self):
        logger.info("Herramienta de perfil activada")

    def _start_distance_tool(self):
        logger.info("Herramienta de distancia activada")

    def _start_area_tool(self):
        logger.info("Herramienta de área activada")

    def _start_volume_tool(self):
        logger.info("Herramienta de volumen activada")

    # --- Export ---
    def _show_export_dialog(self):
        from app.ui.dialogs.export_dialog import ExportDialog
        dlg = ExportDialog(self.layer_manager, self)
        dlg.exec()

    def _export_layer(self, index: int):
        entry = self.layer_manager.get_entry(index)
        if not entry:
            return
        from app.ui.dialogs.export_dialog import ExportDialog
        dlg = ExportDialog(self.layer_manager, self, preset_layer=index)
        dlg.exec()

    # --- About ---
    def _show_about(self):
        QMessageBox.about(
            self,
            tr("dialog.about_title"),
            f"<h2>{APP_NAME} v{APP_VERSION}</h2>"
            f"<p>{APP_FULL_NAME}</p>"
            f"<p>{tr('dialog.about_text')}</p>"
            f"<p>Python + PyQt6 + PyVista + PDAL</p>"
        )

    # --- Language ---
    def _change_language(self, lang: str):
        set_language(lang)
        self.preferences.set("language", lang)
        QMessageBox.information(
            self, "Idioma / Language",
            "El cambio de idioma se aplicará completamente al reiniciar la aplicación.\n"
            "Language change will be fully applied after restarting."
        )

    # ==================================================================
    # State persistence
    # ==================================================================

    def _restore_state(self):
        geom = self.preferences.get("window_geometry")
        if geom:
            try:
                from PyQt6.QtCore import QByteArray
                self.restoreGeometry(QByteArray.fromHex(geom.encode()))
            except Exception:
                pass

    def closeEvent(self, event):
        self.preferences.set("window_geometry",
                              bytes(self.saveGeometry().toHex()).decode())
        self.preferences.save()
        self.viewport.closeEvent(event)
        super().closeEvent(event)
