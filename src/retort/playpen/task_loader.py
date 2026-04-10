"""Load task specifications from various sources."""

from __future__ import annotations

import importlib.resources
from pathlib import Path

import yaml

from retort.playpen.runner import TaskSpec

BUNDLED_TASKS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "tasks"


def load_task(source: str) -> TaskSpec:
    """Load a task from a source URI.

    Supported schemes:
    - bundled://<name> — load from the bundled tasks directory
    - local://<path> — load from a local directory
    """
    if source.startswith("bundled://"):
        name = source[len("bundled://"):]
        return _load_bundled(name)
    elif source.startswith("local://"):
        path = Path(source[len("local://"):])
        return _load_from_dir(path)
    else:
        raise ValueError(f"Unsupported task source: {source!r}")


def _load_bundled(name: str) -> TaskSpec:
    """Load a bundled task by name."""
    task_dir = BUNDLED_TASKS_DIR / name
    if not task_dir.exists():
        available = [
            d.name for d in BUNDLED_TASKS_DIR.iterdir()
            if d.is_dir() and (d / "task.yaml").exists()
        ]
        raise FileNotFoundError(
            f"Bundled task {name!r} not found. Available: {available}"
        )
    return _load_from_dir(task_dir)


def _load_from_dir(task_dir: Path) -> TaskSpec:
    """Load a TaskSpec from a directory containing task.yaml."""
    yaml_path = task_dir / "task.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"No task.yaml found in {task_dir}")

    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    validate_path = task_dir / "validate.py"
    validation_script = str(validate_path) if validate_path.exists() else None

    return TaskSpec(
        name=data["name"],
        description=data.get("description", ""),
        prompt=data.get("prompt", ""),
        validation_script=validation_script,
        timeout_minutes=data.get("timeout_minutes", 30),
    )


def list_bundled_tasks() -> list[str]:
    """List available bundled task names."""
    if not BUNDLED_TASKS_DIR.exists():
        return []
    return sorted(
        d.name for d in BUNDLED_TASKS_DIR.iterdir()
        if d.is_dir() and (d / "task.yaml").exists()
    )
