"""Venv detection and dependency installation for scorer subprocesses."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
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


def install_project_deps(venv: Path, output_dir: Path) -> None:
    """Install the project's declared runtime deps into ``venv``.

    Without this, pytest run from a bare interpreter hits ModuleNotFoundError on
    the project's imports (mcp/pandas/anyio/…) during collection, produces no
    coverage line, and scores test_coverage=0 — a false failure even though the
    tests run and pass once deps are present.
    """
    pip = venv / "bin" / "pip"
    if not pip.exists():
        return
    for req in ("requirements.txt", "requirements-dev.txt", "test-requirements.txt"):
        p = output_dir / req
        if p.exists():
            try:
                subprocess.run(
                    [str(pip), "install", "-q", "-r", str(p)],
                    cwd=output_dir, capture_output=True, timeout=600,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.debug("Failed installing %s", p)
    if (output_dir / "pyproject.toml").exists() or (output_dir / "setup.py").exists():
        try:
            subprocess.run(
                [str(pip), "install", "-q", "-e", "."],
                cwd=output_dir, capture_output=True, timeout=600,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.debug("Failed editable-installing project in %s", output_dir)


def ensure_python_env(output_dir: Path) -> tuple[dict[str, str] | None, Path | None]:
    """Prepare an env that runs pytest with the project's deps available.

    Returns ``(env, cleanup_dir)``. ``env`` puts an interpreter that has the
    project's declared deps on PATH (None if none could be prepared).
    ``cleanup_dir`` is a throwaway directory the caller MUST remove after use
    (None when an existing venv was reused).

    Uses an existing venv if the agent left one; otherwise creates a throwaway
    venv so a passing suite isn't scored 0 just because no venv was shipped.
    The throwaway venv is created OUTSIDE ``output_dir`` (in a temp dir) so it
    does not pollute ``pytest --cov=.`` collection or coverage measurement —
    putting it inside output_dir made an empty workspace mis-measure coverage.
    """
    venv = find_venv(output_dir)
    if venv is not None:
        ensure_test_deps(venv)
        return make_venv_env(venv), None
    tmp = Path(tempfile.mkdtemp(prefix="retort-venv-"))
    venv = tmp / "venv"
    try:
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv)],
            capture_output=True, timeout=180,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        shutil.rmtree(tmp, ignore_errors=True)
        return None, None
    if not (venv / "bin" / "python").exists():
        shutil.rmtree(tmp, ignore_errors=True)
        return None, None
    install_project_deps(venv, output_dir)
    ensure_test_deps(venv)
    return make_venv_env(venv), tmp
