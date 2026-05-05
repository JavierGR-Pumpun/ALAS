import laspy
import numpy as np

las = laspy.read("/Users/pumpun/Downloads/PNOA_2021_CAT_260-4517_NPC01.laz")
classes, counts = np.unique(las.classification, return_counts=True)
for c, n in zip(classes, counts):
    print(f"Clase {c:3d}: {n:,} puntos")