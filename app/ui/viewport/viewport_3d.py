"""
ALAS — 3D Viewport
3D viewport based on PyVista QtInteractor for point cloud visualization.
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
    3D viewport widget wrapping PyVista QtInteractor.
    Displays point clouds and raster surfaces.
    """

    point_picked = pyqtSignal(float, float, float)   # x, y, z
    cursor_moved = pyqtSignal(float, float, float)    # coordinates under cursor

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._current_actors = {}  # {layer_name: actor}
        self._point_size = DEFAULT_POINT_SIZE
        self._colorize_mode = COLORIZE_HEIGHT

        # Figures
        self._figure_meta: dict = {}     # actor_name → (ftype, center, params)
        self._figure_id_map: dict = {}   # actor_name → figure_id
        self._drag_observers_active = False

        # Tools state
        self._picked_points = []
        self._measuring_widget = None
        self._picking_callback = None
        self._temp_actors = []       # Temporary actors (lines, measurement points)
        self._picking_active = False # Flag to disable button remap during picking

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Configure PyVista
        pv.global_theme.background = DEFAULT_BACKGROUND_COLOR
        pv.global_theme.font.color = "white"
        
        # On Windows MSAA can be very slow, we use FXAA or disable it
        if sys.platform == "win32":
            pv.global_theme.anti_aliasing = "fxaa"
        else:
            pv.global_theme.anti_aliasing = "msaa"

        self.plotter = QtInteractor(self)
        
        # Eye Dome Lighting is excellent but heavy, we enable it with optimized parameters
        self.plotter.enable_eye_dome_lighting() 
        layout.addWidget(self.plotter.interactor)

        # Configure interaction
        self.plotter.enable_trackball_style()
        self.plotter.interactor.installEventFilter(self)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtGui import QMouseEvent
        from PyQt6.QtWidgets import QApplication

        # No intercept events if there is picking active (area, distance, points)
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

    @staticmethod
    def prepare_display_data(pc: PointCloudData,
                              colorize_by: str) -> pv.PolyData:
        """Decimate and build a colored PolyData mesh — safe to run off the main thread."""
        display_pc = pc
        if pc.point_count > MAX_VIEWPORT_POINTS:
            display_pc = pc.decimate_for_display(MAX_VIEWPORT_POINTS)
            logger.info(
                f"Automatic decimation: {pc.point_count:,} → "
                f"{display_pc.point_count:,} points for visualization"
            )

        points = display_pc.xyz.astype(np.float32)
        cloud = pv.PolyData(points)

        colors = Viewport3D._generate_colors_static(display_pc, colorize_by)
        if colors is not None:
            cloud["RGB"] = colors

        return cloud

    def render_prepared_cloud(self, cloud: pv.PolyData, name: str):
        """Upload a prepared PolyData mesh to the plotter — must run on the main thread."""
        has_colors = "RGB" in cloud.point_data
        self._remove_actor(name)
        actor = self.plotter.add_mesh(
            cloud,
            scalars="RGB" if has_colors else None,
            rgb=has_colors,
            point_size=self._point_size,
            render_points_as_spheres=False,
            name=name,
            show_scalar_bar=False,
        )
        self._current_actors[name] = actor
        logger.info(f"Rendered {cloud.n_points:,} points | name={name}")

    def display_point_cloud(self, pc: PointCloudData,
                             colorize_by: str = None,
                             name: str = None):
        """Display a point cloud synchronously (used by update_colorization)."""
        if pc.xyz is None or pc.point_count == 0:
            logger.warning("Empty cloud, nothing to display")
            return
        name = name or pc.name
        colorize_by = colorize_by or self._colorize_mode
        cloud = Viewport3D.prepare_display_data(pc, colorize_by)
        self.render_prepared_cloud(cloud, name)

    def update_colorization(self, pc: PointCloudData,
                              colorize_by: str, name: str = None):
        """Update the colorization of an already displayed cloud."""
        self._colorize_mode = colorize_by
        self.display_point_cloud(pc, colorize_by, name)

    @staticmethod
    def _generate_colors_static(pc: PointCloudData,
                                 mode: str) -> Optional[np.ndarray]:
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
                return colorize_by_height(pc.xyz[:, 2])
        except Exception as e:
            logger.error(f"Error in colorization ({mode}): {e}")
            return colorize_by_height(pc.xyz[:, 2])

    # ------------------------------------------------------------------
    # Raster Display
    # ------------------------------------------------------------------

    def display_raster_surface(self, raster: RasterLayer, name: str = None):
        """
        Display a raster as a 3D surface (StructuredGrid).
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
        y = np.linspace(ymax, ymin, rows)  # Y inverted in rasters
        xx, yy = np.meshgrid(x, y)

        terrain_arr = getattr(raster, "flood_terrain_arr", None)
        is_flood = terrain_arr is not None

        if is_flood:
            z = np.asarray(terrain_arr, dtype=np.float32).copy()
            z[z == raster.nodata] = np.nan

            depth = data.astype(np.float32).copy()
            depth[depth == raster.nodata] = np.nan
            depth[depth <= 0.0] = np.nan

            self._remove_actor(name)

            if not np.any(np.isfinite(depth)):
                # Water level below terrain — nothing flooded, nothing to show.
                logger.info(f"Flood layer '{name}': no flooded cells at this water level")
                return

            grid = pv.StructuredGrid(xx, yy, z)

            # Build per-point RGBA: semi-transparent blue where flooded,
            # fully transparent elsewhere.  Terrain shape comes from z so
            # the surface follows the DTM and can be overlaid for comparison.
            n_pts = rows * cols
            rgba = np.zeros((n_pts, 4), dtype=np.uint8)
            depth_flat = depth.ravel(order="F")
            flooded = np.isfinite(depth_flat)

            valid_depth = depth_flat[flooded]
            vmax = float(np.nanpercentile(valid_depth, 99.0))
            norm = np.clip(valid_depth / max(vmax, 0.01), 0.0, 1.0)
            # Light-blue (shallow) → dark-blue (deep)
            rgba[flooded, 0] = np.interp(norm, [0, 1], [173,   8]).astype(np.uint8)
            rgba[flooded, 1] = np.interp(norm, [0, 1], [216,  48]).astype(np.uint8)
            rgba[flooded, 2] = np.interp(norm, [0, 1], [230, 107]).astype(np.uint8)
            rgba[flooded, 3] = 200  # ~78 % opacity so terrain shape shows through

            grid["FloodColor"] = rgba
            actor = self.plotter.add_mesh(
                grid,
                scalars="FloodColor",
                rgba=True,
                show_scalar_bar=False,
                name=name,
            )
        else:
            z = data.astype(np.float32).copy()
            z[z == raster.nodata] = np.nan

            grid = pv.StructuredGrid(xx, yy, z)
            self._remove_actor(name)

            grid["Elevation"] = z.ravel(order="F")
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
        """Remove an actor by name."""
        self._remove_actor(name)
        self.plotter.render()

    def set_layer_visibility(self, name: str, visible: bool):
        if name in self._current_actors:
            actor = self._current_actors[name]
            actor.SetVisibility(visible)
            self.plotter.render()

    def clear_all(self):
        """Remove all actors."""
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
        """Zoom to a specific extent."""
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
        """Capture the current viewport. Returns array or saves to file."""
        if path:
            self.plotter.screenshot(path)
            logger.info(f"Screenshot saved: {path}")
            return None
        return self.plotter.screenshot(return_img=True)

    # ------------------------------------------------------------------
    # Interactive Tools
    # ------------------------------------------------------------------

    def enable_point_picking(self, callback=None):
        """Enable point picking in the viewport."""
        logger.info("Enabling point picking...")
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
        logger.info("Point picking ready. Left-click on points.")

    def _on_point_picked(self, point):
        """Callback when a point is picked."""
        logger.debug(f"Picking event triggered. Point: {point}")
        if point is None:
            logger.warning("Picking triggered but no point found.")
            return

        x, y, z = point
        logger.info(f"Point detected: X={x:.3f}, Y={y:.3f}, Z={z:.3f}")

        sphere = pv.Sphere(radius=0.2, center=point)
        actor = self.plotter.add_mesh(
            sphere, color="#ffff00",
            name=f"_tmp_point_{len(self._temp_actors)}"
        )
        self._temp_actors.append(actor)

        self.point_picked.emit(x, y, z)
        if self._picking_callback:
            logger.debug("Calling tool callback...")
            self._picking_callback(x, y, z)

    def add_temporary_line(self, p1, p2, color="#ffff00"):
        """Draw a highlighted temporary line between two points."""
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
        Mark a measurement point with the same style as the area tool:
        black sphere of 14px.
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
        Draw a measurement line with the same style as the area tool:
        black, line_width=3, no tubes.
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
        """Enable the distance measurement tool."""
        self.disable_tools()
        self._picking_active = True
        self._measuring_widget = self.plotter.add_measurement_widget(color="#000000")
        logger.info("Distance tool enabled")

    def enable_world_picking(self, callback):
        """
        Enable world coordinate picking via vtkWorldPointPicker.
        Uses the same mechanism as the area tool: reads from Z-buffer
        with O(1), does not require click to land on geometry.
        callback(x, y, z) is called on each click.
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
        Enable the area tool.

        Performance:
        - vtkWorldPointPicker: O(1) — reads the Z-buffer, does NOT traverse geometry.
        - Single PolyData actor for all vertices (large points).
        - Single PolyData actor for all lines, updated on each click.
        - Click vs drag: if mouse moves < 5 px between press and release = click.
        """
        import vtk as _vtk
        logger.info("Enabling area tool...")
        self.disable_tools()
        self._picking_active = True
        self._area_vertices: list = []
        self._area_press_pos = None
        self._area_markers_actor = None
        self._area_lines_actor   = None

        # WorldPointPicker: instant, uses depth buffer
        wp_picker = _vtk.vtkWorldPointPicker()
        self._area_picker = wp_picker  # keep reference alive

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
            if (dx * dx + dy * dy) > 25:   # > 5 px → drag, not click
                return

            # Pick O(1): deproject screen coordinates using Z-buffer
            wp_picker.Pick(press_pos[0], press_pos[1], 0, self.plotter.renderer)
            p = wp_picker.GetPickPosition()
            x, y, z = float(p[0]), float(p[1]), float(p[2])

            self._area_vertices.append((x, y, z))
            pts = np.array(self._area_vertices, dtype=np.float32)

            # --- Vertices actor: single PolyData with large points ---
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

            # --- Lines actor: single PolyData with segments ---
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
            logger.debug(f"Area — vertex {len(self._area_vertices)}: ({x:.2f}, {y:.2f}, {z:.2f})")

            if on_vertex_added:
                on_vertex_added(x, y, z)

        style = iren.GetInteractorStyle()
        self._area_obs_press   = style.AddObserver("LeftButtonPressEvent",   _on_press)
        self._area_obs_release = style.AddObserver("LeftButtonReleaseEvent", _on_release)
        self._area_style_ref   = style

        logger.info("Area tool ready. Click to add vertices.")

    def draw_closing_line(self):
        """Add the polygon closing line to the existing lines actor."""
        if not hasattr(self, "_area_vertices") or len(self._area_vertices) < 3:
            return
        pts = np.array(self._area_vertices, dtype=np.float32)
        n = len(pts)
        # Lines: 0-1, 1-2, ..., (n-1)-0  (closing)
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
    def clear_volume_graphics(self):
        """Clear only the colored 3D solid of the volume."""
        if hasattr(self, "_volume_solid_actor") and self._volume_solid_actor is not None:
            try:
                self.plotter.remove_actor(self._volume_solid_actor)
                if self._volume_solid_actor in self._temp_actors:
                    self._temp_actors.remove(self._volume_solid_actor)
            except Exception:
                pass
            self._volume_solid_actor = None
        self.plotter.render()

    def display_volume_region(self, grid_x: np.ndarray, grid_y: np.ndarray, grid_z: np.ndarray, reference_z: float):
        """Draw the 3D solid block corresponding to the calculated volume."""
        self.clear_volume_graphics()
        try:
            # 1. Prepare top and bottom layers
            # Temporarily fill NaNs to build the structured grid
            z_terrain = grid_z.copy()
            valid_mask = ~np.isnan(z_terrain)
            
            if not np.any(valid_mask):
                return
                
            z_terrain[~valid_mask] = reference_z
            z_ref_layer = np.full_like(z_terrain, reference_z)

            # 2. Create the 3D matrices by stacking the two layers (terrain and reference)
            x3d = np.dstack((grid_x, grid_x))
            y3d = np.dstack((grid_y, grid_y))
            z3d = np.dstack((z_terrain, z_ref_layer))

            grid = pv.StructuredGrid(x3d, y3d, z3d)

            # 3. Calculate difference and classify: Cut (1), Fill (-1)
            diff_2d = z_terrain - reference_z
            diff_3d = np.dstack((diff_2d, diff_2d))
            category_3d = np.where(diff_3d > 0, 1, -1)

            # 4. Valid cells mask (only cells that were inside the polygon)
            valid_3d = np.dstack((valid_mask, valid_mask)).astype(float)

            # Assign scalars to grid points (Flatten Fortran order for X,Y,Z of PyVista)
            grid["Category"] = category_3d.flatten(order="F")
            grid["Valid"] = valid_3d.flatten(order="F")

            # 5. Extract only valid cells using a threshold
            solid_volume = grid.threshold(0.5, scalars="Valid")

            if solid_volume.n_points == 0:
                return

            from matplotlib.colors import ListedColormap
            cmap = ListedColormap(["#3b82f6", "#ef4444"]) # Blue (Fill), Red (Cut)

            actor = self.plotter.add_mesh(
                solid_volume,
                scalars="Category",
                cmap=cmap,
                show_scalar_bar=False,
                name=f"_tmp_vol_solid_{len(self._temp_actors)}",
                opacity=0.9,
                reset_camera=False
            )
            self._temp_actors.append(actor)
            self._volume_solid_actor = actor
        except Exception as e:
            logger.error(f"Error generating 3D volume solid: {e}")

        self.plotter.render()

    def clear_temporary_graphics(self):
        """Clear temporary selection lines and points."""
        for actor in self._temp_actors:
            try:
                self.plotter.remove_actor(actor)
            except Exception:
                pass
        self._temp_actors = []
        # Clear area tool actors
        for attr in ("_area_markers_actor", "_area_lines_actor"):
            actor = getattr(self, attr, None)
            if actor is not None:
                try:
                    self.plotter.remove_actor(actor)
                except Exception:
                    pass
                setattr(self, attr, None)
        self.plotter.render()

    # ------------------------------------------------------------------
    # Geometric figures
    # ------------------------------------------------------------------

    @staticmethod
    def _build_figure_mesh(figure_type: str, center, params: dict):
        cx, cy, cz = float(center[0]), float(center[1]), float(center[2])
        if figure_type == "cube":
            s = float(params.get("size", 1.0))
            h = s / 2.0
            return pv.Box(bounds=(cx - h, cx + h, cy - h, cy + h, cz - h, cz + h))
        if figure_type == "sphere":
            r = float(params.get("radius", 1.0))
            return pv.Sphere(radius=r, center=(cx, cy, cz))
        if figure_type == "cylinder":
            r = float(params.get("radius", 1.0))
            h = float(params.get("height", 2.0))
            return pv.Cylinder(center=(cx, cy, cz + h / 2.0),
                               direction=(0, 0, 1), radius=r, height=h, resolution=48)
        if figure_type == "cone":
            r = float(params.get("radius", 1.0))
            h = float(params.get("height", 2.0))
            return pv.Cone(center=(cx, cy, cz + h / 2.0),
                           direction=(0, 0, 1), radius=r, height=h, resolution=48)
        if figure_type == "plane":
            w = float(params.get("size_x", 2.0))
            d = float(params.get("size_y", 2.0))
            return pv.Plane(center=(cx, cy, cz), direction=(0, 0, 1),
                            i_size=w, j_size=d)
        raise ValueError(f"Unknown figure type: {figure_type}")

    def add_figure(self, figure_type: str, center, params: dict,
                   name: str, color: str = "#a855f7", opacity: float = 0.55):
        """Add a geometric figure as a named actor. Returns the actor."""
        mesh = self._build_figure_mesh(figure_type, center, params)
        self._remove_actor(name)
        actor = self.plotter.add_mesh(
            mesh, color=color, opacity=opacity, name=name,
            show_edges=True, edge_color="#ffffff", line_width=1,
            reset_camera=False,
        )
        self._current_actors[name] = actor
        # Keep metadata so the drag system can rebuild the mesh
        self._figure_meta[name] = (figure_type, list(center), dict(params))
        self.plotter.render()
        return actor

    def update_figure(self, figure_type: str, center, params: dict,
                      name: str, color: str = "#a855f7", opacity: float = 0.55):
        """Replace an existing figure actor (same name) with new parameters."""
        return self.add_figure(figure_type, center, params, name, color, opacity)

    def register_figure_id(self, name: str, figure_id: int):
        """Map actor name → figure id used by the drag callback."""
        self._figure_id_map[name] = figure_id

    def unregister_figure(self, name: str):
        self._figure_meta.pop(name, None)
        self._figure_id_map.pop(name, None)

    def enable_figure_dragging(self, on_figure_moved):
        """
        Install persistent VTK observers that let the user drag any figure by
        holding the left mouse button on it.  ``on_figure_moved(figure_id, x, y, z)``
        is called after each completed drag.
        Non-figure left-clicks fall through to the normal camera trackball.
        """
        import vtk as _vtk
        if getattr(self, "_drag_observers_active", False):
            return  # already installed

        prop_picker = _vtk.vtkPropPicker()
        wp_picker   = _vtk.vtkWorldPointPicker()
        self._drag_prop_picker = prop_picker
        self._drag_wp_picker   = wp_picker
        self._drag_on_moved    = on_figure_moved
        self._drag_active      = False
        self._drag_name        = None
        self._drag_figure_id   = None
        self._drag_center      = None
        self._drag_press_screen = None

        iren  = self.plotter.iren.interactor
        style = iren.GetInteractorStyle()
        self._drag_style_ref = style

        def _on_press(obj, event):
            pos = iren.GetEventPosition()
            self._drag_press_screen = pos

            # Pick — check if we hit a figure actor
            prop_picker.Pick(pos[0], pos[1], 0, self.plotter.renderer)
            hit_actor = prop_picker.GetActor()

            name = None
            if hit_actor is not None:
                for n, a in self._current_actors.items():
                    if a is hit_actor and n in self._figure_meta:
                        name = n
                        break

            if name is not None:
                # Begin drag — consume the event (don't rotate camera)
                self._drag_active   = True
                self._drag_name     = name
                self._drag_figure_id = self._figure_id_map.get(name)
                _, center, _ = self._figure_meta[name]
                self._drag_center   = list(center)
                wp_picker.Pick(pos[0], pos[1], 0, self.plotter.renderer)
                p = wp_picker.GetPickPosition()
                self._drag_pick_offset = (
                    self._drag_center[0] - p[0],
                    self._drag_center[1] - p[1],
                )
            else:
                self._drag_active = False
                obj.OnLeftButtonDown()

        def _on_move(obj, event):
            if not self._drag_active:
                obj.OnMouseMove()
                return
            pos = iren.GetEventPosition()
            wp_picker.Pick(pos[0], pos[1], 0, self.plotter.renderer)
            p = wp_picker.GetPickPosition()
            nx = p[0] + self._drag_pick_offset[0]
            ny = p[1] + self._drag_pick_offset[1]
            nz = self._drag_center[2]
            self._drag_center = [nx, ny, nz]
            ftype, _, params = self._figure_meta[self._drag_name]
            self._figure_meta[self._drag_name] = (ftype, [nx, ny, nz], params)
            mesh = self._build_figure_mesh(ftype, (nx, ny, nz), params)
            self._remove_actor(self._drag_name)
            actor = self.plotter.add_mesh(
                mesh, color="#a855f7", opacity=0.55, name=self._drag_name,
                show_edges=True, edge_color="#ffffff", line_width=1,
                reset_camera=False,
            )
            self._current_actors[self._drag_name] = actor
            self.plotter.render()

        def _on_release(obj, event):
            if not self._drag_active:
                obj.OnLeftButtonUp()
                return
            self._drag_active = False
            cx, cy, cz = self._drag_center
            if self._drag_figure_id is not None:
                self._drag_on_moved(self._drag_figure_id, cx, cy, cz)
            obj.OnLeftButtonUp()

        self._drag_obs_press   = style.AddObserver("LeftButtonPressEvent",   _on_press)
        self._drag_obs_move    = style.AddObserver("MouseMoveEvent",          _on_move)
        self._drag_obs_release = style.AddObserver("LeftButtonReleaseEvent",  _on_release)
        self._drag_observers_active = True
        logger.info("Figure dragging enabled")

    def disable_figure_dragging(self):
        style = getattr(self, "_drag_style_ref", None)
        if style is None:
            return
        for attr in ("_drag_obs_press", "_drag_obs_move", "_drag_obs_release"):
            obs = getattr(self, attr, None)
            if obs is not None:
                try:
                    style.RemoveObserver(obs)
                except Exception:
                    pass
                setattr(self, attr, None)
        self._drag_style_ref = None
        self._drag_observers_active = False

    def disable_tools(self):
        """Disable interactive tools and clean up widgets."""
        self._picking_active = False
        # Remove VTK observers from area tool
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
        # Remove VTK observers from world picker (distance, profile...)
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
        logger.info("Interactive tools disabled")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        self.plotter.close()
        super().closeEvent(event)