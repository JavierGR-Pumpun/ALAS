"""
ALAS — Layer Panel
Panel de capas con árbol, visibilidad y menú contextual.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QMenu, QHeaderView, QAbstractItemView, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QColor, QBrush, QAction

from app.core.layer_manager import LayerManager, LayerEntry
from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.layer_panel")


class LayerPanel(QWidget):
    """Panel de capas con QTreeWidget."""

    zoom_to_layer_requested = pyqtSignal(int)
    export_layer_requested = pyqtSignal(int)

    def __init__(self, layer_manager: LayerManager, parent=None):
        super().__init__(parent)
        self.layer_manager = layer_manager
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("panel.layers"), "Tipo"])
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.setAlternatingRowColors(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(12)

        layout.addWidget(self.tree)

    def _connect_signals(self):
        # Layer manager signals
        self.layer_manager.layer_added.connect(self._on_layer_added)
        self.layer_manager.layer_removed.connect(self._on_layer_removed)
        self.layer_manager.layer_renamed.connect(self._on_layer_renamed)
        self.layer_manager.layers_cleared.connect(self._on_layers_cleared)

        # Tree signals
        self.tree.currentItemChanged.connect(self._on_selection_changed)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)

    def _on_layer_added(self, index: int):
        entry = self.layer_manager.get_entry(index)
        if entry is None:
            return

        item = QTreeWidgetItem()
        item.setText(0, entry.name)
        item.setText(1, "☁" if entry.is_point_cloud else "▦")
        item.setCheckState(0, Qt.CheckState.Checked if entry.visible else Qt.CheckState.Unchecked)
        item.setData(0, Qt.ItemDataRole.UserRole, index)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)

        # Color de tipo
        if entry.is_point_cloud:
            item.setForeground(1, QBrush(QColor("#7c3aed")))
        else:
            item.setForeground(1, QBrush(QColor("#22d3ee")))

        self.tree.addTopLevelItem(item)
        self.tree.setCurrentItem(item)

    def _on_layer_removed(self, index: int):
        if 0 <= index < self.tree.topLevelItemCount():
            self.tree.takeTopLevelItem(index)
            self._refresh_indices()

    def _on_layer_renamed(self, index: int, name: str):
        if 0 <= index < self.tree.topLevelItemCount():
            self.tree.topLevelItem(index).setText(0, name)

    def _on_layers_cleared(self):
        self.tree.clear()

    def _on_selection_changed(self, current, previous):
        if current is not None:
            idx = current.data(0, Qt.ItemDataRole.UserRole)
            if idx is not None:
                self.layer_manager.set_active(idx)

    def _on_item_changed(self, item, column):
        if column == 0:
            idx = item.data(0, Qt.ItemDataRole.UserRole)
            if idx is not None:
                visible = item.checkState(0) == Qt.CheckState.Checked
                self.layer_manager.set_visibility(idx, visible)

    def _show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if item is None:
            return

        idx = item.data(0, Qt.ItemDataRole.UserRole)
        if idx is None:
            return

        menu = QMenu(self)

        action_zoom = QAction(tr("layer.zoom_to"), self)
        action_zoom.triggered.connect(lambda: self.zoom_to_layer_requested.emit(idx))
        menu.addAction(action_zoom)

        menu.addSeparator()

        action_rename = QAction(tr("layer.rename"), self)
        action_rename.triggered.connect(lambda: self._rename_layer(idx))
        menu.addAction(action_rename)

        action_export = QAction(tr("layer.export"), self)
        action_export.triggered.connect(lambda: self.export_layer_requested.emit(idx))
        menu.addAction(action_export)

        menu.addSeparator()

        action_remove = QAction(tr("layer.remove"), self)
        action_remove.triggered.connect(lambda: self._remove_layer(idx))
        menu.addAction(action_remove)

        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _rename_layer(self, index: int):
        entry = self.layer_manager.get_entry(index)
        if entry is None:
            return
        new_name, ok = QInputDialog.getText(
            self, tr("layer.rename"), "Nombre:", text=entry.name
        )
        if ok and new_name.strip():
            self.layer_manager.rename_layer(index, new_name.strip())

    def _remove_layer(self, index: int):
        entry = self.layer_manager.get_entry(index)
        if entry is None:
            return
        reply = QMessageBox.question(
            self, tr("layer.remove"),
            f"¿Eliminar capa '{entry.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.layer_manager.remove_layer(index)

    def _refresh_indices(self):
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setData(0, Qt.ItemDataRole.UserRole, i)
