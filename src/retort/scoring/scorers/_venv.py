"""Venv detection and dependency installation for scorer subprocesses."""

from __future__ import annotations

import ast
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_VENV_DIRS = ("venv", ".venv")

# Import name -> PyPI package name, for the common cases where they differ.
# Most web/test deps (flask, fastapi, httpx, pydantic, requests, …) match, so
# they need no entry; this only lists the well-known mismatches.
_IMPORT_TO_PACKAGE = {
    "yaml": "PyYAML",
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "bs4": "beautifulsoup4",
    "sklearn": "scikit-learn",
    "dotenv": "python-dotenv",
    "jwt": "PyJWT",
    "jose": "python-jose",
    "dateutil": "python-dateutil",
    "psycopg2": "psycopg2-binary",
    "serial": "pyserial",
    "attr": "attrs",
}


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


def _imported_top_modules(output_dir: Path) -> set[str]:
    """Top-level module names imported by the project's ``.py`` files (via AST).

    Only absolute imports count — relative imports (``from . import x``) are the
    project's own modules, never third-party.
    """
    names: set[str] = set()
    for py in output_dir.rglob("*.py"):
        if any(part in _VENV_DIRS or part.startswith(".") for part in py.parts):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
        except (SyntaxError, ValueError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    names.add(node.module.split(".")[0])
    return names


def _inferred_packages(output_dir: Path) -> set[str]:
    """PyPI package names the project imports but does not declare.

    Drops the stdlib and the project's own local modules (top-level ``.py`` files
    and directories), skips the test runner (handled separately), and maps the
    known import->PyPI name mismatches. Pure (no installation) so it's testable.
    """
    local = {p.stem for p in output_dir.glob("*.py")}
    local |= {p.name for p in output_dir.iterdir() if p.is_dir()}
    skip = {"pytest", "pytest_cov", "_pytest"}
    packages: set[str] = set()
    for name in _imported_top_modules(output_dir):
        if not name or name in sys.stdlib_module_names or name in local or name in skip:
            continue
        packages.add(_IMPORT_TO_PACKAGE.get(name, name))
    return packages


def install_inferred_imports(venv: Path, output_dir: Path) -> None:
    """Install third-party packages the project IMPORTS but does not DECLARE.

    Models sometimes ship working code + tests but omit ``requirements.txt``, so a
    passing suite is scored 0 on ModuleNotFoundError at collection — the
    undeclared-dependency confound. This installs the inferred imports
    (best-effort, one at a time so one bad guess doesn't abort the rest).
    """
    pip = venv / "bin" / "pip"
    if not pip.exists():
        return
    for pkg in sorted(_inferred_packages(output_dir)):
        try:
            subprocess.run(
                [str(pip), "install", "-q", pkg],
                cwd=output_dir, capture_output=True, timeout=300,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.debug("Failed installing inferred dep %s", pkg)


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
    install_inferred_imports(venv, output_dir)
    ensure_test_deps(venv)
    return make_venv_env(venv), tmp
