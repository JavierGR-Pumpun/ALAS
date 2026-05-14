"""
ALAS — Layer Panel
Layer panel with tree, visibility, and context menu. Also hosts the
collapsible "Figures" group for geometric figures placed in the viewport.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QMenu, QHeaderView, QAbstractItemView, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QColor, QBrush, QFont, QAction

from app.core.layer_manager import LayerManager, LayerEntry
from app.i18n import tr
from app.logger import get_logger

logger = get_logger("ui.layer_panel")

# UserRole tags stored on tree items to distinguish figures from layers
_ROLE_KIND  = Qt.ItemDataRole.UserRole       # "layer" | "figure" | "figures_group"
_ROLE_INDEX = Qt.ItemDataRole.UserRole + 1   # layer index  or  figure id


class LayerPanel(QWidget):
    """Layer panel with QTreeWidget."""

    zoom_to_layer_requested  = pyqtSignal(int)
    export_layer_requested   = pyqtSignal(int)
    figure_edit_requested    = pyqtSignal(int)   # figure id
    figure_remove_requested  = pyqtSignal(int)   # figure id

    def __init__(self, layer_manager: LayerManager, parent=None):
        super().__init__(parent)
        self.layer_manager = layer_manager
        self._figures_root: QTreeWidgetItem | None = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("panel.layers"), tr("layer.type")])
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
        self.layer_manager.layer_added.connect(self._on_layer_added)
        self.layer_manager.layer_removed.connect(self._on_layer_removed)
        self.layer_manager.layer_renamed.connect(self._on_layer_renamed)
        self.layer_manager.layers_cleared.connect(self._on_layers_cleared)

        self.tree.currentItemChanged.connect(self._on_selection_changed)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemClicked.connect(self._on_item_clicked)

    # ------------------------------------------------------------------
    # Layer manager callbacks
    # ------------------------------------------------------------------

    def _on_layer_added(self, index: int):
        entry = self.layer_manager.get_entry(index)
        if entry is None:
            return

        item = QTreeWidgetItem()
        item.setText(0, entry.name)
        item.setText(1, tr("layer.pc") if entry.is_point_cloud else tr("layer.rl"))
        item.setCheckState(0, Qt.CheckState.Checked if entry.visible else Qt.CheckState.Unchecked)
        item.setData(0, _ROLE_KIND,  "layer")
        item.setData(0, _ROLE_INDEX, index)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)

        if entry.is_point_cloud:
            item.setForeground(1, QBrush(QColor("#7c3aed")))
        else:
            item.setForeground(1, QBrush(QColor("#22d3ee")))

        self.tree.addTopLevelItem(item)
        self.tree.setCurrentItem(item)

    def _on_layer_removed(self, index: int):
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if (item.data(0, _ROLE_KIND) == "layer"
                    and item.data(0, _ROLE_INDEX) == index):
                self.tree.takeTopLevelItem(i)
                self._refresh_layer_indices()
                return

    def _on_layer_renamed(self, index: int, name: str):
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if (item.data(0, _ROLE_KIND) == "layer"
                    and item.data(0, _ROLE_INDEX) == index):
                item.setText(0, name)
                return

    def _on_layers_cleared(self):
        # Remove only layer items, keep the figures group
        to_remove = []
        for i in range(self.tree.topLevelItemCount()):
            if self.tree.topLevelItem(i).data(0, _ROLE_KIND) == "layer":
                to_remove.append(i)
        for i in reversed(to_remove):
            self.tree.takeTopLevelItem(i)

    # ------------------------------------------------------------------
    # Selection / edit
    # ------------------------------------------------------------------

    def _on_selection_changed(self, current, previous):
        if current is None:
            return
        if current.data(0, _ROLE_KIND) == "layer":
            idx = current.data(0, _ROLE_INDEX)
            if idx is not None:
                self.layer_manager.set_active(idx)

    def _on_item_changed(self, item, column):
        if column == 0 and item.data(0, _ROLE_KIND) == "layer":
            idx = item.data(0, _ROLE_INDEX)
            if idx is not None:
                visible = item.checkState(0) == Qt.CheckState.Checked
                self.layer_manager.set_visibility(idx, visible)

    def _on_item_clicked(self, item, column):
        if item.data(0, _ROLE_KIND) == "figure":
            fig_id = item.data(0, _ROLE_INDEX)
            if fig_id is not None:
                self.figure_edit_requested.emit(fig_id)

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def _show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if item is None:
            return
        kind = item.data(0, _ROLE_KIND)

        if kind == "layer":
            self._layer_context_menu(item, pos)
        elif kind == "figure":
            self._figure_context_menu(item, pos)

    def _layer_context_menu(self, item, pos):
        idx = item.data(0, _ROLE_INDEX)
        if idx is None:
            return
        menu = QMenu(self)
        a_zoom = QAction(tr("layer.zoom_to"), self)
        a_zoom.triggered.connect(lambda: self.zoom_to_layer_requested.emit(idx))
        menu.addAction(a_zoom)
        menu.addSeparator()
        a_rename = QAction(tr("layer.rename"), self)
        a_rename.triggered.connect(lambda: self._rename_layer(idx))
        menu.addAction(a_rename)
        a_export = QAction(tr("layer.export"), self)
        a_export.triggered.connect(lambda: self.export_layer_requested.emit(idx))
        menu.addAction(a_export)
        menu.addSeparator()
        a_remove = QAction(tr("layer.remove"), self)
        a_remove.triggered.connect(lambda: self._remove_layer(idx))
        menu.addAction(a_remove)
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _figure_context_menu(self, item, pos):
        fig_id = item.data(0, _ROLE_INDEX)
        if fig_id is None:
            return
        menu = QMenu(self)
        a_edit = QAction(tr("fig.edit"), self)
        a_edit.triggered.connect(lambda: self.figure_edit_requested.emit(fig_id))
        menu.addAction(a_edit)
        menu.addSeparator()
        a_remove = QAction(tr("fig.remove_selected"), self)
        a_remove.triggered.connect(lambda: self.figure_remove_requested.emit(fig_id))
        menu.addAction(a_remove)
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------------
    # Figures group — public API called from main_window
    # ------------------------------------------------------------------

    def _ensure_figures_root(self) -> QTreeWidgetItem:
        if self._figures_root is None or self._figures_root.treeWidget() is None:
            root = QTreeWidgetItem()
            root.setText(0, tr("layer.figures"))
            root.setText(1, "")
            root.setData(0, _ROLE_KIND, "figures_group")
            root.setFlags(root.flags() & ~Qt.ItemFlag.ItemIsSelectable
                          & ~Qt.ItemFlag.ItemIsDragEnabled
                          & ~Qt.ItemFlag.ItemIsDropEnabled)
            font = QFont()
            font.setBold(True)
            root.setFont(0, font)
            root.setForeground(0, QBrush(QColor("#a855f7")))
            self.tree.addTopLevelItem(root)
            root.setExpanded(True)
            self._figures_root = root
        return self._figures_root

    def add_figure_item(self, figure_id: int, ftype: str, params_text: str):
        """Add a child row under the Figures group."""
        root = self._ensure_figures_root()
        item = QTreeWidgetItem()
        item.setText(0, f"{tr(f'fig.type_{ftype}')}  #{figure_id}")
        item.setText(1, params_text)
        item.setData(0, _ROLE_KIND,  "figure")
        item.setData(0, _ROLE_INDEX, figure_id)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable
                      & ~Qt.ItemFlag.ItemIsDragEnabled
                      & ~Qt.ItemFlag.ItemIsDropEnabled)
        item.setForeground(0, QBrush(QColor("#d0a0ff")))
        item.setForeground(1, QBrush(QColor("#888899")))
        item.setToolTip(0, tr("fig.edit_tooltip"))
        root.addChild(item)

    def update_figure_item(self, figure_id: int, ftype: str, params_text: str):
        """Update the label of an existing figure child row."""
        root = self._figures_root
        if root is None:
            return
        for i in range(root.childCount()):
            child = root.child(i)
            if child.data(0, _ROLE_INDEX) == figure_id:
                child.setText(0, f"{tr(f'fig.type_{ftype}')}  #{figure_id}")
                child.setText(1, params_text)
                return

    def remove_figure_item(self, figure_id: int):
        """Remove a figure child row. Hides the group if it becomes empty."""
        root = self._figures_root
        if root is None:
            return
        for i in range(root.childCount()):
            if root.child(i).data(0, _ROLE_INDEX) == figure_id:
                root.takeChild(i)
                break
        if root.childCount() == 0:
            idx = self.tree.indexOfTopLevelItem(root)
            if idx >= 0:
                self.tree.takeTopLevelItem(idx)
            self._figures_root = None

    def clear_figure_items(self):
        """Remove the entire Figures group."""
        if self._figures_root is not None:
            idx = self.tree.indexOfTopLevelItem(self._figures_root)
            if idx >= 0:
                self.tree.takeTopLevelItem(idx)
            self._figures_root = None

    # ------------------------------------------------------------------
    # Layer helpers
    # ------------------------------------------------------------------

    def _rename_layer(self, index: int):
        entry = self.layer_manager.get_entry(index)
        if entry is None:
            return
        new_name, ok = QInputDialog.getText(
            self, tr("layer.rename"), tr("layer.name_label"), text=entry.name
        )
        if ok and new_name.strip():
            self.layer_manager.rename_layer(index, new_name.strip())

    def _remove_layer(self, index: int):
        entry = self.layer_manager.get_entry(index)
        if entry is None:
            return
        reply = QMessageBox.question(
            self, tr("layer.remove"),
            tr("layer.remove_confirm").format(entry.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.layer_manager.remove_layer(index)

    def _refresh_layer_indices(self):
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.data(0, _ROLE_KIND) == "layer":
                item.setData(0, _ROLE_INDEX, i)
