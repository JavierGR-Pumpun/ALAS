"""
ALAS — Settings Dialog
Application preferences: display, processing defaults, and general options.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QComboBox, QSlider, QDoubleSpinBox, QSpinBox,
    QPushButton, QFrame, QColorDialog, QCheckBox, QFormLayout,
    QGroupBox, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette

from app.i18n import tr, set_language
from app.config import (
    DEFAULT_POINT_SIZE, DEFAULT_DEM_RESOLUTION,
    DEFAULT_BACKGROUND_COLOR, DEFAULT_IDW_POWER
)


class _ColorButton(QPushButton):
    color_changed = pyqtSignal(str)

    def __init__(self, color: str = "#000000", parent=None):
        super().__init__(parent)
        self._color = color
        self._apply_color(color)
        self.setFixedSize(80, 28)
        self.clicked.connect(self._pick)

    def _apply_color(self, hex_color: str):
        self._color = hex_color
        self.setStyleSheet(
            f"background-color: {hex_color}; border: 1px solid #555; border-radius: 4px;"
        )

    def _pick(self):
        col = QColorDialog.getColor(QColor(self._color), self, tr("settings.pick_color"))
        if col.isValid():
            self._apply_color(col.name())
            self.color_changed.emit(self._color)

    def color(self) -> str:
        return self._color

    def set_color(self, hex_color: str):
        self._apply_color(hex_color)


class SettingsDialog(QDialog):
    """
    Application settings modal.
    Changes are applied immediately on Save; Cancel discards them.
    """

    settings_changed = pyqtSignal(dict)

    def __init__(self, preferences, parent=None):
        super().__init__(parent)
        self._prefs = preferences
        self.setWindowTitle(tr("menu.settings"))
        self.setMinimumWidth(460)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self._build_ui()
        self._load_values()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        tabs = QTabWidget()

        tabs.addTab(self._build_general_tab(), tr("settings.tab_general"))
        tabs.addTab(self._build_display_tab(), tr("settings.tab_display"))
        tabs.addTab(self._build_processing_tab(), tr("settings.tab_processing"))

        root.addWidget(tabs)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(
            self._restore_defaults
        )
        root.addWidget(buttons)

    # --- General tab ---
    def _build_general_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(16)

        # Language
        lang_group = QGroupBox(tr("settings.language"))
        lang_form = QFormLayout(lang_group)
        lang_form.setSpacing(8)

        self._lang_combo = QComboBox()
        self._lang_combo.addItem(tr("lang.spanish"), "es")
        self._lang_combo.addItem(tr("lang.english"), "en")
        lang_form.addRow(tr("settings.interface_language"), self._lang_combo)
        layout.addWidget(lang_group)

        # Startup
        startup_group = QGroupBox(tr("settings.startup"))
        startup_form = QFormLayout(startup_group)
        startup_form.setSpacing(8)

        self._restore_geometry_check = QCheckBox()
        startup_form.addRow(tr("settings.restore_window"), self._restore_geometry_check)

        self._decimate_on_open_check = QCheckBox()
        startup_form.addRow(tr("settings.ask_decimate"), self._decimate_on_open_check)

        layout.addWidget(startup_group)
        layout.addStretch()
        return w

    # --- Display tab ---
    def _build_display_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(16)

        # Viewport
        vp_group = QGroupBox(tr("settings.viewport"))
        vp_form = QFormLayout(vp_group)
        vp_form.setSpacing(8)

        self._bg_btn = _ColorButton(DEFAULT_BACKGROUND_COLOR)
        vp_form.addRow(tr("settings.background_color"), self._bg_btn)

        self._point_size_spin = QDoubleSpinBox()
        self._point_size_spin.setRange(0.5, 20.0)
        self._point_size_spin.setSingleStep(0.5)
        self._point_size_spin.setDecimals(1)
        self._point_size_spin.setSuffix(" px")
        vp_form.addRow(tr("settings.default_point_size"), self._point_size_spin)

        layout.addWidget(vp_group)

        # Colorization
        color_group = QGroupBox(tr("settings.colorization"))
        color_form = QFormLayout(color_group)
        color_form.setSpacing(8)

        self._default_colorize_combo = QComboBox()
        self._default_colorize_combo.addItem(tr("colorize.height_label"), "height")
        self._default_colorize_combo.addItem(tr("colorize.intensity_label"), "intensity")
        self._default_colorize_combo.addItem(tr("colorize.classification_label"), "classification")
        self._default_colorize_combo.addItem(tr("colorize.return_label"), "return_number")
        self._default_colorize_combo.addItem(tr("colorize.rgb_label"), "rgb")
        color_form.addRow(tr("settings.default_colorize"), self._default_colorize_combo)

        layout.addWidget(color_group)
        layout.addStretch()
        return w

    # --- Processing tab ---
    def _build_processing_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(16)

        # DEM defaults
        dem_group = QGroupBox(tr("settings.dem_defaults"))
        dem_form = QFormLayout(dem_group)
        dem_form.setSpacing(8)

        self._dem_res_spin = QDoubleSpinBox()
        self._dem_res_spin.setRange(0.1, 100.0)
        self._dem_res_spin.setSingleStep(0.1)
        self._dem_res_spin.setDecimals(2)
        self._dem_res_spin.setSuffix(" m")
        dem_form.addRow(tr("settings.dem_resolution"), self._dem_res_spin)

        self._interp_combo = QComboBox()
        self._interp_combo.addItem(tr("dem.method_idw"), "idw")
        self._interp_combo.addItem(tr("dem.method_tin"), "tin")
        self._interp_combo.addItem(tr("dem.method_nearest"), "nearest")
        dem_form.addRow(tr("settings.interpolation"), self._interp_combo)

        self._idw_power_spin = QDoubleSpinBox()
        self._idw_power_spin.setRange(1.0, 6.0)
        self._idw_power_spin.setSingleStep(0.5)
        self._idw_power_spin.setDecimals(1)
        dem_form.addRow(tr("settings.idw_power"), self._idw_power_spin)

        layout.addWidget(dem_group)

        # Classification defaults
        cls_group = QGroupBox(tr("settings.classification_defaults"))
        cls_form = QFormLayout(cls_group)
        cls_form.setSpacing(8)

        self._default_algo_combo = QComboBox()
        self._default_algo_combo.addItem("SMRF", "smrf")
        self._default_algo_combo.addItem("CSF", "csf")
        self._default_algo_combo.addItem("PMF", "pmf")
        cls_form.addRow(tr("settings.default_algorithm"), self._default_algo_combo)

        self._classify_veg_check = QCheckBox()
        cls_form.addRow(tr("settings.classify_vegetation"), self._classify_veg_check)

        layout.addWidget(cls_group)
        layout.addStretch()
        return w

    # ------------------------------------------------------------------
    # Load / save / defaults
    # ------------------------------------------------------------------

    def _load_values(self):
        p = self._prefs

        # General
        lang = p.get("language", "es")
        idx = self._lang_combo.findData(lang)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)

        self._restore_geometry_check.setChecked(p.get("restore_geometry", True))
        self._decimate_on_open_check.setChecked(p.get("ask_decimate_on_open", True))

        # Display
        self._bg_btn.set_color(p.get("background_color", DEFAULT_BACKGROUND_COLOR))
        self._point_size_spin.setValue(float(p.get("default_point_size", DEFAULT_POINT_SIZE)))
        colorize = p.get("default_colorize", "height")
        idx = self._default_colorize_combo.findData(colorize)
        if idx >= 0:
            self._default_colorize_combo.setCurrentIndex(idx)

        # Processing
        self._dem_res_spin.setValue(float(p.get("dem_resolution", DEFAULT_DEM_RESOLUTION)))
        interp = p.get("interpolation_method", "idw")
        idx = self._interp_combo.findData(interp)
        if idx >= 0:
            self._interp_combo.setCurrentIndex(idx)
        self._idw_power_spin.setValue(float(p.get("idw_power", DEFAULT_IDW_POWER)))
        algo = p.get("default_classification_algo", "smrf")
        idx = self._default_algo_combo.findData(algo)
        if idx >= 0:
            self._default_algo_combo.setCurrentIndex(idx)
        self._classify_veg_check.setChecked(p.get("classify_vegetation_default", False))

    def _collect_values(self) -> dict:
        return {
            "language": self._lang_combo.currentData(),
            "restore_geometry": self._restore_geometry_check.isChecked(),
            "ask_decimate_on_open": self._decimate_on_open_check.isChecked(),
            "background_color": self._bg_btn.color(),
            "default_point_size": self._point_size_spin.value(),
            "default_colorize": self._default_colorize_combo.currentData(),
            "dem_resolution": self._dem_res_spin.value(),
            "interpolation_method": self._interp_combo.currentData(),
            "idw_power": self._idw_power_spin.value(),
            "default_classification_algo": self._default_algo_combo.currentData(),
            "classify_vegetation_default": self._classify_veg_check.isChecked(),
        }

    def _on_save(self):
        values = self._collect_values()
        for key, val in values.items():
            self._prefs.set(key, val)
        self._prefs.save()
        set_language(values["language"])
        self.settings_changed.emit(values)
        self.accept()

    def _restore_defaults(self):
        self._lang_combo.setCurrentIndex(self._lang_combo.findData("es"))
        self._restore_geometry_check.setChecked(True)
        self._decimate_on_open_check.setChecked(True)
        self._bg_btn.set_color(DEFAULT_BACKGROUND_COLOR)
        self._point_size_spin.setValue(DEFAULT_POINT_SIZE)
        self._default_colorize_combo.setCurrentIndex(0)
        self._dem_res_spin.setValue(DEFAULT_DEM_RESOLUTION)
        self._interp_combo.setCurrentIndex(0)
        self._idw_power_spin.setValue(DEFAULT_IDW_POWER)
        self._default_algo_combo.setCurrentIndex(0)
        self._classify_veg_check.setChecked(False)
