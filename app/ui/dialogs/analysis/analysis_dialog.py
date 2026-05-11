"""
ALAS — Analysis Dialog
Assembles the four analysis tab widgets into a tabbed dialog.
Each tab is a self-contained class in its own module.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton,
)

from app.core.layer_manager import LayerManager
from app.i18n import tr

from .geomorphology import GeomorphologyTab
from .hydrology import HydrologyTab
from .vegetation import VegetationTab
from .multitemporal import MultitemporalTab


_TAB_NAMES = ["geomorphology", "hydrology", "vegetation", "multitemporal"]
_TAB_INDEX = {name: i for i, name in enumerate(_TAB_NAMES)}


class AnalysisDialog(QDialog):
    """Tabbed analysis dialog. Each tab is an independent QWidget subclass."""

    def __init__(self, initial_tab: str, layer_manager: LayerManager, parent=None):
        super().__init__(parent)
        self.layer_manager = layer_manager
        self.setWindowTitle(tr("menu.analysis"))
        self.setMinimumSize(550, 600)
        self._setup_ui(initial_tab)

        self.layer_manager.layer_added.connect(self._refresh_combos)
        self.layer_manager.layer_removed.connect(self._refresh_combos)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_tab(self, tab_name: str):
        """Switch to the named tab programmatically."""
        self._tabs.setCurrentIndex(_TAB_INDEX.get(tab_name, 0))

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_ui(self, initial_tab: str):
        layout = QVBoxLayout(self)

        main_window = self.parent()

        self._tabs = QTabWidget()

        self._geo_tab = GeomorphologyTab(self.layer_manager, main_window)
        self._tabs.addTab(self._geo_tab, tr("analysis.geomorphology"))

        self._hydro_tab = HydrologyTab(self.layer_manager, main_window)
        self._tabs.addTab(self._hydro_tab, tr("analysis.hydrology"))

        self._veg_tab = VegetationTab(self.layer_manager, main_window)
        self._tabs.addTab(self._veg_tab, tr("analysis.vegetation"))

        self._multi_tab = MultitemporalTab(self.layer_manager, main_window)
        self._tabs.addTab(self._multi_tab, tr("analysis.multitemporal"))

        self._tabs.setCurrentIndex(_TAB_INDEX.get(initial_tab, 0))
        layout.addWidget(self._tabs)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton(tr("dialog.close"))
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Combo refresh
    # ------------------------------------------------------------------

    def _refresh_combos(self, *args):
        """Propagate layer-list changes to every tab."""
        self._geo_tab.refresh_combos()
        self._hydro_tab.refresh_combos()
        self._veg_tab.refresh_combos()
        self._multi_tab.refresh_combos()