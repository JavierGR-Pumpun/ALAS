"""
ALAS — Configuration & Constants
Global constants, ASPRS codes, color palettes, file filters.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
RESOURCES_DIR = ROOT_DIR / "resources"
ICONS_DIR = RESOURCES_DIR / "icons"
STYLES_DIR = RESOURCES_DIR / "styles"
COLORMAPS_DIR = RESOURCES_DIR / "colormaps"
MODELS_DIR    = RESOURCES_DIR / "models"

# ---------------------------------------------------------------------------
# User preferences file
# ---------------------------------------------------------------------------
USER_CONFIG_DIR = Path.home() / ".alas"
USER_CONFIG_FILE = USER_CONFIG_DIR / "preferences.json"

# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------
APP_NAME = "ALAS"
APP_FULL_NAME = "Aerial LiDAR Analysis Software"
APP_VERSION = "1.0.0"
APP_ORGANIZATION = "ALAS Project"

# ---------------------------------------------------------------------------
# Supported file formats
# ---------------------------------------------------------------------------
POINT_CLOUD_EXTENSIONS = [".las", ".laz"]
RASTER_EXTENSIONS = [".tif", ".tiff", ".geotiff"]
VECTOR_EXTENSIONS = [".shp", ".geojson", ".gpkg"]
MESH_EXTENSIONS = [".obj", ".ply", ".stl"]

POINT_CLOUD_FILTER = "Point clouds (*.las *.laz);;All files (*)"
RASTER_FILTER = "GeoTIFF (*.tif *.tiff);;All files (*)"
VECTOR_FILTER = "Shapefile (*.shp);;GeoJSON (*.geojson);;GeoPackage (*.gpkg);;All (*)"

# ---------------------------------------------------------------------------
# ASPRS LAS Classification Codes (v1.4)
# ---------------------------------------------------------------------------
ASPRS_CLASSIFICATION = {
    0: "Created / Never Classified",
    1: "Unclassified",
    2: "Ground",
    3: "Low Vegetation",
    4: "Medium Vegetation",
    5: "High Vegetation",
    6: "Building",
    7: "Low Point (Noise)",
    8: "Model Key-point",
    9: "Water",
    10: "Rail",
    11: "Road Surface",
    12: "Overlap",
    13: "Wire - Guard (Shield)",
    14: "Wire - Conductor (Phase)",
    15: "Transmission Tower",
    16: "Wire-structure Connector",
    17: "Bridge Deck",
    18: "High Noise",
}

# Standard ASPRS colors (RGBA 0-255)
ASPRS_COLORS = {
    0: (180, 180, 180, 255),   # Light gray
    1: (200, 200, 200, 255),   # Gray
    2: (139, 90, 43, 255),     # Brown earth
    3: (144, 238, 144, 255),   # Light green
    4: (34, 139, 34, 255),     # Medium green
    5: (0, 100, 0, 255),       # Dark green
    6: (255, 0, 0, 255),       # Red buildings
    7: (255, 105, 180, 255),   # Pink noise
    8: (255, 255, 0, 255),     # Yellow
    9: (0, 0, 255, 255),       # Blue water
    10: (160, 82, 45, 255),    # Sienna rail
    11: (64, 64, 64, 255),     # Dark gray road
    12: (255, 165, 0, 255),    # Orange overlap
    13: (128, 0, 128, 255),    # Purple
    14: (255, 215, 0, 255),    # Gold
    15: (192, 192, 192, 255),  # Silver
    16: (0, 255, 255, 255),    # Cyan
    17: (210, 180, 140, 255),  # Tan
    18: (255, 0, 255, 255),    # Magenta
}

# ---------------------------------------------------------------------------
# Colorization modes
# ---------------------------------------------------------------------------
COLORIZE_HEIGHT = "height"
COLORIZE_INTENSITY = "intensity"
COLORIZE_CLASSIFICATION = "classification"
COLORIZE_RETURN_NUMBER = "return_number"
COLORIZE_RGB = "rgb"
COLORIZE_SINGLE = "single_color"

COLORIZE_MODES = [
    COLORIZE_HEIGHT,
    COLORIZE_INTENSITY,
    COLORIZE_CLASSIFICATION,
    COLORIZE_RETURN_NUMBER,
    COLORIZE_RGB,
    COLORIZE_SINGLE,
]

# ---------------------------------------------------------------------------
# Default colormaps (matplotlib names)
# ---------------------------------------------------------------------------
DEFAULT_HEIGHT_CMAP = "terrain"
DEFAULT_INTENSITY_CMAP = "gray"
DEFAULT_SLOPE_CMAP = "RdYlGn_r"
DEFAULT_ASPECT_CMAP = "hsv"
DEFAULT_CURVATURE_CMAP = "RdBu_r"
DEFAULT_HILLSHADE_CMAP = "gray"
DEFAULT_FLOW_ACC_CMAP = "Blues"
DEFAULT_CHM_CMAP = "YlGn"

# ---------------------------------------------------------------------------
# DEM generation defaults
# ---------------------------------------------------------------------------
DEFAULT_DEM_RESOLUTION = 1.0           # meters
DEFAULT_INTERPOLATION_METHOD = "idw"   # idw, tin, nearest
DEFAULT_IDW_POWER = 2.0
DEFAULT_GEOTIFF_COMPRESS = "lzw"
DEFAULT_NODATA = -9999.0

# ---------------------------------------------------------------------------
# Classification algorithm defaults
# ---------------------------------------------------------------------------
SMRF_DEFAULTS = {
    "window": 18.0,
    "slope": 0.15,
    "threshold": 0.5,
    "scalar": 1.25,
}

CSF_DEFAULTS = {
    "resolution": 0.5,
    "threshold": 0.5,
    "rigidness": 2,
    "iterations": 500,
}

PMF_DEFAULTS = {
    "max_window_size": 33.0,
    "slope": 1.0,
    "initial_distance": 0.15,
    "max_distance": 2.5,
}

# ---------------------------------------------------------------------------
# Vegetation analysis defaults
# ---------------------------------------------------------------------------
DEFAULT_MIN_TREE_HEIGHT = 2.0   # meters
DEFAULT_CROWN_WINDOW = 5        # pixels
DEFAULT_CANOPY_CELL_SIZE = 10   # meters

# ---------------------------------------------------------------------------
# Hillshade defaults
# ---------------------------------------------------------------------------
DEFAULT_HILLSHADE_AZIMUTH = 315.0
DEFAULT_HILLSHADE_ALTITUDE = 45.0

# ---------------------------------------------------------------------------
# Hydrology defaults
# ---------------------------------------------------------------------------
DEFAULT_FLOW_ACC_THRESHOLD = 1000  # accumulated cells for drainage network

# ---------------------------------------------------------------------------
# Visualization defaults
# ---------------------------------------------------------------------------
DEFAULT_POINT_SIZE = 2.0
DEFAULT_BACKGROUND_COLOR = "#000000"
MAX_VIEWPORT_POINTS = 50_000_000   # automatic decimation if exceeded
VOXEL_DOWNSAMPLE_SIZE = 0.5       # meters by default

# ---------------------------------------------------------------------------
# Above-ground classification height thresholds (meters)
# ---------------------------------------------------------------------------
LOW_VEG_MAX_HEIGHT = 0.5
MEDIUM_VEG_MAX_HEIGHT = 2.0
HIGH_VEG_MAX_HEIGHT = 100.0
BUILDING_MIN_HEIGHT = 2.0

# ---------------------------------------------------------------------------
# Change detection defaults
# ---------------------------------------------------------------------------
DEFAULT_DOD_THRESHOLD = 0.3  # meters, erosion/deposition threshold

# ---------------------------------------------------------------------------
# Languages
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES = ["es", "en"]
DEFAULT_LANGUAGE = "es"
