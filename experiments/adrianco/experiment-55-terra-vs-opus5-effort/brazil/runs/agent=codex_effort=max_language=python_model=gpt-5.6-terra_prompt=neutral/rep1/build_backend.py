"""Minimal PEP 517 build backend for this dependency-free two-module project.

The execution environment intentionally ships without setuptools.  Keeping the
wheel builder here makes ``pip wheel .`` work offline while producing a normal
pure-Python wheel with the MCP console script.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import zipfile
from pathlib import Path
from typing import Any


NAME = "brazilian-soccer-mcp"
NORMALIZED_NAME = "brazilian_soccer_mcp"
VERSION = "1.0.0"
DIST_INFO = f"{NORMALIZED_NAME}-{VERSION}.dist-info"
ROOT = Path(__file__).resolve().parent


def get_requires_for_build_wheel(config_settings: dict[str, Any] | None = None) -> list[str]:
    """This project has no build-time dependencies."""

    return []


def prepare_metadata_for_build_wheel(
    metadata_directory: str, config_settings: dict[str, Any] | None = None
) -> str:
    """Write standard wheel metadata and return its dist-info directory name."""

    destination = Path(metadata_directory) / DIST_INFO
    destination.mkdir(parents=True, exist_ok=True)
    _write_metadata_directory(destination)
    return DIST_INFO


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    """Build a universal pure-Python wheel containing the two runtime modules."""

    filename = f"{NORMALIZED_NAME}-{VERSION}-py3-none-any.whl"
    target = Path(wheel_directory) / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    files: dict[str, bytes] = {
        "server.py": (ROOT / "server.py").read_bytes(),
        "soccer_data.py": (ROOT / "soccer_data.py").read_bytes(),
        f"{DIST_INFO}/METADATA": _metadata().encode("utf-8"),
        f"{DIST_INFO}/WHEEL": _wheel_metadata().encode("utf-8"),
        f"{DIST_INFO}/entry_points.txt": b"[console_scripts]\nbrazilian-soccer-mcp = server:main\n",
    }
    for data_file in sorted((ROOT / "data" / "kaggle").glob("*.csv")):
        files[data_file.relative_to(ROOT).as_posix()] = data_file.read_bytes()
    records = [
        (path, f"sha256={_digest(contents)}", str(len(contents)))
        for path, contents in files.items()
    ]
    records.append((f"{DIST_INFO}/RECORD", "", ""))
    record_buffer = io.StringIO()
    csv.writer(record_buffer, lineterminator="\n").writerows(records)
    files[f"{DIST_INFO}/RECORD"] = record_buffer.getvalue().encode("utf-8")

    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, contents in files.items():
            archive.writestr(path, contents)
    return filename


def _write_metadata_directory(destination: Path) -> None:
    (destination / "METADATA").write_text(_metadata(), encoding="utf-8")
    (destination / "WHEEL").write_text(_wheel_metadata(), encoding="utf-8")
    (destination / "entry_points.txt").write_text(
        "[console_scripts]\nbrazilian-soccer-mcp = server:main\n", encoding="utf-8"
    )


def _metadata() -> str:
    return (
        "Metadata-Version: 2.1\n"
        f"Name: {NAME}\n"
        f"Version: {VERSION}\n"
        "Summary: Dependency-free MCP server for bundled Brazilian soccer data\n"
        "Requires-Python: >=3.10\n"
        "Provides-Extra: dev\n"
        "Requires-Dist: pytest>=7; extra == 'dev'\n"
    )


def _wheel_metadata() -> str:
    return "Wheel-Version: 1.0\nGenerator: brazilian-soccer-mcp\nRoot-Is-Purelib: true\nTag: py3-none-any\n"


def _digest(contents: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(contents).digest()).decode("ascii").rstrip("=")
