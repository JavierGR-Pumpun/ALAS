"""
ALAS — 3D Viewport
Viewport 3D basado en PyVista QtInteractor para visualización de nubes de puntos.
"""

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt
import sys
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

        # Tools state
        self._picked_points = []
        self._measuring_widget = None
        self._picking_callback = None
        self._temp_actors = []       # Actores temporales (líneas, puntos de medida)
        self._picking_active = False # Flag para desactivar remap de botones durante picking

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Configurar PyVista
        pv.global_theme.background = DEFAULT_BACKGROUND_COLOR
        pv.global_theme.font.color = "white"
        
        # En Windows MSAA puede ser muy lento, usamos FXAA o desactivamos
        if sys.platform == "win32":
            pv.global_theme.anti_aliasing = "fxaa"
        else:
            pv.global_theme.anti_aliasing = "msaa"

        self.plotter = QtInteractor(self)
        
        # El Eye Dome Lighting es excelente pero pesado, lo habilitamos con parámetros optimizados
        self.plotter.enable_eye_dome_lighting() 
        layout.addWidget(self.plotter.interactor)

        # Configurar interacción
        self.plotter.enable_trackball_style()
        self.plotter.interactor.installEventFilter(self)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtGui import QMouseEvent
        from PyQt6.QtWidgets import QApplication

        # No interceptar eventos si hay picking activo (área, distancia, puntos)
        if self._picking_active:
            return super().eventFilter(obj, event)

        if hasattr(self, 'plotter') and obj == self.plotter.interactor:
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.RightButton:
                    new_event = QMouseEvent(
                        QEvent.Type.MouseButtonPress,
                        event.position(),
                        event.globalPosition(),
                        Qt.MouseButton.MiddleButton,
                        (event.buttons() & ~Qt.MouseButton.RightButton) | Qt.MouseButton.MiddleButton,
                        event.modifiers()
                    )
                    QApplication.postEvent(obj, new_event)
                    return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.RightButton:
                    new_event = QMouseEvent(
                        QEvent.Type.MouseButtonRelease,
                        event.position(),
                        event.globalPosition(),
                        Qt.MouseButton.MiddleButton,
                        (event.buttons() & ~Qt.MouseButton.RightButton),
                        event.modifiers()
                    )
                    QApplication.postEvent(obj, new_event)
                    return True
            elif event.type() == QEvent.Type.MouseMove:
                if event.buttons() & Qt.MouseButton.RightButton:
                    new_event = QMouseEvent(
                        QEvent.Type.MouseMove,
                        event.position(),
                        event.globalPosition(),
                        Qt.MouseButton.NoButton,
                        (event.buttons() & ~Qt.MouseButton.RightButton) | Qt.MouseButton.MiddleButton,
                        event.modifiers()
                    )
                    QApplication.postEvent(obj, new_event)
                    return True
        return super().eventFilter(obj, event)

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
    # Interactive Tools
    # ------------------------------------------------------------------

    def enable_point_picking(self, callback=None):
        """Habilita la selección de puntos en el viewport."""
        logger.info("Habilitando selección de puntos...")
        self.disable_tools()
        self._picking_active = True
        self._picking_callback = callback

        self.plotter.enable_point_picking(
            callback=self._on_point_picked,
            show_message="",
            color="#ffff00",
            point_size=12,
            use_picker=True,
            left_clicking=True
        )
        logger.info("Selección de puntos lista. Haz clic izquierdo en los puntos.")

    def _on_point_picked(self, point):
        """Callback cuando se selecciona un punto."""
        logger.debug(f"Evento de picking disparado. Punto: {point}")
        if point is None:
            logger.warning("Picking disparado pero no se encontró ningún punto.")
            return

        x, y, z = point
        logger.info(f"Punto detectado: X={x:.3f}, Y={y:.3f}, Z={z:.3f}")

        sphere = pv.Sphere(radius=0.2, center=point)
        actor = self.plotter.add_mesh(
            sphere, color="#ffff00",
            name=f"_tmp_point_{len(self._temp_actors)}"
        )
        self._temp_actors.append(actor)

        self.point_picked.emit(x, y, z)
        if self._picking_callback:
            logger.debug("Llamando al callback de la herramienta...")
            self._picking_callback(x, y, z)

    def add_temporary_line(self, p1, p2, color="#ffff00"):
        """Dibuja una linea temporal resaltada entre dos puntos."""
        line = pv.Line(p1, p2)
        actor = self.plotter.add_mesh(
            line,
            color=color,
            line_width=12,
            name=f"_tmp_line_{len(self._temp_actors)}",
            render_lines_as_tubes=True,
            smooth_shading=True,
        )
        try:
            actor.GetProperty().SetLighting(False)
            actor.GetProperty().SetAmbient(1.0)
        except Exception:
            pass

        self._temp_actors.append(actor)
        return actor

    def add_measurement_marker(self, p):
        """
        Marca un punto de medicion con el mismo estilo que la herramienta de area:
        esfera negra de 14px.
        """
        pts = pv.PolyData([list(p)])
        actor = self.plotter.add_mesh(
            pts,
            color="#000000",
            point_size=14,
            render_points_as_spheres=True,
            name=f"_meas_marker_{len(self._temp_actors)}",
            reset_camera=False,
        )
        self._temp_actors.append(actor)
        return actor

    def add_measurement_line(self, p1, p2):
        """
        Dibuja una linea de medicion con el mismo estilo que la herramienta de area:
        negra, line_width=3, sin tubes.
        """
        line = pv.Line(p1, p2)
        actor = self.plotter.add_mesh(
            line,
            color="#000000",
            line_width=3,
            name=f"_meas_line_{len(self._temp_actors)}",
            reset_camera=False,
        )
        self._temp_actors.append(actor)
        self.plotter.render()
        return actor

    def enable_distance_tool(self):
        """Habilita la herramienta de medicion de distancia."""
        self.disable_tools()
        self._picking_active = True
        self._measuring_widget = self.plotter.add_measurement_widget(color="#000000")
        logger.info("Herramienta de distancia habilitada")

    def enable_world_picking(self, callback):
        """
        Habilita picking de coordenadas de mundo mediante vtkWorldPointPicker.
        Usa el mismo mecanismo que la herramienta de area: lee del Z-buffer
        con O(1), no requiere que el clic aterrice sobre la geometria.
        callback(x, y, z) se llama en cada clic.
        """
        import vtk as _vtk
        self.disable_tools()
        self._picking_active = True

        wp_picker = _vtk.vtkWorldPointPicker()
        self._wp_picker_ref = wp_picker

        iren = self.plotter.iren.interactor
        press_pos_ref = [None]

        def _on_press(obj, event):
            press_pos_ref[0] = iren.GetEventPosition()
            obj.OnLeftButtonDown()

        def _on_release(obj, event):
            release_pos = iren.GetEventPosition()
            press_pos   = press_pos_ref[0]
            obj.OnLeftButtonUp()

            if press_pos is None:
                return
            dx = release_pos[0] - press_pos[0]
            dy = release_pos[1] - press_pos[1]
            if (dx * dx + dy * dy) > 25:   # drag, not a click
                return

            wp_picker.Pick(press_pos[0], press_pos[1], 0, self.plotter.renderer)
            p = wp_picker.GetPickPosition()
            x, y, z = float(p[0]), float(p[1]), float(p[2])
            logger.debug(f"World pick: ({x:.3f}, {y:.3f}, {z:.3f})")
            callback(x, y, z)

        style = iren.GetInteractorStyle()
        self._wp_obs_press   = style.AddObserver("LeftButtonPressEvent",   _on_press)
        self._wp_obs_release = style.AddObserver("LeftButtonReleaseEvent", _on_release)
        self._wp_style_ref   = style

    def enable_area_tool(self, on_vertex_added=None):
        """
        Habilita la herramienta de área.

        Rendimiento:
        - vtkWorldPointPicker: O(1) — lee el Z-buffer, NO traversa la geometría.
        - Un único actor PolyData para todos los vértices (puntos grandes).
        - Un único actor PolyData para todas las líneas, actualizado en cada clic.
        - Click vs drag: si el ratón se mueve < 5 px entre press y release = clic.
        """
        import vtk as _vtk
        logger.info("Habilitando herramienta de área...")
        self.disable_tools()
        self._picking_active = True
        self._area_vertices: list = []
        self._area_press_pos = None
        self._area_markers_actor = None
        self._area_lines_actor   = None

        # WorldPointPicker: instantáneo, usa depth buffer
        wp_picker = _vtk.vtkWorldPointPicker()
        self._area_picker = wp_picker  # mantener referencia viva

        iren = self.plotter.iren.interactor

        def _on_press(obj, event):
            self._area_press_pos = iren.GetEventPosition()
            obj.OnLeftButtonDown()

        def _on_release(obj, event):
            release_pos = iren.GetEventPosition()
            press_pos   = self._area_press_pos
            obj.OnLeftButtonUp()

            if press_pos is None:
                return
            dx = release_pos[0] - press_pos[0]
            dy = release_pos[1] - press_pos[1]
            if (dx * dx + dy * dy) > 25:   # > 5 px → arrastre, no clic
                return

            # Pick O(1): desprojecta las coordenadas de pantalla usando el Z-buffer
            wp_picker.Pick(press_pos[0], press_pos[1], 0, self.plotter.renderer)
            p = wp_picker.GetPickPosition()
            x, y, z = float(p[0]), float(p[1]), float(p[2])

            self._area_vertices.append((x, y, z))
            pts = np.array(self._area_vertices, dtype=np.float32)

            # --- Actor de vértices: un único PolyData con puntos grandes ---
            markers = pv.PolyData(pts)
            if self._area_markers_actor is not None:
                self.plotter.remove_actor(self._area_markers_actor)
            self._area_markers_actor = self.plotter.add_mesh(
                markers,
                color="#000000",
                point_size=14,
                render_points_as_spheres=True,
                name="_area_markers",
                reset_camera=False,
            )

            # --- Actor de líneas: un único PolyData con segmentos ---
            if len(self._area_vertices) >= 2:
                n = len(pts)
                cells = np.empty((n - 1) * 3, dtype=np.int_)
                cells[0::3] = 2
                cells[1::3] = np.arange(n - 1)
                cells[2::3] = np.arange(1, n)
                lines_pd = pv.PolyData()
                lines_pd.points = pts
                lines_pd.lines  = cells
                if self._area_lines_actor is not None:
                    self.plotter.remove_actor(self._area_lines_actor)
                self._area_lines_actor = self.plotter.add_mesh(
                    lines_pd,
                    color="#000000",
                    line_width=3,
                    name="_area_lines",
                    reset_camera=False,
                )

            self.plotter.render()
            logger.debug(f"Área — vértice {len(self._area_vertices)}: ({x:.2f}, {y:.2f}, {z:.2f})")

            if on_vertex_added:
                on_vertex_added(x, y, z)

        style = iren.GetInteractorStyle()
        self._area_obs_press   = style.AddObserver("LeftButtonPressEvent",   _on_press)
        self._area_obs_release = style.AddObserver("LeftButtonReleaseEvent", _on_release)
        self._area_style_ref   = style

        logger.info("Herramienta de área lista. Haz clic para añadir vértices.")

    def draw_closing_line(self):
        """Añade la línea de cierre del polígono al actor de líneas existente."""
        if not hasattr(self, "_area_vertices") or len(self._area_vertices) < 3:
            return
        pts = np.array(self._area_vertices, dtype=np.float32)
        n = len(pts)
        # Líneas: 0-1, 1-2, ..., (n-1)-0  (cierre)
        cells = np.empty(n * 3, dtype=np.int_)
        cells[0::3] = 2
        cells[1::3] = np.arange(n)
        cells[2::3] = np.arange(1, n + 1) % n
        lines_pd = pv.PolyData()
        lines_pd.points = pts
        lines_pd.lines  = cells
        if hasattr(self, "_area_lines_actor") and self._area_lines_actor is not None:
            self.plotter.remove_actor(self._area_lines_actor)
        self._area_lines_actor = self.plotter.add_mesh(
            lines_pd, color="#000000", line_width=3, name="_area_lines",
            reset_camera=False,
        )
        self.plotter.render()



    def clear_temporary_graphics(self):
        """Limpia líneas y puntos de selección temporales."""
        for actor in self._temp_actors:
            try:
                self.plotter.remove_actor(actor)
            except Exception:
                pass
        self._temp_actors = []
        # Limpiar actores del área tool
        for attr in ("_area_markers_actor", "_area_lines_actor"):
            actor = getattr(self, attr, None)
            if actor is not None:
                try:
                    self.plotter.remove_actor(actor)
                except Exception:
                    pass
                setattr(self, attr, None)
        self.plotter.render()

    def disable_tools(self):
        """Deshabilita herramientas interactivas y limpia widgets."""
        self._picking_active = False
        # Eliminar observadores VTK del area tool
        style_ref = getattr(self, "_area_style_ref", None)
        if style_ref is not None:
            for obs_attr in ("_area_obs_press", "_area_obs_release"):
                obs_id = getattr(self, obs_attr, None)
                if obs_id is not None:
                    try:
                        style_ref.RemoveObserver(obs_id)
                    except Exception:
                        pass
                    setattr(self, obs_attr, None)
            self._area_style_ref = None
        # Eliminar observadores VTK del world picker (distancia, perfil...)
        wp_style = getattr(self, "_wp_style_ref", None)
        if wp_style is not None:
            for obs_attr in ("_wp_obs_press", "_wp_obs_release"):
                obs_id = getattr(self, obs_attr, None)
                if obs_id is not None:
                    try:
                        wp_style.RemoveObserver(obs_id)
                    except Exception:
                        pass
                    setattr(self, obs_attr, None)
            self._wp_style_ref = None
        self.plotter.disable_picking()
        self.clear_temporary_graphics()
        if self._measuring_widget:
            try:
                self.plotter.clear_measurements()
            except Exception:
                pass
            self._measuring_widget = None
        self._picking_callback = None
        logger.info("Herramientas interactivas deshabilitadas")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        self.plotter.close()
        super().closeEvent(event)