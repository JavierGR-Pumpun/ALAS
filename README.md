# ALAS — Aerial LiDAR Analysis Software

**Version 1.0.0**

ALAS is a desktop application for professional processing, analysis, and visualization of aerial LiDAR point clouds. Built with Python, PyQt6, and PyVista.

---

## Features

### Point Cloud Management
- Load single or multiple `.las` / `.laz` files
- Automatic decimation on import for large files (>1M points)
- Merge multiple tiles into a single cloud
- Layer panel with visibility toggle, rename, zoom-to, and export

### Visualization
- Interactive 3D viewport powered by PyVista / VTK
- Colorization modes: Height (Z), Intensity, Classification, Return Number, Original RGB, Solid color
- Top, Front, and Side orthographic views
- Adjustable point size

### Classification
- **SMRF** (Simple Morphological Filter)
- **CSF** (Cloth Simulation Filter)
- **PMF** (Progressive Morphological Filter)
- **AI** (Neural Network — optional, requires a `.pt` model file)
- Optional post-processing: vegetation and building classification
- Classification history with detailed per-run statistics

### Digital Model Generation
- **DTM** — Digital Terrain Model
- **DSM** — Digital Surface Model
- **CHM** — Canopy Height Model
- Interpolation: IDW, TIN (Delaunay), Nearest Neighbor
- Auto-export as GeoTIFF

### Analysis
| Module | Outputs |
|---|---|
| **Geomorphology** | Slope, Aspect, Curvature, Roughness, Hillshade, Morphometric classification |
| **Hydrology** | Flow direction (D8), Flow accumulation, Ponding zones, Rainfall simulation, Flood simulation |
| **Vegetation** | Tree detection, Crown segmentation, Density map |
| **Multitemporal** | DEM of Difference (DoD), Change classification, Deforestation detection |

### Measurement Tools
- Topographic profile (click 2 points)
- 3D / 2D distance measurement
- Polygon area (planimetric + surface via DEM)
- Volume calculation (cut/fill against reference Z)
- Measurements history with copy and export

### Processing Utilities
- Noise filtering (SOR)
- Voxel-based decimation
- Overlap removal
- CRS reprojection (via pyproj)
- Project save / load (`.alas`)
- Export: LAZ, LAS, GeoTIFF, OBJ 3D, PDF report

---

## Requirements

```
Python >= 3.10
PyQt6
PyVista
laspy
PDAL
rasterio
pyproj
richdem
pysheds
numpy
scipy
matplotlib
```

Install the environment:

```bash
conda env create -f environment.yml
conda activate alas
```

---

## Running

```bash
python main.py
```

---

## Project Structure

```
ALAS/
├── app/
│   ├── auth/           — Authentication (login, register, session)
│   ├── core/           — Data models (PointCloudData, RasterLayer, LayerManager)
│   ├── processing/     — Algorithms (classification, DEM, analysis, measurements)
│   ├── ui/
│   │   ├── dialogs/    — Modal dialogs
│   │   ├── panels/     — Dock panels (Layers, Properties, Tools, Statistics, Log)
│   │   └── viewport/   — 3D viewport + measurement tools
│   ├── config.py       — Constants and defaults
│   ├── i18n.py         — ES / EN translations
│   └── logger.py       — Application logger
├── resources/
│   ├── icons/
│   ├── styles/
│   └── models/         — AI model weights (.pt)
├── main.py
└── environment.yml
```

---

## Coordinate Systems

ALAS preserves the original CRS embedded in LAS/LAZ files. If no CRS is found, it prompts the user to enter an EPSG code. Common codes:

| EPSG | Description |
|------|-------------|
| 25830 | ETRS89 / UTM zone 30N (Spain) |
| 25829 | ETRS89 / UTM zone 29N |
| 32630 | WGS84 / UTM zone 30N |
| 4326  | WGS84 geographic |

---

## License

© 2026 ALAS Project. All rights reserved.
