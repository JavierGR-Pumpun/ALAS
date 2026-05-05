"""
ALAS — Internationalization (i18n)
Sistema bilingüe ES / EN con diccionarios de traducción.
"""

from app.config import DEFAULT_LANGUAGE

# ---------------------------------------------------------------------------
# Translation dictionaries
# ---------------------------------------------------------------------------
_TRANSLATIONS = {
    # --- Menu ---
    "menu.file": {"es": "Archivo", "en": "File"},
    "menu.edit": {"es": "Editar", "en": "Edit"},
    "menu.view": {"es": "Vista", "en": "View"},
    "menu.process": {"es": "Procesamiento", "en": "Processing"},
    "menu.analysis": {"es": "Análisis", "en": "Analysis"},
    "menu.tools": {"es": "Herramientas", "en": "Tools"},
    "menu.help": {"es": "Ayuda", "en": "Help"},

    # --- File menu ---
    "action.open": {"es": "Abrir archivo...", "en": "Open file..."},
    "action.open_multiple": {"es": "Abrir múltiples archivos...", "en": "Open multiple files..."},
    "action.save_project": {"es": "Guardar proyecto", "en": "Save project"},
    "action.load_project": {"es": "Cargar proyecto", "en": "Load project"},
    "action.export": {"es": "Exportar...", "en": "Export..."},
    "action.exit": {"es": "Salir", "en": "Exit"},

    # --- View menu ---
    "action.reset_view": {"es": "Restablecer vista", "en": "Reset view"},
    "action.top_view": {"es": "Vista superior", "en": "Top view"},
    "action.front_view": {"es": "Vista frontal", "en": "Front view"},
    "action.side_view": {"es": "Vista lateral", "en": "Side view"},
    "action.fullscreen": {"es": "Pantalla completa", "en": "Fullscreen"},

    # --- Processing ---
    "action.merge_tiles": {"es": "Fusionar tiles", "en": "Merge tiles"},
    "action.filter_noise": {"es": "Filtrar ruido", "en": "Filter noise"},
    "action.reproject": {"es": "Reproyectar...", "en": "Reproject..."},
    "action.decimate": {"es": "Decimar nube", "en": "Decimate cloud"},
    "action.remove_overlap": {"es": "Eliminar solapamiento", "en": "Remove overlap"},
    "action.classify": {"es": "Clasificar terreno...", "en": "Classify terrain..."},
    "action.generate_dem": {"es": "Generar modelo digital...", "en": "Generate digital model..."},

    # --- Analysis ---
    "action.geomorphology": {"es": "Análisis geomorfológico...", "en": "Geomorphological analysis..."},
    "action.hydrology": {"es": "Análisis hidrológico...", "en": "Hydrological analysis..."},
    "action.vegetation": {"es": "Análisis de vegetación...", "en": "Vegetation analysis..."},
    "action.measurements": {"es": "Mediciones...", "en": "Measurements..."},
    "action.multitemporal": {"es": "Análisis multitemporal...", "en": "Multitemporal analysis..."},

    # --- Tools ---
    "action.profile": {"es": "Perfil topográfico", "en": "Topographic profile"},
    "action.distance": {"es": "Medir distancia", "en": "Measure distance"},
    "action.area": {"es": "Medir área", "en": "Measure area"},
    "action.volume": {"es": "Calcular volumen", "en": "Calculate volume"},

    # --- Panels ---
    "panel.layers": {"es": "Capas", "en": "Layers"},
    "panel.properties": {"es": "Propiedades", "en": "Properties"},
    "panel.tools": {"es": "Herramientas", "en": "Tools"},
    "panel.statistics": {"es": "Estadísticas", "en": "Statistics"},
    "panel.log": {"es": "Registro", "en": "Log"},

    # --- Colorize ---
    "colorize.height": {"es": "Colorear por altura", "en": "Colorize by height"},
    "colorize.intensity": {"es": "Colorear por intensidad", "en": "Colorize by intensity"},
    "colorize.classification": {"es": "Colorear por clasificación", "en": "Colorize by classification"},
    "colorize.return": {"es": "Colorear por retorno", "en": "Colorize by return number"},
    "colorize.rgb": {"es": "Color RGB original", "en": "Original RGB color"},

    # --- Layer panel ---
    "layer.zoom_to": {"es": "Zoom a capa", "en": "Zoom to layer"},
    "layer.remove": {"es": "Eliminar capa", "en": "Remove layer"},
    "layer.rename": {"es": "Renombrar", "en": "Rename"},
    "layer.export": {"es": "Exportar capa...", "en": "Export layer..."},
    "layer.properties": {"es": "Propiedades", "en": "Properties"},

    # --- Properties ---
    "prop.filename": {"es": "Archivo", "en": "File"},
    "prop.point_count": {"es": "Nº de puntos", "en": "Point count"},
    "prop.bounds": {"es": "Extensión", "en": "Bounds"},
    "prop.crs": {"es": "Sistema de coordenadas", "en": "Coordinate system"},
    "prop.resolution": {"es": "Resolución", "en": "Resolution"},
    "prop.bands": {"es": "Bandas", "en": "Bands"},
    "prop.nodata": {"es": "Sin dato", "en": "NoData"},
    "prop.min": {"es": "Mínimo", "en": "Minimum"},
    "prop.max": {"es": "Máximo", "en": "Maximum"},
    "prop.mean": {"es": "Media", "en": "Mean"},

    # --- Classification ---
    "class.ground": {"es": "Suelo", "en": "Ground"},
    "class.low_veg": {"es": "Vegetación baja", "en": "Low vegetation"},
    "class.med_veg": {"es": "Vegetación media", "en": "Medium vegetation"},
    "class.high_veg": {"es": "Vegetación alta", "en": "High vegetation"},
    "class.building": {"es": "Edificio", "en": "Building"},
    "class.water": {"es": "Agua", "en": "Water"},
    "class.noise": {"es": "Ruido", "en": "Noise"},

    # --- DEM types ---
    "dem.dtm": {"es": "MDT (Modelo Digital del Terreno)", "en": "DTM (Digital Terrain Model)"},
    "dem.dsm": {"es": "MDS (Modelo Digital de Superficie)", "en": "DSM (Digital Surface Model)"},
    "dem.chm": {"es": "MDSC / CHM (Modelo de Altura del Dosel)", "en": "CHM (Canopy Height Model)"},

    # --- Status bar ---
    "status.ready": {"es": "Listo", "en": "Ready"},
    "status.loading": {"es": "Cargando...", "en": "Loading..."},
    "status.processing": {"es": "Procesando...", "en": "Processing..."},
    "status.points": {"es": "puntos", "en": "points"},
    "status.no_crs": {"es": "Sin CRS", "en": "No CRS"},

    # --- Dialogs ---
    "dialog.confirm": {"es": "Confirmar", "en": "Confirm"},
    "dialog.cancel": {"es": "Cancelar", "en": "Cancel"},
    "dialog.ok": {"es": "Aceptar", "en": "OK"},
    "dialog.apply": {"es": "Aplicar", "en": "Apply"},
    "dialog.close": {"es": "Cerrar", "en": "Close"},
    "dialog.about_title": {"es": "Acerca de ALAS", "en": "About ALAS"},
    "dialog.about_text": {
        "es": "ALAS — Aerial LiDAR Analysis Software\nAnálisis completo de nubes de puntos LiDAR.",
        "en": "ALAS — Aerial LiDAR Analysis Software\nComprehensive LiDAR point cloud analysis.",
    },

    # --- Errors ---
    "error.file_not_found": {"es": "Archivo no encontrado", "en": "File not found"},
    "error.invalid_format": {"es": "Formato de archivo no válido", "en": "Invalid file format"},
    "error.no_crs": {"es": "El archivo no contiene información de CRS", "en": "File has no CRS information"},
    "error.processing_failed": {"es": "Error en el procesamiento", "en": "Processing failed"},
    "error.export_failed": {"es": "Error al exportar", "en": "Export failed"},

    # --- Success ---
    "success.loaded": {"es": "Archivo cargado correctamente", "en": "File loaded successfully"},
    "success.exported": {"es": "Exportación completada", "en": "Export completed"},
    "success.classification_done": {"es": "Clasificación completada", "en": "Classification completed"},
    "success.dem_generated": {"es": "Modelo digital generado", "en": "Digital model generated"},
}

# ---------------------------------------------------------------------------
# Current language state
# ---------------------------------------------------------------------------
_current_language = DEFAULT_LANGUAGE


def set_language(lang: str):
    """Establece el idioma actual (es/en)."""
    global _current_language
    if lang in ("es", "en"):
        _current_language = lang


def get_language() -> str:
    """Devuelve el idioma actual."""
    return _current_language


def tr(key: str) -> str:
    """
    Traduce una clave al idioma actual.
    Si la clave no existe, devuelve la propia clave.
    """
    entry = _TRANSLATIONS.get(key)
    if entry is None:
        return key
    return entry.get(_current_language, entry.get("es", key))
