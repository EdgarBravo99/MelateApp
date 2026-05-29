from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    path = project_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def outputs_dir() -> Path:
    path = project_root() / "outputs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def resources_dir() -> Path:
    path = project_root() / "resources"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_memory_path() -> Path:
    return data_dir() / "melate_app_memory.sqlite"

