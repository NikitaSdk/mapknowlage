"""Пути к каталогу, шрифтам и базе прогресса."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", project_root()))
    return project_root()


def catalog_dir() -> Path:
    return resource_root() / "data"


def asset_dir() -> Path:
    return resource_root() / "assets"


def progress_path() -> Path:
    if getattr(sys, "frozen", False):
        root = Path(os.environ.get("APPDATA", str(project_root()))) / "MapKnowlage"
        root.mkdir(parents=True, exist_ok=True)
        return root / "progress.db"
    path = project_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path / "progress.db"
