from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .paths import default_memory_path, outputs_dir


@dataclass(frozen=True)
class AppConfig:
    memory_path: Path = default_memory_path()
    outputs_path: Path = outputs_dir()
    review_mode: str = "review_default"


def load_config() -> AppConfig:
    return AppConfig()
