"""
ALAS — Exporters
Export to GeoTIFF, OBJ, Shapefile, GeoJSON, and PDF.
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
    """Exports point cloud to LAS/LAZ."""
    pc.to_file(path, compress=compress)


def export_geotiff(raster: RasterLayer, path: str,
                    compress: str = None):
    """Exports raster to GeoTIFF."""
    raster.to_geotiff(path, compress=compress or DEFAULT_GEOTIFF_COMPRESS)


def export_mesh_obj(vertices: np.ndarray, faces: np.ndarray,
                     path: str):
    """
    Exports a 3D mesh to OBJ format.
    vertices: (N, 3) array of vertices.
    faces: (M, 3) array of triangle indices.
    """
    logger.info(f"Exporting OBJ: {Path(path).name}")
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
            # OBJ uses 1-based indices
            f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")

    logger.info(f"OBJ saved: {path}")


def raster_to_mesh(raster: RasterLayer) -> tuple:
    """
    Converts a raster to triangulated mesh for OBJ export.
    Returns (vertices, faces).
    """
    data = raster.get_band(0)
    rows, cols = data.shape
    bounds = raster.bounds

    if bounds is None:
        raise ValueError("Raster without defined extent.")

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

    # Triangles
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

    logger.info(f"Mesh: {len(vertices)} vertices, {len(faces)} triangles")
    return vertices, faces


def export_vector(geometries: list, attributes: list,
                   path: str, crs_epsg: int = None):
    """
    Exports geometries to Shapefile or GeoJSON.
    geometries: list of shapely geometries.
    attributes: list of dicts with properties.
    """
    import geopandas as gpd
    from shapely.geometry import mapping

    logger.info(f"Exporting vector: {Path(path).name}")

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

    logger.info(f"Vector saved: {path} ({len(geometries)} features)")


def export_pdf_report(title: str, metadata: dict,
                       statistics: dict, screenshots: list,
                       path: str, analysis_results: dict = None,
                       hydro_results: dict = None):
    """
    Generates a PDF report with statistics and screenshots.
    analysis_results: dict with layer_type -> {'image': path, 'legend': text, 'stats': dict}
    hydro_results: legacy alias for analysis_results.
    """
    if analysis_results is None and hydro_results is not None:
        analysis_results = hydro_results
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER

    logger.info(f"Generating PDF report: {Path(path).name}")

    doc = SimpleDocTemplate(str(path), pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    # Title style
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Title'],
        fontSize=24, textColor=colors.black,
        spaceAfter=10
    )
    
    # Subtitle style
    subtitle_style = ParagraphStyle(
        'CustomSubtitle', parent=styles['Normal'],
        fontSize=12, textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=20
    )

    # Title
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph("ALAS — Aerial LiDAR Analysis Software", subtitle_style))
    elements.append(Spacer(1, 20))

    # Metadata
    if metadata:
        elements.append(Paragraph("Project information", styles['Heading2']))
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

    # Statistics
    if statistics:
        elements.append(Paragraph("Statistics", styles['Heading2']))
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

    # Analysis results with images and legends
    if analysis_results:
        from reportlab.graphics.shapes import Drawing, Rect
        from reportlab.platypus import KeepTogether
        
        legend_style = ParagraphStyle(
            'LegendStyle', parent=styles['Normal'],
            fontSize=10, textColor=colors.HexColor("#333333"),
            leftIndent=15, rightIndent=15,
            spaceAfter=5, leading=14
        )
        
        def create_color_legend(layer_type: str) -> list:
            """Create legend with colored boxes."""
            legend_elements = []
            
            color_maps = {
                "flow_direction": [
                    ("#1f77b4", "East (1)"),
                    ("#ff7f0e", "Southeast (2)"),
                    ("#2ca02c", "South (4)"),
                    ("#d62728", "Southwest (8)"),
                    ("#9467bd", "West (16)"),
                    ("#8c564b", "Northwest (32)"),
                    ("#e377c2", "North (64)"),
                    ("#7f7f7f", "Northeast (128)")
                ],
                "flow_accumulation": [
                    ("#dddddd", "Low accumulation"),
                    ("#3a79e0", "Medium accumulation"),
                    ("#001f3f", "High accumulation")
                ],
                "ponding": [
                    ("#d2b48c", "High depth"),
                    ("#2ca02c", "Medium depth"),
                    ("#1f77b4", "Low depth"),
                    ("#000080", "Very high depth")
                ],
                "rainfall_runoff": [
                    ("#e8f4fd", "Weak (< 1 mm/h)"),
                    ("#2196f3", "Moderate (1-10 mm/h)"),
                    ("#0d47a1", "Strong (10-50 mm/h)"),
                    ("#1a237e", "Extreme (> 50 mm/h)")
                ],
                "flood_simulation": [
                    ("#aad4f5", "Shallow (< 0.5 m)"),
                    ("#2196f3", "Moderate (0.5-2 m)"),
                    ("#1565c0", "Deep (2-5 m)"),
                    ("#000033", "Very deep (> 5 m)")
                ]
            }
            
            color_list = color_maps.get(layer_type, [])
            
            if color_list:
                for color_hex, label in color_list:
                    d = Drawing(0.4*cm, 0.4*cm)
                    d.add(Rect(0, 0, 0.4*cm, 0.4*cm, 
                              fillColor=colors.HexColor(color_hex),
                              strokeColor=colors.grey,
                              strokeWidth=0.5))
                    
                    legend_table = Table([[d, label]], colWidths=[0.6*cm, 13*cm])
                    legend_table.setStyle(TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('LEFTPADDING', (0, 0), (0, 0), 0),
                        ('LEFTPADDING', (1, 0), (1, 0), 5),
                    ]))
                    legend_elements.append(legend_table)
            
            return legend_elements
        
        for layer_type, result_data in analysis_results.items():
            elements.append(PageBreak())
            
            # Layer title
            layer_title = layer_type.replace('_', ' ').title()
            elements.append(Paragraph(f"Result: {layer_title}", styles['Heading2']))
            elements.append(Spacer(1, 10))
            
            # Image
            img_path = result_data.get('image')
            if img_path and Path(img_path).exists():
                try:
                    img = Image(img_path, width=15*cm, height=11.25*cm)
                    elements.append(img)
                    elements.append(Spacer(1, 10))
                except Exception as e:
                    logger.error(f"Error adding image {img_path}: {e}")
            
            # Legend with colors
            elements.append(Paragraph("<b>Legend:</b>", legend_style))
            elements.append(Spacer(1, 5))
            
            color_legend = create_color_legend(layer_type)
            if color_legend:
                for item in color_legend:
                    elements.append(item)
            else:
                legend_text = result_data.get('legend', '')
                if legend_text:
                    legend_lines = legend_text.split('\n')
                    for line in legend_lines:
                        if line.strip():
                            elements.append(Paragraph(line, legend_style))
            
            elements.append(Spacer(1, 15))
            
            # Statistics for this layer
            layer_stats = result_data.get('stats', {})
            if layer_stats:
                elements.append(Paragraph("Layer Statistics", styles['Heading3']))
                stats_data = [[k, f"{v:.4f}" if isinstance(v, float) else str(v)]
                             for k, v in layer_stats.items()]
                stats_table = Table(stats_data, colWidths=[7*cm, 7*cm])
                stats_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                elements.append(stats_table)
                elements.append(Spacer(1, 15))

    # Screenshots
    for img_path in screenshots:
        if Path(img_path).exists():
            elements.append(Paragraph("Visualization", styles['Heading2']))
            img = Image(img_path, width=16*cm, height=12*cm)
            elements.append(img)
            elements.append(Spacer(1, 10))

    doc.build(elements)
    logger.info(f"PDF report saved: {path}")
