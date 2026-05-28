from __future__ import annotations

import sys
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_dist_path() -> Path:
    return get_project_root() / "dist" / "MelateApp"


def build_command() -> list[str]:
    entrypoint = get_project_root() / "melate_app_lab" / "desktop_app.py"
    return [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--name",
        "MelateApp",
        "--windowed",
        "--collect-all",
        "PySide6",
        str(entrypoint),
    ]


def build_info() -> dict[str, object]:
    return {
        "project_root": str(get_project_root()),
        "dist_path": str(get_dist_path()),
        "command": build_command(),
        "review_mode": "review_default",
    }
