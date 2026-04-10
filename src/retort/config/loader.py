"""Load and validate workspace YAML configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from retort.config.schema import WorkspaceConfig


class ConfigError(Exception):
    """Raised when workspace configuration is invalid or unreadable."""


def load_workspace(path: str | Path) -> WorkspaceConfig:
    """Load a workspace.yaml file, validate it, and return the typed config.

    Parameters
    ----------
    path:
        Path to the workspace YAML file.

    Returns
    -------
    WorkspaceConfig
        Validated configuration object.

    Raises
    ------
    ConfigError
        If the file cannot be read, is not valid YAML, or fails validation.
    """
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot read config file: {exc}") from exc

    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"workspace config must be a YAML mapping, got {type(data).__name__}")

    try:
        return WorkspaceConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"workspace config validation failed:\n{exc}") from exc


def load_workspace_dict(data: dict[str, Any]) -> WorkspaceConfig:
    """Validate a pre-parsed dict as a workspace config.

    Useful when the YAML has already been loaded (e.g. from an API or tests).
    """
    try:
        return WorkspaceConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"workspace config validation failed:\n{exc}") from exc
