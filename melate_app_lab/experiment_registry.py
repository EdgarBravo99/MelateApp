from __future__ import annotations

import datetime
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def get_git_info() -> tuple[str, str]:
    """Retorna (commit_sha, branch_name) usando git en subprocess."""
    try:
        commit_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        commit_sha = "unknown"

    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        branch = "unknown"

    return commit_sha, branch


def get_sklearn_version() -> str | None:
    """Retorna la version de scikit-learn si esta instalado, de lo contrario None."""
    try:
        import sklearn
        return sklearn.__version__
    except ImportError:
        return None


def build_manifest(
    game: str,
    window: int | str,
    limit: int,
    pool_size: int,
    top_k: int,
    seed: int | None,
    model_name: str | None,
    use_optimizer: bool,
    use_feedback_profile: bool,
    extra_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construye el manifiesto completo de ejecucion de experimento."""
    commit_sha, branch = get_git_info()
    manifest = {
        "commit_sha": commit_sha,
        "branch": branch,
        "python_version": sys.version.split()[0],
        "sklearn_version": get_sklearn_version(),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "game": game,
        "window": window,
        "limit": limit,
        "pool_size": pool_size,
        "top_k": top_k,
        "seed": seed,
        "model_name": model_name or "heuristic",
        "use_optimizer": use_optimizer,
        "use_feedback_profile": use_feedback_profile,
    }
    if extra_config:
        manifest["extra_config"] = extra_config
    return manifest
