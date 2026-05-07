"""
ALAS — Internationalization (i18n)
Bilingual ES / EN system with translation dictionaries.
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
    "action.measurements": {"es": "Historial de mediciones", "en": "Measurements history"},
    "action.multitemporal": {"es": "Análisis multitemporal...", "en": "Multitemporal analysis..."},

    # --- Tools ---
    "action.profile": {"es": "Perfil topográfico", "en": "Topographic profile"},
    "action.distance": {"es": "Medir distancia", "en": "Measure distance"},
    "action.area": {"es": "Calcular área", "en": "Calculate area"},
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

    # --- Statistics Panel ---
    "stat.metadata": {"es": "Metadatos", "en": "Metadata"},
    "stat.las_version": {"es": "Versión LAS", "en": "LAS version"},
    "stat.point_format": {"es": "Formato de punto", "en": "Point format"},
    "stat.crs_epsg": {"es": "CRS (EPSG)", "en": "CRS (EPSG)"},
    "stat.sensor_type": {"es": "Tipo de sensor", "en": "Sensor type"},
    "stat.system_id": {"es": "ID del sistema", "en": "System ID"},
    "stat.creation_date": {"es": "Fecha de creación", "en": "Creation date"},
    "stat.dimensions": {"es": "Dimensiones", "en": "Dimensions"},
    "stat.height_z": {"es": "Altura (Z)", "en": "Height (Z)"},
    "stat.minimum": {"es": "Mínimo", "en": "Minimum"},
    "stat.maximum": {"es": "Máximo", "en": "Maximum"},
    "stat.mean": {"es": "Media", "en": "Mean"},
    "stat.median": {"es": "Mediana", "en": "Median"},
    "stat.std_dev": {"es": "Desv. Est.", "en": "Std Dev"},
    "stat.range": {"es": "Rango", "en": "Range"},
    "stat.intensity": {"es": "Intensidad", "en": "Intensity"},
    "stat.returns": {"es": "Retornos", "en": "Returns"},
    "stat.first_returns": {"es": "Primeros retornos", "en": "First returns"},
    "stat.single_returns": {"es": "Retornos únicos", "en": "Single returns"},
    "stat.last_returns": {"es": "Últimos retornos", "en": "Last returns"},
    "stat.hag_normalization": {"es": "Normalización HAG (Altura sobre el Terreno)", "en": "HAG Normalization (Height Above Ground)"},
    "stat.ground_pts": {"es": "Puntos de terreno", "en": "Ground pts"},
    "stat.non_ground_pts": {"es": "Puntos no terreno", "en": "Non-ground pts"},
    "stat.classification": {"es": "Clasificación", "en": "Classification"},
    "stat.general": {"es": "General", "en": "General"},
    "stat.total_points": {"es": "Total de puntos", "en": "Total points"},
    "stat.xy_area": {"es": "Área XY", "en": "XY Area"},
    "stat.density": {"es": "Densidad", "en": "Density"},
    "stat.x_range": {"es": "Rango X", "en": "X range"},
    "stat.y_range": {"es": "Rango Y", "en": "Y range"},
    "stat.z_range": {"es": "Rango Z", "en": "Z range"},
    "stat.no_data": {"es": "Sin datos estadísticos", "en": "No statistical data"},
    "stat.values": {"es": "Valores", "en": "Values"},
    "stat.size": {"es": "Tamaño", "en": "Size"},
    "stat.resolution_x": {"es": "Resolución X", "en": "Resolution X"},
    "stat.resolution_y": {"es": "Resolución Y", "en": "Resolution Y"},
    "stat.area": {"es": "Área", "en": "Area"},
    "stat.bands": {"es": "Bandas", "en": "Bands"},
    "stat.band_names": {"es": "Nombres de bandas", "en": "Band names"},
    "stat.data_type": {"es": "Tipo de dato", "en": "Data type"},
    "stat.nodata_value": {"es": "Valor sin dato", "en": "No-data value"},

    # --- Log Panel ---
    "log.clear": {"es": "Limpiar", "en": "Clear"},

    # --- Import Dialog ---
    "import.title": {"es": "Opciones de importación", "en": "Import options"},
    "import.file": {"es": "Archivo", "en": "File"},
    "import.coordinate_system": {"es": "Sistema de coordenadas", "en": "Coordinate system"},
    "import.assign_crs": {"es": "Asignar CRS manualmente", "en": "Assign CRS manually"},
    "import.epsg": {"es": "EPSG", "en": "EPSG"},
    "import.decimation": {"es": "Decimación en importación", "en": "Decimation on import"},
    "import.decimate": {"es": "Decimar en importación", "en": "Decimate on import"},
    "import.voxel_size": {"es": "Tamaño de vóxel", "en": "Voxel size"},

    # --- Export Dialog ---
    "export.layer_to_export": {"es": "Capa a exportar", "en": "Layer to export"},
    "export.layer": {"es": "Capa", "en": "Layer"},
    "export.format": {"es": "Formato de exportación", "en": "Export format"},
    "export.options": {"es": "Opciones", "en": "Options"},
    "export.compression": {"es": "Compresión", "en": "Compression"},
    "export.pdf_report": {"es": "Informe PDF", "en": "PDF Report"},
    "export.generate_pdf": {"es": "Generar informe PDF con estadísticas", "en": "Generate PDF report with statistics"},
    "export.title": {"es": "Título", "en": "Title"},
    "export.button": {"es": "Exportar", "en": "Export"},
    "export.success": {"es": "Exportado", "en": "Exported"},

    # --- CRS Dialog ---
    "crs.title": {"es": "Reproyectar", "en": "Reproject"},
    "crs.current": {"es": "CRS actual", "en": "Current CRS"},
    "crs.current_system": {"es": "Sistema actual", "en": "Current system"},
    "crs.source": {"es": "EPSG de origen", "en": "Source EPSG"},
    "crs.source_epsg": {"es": "EPSG de origen", "en": "Source EPSG"},
    "crs.target": {"es": "EPSG de destino", "en": "Target EPSG"},
    "crs.target_epsg": {"es": "EPSG de destino", "en": "Target EPSG"},
    "crs.common": {"es": "Comunes: 4326 (WGS84) | 25830 (ETRS89 UTM 30N) | 25829 (UTM 29N) | 32630 (WGS84 UTM 30N)", "en": "Common: 4326 (WGS84) | 25830 (ETRS89 UTM 30N) | 25829 (UTM 29N) | 32630 (WGS84 UTM 30N)"},
    "crs.reproject_button": {"es": "Reproyectar", "en": "Reproject"},
    "crs.same_epsg": {"es": "Información", "en": "Info"},
    "crs.same_epsg_msg": {"es": "El origen y destino son iguales.", "en": "Source and target are the same."},
    "crs.completed": {"es": "Completado", "en": "Completed"},
    "crs.reprojected": {"es": "Reproyectado de EPSG:{} a EPSG:{}", "en": "Reprojected from EPSG:{} to EPSG:{}"},
    "crs.error": {"es": "Error", "en": "Error"},

    # --- Main Window ---
    "menu.language": {"es": "Idioma / Language", "en": "Idioma / Language"},
    "lang.spanish": {"es": "Español", "en": "Spanish"},
    "lang.english": {"es": "Inglés", "en": "English"},
    "msg.select_point_cloud": {"es": "Seleccione una nube de puntos primero.", "en": "Select a point cloud first."},
    "msg.at_least_2_clouds": {"es": "Se necesitan al menos 2 nubes para fusionar.", "en": "At least 2 clouds are needed to merge."},
    "msg.decimate_title": {"es": "Decimar", "en": "Decimate"},
    "msg.voxel_size": {"es": "Tamaño de vóxel (m):", "en": "Voxel size (m):"},
    "msg.profile_start": {"es": "Seleccione el punto de inicio del perfil", "en": "Select the start point of the profile"},
    "msg.profile_end": {"es": "Seleccione el punto final del perfil", "en": "Select the end point of the profile"},
    "msg.profile_calculated": {"es": "Perfil calculado. Presione Esc para limpiar.", "en": "Profile calculated. Press Esc to clear."},
    "msg.distance_point_a": {"es": "Seleccione el punto A en el visor", "en": "Select point A in the viewer"},
    "msg.distance_point_b": {"es": "Punto A seleccionado. Seleccione el punto B", "en": "Point A selected. Select point B"},
    "msg.area_tool": {"es": "Herramienta de área activa — haga clic en el terreno", "en": "Area tool active — click on the terrain"},
    "msg.area_vertices": {"es": "Área: {} vértice{} — presione Calcular o Intro en el panel", "en": "Area: {} vertex{} — press Calculate or Enter in the panel"},

    # --- Analysis Dialog ---
    "analysis.geomorphology": {"es": "Geomorfología", "en": "Geomorphology"},
    "analysis.hydrology": {"es": "Hidrología", "en": "Hydrology"},
    "analysis.vegetation": {"es": "Vegetación", "en": "Vegetation"},
    "analysis.multitemporal": {"es": "Multitemporal", "en": "Multitemporal"},
    "analysis.input_raster_dem": {"es": "Ráster de entrada (MDE)", "en": "Input raster (DEM)"},
    "analysis.dem": {"es": "MDE", "en": "DEM"},
    "analysis.to_execute": {"es": "Análisis a ejecutar", "en": "Analysis to execute"},
    "analysis.slope": {"es": "Pendiente", "en": "Slope"},
    "analysis.aspect": {"es": "Aspecto", "en": "Aspect"},
    "analysis.curvature": {"es": "Curvatura", "en": "Curvature"},
    "analysis.roughness": {"es": "Rugosidad", "en": "Roughness"},
    "analysis.hillshade": {"es": "Sombreado de colinas", "en": "Hillshade"},
    "analysis.morpho_class": {"es": "Clasificación morfométrica", "en": "Morphometric classification"},
    "analysis.azimuth": {"es": "Acimut", "en": "Azimuth"},
    "analysis.altitude": {"es": "Altitud", "en": "Altitude"},
    "analysis.execute_geomorph": {"es": "Ejecutar análisis geomorfológico", "en": "Execute geomorphological analysis"},
    "analysis.completed_geomorph": {"es": "Análisis geomorfológico completado.", "en": "Geomorphological analysis completed."},
    "analysis.input_raster_chm": {"es": "Ráster de entrada (MCA)", "en": "Input raster (CHM)"},
    "analysis.chm": {"es": "MCA", "en": "CHM"},
    "analysis.parameters": {"es": "Parámetros", "en": "Parameters"},
    "analysis.min_tree_height": {"es": "Altura mín. de árbol", "en": "Min. tree height"},
    "analysis.detection_window": {"es": "Ventana de detección", "en": "Detection window"},
    "analysis.density_cell": {"es": "Celda de densidad", "en": "Density cell"},
    "analysis.analysis": {"es": "Análisis", "en": "Analysis"},
    "analysis.detect_trees": {"es": "Detectar árboles individuales", "en": "Detect individual trees"},
    "analysis.segment_crowns": {"es": "Segmentar copas (cuenca)", "en": "Segment crowns (watershed)"},
    "analysis.density_map": {"es": "Mapa de densidad", "en": "Density map"},
    "analysis.execute_veg": {"es": "Ejecutar análisis de vegetación", "en": "Execute vegetation analysis"},
    "analysis.completed_veg": {"es": "Análisis de vegetación completado.", "en": "Vegetation analysis completed."},
    "analysis.trees_detected": {"es": "Árboles detectados: {}", "en": "Trees detected: {}"},
    "analysis.input_rasters": {"es": "Rásters de entrada", "en": "Input rasters"},
    "analysis.previous_dem": {"es": "MDE anterior", "en": "Previous DEM"},
    "analysis.posterior_dem": {"es": "MDE posterior", "en": "Posterior DEM"},
    "analysis.change_threshold": {"es": "Umbral de cambio", "en": "Change threshold"},
    "analysis.dod": {"es": "Diferencia de MDE (DoD)", "en": "DEM difference (DoD)"},
    "analysis.classify_changes": {"es": "Clasificar cambios", "en": "Classify changes"},
    "analysis.detect_deforest": {"es": "Detectar deforestación (requiere MCA)", "en": "Detect deforestation (requires CHMs)"},
    "analysis.execute_multi": {"es": "Ejecutar análisis multitemporal", "en": "Execute multitemporal analysis"},
    "analysis.completed_multi": {"es": "Análisis multitemporal completado.", "en": "Multitemporal analysis completed."},
    "analysis.warning_select_dem": {"es": "Seleccione un MDE primero.", "en": "Select a DEM first."},
    "analysis.warning_select_chm": {"es": "Seleccione un MCA primero.", "en": "Select a CHM first."},
    "analysis.warning_select_both": {"es": "Seleccione ambos rásters.", "en": "Select both rasters."},
    "analysis.warning_no_analysis": {"es": "No se seleccionó ningún análisis.", "en": "No analysis was selected."},
    "analysis.hydro_results": {"es": "Resultados hidrológicos", "en": "Hydrological Results"},
    "analysis.view_results": {"es": "Ver resultados", "en": "View results"},
    "analysis.completed_hydro": {"es": "Análisis hidrológico completado.\nPresione 'Ver resultados' para ver las imágenes.", "en": "Hydrological analysis completed.\nPress 'View results' to see the images."},
    "analysis.no_raster_layers": {"es": "(Sin capas ráster)", "en": "(No raster layers)"},
    "analysis.result": {"es": "Resultado: {}", "en": "Result: {}"},

    # --- Classification Dialog ---
    "classify.algorithm": {"es": "Algoritmo", "en": "Algorithm"},
    "classify.smrf": {"es": "SMRF (Filtro Morfológico Simple)", "en": "SMRF (Simple Morphological Filter)"},
    "classify.csf": {"es": "CSF (Filtro de Simulación de Tela)", "en": "CSF (Cloth Simulation Filter)"},
    "classify.pmf": {"es": "PMF (Filtro Morfológico Progresivo)", "en": "PMF (Progressive Morphological Filter)"},
    "classify.smrf_params": {"es": "Parámetros SMRF", "en": "SMRF Parameters"},
    "classify.window": {"es": "Ventana (m)", "en": "Window (m)"},
    "classify.slope": {"es": "Pendiente", "en": "Slope"},
    "classify.threshold": {"es": "Umbral (m)", "en": "Threshold (m)"},
    "classify.csf_params": {"es": "Parámetros CSF", "en": "CSF Parameters"},
    "classify.resolution": {"es": "Resolución (m)", "en": "Resolution (m)"},
    "classify.rigidity": {"es": "Rigidez (1-3)", "en": "Rigidity (1-3)"},
    "classify.pmf_params": {"es": "Parámetros PMF", "en": "PMF Parameters"},
    "classify.max_window": {"es": "Ventana máx. (m)", "en": "Max window (m)"},
    "classify.classify_veg": {"es": "Clasificar vegetación y edificios (post-terreno)", "en": "Classify vegetation and buildings (post-ground)"},
    "classify.clear_button": {"es": "Limpiar clasificación", "en": "Clear classification"},
    "classify.info_no_class": {"es": "La nube no tiene clasificación para limpiar.", "en": "The cloud has no classification to clear."},
    "classify.confirm_clear": {"es": "Confirmar", "en": "Confirm"},
    "classify.confirm_msg": {"es": "¿Está seguro de que desea limpiar la clasificación? Esto establecerá todos los puntos como no clasificados.", "en": "Are you sure you want to clear the classification? This will set all points as unclassified."},
    "classify.cloud_info": {"es": "Nube:", "en": "Cloud:"},

    # --- Hydrology Analysis ---
    "hydro.flow_direction": {"es": "Dirección de flujo", "en": "Flow direction"},
    "hydro.flow_accumulation": {"es": "Acumulación de flujo", "en": "Flow accumulation"},
    "hydro.ponding_zones": {"es": "Zonas de encharcamiento", "en": "Ponding zones"},
    "hydro.rainfall_simulation": {"es": "Simulación de lluvia", "en": "Rainfall simulation"},
    "hydro.flood_simulation": {"es": "Simulación de inundación", "en": "Flood simulation"},
    "hydro.drainage_threshold": {"es": "Umbral de red de drenaje", "en": "Drainage network threshold"},
    "hydro.rainfall_intensity": {"es": "Intensidad de lluvia", "en": "Rainfall intensity"},
    "hydro.water_level": {"es": "Nivel de agua (elevación absoluta)", "en": "Water level (absolute elevation)"},
    "hydro.execute": {"es": "▶ Ejecutar análisis hidrológico", "en": "▶ Execute hydrological analysis"},
    "hydro.history": {"es": "Historial", "en": "History"},
    "hydro.history_title": {"es": "Historial de análisis hidrológico", "en": "Hydrological Analysis History"},
    "hydro.no_history": {"es": "Sin análisis hidrológicos en el historial.", "en": "No hydrological analyses in the history."},
    "hydro.legend_flow_direction": {"es": "Dirección de flujo (D8):", "en": "Flow Direction (D8):"},
    "hydro.legend_flow_accumulation": {"es": "Acumulación de flujo:", "en": "Flow Accumulation:"},
    "hydro.legend_ponding": {"es": "Zonas de encharcamiento:", "en": "Ponding Zones:"},
    "hydro.legend_rainfall": {"es": "Escurrimiento por precipitación (m³/h):", "en": "Runoff by Precipitation (m³/h):"},
    "hydro.legend_runoff_title": {"es": "Escurrimiento por precipitación — {} mm/h", "en": "Runoff by Precipitation — {} mm/h"},
    "hydro.legend_flood_title": {"es": "Simulación de inundación — Nivel {} m", "en": "Flood Simulation — Level {} m"},

    # --- Export Dialog ---
    "export.default_title": {"es": "Informe ALAS", "en": "ALAS Report"},
    "export.laz_format": {"es": "LAZ (comprimido)", "en": "LAZ (compressed)"},
    "export.las_format": {"es": "LAS (sin comprimir)", "en": "LAS (uncompressed)"},
    "export.geotiff_format": {"es": "GeoTIFF (.tif)", "en": "GeoTIFF (.tif)"},
    "export.obj_format": {"es": "OBJ 3D (.obj)", "en": "OBJ 3D (.obj)"},
    "export.dialog_title": {"es": "Exportar", "en": "Export"},
    "export.files_filter": {"es": "Archivos", "en": "Files"},
    "export.exported_message": {"es": "Exportado:", "en": "Exported:"},
    "export.metadata_layer": {"es": "Capa", "en": "Layer"},
    "export.metadata_format": {"es": "Formato", "en": "Format"},
    "export.metadata_file": {"es": "Archivo exportado", "en": "Exported file"},
    "export.metadata_points": {"es": "Puntos", "en": "Points"},
    "export.metadata_crs": {"es": "CRS", "en": "CRS"},
    "export.metadata_size": {"es": "Tamaño", "en": "Size"},

    # --- Main Window Messages ---
    "msg.decimate_question": {"es": "El archivo tiene {} puntos.\n¿Desea decimarlo al cargar para ahorrar memoria y tiempo?", "en": "The file has {} points.\nDo you want to decimate it when loading to save memory and time?"},
    "msg.target_points": {"es": "Número objetivo de puntos:", "en": "Target number of points:"},
    "msg.area_calculated": {"es": "Área calculada: {:.2f} m² | Perímetro: {:.2f} m", "en": "Area calculated: {:.2f} m² | Perimeter: {:.2f} m"},
    "msg.volume_calculated": {"es": "Volumen calculado: Neto {:.2f} m³ (Z ref={:.2f})", "en": "Volume calculated: Net {:.2f} m³ (Z ref={:.2f})"},
    "msg.volume_tool_active": {"es": "Herramienta de volumen activa — haga clic en el terreno", "en": "Volume tool active — click on the terrain"},
    "msg.volume_vertices": {"es": "Volumen: {} vértice{} — defina Z y presione Calcular", "en": "Volume: {} vertex{} — define Z and press Calculate"},
    "msg.volume_cleared": {"es": "Volumen 3D oculto. Puede calcular de nuevo.", "en": "3D volume hidden. You can calculate again."},
    "msg.volume_no_dem": {"es": "Se debe cargar una capa ráster (MDE).", "en": "A Raster layer (DEM) must be loaded."},
    "msg.language_change": {"es": "El cambio de idioma se aplicará completamente después de reiniciar la aplicación.", "en": "Language change will be fully applied after restarting the application."},
    "msg.language_change_restart": {"es": "El cambio de idioma se aplicará completamente después de reiniciar.", "en": "Language change will be fully applied after restarting."},
    "msg.app_info": {"es": "Python + PyQt6 + PyVista + PDAL", "en": "Python + PyQt6 + PyVista + PDAL"},

    # --- Dialog Info ---
    "dialog.info": {"es": "Información", "en": "Info"},

    # --- Status Messages ---
    "status.distance": {"es": "Distancia: {0:.3f} m  |  2D: {1:.3f} m  |  dZ: {2:.3f} m  |  Pendiente: {3:.1f} deg", "en": "Distance: {0:.3f} m  |  2D: {1:.3f} m  |  dZ: {2:.3f} m  |  Slope: {3:.1f} deg"},
    "msg.enter_epsg": {"es": "Introduzca código EPSG:", "en": "Enter EPSG code:"},
    "crs.epsg_prefix": {"es": "EPSG:", "en": "EPSG:"},

    # --- Layer Panel ---
    "layer.type": {"es": "Tipo", "en": "Type"},
    "layer.pc": {"es": "PC", "en": "PC"},
    "layer.rl": {"es": "RL", "en": "RL"},
    "layer.name_label": {"es": "Nombre:", "en": "Name:"},
    "layer.remove_confirm": {"es": "¿Eliminar capa '{0}'?", "en": "Remove layer '{0}'?"},

    # --- Properties Panel ---
    "prop.select_layer": {"es": "Seleccione una capa para ver sus propiedades", "en": "Select a layer to view its properties"},
    "prop.point_cloud": {"es": "Nube de puntos", "en": "Point cloud"},
    "prop.general_info": {"es": "Información general", "en": "General information"},
    "prop.file_size": {"es": "Tamaño de archivo", "en": "File size"},
    "prop.las_format": {"es": "Formato LAS", "en": "LAS format"},
    "prop.sensor": {"es": "Sensor", "en": "Sensor"},
    "prop.crs_tooltip": {"es": "Sistema de referencia de coordenadas", "en": "Coordinate Reference System"},
    "prop.x": {"es": "X", "en": "X"},
    "prop.y": {"es": "Y", "en": "Y"},
    "prop.z": {"es": "Z", "en": "Z"},
    "prop.z_stats": {"es": "Estadísticas Z", "en": "Z statistics"},
    "prop.std_dev": {"es": "Desviación estándar", "en": "Standard deviation"},
    "prop.available_dims": {"es": "Dimensiones disponibles", "en": "Available dimensions"},
    "prop.fields": {"es": "Campos", "en": "Fields"},
    "prop.raster_model": {"es": "Modelo ráster", "en": "Raster Model"},
    "prop.size": {"es": "Tamaño", "en": "Size"},
    "prop.nodata_tooltip": {"es": "Valor usado para representar píxeles sin información", "en": "Value used to represent pixels without information"},
    "prop.ground": {"es": "Suelo", "en": "Ground"},

    # --- Tools Panel ---
    "tool.visualization": {"es": "Visualización", "en": "Visualization"},
    "tool.point_size": {"es": "Tamaño de punto", "en": "Point size"},
    "tool.colorize_by": {"es": "Colorear por", "en": "Colorize by"},
    "tool.camera": {"es": "Cámara", "en": "Camera"},
    "tool.reset": {"es": "Restablecer", "en": "Reset"},
    "tool.top": {"es": "Superior", "en": "Top"},
    "tool.front": {"es": "Frontal", "en": "Front"},
    "tool.side": {"es": "Lateral", "en": "Side"},
    "colorize.height_label": {"es": "Altura (Z)", "en": "Height (Z)"},
    "colorize.intensity_label": {"es": "Intensidad", "en": "Intensity"},
    "colorize.classification_label": {"es": "Clasificación", "en": "Classification"},
    "colorize.return_label": {"es": "Número de retorno", "en": "Return Number"},
    "colorize.rgb_label": {"es": "RGB original", "en": "Original RGB"},
    "colorize.solid_label": {"es": "Color sólido", "en": "Solid color"},

    # --- DEM Dialog ---
    "dem.cloud": {"es": "Nube:", "en": "Cloud:"},
    "dem.model_type": {"es": "Tipo de modelo", "en": "Model type"},
    "dem.model": {"es": "Modelo", "en": "Model"},
    "dem.all": {"es": "DTM, DSM, CHM", "en": "DTM, DSM, CHM"},
    "dem.resolution": {"es": "Resolución", "en": "Resolution"},
    "dem.interpolation": {"es": "Interpolación", "en": "Interpolation"},
    "dem.method_idw": {"es": "IDW (Distancia Inversa Ponderada)", "en": "IDW (Inverse Distance Weighting)"},
    "dem.method_tin": {"es": "TIN (Triangulación de Delaunay)", "en": "TIN (Delaunay Triangulation)"},
    "dem.method_nearest": {"es": "Vecino más cercano", "en": "Nearest neighbor"},
    "dem.idw_power": {"es": "Potencia IDW", "en": "IDW power"},
    "dem.auto_export": {"es": "Auto-exportar como GeoTIFF", "en": "Auto-export as GeoTIFF"},
    "dem.generate": {"es": "Generar", "en": "Generate"},
    "dem.save_geotiff": {"es": "Guardar GeoTIFF", "en": "Save GeoTIFF"},
    "dem.geotiff_filter": {"es": "GeoTIFF (*.tif)", "en": "GeoTIFF (*.tif)"},
    "dem.select_folder": {"es": "Seleccione carpeta para guardar GeoTIFFs", "en": "Select folder to save GeoTIFFs"},

    # --- Analysis Dialog Legend ---
    "legend.weak": {"es": "Débil", "en": "Weak"},
    "legend.moderate": {"es": "Moderado", "en": "Moderate"},
    "legend.strong": {"es": "Fuerte", "en": "Strong"},
    "legend.extreme": {"es": "Extremo", "en": "Extreme"},
    "legend.shallow": {"es": "Poco profundo", "en": "Shallow"},
    "legend.deep": {"es": "Profundo", "en": "Deep"},
    "legend.very_deep": {"es": "Muy profundo", "en": "Very deep"},
    "legend.east": {"es": "Este", "en": "East"},
    "legend.southeast": {"es": "Sureste", "en": "Southeast"},
    "legend.south": {"es": "Sur", "en": "South"},
    "legend.southwest": {"es": "Suroeste", "en": "Southwest"},
    "legend.west": {"es": "Oeste", "en": "West"},
    "legend.northwest": {"es": "Noroeste", "en": "Northwest"},
    "legend.north": {"es": "Norte", "en": "North"},
    "legend.northeast": {"es": "Noreste", "en": "Northeast"},
    "legend.low": {"es": "Bajo", "en": "Low"},
    "legend.medium": {"es": "Medio", "en": "Medium"},
    "legend.high": {"es": "Alto", "en": "High"},
    "legend.very_high": {"es": "Muy alto", "en": "Very High"},
    "legend.scale": {"es": "Escala", "en": "Scale"},
    "legend.flooded_cells": {"es": "Celdas inundadas", "en": "Flooded cells"},
    "legend.max_depth": {"es": "Profundidad máxima", "en": "Maximum depth"},
    "analysis.history_dem": {"es": "MDE:", "en": "DEM:"},
    "analysis.history_layers": {"es": "capas", "en": "layers"},

    # --- Statistics Panel ASPRS ---
    "asprs.never_classified": {"es": "Nunca clasificado", "en": "Never classified"},
    "asprs.unclassified": {"es": "Sin clasificar", "en": "Unclassified"},
    "asprs.low_vegetation": {"es": "Vegetación baja", "en": "Low vegetation"},
    "asprs.medium_vegetation": {"es": "Vegetación media", "en": "Medium vegetation"},
    "asprs.high_vegetation": {"es": "Vegetación alta", "en": "High vegetation"},
    "asprs.building": {"es": "Edificio", "en": "Building"},
    "asprs.noise": {"es": "Ruido", "en": "Noise"},
    "asprs.reserved": {"es": "Reservado", "en": "Reserved"},
    "asprs.water": {"es": "Agua", "en": "Water"},
    "asprs.rail": {"es": "Ferrocarril", "en": "Rail"},
    "asprs.road_surface": {"es": "Superficie de carretera", "en": "Road surface"},
    "asprs.overlap": {"es": "Solapamiento", "en": "Overlap"},
    "asprs.wire_guard": {"es": "Cable de guarda", "en": "Wire guard"},
    "asprs.wire_conductor": {"es": "Cable conductor", "en": "Wire conductor"},
    "asprs.transmission_tower": {"es": "Torre de transmisión", "en": "Transmission tower"},
    "asprs.wire_connector": {"es": "Conector de cable", "en": "Wire connector"},
    "asprs.bridge_deck": {"es": "Cubierta de puente", "en": "Bridge deck"},
    "asprs.high_noise": {"es": "Ruido alto", "en": "High noise"},

    # --- Distance Tool ---
    "dist.instructions": {"es": "Clic izquierdo para seleccionar punto A, luego punto B.\nLos resultados se mostrarán automáticamente.", "en": "Left-click to select point A, then point B.\nResults will be shown automatically."},
    "dist.points": {"es": "Puntos", "en": "Points"},
    "dist.results": {"es": "Resultados", "en": "Results"},
    "dist.3d_distance": {"es": "Distancia 3D:", "en": "3D Distance:"},
    "dist.2d_distance": {"es": "Distancia 2D:", "en": "2D Distance:"},
    "dist.z_diff": {"es": "Diferencia Z:", "en": "Z Difference:"},
    "dist.slope": {"es": "Pendiente:", "en": "Slope:"},
    "dist.clear": {"es": "Limpiar", "en": "Clear"},
    "dist.unit_m": {"es": "m", "en": "m"},
    "dist.unit_deg": {"es": "°", "en": "°"},

    # --- Area Tool ---
    "area.instructions": {"es": "Clic izquierdo para añadir vértices al polígono.\nPresione <b>Calcular</b> con ≥ 3 vértices.", "en": "Left-click to add vertices to the polygon.\nPress <b>Calculate</b> with ≥ 3 vertices."},
    "area.vertices": {"es": "Vértices", "en": "Vertices"},
    "area.zero_vertices": {"es": "0 vértices", "en": "0 vertices"},
    "area.calculate": {"es": "Calcular", "en": "Calculate"},
    "area.undo": {"es": "Deshacer", "en": "Undo"},
    "area.clear": {"es": "Limpiar", "en": "Clear"},
    "area.planimetric": {"es": "Área planimétrica:", "en": "Planimetric area:"},
    "area.surface": {"es": "Área superficial:", "en": "Surface area:"},
    "area.perimeter": {"es": "Perímetro 2D:", "en": "2D Perimeter:"},
    "area.vertex_count": {"es": "Vértices:", "en": "Vertices:"},
    "area.without_dem": {"es": "— (sin MDE)", "en": "— (without DEM)"},
    "area.source_dem": {"es": "Área superficial calculada usando el MDE activo.", "en": "Surface area calculated using the active DEM."},
    "area.source_no_dem": {"es": "Sin MDE cargado. Solo área planimétrica (Shoelace).", "en": "No DEM loaded. Only planimetric area (Shoelace)."},
    "area.unit_m2": {"es": "m²", "en": "m²"},
    "area.unit_ha": {"es": "ha", "en": "ha"},

    # --- Volume Tool ---
    "vol.title": {"es": "Cálculo de volumen", "en": "Volume Calculation"},
    "vol.instructions": {"es": "Clic izquierdo para añadir vértices al polígono de cálculo.\nDefina el nivel de referencia Z y presione <b>Calcular</b> con ≥ 3 vértices.", "en": "Left-click to add vertices to the calculation polygon.\nDefine the reference Z level and press <b>Calculate</b> with ≥ 3 vertices."},
    "vol.config": {"es": "Configuración", "en": "Configuration"},
    "vol.ref_level": {"es": "Nivel de ref. (Z):", "en": "Ref. level (Z):"},
    "vol.polygon_verts": {"es": "Vértices del polígono", "en": "Polygon Vertices"},
    "vol.calculate": {"es": "Calcular", "en": "Calculate"},
    "vol.undo": {"es": "Deshacer", "en": "Undo"},
    "vol.clear_volume": {"es": "Limpiar volumen", "en": "Clear volume"},
    "vol.clear_all": {"es": "Limpiar todo", "en": "Clear all"},
    "vol.clear_volume_tooltip": {"es": "Limpiar solo la representación de volumen 3D coloreado", "en": "Clear only the colored 3D volume representation"},
    "vol.results": {"es": "Resultados", "en": "Results"},
    "vol.cut": {"es": "Corte (Excavación):", "en": "Cut (Excavation):"},
    "vol.fill": {"es": "Relleno (Terraplén):", "en": "Fill (Embankment):"},
    "vol.net": {"es": "Volumen neto:", "en": "Net Volume:"},
    "vol.base_area": {"es": "Área base:", "en": "Base area:"},
    "vol.source": {"es": "Volumen calculado usando el MDE activo y el nivel de referencia Z.", "en": "Volume calculated using the active DEM and the reference Z level."},
    "vol.unit_m3": {"es": "m³", "en": "m³"},

    # --- Profile Tool ---
    "prof.coords": {"es": "Coordenadas del perfil", "en": "Profile coordinates"},
    "prof.x_start": {"es": "X inicio", "en": "X start"},
    "prof.y_start": {"es": "Y inicio", "en": "Y start"},
    "prof.x_end": {"es": "X fin", "en": "X end"},
    "prof.y_end": {"es": "Y fin", "en": "Y end"},
    "prof.calculate": {"es": "Calcular", "en": "Calculate"},
    "prof.error_select": {"es": "Error: Seleccione primero una capa activa.", "en": "Error: Select an active layer first."},
    "prof.title": {"es": "Perfil - {0}", "en": "Profile - {0}"},
    "prof.distance": {"es": "Distancia (m)", "en": "Distance (m)"},
    "prof.elevation": {"es": "Elevación (m)", "en": "Elevation (m)"},
    "prof.info": {"es": "Distancia: {0:.1f}m | Z min: {1:.2f}m | Z max: {2:.2f}m | Cambio de elevación: {3:.2f}m", "en": "Distance: {0:.1f}m | Z min: {1:.2f}m | Z max: {2:.2f}m | Elevation change: {3:.2f}m"},

    # --- Import Dialog ---
    "import.file_label": {"es": "Archivo:", "en": "File:"},

    # --- Authentication ---
    "auth.login":                       {"es": "Iniciar sesión",            "en": "Log in"},
    "auth.register":                    {"es": "Registrarse",               "en": "Register"},
    "auth.full_name":                   {"es": "Nombre completo",           "en": "Full name"},
    "auth.email":                       {"es": "Correo electrónico",        "en": "Email"},
    "auth.phone":                       {"es": "Teléfono",                  "en": "Phone"},
    "auth.password":                    {"es": "Contraseña",                "en": "Password"},
    "auth.confirm_password":            {"es": "Confirmar contraseña",      "en": "Confirm password"},
    "auth.remember_me":                 {"es": "Recordarme",                "en": "Remember me"},
    "auth.logout":                      {"es": "Cerrar sesión",             "en": "Log out"},
    "auth.member_since":                {"es": "Miembro desde",             "en": "Member since"},
    "auth.my_account":                  {"es": "Mi cuenta",                 "en": "My account"},
    "auth.error_fill_all_fields":       {"es": "Por favor rellena todos los campos obligatorios.", "en": "Please fill in all required fields."},
    "auth.error_passwords_no_match":    {"es": "Las contraseñas no coinciden.", "en": "Passwords do not match."},
    "auth.error_password_too_short":    {"es": "La contraseña debe tener al menos 8 caracteres.", "en": "Password must be at least 8 characters."},
    "auth.error_invalid_email":         {"es": "Formato de correo electrónico inválido.", "en": "Invalid email format."},
    "auth.error_invalid_credentials":   {"es": "Correo o contraseña incorrectos.", "en": "Incorrect email or password."},
    "auth.error_email_taken":           {"es": "Ya existe una cuenta con ese correo.", "en": "An account with that email already exists."},
    "auth.error_processing_failed":     {"es": "Error de conexión. Inténtalo de nuevo.", "en": "Connection error. Please try again."},

    # --- Splash Screen ---
    "splash.loading_modules": {"es": "Cargando módulos...", "en": "Loading modules..."},
    "splash.ready": {"es": "Listo", "en": "Ready"},

    # --- Properties Panel ---
    "prop.classification": {"es": "Clasificación", "en": "Classification"},
    "prop.sensor_tooltip": {"es": "Identificador del sensor/sistema LiDAR", "en": "LiDAR sensor/system identifier"},
    "prop.not_specified": {"es": "No especificado", "en": "Not specified"},
    "prop.width": {"es": "Ancho", "en": "Width"},
    "prop.height": {"es": "Alto", "en": "Height"},

    # --- About Dialog ---
    "dialog.about_stack": {"es": "Python • PyQt6 • PyVista • PDAL • rasterio • richdem • pysheds", "en": "Python • PyQt6 • PyVista • PDAL • rasterio • richdem • pysheds"},

    # --- Measurements History Dialog ---
    "hist.title": {"es": "Historial de mediciones", "en": "Measurements History"},
    "hist.area": {"es": "Área", "en": "Area"},
    "hist.distance": {"es": "Distancia", "en": "Distance"},
    "hist.volume": {"es": "Volumen", "en": "Volume"},
    "hist.profile": {"es": "Perfil", "en": "Profile"},
    "hist.measurement": {"es": "Medición", "en": "Measurement"},
    "hist.planimetric_area": {"es": "Área planimétrica", "en": "Planimetric area"},
    "hist.surface_area": {"es": "Área superficial", "en": "Surface area"},
    "hist.perimeter_2d": {"es": "Perímetro 2D", "en": "2D Perimeter"},
    "hist.num_vertices": {"es": "Núm. vértices", "en": "Num. vertices"},
    "hist.source": {"es": "Fuente", "en": "Source"},
    "hist.no_dem": {"es": "— (sin MDE)", "en": "— (no DEM)"},
    "hist.source_dem": {"es": "MDE", "en": "DEM"},
    "hist.source_no_dem": {"es": "Shoelace (sin MDE)", "en": "Shoelace (no DEM)"},
    "hist.vertices": {"es": "Vértices", "en": "Vertices"},
    "hist.and_more": {"es": "y {} más...", "en": "and {} more..."},
    "hist.distance_3d": {"es": "Distancia 3D", "en": "3D Distance"},
    "hist.distance_2d": {"es": "Distancia 2D", "en": "2D Distance"},
    "hist.dz": {"es": "Diferencia Z", "en": "Z Difference"},
    "hist.slope": {"es": "Pendiente", "en": "Slope"},
    "hist.point_a": {"es": "Punto A", "en": "Point A"},
    "hist.point_b": {"es": "Punto B", "en": "Point B"},
    "hist.cut": {"es": "Corte (Excavación)", "en": "Cut (Excavation)"},
    "hist.fill": {"es": "Relleno (Terraplén)", "en": "Fill (Embankment)"},
    "hist.net": {"es": "Neto", "en": "Net"},
    "hist.base_area": {"es": "Área base", "en": "Base area"},
    "hist.z_ref": {"es": "Z referencia", "en": "Z Reference"},
    "hist.length": {"es": "Longitud", "en": "Length"},
    "hist.z_min": {"es": "Z mínimo", "en": "Z Minimum"},
    "hist.z_max": {"es": "Z máximo", "en": "Z Maximum"},
    "hist.count_zero": {"es": "0 mediciones", "en": "0 measurements"},
    "hist.count_one": {"es": "1 medición", "en": "1 measurement"},
    "hist.count": {"es": "{} mediciones", "en": "{} measurements"},
    "hist.measurements": {"es": "MEDICIONES", "en": "MEASUREMENTS"},
    "hist.col_id": {"es": "#", "en": "#"},
    "hist.col_time": {"es": "HORA", "en": "TIME"},
    "hist.col_type": {"es": "TIPO", "en": "TYPE"},
    "hist.col_result": {"es": "RESULTADO", "en": "RESULT"},
    "hist.empty_message": {"es": "Aún no hay mediciones registradas.\nUse las herramientas de perfil, distancia, área o volumen.", "en": "No measurements recorded yet.\nUse the profile, distance, area, or volume tools."},
    "hist.detail": {"es": "DETALLE", "en": "DETAIL"},
    "hist.placeholder": {"es": "Seleccione una medición para ver los detalles", "en": "Select a measurement to view details"},
    "hist.copy_detail": {"es": "Copiar detalle", "en": "Copy detail"},
    "hist.copy_all": {"es": "Copiar todo", "en": "Copy all"},
    "hist.clear_history": {"es": "Limpiar historial", "en": "Clear history"},
    "hist.copied_title": {"es": "Copiado", "en": "Copied"},
    "hist.copied_message": {"es": "Historial copiado ({} entradas).", "en": "History copied ({} entries)."},
    "hist.clear_confirm_title": {"es": "Confirmar", "en": "Confirm"},
    "hist.clear_confirm_message": {"es": "¿Eliminar {} mediciones del historial?", "en": "Delete {} measurements from history?"},
}

# ---------------------------------------------------------------------------
# Current language state
# ---------------------------------------------------------------------------
_current_language = DEFAULT_LANGUAGE


def set_language(lang: str):
    """Set the current language (es/en)."""
    global _current_language
    if lang in ("es", "en"):
        _current_language = lang


def get_language() -> str:
    """Return the current language."""
    return _current_language


def tr(key: str) -> str:
    """
    Translate a key to the current language.
    If the key does not exist, return the key itself.
    """
    entry = _TRANSLATIONS.get(key)
    if entry is None:
        return key
    return entry.get(_current_language, entry.get("es", key))
