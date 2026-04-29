"""
ALAS — Layer Manager
Gestor de capas: nubes de puntos y rasters con señales Qt.
"""

from typing import Optional, Union, List
from PyQt6.QtCore import QObject, pyqtSignal

from app.core.point_cloud import PointCloudData
from app.core.raster_layer import RasterLayer
from app.logger import get_logger

logger = get_logger("core.layer_manager")

LayerType = Union[PointCloudData, RasterLayer]


class LayerEntry:
    """Entrada individual en el gestor de capas."""

    def __init__(self, layer: LayerType, visible: bool = True):
        self.layer = layer
        self.visible = visible
        self.opacity = 1.0
        self.locked = False

    @property
    def name(self) -> str:
        return self.layer.name

    @name.setter
    def name(self, value: str):
        self.layer.name = value

    @property
    def is_point_cloud(self) -> bool:
        return isinstance(self.layer, PointCloudData)

    @property
    def is_raster(self) -> bool:
        return isinstance(self.layer, RasterLayer)

    @property
    def layer_type_str(self) -> str:
        if self.is_point_cloud:
            return "point_cloud"
        return "raster"


class LayerManager(QObject):
    """
    Gestor centralizado de capas.
    Emite señales cuando cambia la lista, visibilidad o capa activa.
    """

    # Signals
    layer_added = pyqtSignal(int)               # index
    layer_removed = pyqtSignal(int)              # index
    layer_moved = pyqtSignal(int, int)           # from_idx, to_idx
    layer_renamed = pyqtSignal(int, str)         # index, new_name
    layer_visibility_changed = pyqtSignal(int, bool)  # index, visible
    active_layer_changed = pyqtSignal(int)       # index (-1 = ninguna)
    layers_cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layers: List[LayerEntry] = []
        self._active_index: int = -1

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def count(self) -> int:
        return len(self._layers)

    @property
    def active_index(self) -> int:
        return self._active_index

    @property
    def active_layer(self) -> Optional[LayerEntry]:
        if 0 <= self._active_index < len(self._layers):
            return self._layers[self._active_index]
        return None

    @property
    def active_data(self) -> Optional[LayerType]:
        entry = self.active_layer
        if entry:
            return entry.layer
        return None

    # ------------------------------------------------------------------
    # Add / Remove
    # ------------------------------------------------------------------

    def add_layer(self, layer: LayerType, make_active: bool = True) -> int:
        """Añade una capa y devuelve su índice."""
        entry = LayerEntry(layer)
        self._layers.append(entry)
        idx = len(self._layers) - 1

        logger.info(f"Capa añadida [{idx}]: {entry.name} ({entry.layer_type_str})")
        self.layer_added.emit(idx)

        if make_active:
            self.set_active(idx)

        return idx

    def remove_layer(self, index: int):
        """Elimina una capa por índice."""
        if not (0 <= index < len(self._layers)):
            return
        name = self._layers[index].name
        self._layers.pop(index)

        logger.info(f"Capa eliminada [{index}]: {name}")
        self.layer_removed.emit(index)

        # Ajustar índice activo
        if self._active_index == index:
            new_idx = min(index, len(self._layers) - 1)
            self._active_index = new_idx
            self.active_layer_changed.emit(new_idx)
        elif self._active_index > index:
            self._active_index -= 1

    def clear(self):
        """Elimina todas las capas."""
        self._layers.clear()
        self._active_index = -1
        self.layers_cleared.emit()
        logger.info("Todas las capas eliminadas")

    # ------------------------------------------------------------------
    # Active layer
    # ------------------------------------------------------------------

    def set_active(self, index: int):
        """Establece la capa activa."""
        if 0 <= index < len(self._layers):
            self._active_index = index
            self.active_layer_changed.emit(index)

    # ------------------------------------------------------------------
    # Visibility
    # ------------------------------------------------------------------

    def set_visibility(self, index: int, visible: bool):
        """Cambia la visibilidad de una capa."""
        if 0 <= index < len(self._layers):
            self._layers[index].visible = visible
            self.layer_visibility_changed.emit(index, visible)

    def toggle_visibility(self, index: int):
        if 0 <= index < len(self._layers):
            new_vis = not self._layers[index].visible
            self.set_visibility(index, new_vis)

    # ------------------------------------------------------------------
    # Rename / Move
    # ------------------------------------------------------------------

    def rename_layer(self, index: int, name: str):
        if 0 <= index < len(self._layers):
            self._layers[index].name = name
            self.layer_renamed.emit(index, name)

    def move_layer(self, from_idx: int, to_idx: int):
        if not (0 <= from_idx < len(self._layers)):
            return
        to_idx = max(0, min(to_idx, len(self._layers) - 1))
        entry = self._layers.pop(from_idx)
        self._layers.insert(to_idx, entry)
        self.layer_moved.emit(from_idx, to_idx)

        # Ajustar activo
        if self._active_index == from_idx:
            self._active_index = to_idx
        elif from_idx < self._active_index <= to_idx:
            self._active_index -= 1
        elif to_idx <= self._active_index < from_idx:
            self._active_index += 1

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_entry(self, index: int) -> Optional[LayerEntry]:
        if 0 <= index < len(self._layers):
            return self._layers[index]
        return None

    def get_layer(self, index: int) -> Optional[LayerType]:
        entry = self.get_entry(index)
        return entry.layer if entry else None

    def get_all_entries(self) -> List[LayerEntry]:
        return list(self._layers)

    def get_point_clouds(self) -> List[PointCloudData]:
        return [e.layer for e in self._layers if e.is_point_cloud]

    def get_rasters(self) -> List[RasterLayer]:
        return [e.layer for e in self._layers if e.is_raster]

    def get_visible_entries(self) -> List[LayerEntry]:
        return [e for e in self._layers if e.visible]

    def find_by_name(self, name: str) -> Optional[int]:
        for i, entry in enumerate(self._layers):
            if entry.name == name:
                return i
        return None

    def replace_layer(self, index: int, new_layer: LayerType):
        """Reemplaza los datos de una capa existente (mantiene posición y visibilidad)."""
        if 0 <= index < len(self._layers):
            old_name = self._layers[index].name
            self._layers[index].layer = new_layer
            if new_layer.name == "Sin nombre":
                new_layer.name = old_name
            logger.info(f"Capa [{index}] actualizada: {new_layer.name}")
