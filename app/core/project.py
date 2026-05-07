"""
ALAS — Project Model
Project model: stores state, CRS, paths, processing history.
Save and load as JSON.
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
from datetime import datetime

from app.config import USER_CONFIG_DIR, USER_CONFIG_FILE


@dataclass
class ProjectSettings:
    """Current project preferences."""
    name: str = "Untitled"
    crs_epsg: Optional[int] = None
    last_import_dir: str = ""
    last_export_dir: str = ""
    language: str = "es"
    point_size: float = 2.0
    background_color: str = "#1a1a2e"


@dataclass
class ProcessingHistoryEntry:
    """Processing history entry."""
    timestamp: str = ""
    operation: str = ""
    parameters: dict = field(default_factory=dict)
    input_file: str = ""
    output_file: str = ""
    duration_seconds: float = 0.0


@dataclass
class Project:
    """
    Complete ALAS project model.
    Manages state, loaded files and history.
    """
    settings: ProjectSettings = field(default_factory=ProjectSettings)
    loaded_files: list = field(default_factory=list)
    processing_history: list = field(default_factory=list)
    project_file: Optional[str] = None
    created_at: str = ""
    modified_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.modified_at = datetime.now().isoformat()

    def add_history(self, operation: str, parameters: dict,
                    input_file: str = "", output_file: str = "",
                    duration: float = 0.0):
        """Add an entry to the processing history."""
        entry = ProcessingHistoryEntry(
            timestamp=datetime.now().isoformat(),
            operation=operation,
            parameters=parameters,
            input_file=input_file,
            output_file=output_file,
            duration_seconds=duration,
        )
        self.processing_history.append(asdict(entry))
        self.modified_at = datetime.now().isoformat()

    def save(self, path: Optional[str] = None):
        """Save the project as JSON."""
        save_path = Path(path) if path else (
            Path(self.project_file) if self.project_file else None
        )
        if save_path is None:
            raise ValueError("No path specified for saving.")

        self.modified_at = datetime.now().isoformat()
        self.project_file = str(save_path)

        data = {
            "settings": asdict(self.settings),
            "loaded_files": self.loaded_files,
            "processing_history": self.processing_history,
            "project_file": self.project_file,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
        }

        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "Project":
        """Load a project from JSON."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        settings = ProjectSettings(**data.get("settings", {}))
        project = cls(
            settings=settings,
            loaded_files=data.get("loaded_files", []),
            processing_history=data.get("processing_history", []),
            project_file=str(path),
            created_at=data.get("created_at", ""),
            modified_at=data.get("modified_at", ""),
        )
        return project


class UserPreferences:
    """
    Global user preferences (persist between projects).
    Stores last CRS, language, last directory used, etc.
    """

    def __init__(self):
        self._prefs = {
            "last_crs_epsg": None,
            "language": "es",
            "last_import_dir": "",
            "last_export_dir": "",
            "recent_files": [],
            "window_geometry": None,
            "window_state": None,
            "session_token": None,
        }
        self._load()

    def _load(self):
        if USER_CONFIG_FILE.exists():
            try:
                with open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._prefs.update(saved)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self._prefs, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default=None):
        return self._prefs.get(key, default)

    def set(self, key: str, value):
        self._prefs[key] = value
        self.save()

    def add_recent_file(self, path: str):
        recent = self._prefs.get("recent_files", [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self._prefs["recent_files"] = recent[:20]
        self.save()

    @property
    def last_crs(self) -> Optional[int]:
        return self._prefs.get("last_crs_epsg")

    @last_crs.setter
    def last_crs(self, epsg: int):
        self.set("last_crs_epsg", epsg)
