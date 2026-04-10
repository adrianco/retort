"""Load task specifications from various sources."""

from __future__ import annotations

import importlib.resources
import subprocess
import tempfile
from pathlib import Path

import yaml

from retort.playpen.runner import TaskSpec

BUNDLED_TASKS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "tasks"


def load_task(source: str) -> TaskSpec:
    """Load a task from a source URI.

    Supported schemes:
    - bundled://<name> — load from the bundled tasks directory
    - local://<path> — load from a local directory
    - git://<url> — clone from a git repository
    """
    if source.startswith("bundled://"):
        name = source[len("bundled://"):]
        return _load_bundled(name)
    elif source.startswith("local://"):
        path = Path(source[len("local://"):])
        return _load_from_dir(path)
    elif source.startswith("git://"):
        url = source[len("git://"):]
        return _load_from_git(url)
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


def _load_from_git(url: str) -> TaskSpec:
    """Clone a git repo and load the task spec from it."""
    # Normalize URL — git:// scheme maps to https://
    if not url.startswith("http"):
        url = f"https://{url}"

    clone_dir = Path(tempfile.mkdtemp(prefix="retort-task-"))
    result = subprocess.run(
        ["git", "clone", "--depth", "1", "-q", url, str(clone_dir / "repo")],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to clone {url}: {result.stderr.strip()}"
        )

    repo_dir = clone_dir / "repo"

    # Look for task.yaml in repo root
    if (repo_dir / "task.yaml").exists():
        return _load_from_dir(repo_dir)

    # If no task.yaml, create a synthetic task from the repo's README
    readme = None
    for name in ("README.md", "readme.md", "README"):
        if (repo_dir / name).exists():
            readme = (repo_dir / name).read_text()
            break

    if readme is None:
        raise FileNotFoundError(
            f"No task.yaml or README found in {url}"
        )

    return TaskSpec(
        name=repo_dir.name,
        description=f"Task from {url}",
        prompt=readme,
        timeout_minutes=30,
    )


def list_bundled_tasks() -> list[str]:
    """List available bundled task names."""
    if not BUNDLED_TASKS_DIR.exists():
        return []
    return sorted(
        d.name for d in BUNDLED_TASKS_DIR.iterdir()
        if d.is_dir() and (d / "task.yaml").exists()
    )
