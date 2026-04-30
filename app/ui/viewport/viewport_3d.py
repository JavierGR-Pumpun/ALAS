"""
ALAS — 3D Viewport
Viewport 3D basado en PyVista QtInteractor para visualización de nubes de puntos.
"""

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal
from typing import Optional

from app.core.point_cloud import PointCloudData
from app.core.raster_layer import RasterLayer
from app.ui.viewport.colorizers import (
    colorize_by_height, colorize_by_intensity, colorize_by_classification,
    colorize_by_return_number, colorize_rgb, colorize_single
)
from app.config import (
    DEFAULT_POINT_SIZE, DEFAULT_BACKGROUND_COLOR,
    COLORIZE_HEIGHT, COLORIZE_INTENSITY, COLORIZE_CLASSIFICATION,
    COLORIZE_RETURN_NUMBER, COLORIZE_RGB, COLORIZE_SINGLE,
    MAX_VIEWPORT_POINTS
)
from app.logger import get_logger

logger = get_logger("ui.viewport")


class Viewport3D(QWidget):
    """
    Widget de viewport 3D que envuelve PyVista QtInteractor.
    Muestra nubes de puntos y superficies raster.
    """

    point_picked = pyqtSignal(float, float, float)   # x, y, z
    cursor_moved = pyqtSignal(float, float, float)    # coordenadas bajo cursor

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._current_actors = {}  # {layer_name: actor}
        self._point_size = DEFAULT_POINT_SIZE
        self._colorize_mode = COLORIZE_HEIGHT

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Configurar PyVista
        pv.global_theme.background = DEFAULT_BACKGROUND_COLOR
        pv.global_theme.font.color = "white"
        pv.global_theme.anti_aliasing = "msaa"

        self.plotter = QtInteractor(self)
        self.plotter.enable_eye_dome_lighting()  # Mejor percepción de profundidad
        layout.addWidget(self.plotter.interactor)

        # Configurar interacción
        self.plotter.enable_trackball_style()
        self._setup_camera_controls()

    def _setup_camera_controls(self):
        step = 5.0  # metros por paso (se puede ajustar luego o hacerlo dinámico)
        
        def move_forward():
            pos = np.array(self.plotter.camera.position)
            foc = np.array(self.plotter.camera.focal_point)
            vec = foc - pos
            norm = np.linalg.norm(vec)
            if norm == 0: return
            vec = vec / norm * step
            self.plotter.camera.position = pos + vec
            self.plotter.camera.focal_point = foc + vec
            self.plotter.render()
            
        def move_backward():
            pos = np.array(self.plotter.camera.position)
            foc = np.array(self.plotter.camera.focal_point)
            vec = foc - pos
            norm = np.linalg.norm(vec)
            if norm == 0: return
            vec = vec / norm * step
            self.plotter.camera.position = pos - vec
            self.plotter.camera.focal_point = foc - vec
            self.plotter.render()
            
        def move_up():
            up = np.array(self.plotter.camera.up)
            norm = np.linalg.norm(up)
            if norm == 0: return
            up = up / norm * step
            self.plotter.camera.position = np.array(self.plotter.camera.position) + up
            self.plotter.camera.focal_point = np.array(self.plotter.camera.focal_point) + up
            self.plotter.render()
            
        def move_down():
            up = np.array(self.plotter.camera.up)
            norm = np.linalg.norm(up)
            if norm == 0: return
            up = up / norm * step
            self.plotter.camera.position = np.array(self.plotter.camera.position) - up
            self.plotter.camera.focal_point = np.array(self.plotter.camera.focal_point) - up
            self.plotter.render()
            
        def move_left():
            pos = np.array(self.plotter.camera.position)
            foc = np.array(self.plotter.camera.focal_point)
            up = np.array(self.plotter.camera.up)
            vec = foc - pos
            left = np.cross(up, vec)
            norm = np.linalg.norm(left)
            if norm == 0: return
            left = left / norm * step
            self.plotter.camera.position = pos + left
            self.plotter.camera.focal_point = foc + left
            self.plotter.render()
            
        def move_right():
            pos = np.array(self.plotter.camera.position)
            foc = np.array(self.plotter.camera.focal_point)
            up = np.array(self.plotter.camera.up)
            vec = foc - pos
            right = np.cross(vec, up)
            norm = np.linalg.norm(right)
            if norm == 0: return
            right = right / norm * step
            self.plotter.camera.position = pos + right
            self.plotter.camera.focal_point = foc + right
            self.plotter.render()
            
        self.plotter.add_key_event('w', move_forward)
        self.plotter.add_key_event('s', move_backward)
        self.plotter.add_key_event('a', move_left)
        self.plotter.add_key_event('d', move_right)
        self.plotter.add_key_event('space', move_up)
        self.plotter.add_key_event('c', move_down)

    # ------------------------------------------------------------------
    # Point Cloud Display
    # ------------------------------------------------------------------

    def display_point_cloud(self, pc: PointCloudData,
                             colorize_by: str = None,
                             name: str = None):
        """
        Muestra una nube de puntos en el viewport.
        Si ya existe un actor con el mismo nombre, lo reemplaza.
        """
        if pc.xyz is None or pc.point_count == 0:
            logger.warning("Nube vacía, nada que mostrar")
            return

        name = name or pc.name
        colorize_by = colorize_by or self._colorize_mode

        # Decimado automático para rendimiento
        display_pc = pc
        if pc.point_count > MAX_VIEWPORT_POINTS:
            display_pc = pc.decimate_for_display(MAX_VIEWPORT_POINTS)
            logger.info(
                f"Decimado automático: {pc.point_count:,} → "
                f"{display_pc.point_count:,} puntos para visualización"
            )

        # Crear mesh de puntos PyVista
        points = display_pc.xyz.astype(np.float32)
        cloud = pv.PolyData(points)

        # Generar colores
        colors = self._generate_colors(display_pc, colorize_by)
        if colors is not None:
            cloud["RGB"] = colors

        # Eliminar actor anterior si existe
        self._remove_actor(name)

        # Añadir al plotter
        actor = self.plotter.add_mesh(
            cloud,
            scalars="RGB" if colors is not None else None,
            rgb=True if colors is not None else False,
            point_size=self._point_size,
            render_points_as_spheres=False,
            name=name,
            show_scalar_bar=False,
        )
        self._current_actors[name] = actor

        logger.info(
            f"Mostrados {display_pc.point_count:,} puntos | "
            f"Color: {colorize_by}"
        )

    def update_colorization(self, pc: PointCloudData,
                              colorize_by: str, name: str = None):
        """Actualiza la colorización de una nube ya mostrada."""
        self._colorize_mode = colorize_by
        self.display_point_cloud(pc, colorize_by, name)

    def _generate_colors(self, pc: PointCloudData,
                          mode: str) -> Optional[np.ndarray]:
        """Genera array RGB uint8 según el modo de colorización."""
        try:
            if mode == COLORIZE_HEIGHT:
                return colorize_by_height(pc.xyz[:, 2])
            elif mode == COLORIZE_INTENSITY and pc.intensity is not None:
                return colorize_by_intensity(pc.intensity)
            elif mode == COLORIZE_CLASSIFICATION and pc.classification is not None:
                return colorize_by_classification(pc.classification)
            elif mode == COLORIZE_RETURN_NUMBER and pc.return_number is not None:
                return colorize_by_return_number(pc.return_number)
            elif mode == COLORIZE_RGB and pc.has_rgb:
                return colorize_rgb(pc.rgb)
            elif mode == COLORIZE_SINGLE:
                return colorize_single(pc.point_count)
            else:
                # Fallback: color por altura
                return colorize_by_height(pc.xyz[:, 2])
        except Exception as e:
            logger.error(f"Error en colorización ({mode}): {e}")
            return colorize_by_height(pc.xyz[:, 2])

    # ------------------------------------------------------------------
    # Raster Display
    # ------------------------------------------------------------------

    def display_raster_surface(self, raster: RasterLayer, name: str = None):
        """
        Muestra un raster como superficie 3D (StructuredGrid).
        """
        if not raster.is_loaded:
            return

        name = name or raster.name

        data = raster.get_band(0)
        rows, cols = data.shape
        bounds = raster.bounds  # (xmin, ymin, xmax, ymax)

        if bounds is None:
            return

        xmin, ymin, xmax, ymax = bounds
        x = np.linspace(xmin, xmax, cols)
        y = np.linspace(ymax, ymin, rows)  # Y invertido en rasters
        xx, yy = np.meshgrid(x, y)

        # Reemplazar nodata por NaN
        z = data.astype(np.float32).copy()
        z[z == raster.nodata] = np.nan

        grid = pv.StructuredGrid(xx, yy, z)
        grid["Elevation"] = z.ravel(order="F")

        self._remove_actor(name)

        actor = self.plotter.add_mesh(
            grid,
            scalars="Elevation",
            cmap="terrain",
            nan_opacity=0,
            show_scalar_bar=False,
            name=name,
        )
        self._current_actors[name] = actor

    # ------------------------------------------------------------------
    # Actor management
    # ------------------------------------------------------------------

    def _remove_actor(self, name: str):
        if name in self._current_actors:
            try:
                self.plotter.remove_actor(self._current_actors[name])
            except Exception:
                pass
            del self._current_actors[name]

    def remove_layer(self, name: str):
        """Elimina un actor por nombre."""
        self._remove_actor(name)
        self.plotter.render()

    def set_layer_visibility(self, name: str, visible: bool):
        if name in self._current_actors:
            actor = self._current_actors[name]
            actor.SetVisibility(visible)
            self.plotter.render()

    def clear_all(self):
        """Elimina todos los actores."""
        self.plotter.clear()
        self._current_actors.clear()

    # ------------------------------------------------------------------
    # Camera controls
    # ------------------------------------------------------------------

    def reset_camera(self):
        self.plotter.reset_camera()
        self.plotter.render()

    def set_view_top(self):
        self.plotter.view_xy()
        self.plotter.render()

    def set_view_front(self):
        self.plotter.view_xz()
        self.plotter.render()

    def set_view_side(self):
        self.plotter.view_yz()
        self.plotter.render()

    def zoom_to_bounds(self, bounds):
        """Zoom a una extensión específica."""
        if bounds is None:
            return
        if len(bounds) == 6:
            xmin, ymin, zmin, xmax, ymax, zmax = bounds
        else:
            xmin, ymin, xmax, ymax = bounds
            zmin, zmax = 0, 100
        self.plotter.reset_camera_clipping_range()
        self.plotter.render()

    # ------------------------------------------------------------------
    # Point size
    # ------------------------------------------------------------------

    def set_point_size(self, size: float):
        self._point_size = size
        # Update all point cloud actors
        for name, actor in self._current_actors.items():
            try:
                prop = actor.GetProperty()
                prop.SetPointSize(size)
            except Exception:
                pass
        self.plotter.render()

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    def take_screenshot(self, path: str = None) -> Optional[np.ndarray]:
        """Captura el viewport actual. Devuelve array o guarda a archivo."""
        if path:
            self.plotter.screenshot(path)
            logger.info(f"Captura guardada: {path}")
            return None
        return self.plotter.screenshot(return_img=True)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        self.plotter.close()
        super().closeEvent(event)
