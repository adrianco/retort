"""Small dependency-free PEP 517 backend used to build this demo server.

The execution environment used for the project intentionally contains no
setuptools. Keeping this backend in the source tree means that a wheel can be
built without fetching a build dependency. It includes the bundled CSV files,
which are required for a standalone installed server.
"""

from __future__ import annotations

import base64
import hashlib
import tarfile
import zipfile
from pathlib import Path


_NAME = "brazilian-soccer-mcp"
_VERSION = "0.1.0"
_NORMALIZED_NAME = _NAME.replace("-", "_")
_WHEEL_NAME = f"{_NORMALIZED_NAME}-{_VERSION}-py3-none-any.whl"
_DIST_INFO = f"{_NORMALIZED_NAME}-{_VERSION}.dist-info"
_ROOT = Path(__file__).resolve().parents[1]


def get_requires_for_build_wheel(config_settings: object | None = None) -> list[str]:
    """This project deliberately has no build-time dependencies."""
    return []


def get_requires_for_build_editable(config_settings: object | None = None) -> list[str]:
    return []


def get_requires_for_build_sdist(config_settings: object | None = None) -> list[str]:
    return []


def prepare_metadata_for_build_wheel(metadata_directory: str, config_settings: object | None = None) -> str:
    """Write the metadata pip needs before it asks us to make a wheel."""
    target = Path(metadata_directory) / _DIST_INFO
    _write_metadata(target)
    return _DIST_INFO


def prepare_metadata_for_build_editable(metadata_directory: str, config_settings: object | None = None) -> str:
    return prepare_metadata_for_build_wheel(metadata_directory, config_settings)


def build_wheel(
    wheel_directory: str,
    config_settings: object | None = None,
    metadata_directory: str | None = None,
) -> str:
    """Build a pure-Python wheel with package code and the supplied datasets."""
    wheel_path = Path(wheel_directory) / _WHEEL_NAME
    records: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in _wheel_files():
            content = (_ROOT / relative).read_bytes()
            archive.writestr(relative.as_posix(), content)
            records.append((relative.as_posix(), content))
        for relative, content in _metadata_files().items():
            member = f"{_DIST_INFO}/{relative}"
            archive.writestr(member, content)
            records.append((member, content))
        record_member = f"{_DIST_INFO}/RECORD"
        record = "\n".join(
            f"{member},sha256={_hash(content)},{len(content)}" for member, content in records
        ) + f"\n{record_member},,\n"
        archive.writestr(record_member, record)
    return _WHEEL_NAME


def build_editable(
    wheel_directory: str,
    config_settings: object | None = None,
    metadata_directory: str | None = None,
) -> str:
    """Provide a functional install when pip requests PEP 660 editable mode.

    The datasets are part of the runtime contract, so a regular pure wheel is
    preferable to a partial editable link for this small demonstration server.
    """
    return build_wheel(wheel_directory, config_settings, metadata_directory)


def build_sdist(sdist_directory: str, config_settings: object | None = None) -> str:
    """Build a source archive containing code, tests, metadata, and CSV inputs."""
    filename = f"{_NORMALIZED_NAME}-{_VERSION}.tar.gz"
    destination = Path(sdist_directory) / filename
    with tarfile.open(destination, "w:gz") as archive:
        for relative in _source_files():
            archive.add(_ROOT / relative, arcname=f"{_NORMALIZED_NAME}-{_VERSION}/{relative.as_posix()}")
    return filename


def _wheel_files() -> list[Path]:
    return sorted(
        path.relative_to(_ROOT)
        for directory in (_ROOT / "soccer_mcp", _ROOT / "data" / "kaggle")
        for path in directory.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )


def _source_files() -> list[Path]:
    included = [Path("pyproject.toml"), Path("README.md")]
    included.extend(_wheel_files())
    included.extend(sorted(path.relative_to(_ROOT) for path in (_ROOT / "tests").rglob("*.py")))
    return included


def _metadata_files() -> dict[str, bytes]:
    return {
        "METADATA": (
            "Metadata-Version: 2.1\n"
            "Name: brazilian-soccer-mcp\n"
            "Version: 0.1.0\n"
            "Summary: An MCP server for querying bundled Brazilian soccer datasets\n"
            "Requires-Python: >=3.10\n"
            "Requires-Dist: mcp (<2.0,>=1.12)\n"
            "Requires-Dist: pydantic (<3.0,>=2.7)\n"
        ).encode(),
        "WHEEL": (
            "Wheel-Version: 1.0\n"
            "Generator: brazilian-soccer-mcp build backend\n"
            "Root-Is-Purelib: true\n"
            "Tag: py3-none-any\n"
        ).encode(),
        "entry_points.txt": b"[console_scripts]\nbrazilian-soccer-mcp = soccer_mcp.server:main\n",
    }


def _write_metadata(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for relative, content in _metadata_files().items():
        (directory / relative).write_bytes(content)


def _hash(content: bytes) -> str:
    digest = hashlib.sha256(content).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
