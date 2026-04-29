"""
ALAS — Exporters
Exportación a GeoTIFF, OBJ, Shapefile, GeoJSON y PDF.
"""

import numpy as np
from pathlib import Path
from typing import Optional, List, Dict

from app.core.point_cloud import PointCloudData
from app.core.raster_layer import RasterLayer
from app.config import DEFAULT_GEOTIFF_COMPRESS, DEFAULT_NODATA
from app.logger import get_logger

logger = get_logger("processing.exporters")


def export_point_cloud(pc: PointCloudData, path: str,
                        compress: bool = True):
    """Exporta nube de puntos a LAS/LAZ."""
    pc.to_file(path, compress=compress)


def export_geotiff(raster: RasterLayer, path: str,
                    compress: str = None):
    """Exporta raster a GeoTIFF."""
    raster.to_geotiff(path, compress=compress or DEFAULT_GEOTIFF_COMPRESS)


def export_mesh_obj(vertices: np.ndarray, faces: np.ndarray,
                     path: str):
    """
    Exporta una malla 3D a formato OBJ.
    vertices: (N, 3) array de vértices.
    faces: (M, 3) array de índices de triángulos.
    """
    logger.info(f"Exportando OBJ: {Path(path).name}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w') as f:
        f.write(f"# ALAS OBJ Export\n")
        f.write(f"# Vertices: {len(vertices)}\n")
        f.write(f"# Faces: {len(faces)}\n\n")

        for v in vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

        f.write("\n")

        for face in faces:
            # OBJ usa índices 1-based
            f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")

    logger.info(f"OBJ guardado: {path}")


def raster_to_mesh(raster: RasterLayer) -> tuple:
    """
    Convierte un raster a malla triangulada para exportar como OBJ.
    Devuelve (vertices, faces).
    """
    data = raster.get_band(0)
    rows, cols = data.shape
    bounds = raster.bounds

    if bounds is None:
        raise ValueError("Raster sin extensión definida.")

    xmin, ymin, xmax, ymax = bounds
    xs = np.linspace(xmin, xmax, cols)
    ys = np.linspace(ymax, ymin, rows)

    vertices = []
    vertex_map = {}

    for r in range(rows):
        for c in range(cols):
            z = data[r, c]
            if z != raster.nodata and not np.isnan(z):
                idx = len(vertices)
                vertices.append([xs[c], ys[r], z])
                vertex_map[(r, c)] = idx

    vertices = np.array(vertices, dtype=np.float64)

    # Triángulos
    faces = []
    for r in range(rows - 1):
        for c in range(cols - 1):
            tl = vertex_map.get((r, c))
            tr = vertex_map.get((r, c+1))
            bl = vertex_map.get((r+1, c))
            br = vertex_map.get((r+1, c+1))

            if tl is not None and tr is not None and bl is not None:
                faces.append([tl, bl, tr])
            if tr is not None and bl is not None and br is not None:
                faces.append([tr, bl, br])

    faces = np.array(faces, dtype=np.int64) if faces else np.zeros((0, 3), dtype=np.int64)

    logger.info(f"Malla: {len(vertices)} vértices, {len(faces)} triángulos")
    return vertices, faces


def export_vector(geometries: list, attributes: list,
                   path: str, crs_epsg: int = None):
    """
    Exporta geometrías a Shapefile o GeoJSON.
    geometries: lista de geometrías shapely.
    attributes: lista de dicts con propiedades.
    """
    import geopandas as gpd
    from shapely.geometry import mapping

    logger.info(f"Exportando vectorial: {Path(path).name}")

    gdf = gpd.GeoDataFrame(attributes, geometry=geometries)
    if crs_epsg:
        gdf.set_crs(epsg=crs_epsg, inplace=True)

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.suffix.lower() == '.shp':
        gdf.to_file(str(path), driver="ESRI Shapefile")
    elif path.suffix.lower() == '.geojson':
        gdf.to_file(str(path), driver="GeoJSON")
    elif path.suffix.lower() == '.gpkg':
        gdf.to_file(str(path), driver="GPKG")
    else:
        gdf.to_file(str(path))

    logger.info(f"Vectorial guardado: {path} ({len(geometries)} features)")


def export_pdf_report(title: str, metadata: dict,
                       statistics: dict, screenshots: list,
                       path: str):
    """
    Genera un reporte PDF con estadísticas y capturas.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER

    logger.info(f"Generando reporte PDF: {Path(path).name}")

    doc = SimpleDocTemplate(str(path), pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    # Estilo título
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Title'],
        fontSize=24, textColor=colors.HexColor("#7c3aed"),
        spaceAfter=20
    )

    # Título
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph("ALAS — Aerial LiDAR Analysis Software", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Metadata
    if metadata:
        elements.append(Paragraph("Información del proyecto", styles['Heading2']))
        meta_data = [[k, str(v)] for k, v in metadata.items()]
        meta_table = Table(meta_data, colWidths=[6*cm, 10*cm])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 20))

    # Estadísticas
    if statistics:
        elements.append(Paragraph("Estadísticas", styles['Heading2']))
        stats_data = [[k, f"{v:.4f}" if isinstance(v, float) else str(v)]
                       for k, v in statistics.items()]
        stats_table = Table(stats_data, colWidths=[8*cm, 8*cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 20))

    # Capturas
    for img_path in screenshots:
        if Path(img_path).exists():
            elements.append(Paragraph("Visualización", styles['Heading2']))
            img = Image(img_path, width=16*cm, height=12*cm)
            elements.append(img)
            elements.append(Spacer(1, 10))

    doc.build(elements)
    logger.info(f"Reporte PDF guardado: {path}")
