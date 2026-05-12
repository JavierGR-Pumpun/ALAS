"""
ALAS — Batch Processing
BatchStep, BatchJob, and BatchWorker for applying a pipeline to multiple files.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from app.core.point_cloud import PointCloudData
from app.logger import get_logger

logger = get_logger("processing.batch")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class BatchStep:
    step_type: str   # "preprocess" | "classify" | "dem" | "export"
    enabled: bool = True
    params: dict = field(default_factory=dict)


@dataclass
class BatchJob:
    file_list: List[Path]
    steps: List[BatchStep]
    output_dir: Path


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

class BatchWorkerSignals(QObject):
    file_started  = pyqtSignal(int, str)        # (index, filename)
    file_progress = pyqtSignal(int, int, str)   # (index, 0-100, message)
    file_done     = pyqtSignal(int, bool, str)  # (index, success, message)
    all_done      = pyqtSignal(int, int)        # (succeeded, failed)


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

class BatchWorker(QRunnable):
    """Runs a BatchJob one file at a time in a background thread."""

    def __init__(self, job: BatchJob):
        super().__init__()
        self.job = job
        self.signals = BatchWorkerSignals()
        self._cancelled = False
        self.setAutoDelete(True)

    def cancel(self):
        self._cancelled = True

    @pyqtSlot()
    def run(self):
        succeeded = 0
        failed = 0
        job = self.job
        job.output_dir.mkdir(parents=True, exist_ok=True)

        for idx, file_path in enumerate(job.file_list):
            if self._cancelled:
                break

            name = file_path.name
            self.signals.file_started.emit(idx, name)

            try:
                self._process_file(idx, file_path, job)
                succeeded += 1
                self.signals.file_done.emit(idx, True, "OK")
                logger.info(f"Batch: {name} completed")
            except Exception as exc:
                failed += 1
                self.signals.file_done.emit(idx, False, str(exc))
                logger.error(f"Batch: {name} failed — {exc}")

        self.signals.all_done.emit(succeeded, failed)

    # ------------------------------------------------------------------

    def _report(self, idx: int, pct: int, msg: str):
        self.signals.file_progress.emit(idx, pct, msg)

    def _process_file(self, idx: int, file_path: Path, job: BatchJob):
        from app.processing.io_handler import read_las
        from app.processing import (
            preprocessing, classification as clf,
            dem_generator, exporters,
        )
        from app.config import SMRF_DEFAULTS, CSF_DEFAULTS, PMF_DEFAULTS

        self._report(idx, 5, "Loading…")
        pc = read_las(str(file_path))

        step_count = sum(1 for s in job.steps if s.enabled)
        completed = 0

        for step in job.steps:
            if not step.enabled or self._cancelled:
                continue

            p = step.params

            # ── Preprocess ───────────────────────────────────────────────
            if step.step_type == "preprocess":
                self._report(idx, _pct(completed, step_count, 0), "Preprocessing…")

                if p.get("filter_noise"):
                    pc = preprocessing.filter_noise(
                        pc,
                        method=p.get("noise_method", "statistical"),
                        k=p.get("noise_k", 6),
                        multiplier=p.get("noise_multiplier", 1.0),
                    )

                if p.get("decimate"):
                    pc = preprocessing.decimate(
                        pc,
                        method="voxel",
                        voxel_size=p.get("voxel_size", 0.5),
                    )

                if p.get("handle_overlap"):
                    pc = preprocessing.handle_overlap(pc, strategy="auto")

                if p.get("reproject") and p.get("target_epsg"):
                    source = p.get("source_epsg") or pc.epsg
                    if source and source != p["target_epsg"]:
                        pc = preprocessing.reproject(pc, int(source), int(p["target_epsg"]))

            # ── Classify ─────────────────────────────────────────────────
            elif step.step_type == "classify":
                self._report(idx, _pct(completed, step_count, 0), "Classifying…")
                algo = p.get("algorithm", "smrf")

                if algo == "smrf":
                    labels = clf.classify_ground_smrf(
                        pc,
                        window=p.get("window", SMRF_DEFAULTS["window"]),
                        slope=p.get("slope", SMRF_DEFAULTS["slope"]),
                        threshold=p.get("threshold", SMRF_DEFAULTS["threshold"]),
                    )
                elif algo == "csf":
                    labels = clf.classify_ground_csf(
                        pc,
                        resolution=p.get("resolution", CSF_DEFAULTS["resolution"]),
                        rigidness=p.get("rigidness", CSF_DEFAULTS["rigidness"]),
                        threshold=p.get("threshold", CSF_DEFAULTS["threshold"]),
                    )
                elif algo == "pmf":
                    labels = clf.classify_ground_pmf(
                        pc,
                        max_window_size=p.get("max_window_size", PMF_DEFAULTS["max_window_size"]),
                        slope=p.get("slope", PMF_DEFAULTS["slope"]),
                    )
                else:
                    labels = None

                if labels is not None:
                    pc.classification = labels
                    pc._hag_cache = None

                    if p.get("classify_above_ground"):
                        self._report(idx, _pct(completed, step_count, 50), "Classifying vegetation…")
                        pc.classification = clf.classify_above_ground(pc)

            # ── DEM ──────────────────────────────────────────────────────
            elif step.step_type == "dem":
                resolution = p.get("resolution", 1.0)
                method = p.get("interpolation", "idw")
                dem_types = p.get("dem_types", ["dtm"])

                stem = file_path.stem

                if "dtm" in dem_types:
                    self._report(idx, _pct(completed, step_count, 0), "Generating DTM…")
                    dtm = dem_generator.generate_dtm(pc, resolution=resolution, method=method)
                    if dtm is not None:
                        out = job.output_dir / f"{stem}_DTM.tif"
                        exporters.export_geotiff(dtm, str(out))

                if "dsm" in dem_types:
                    self._report(idx, _pct(completed, step_count, 33), "Generating DSM…")
                    dsm = dem_generator.generate_dsm(pc, resolution=resolution, method=method)
                    if dsm is not None:
                        out = job.output_dir / f"{stem}_DSM.tif"
                        exporters.export_geotiff(dsm, str(out))

                if "chm" in dem_types and "dtm" in dem_types and "dsm" in dem_types:
                    self._report(idx, _pct(completed, step_count, 66), "Generating CHM…")
                    if dtm is not None and dsm is not None:
                        chm = dem_generator.generate_chm(dtm, dsm)
                        if chm is not None:
                            out = job.output_dir / f"{stem}_CHM.tif"
                            exporters.export_geotiff(chm, str(out))

            # ── Export ───────────────────────────────────────────────────
            elif step.step_type == "export":
                self._report(idx, _pct(completed, step_count, 0), "Exporting…")
                fmt = p.get("format", "laz")
                stem = file_path.stem
                ext = ".laz" if fmt == "laz" else ".las"
                out = job.output_dir / f"{stem}_processed{ext}"
                exporters.export_point_cloud(pc, str(out), compress=(fmt == "laz"))

            completed += 1
            self._report(idx, _pct(completed, step_count, 0), "Step done")

        self._report(idx, 100, "Done")


def _pct(completed: int, total: int, sub: int) -> int:
    if total == 0:
        return 100
    base = int(completed / total * 100)
    return min(base + int(sub / total), 99)
