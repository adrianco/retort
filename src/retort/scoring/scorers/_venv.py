"""Venv detection and dependency installation for scorer subprocesses."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_VENV_DIRS = ("venv", ".venv")


def find_venv(output_dir: Path) -> Path | None:
    """Return the venv directory inside output_dir, or None."""
    for name in _VENV_DIRS:
        candidate = output_dir / name
        if (candidate / "bin" / "python").exists():
            return candidate
    return None


def ensure_test_deps(venv: Path) -> None:
    """Install pytest + pytest-cov into the venv if missing."""
    python = venv / "bin" / "python"
    if not python.exists():
        return
    try:
        result = subprocess.run(
            [str(python), "-c", "import pytest, pytest_cov"],
            capture_output=True, timeout=10,
        )
        if result.returncode == 0:
            return
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    pip = venv / "bin" / "pip"
    if not pip.exists():
        return
    try:
        subprocess.run(
            [str(pip), "install", "-q", "pytest", "pytest-cov"],
            capture_output=True, timeout=120,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        logger.debug("Failed to install test deps into %s", venv)


def make_venv_env(venv: Path) -> dict[str, str]:
    """Build an env dict that activates the given venv for subprocess calls."""
    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(venv)
    env["PATH"] = str(venv / "bin") + os.pathsep + env.get("PATH", "")
    env.pop("PYTHONHOME", None)
    return env
