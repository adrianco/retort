"""Load task specifications from various sources."""

from __future__ import annotations

import importlib.resources
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml

from retort.playpen.runner import TaskSpec

BUNDLED_TASKS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "tasks"
REGISTRY_PATH = BUNDLED_TASKS_DIR / "registry.yaml"


@dataclass(frozen=True)
class RegisteredTask:
    """One entry in tasks/registry.yaml.

    A task's canonical home is its GitHub ``template`` repo; ``local`` names an
    optional offline mirror under ``tasks/<local>/`` that resolution prefers.
    """

    name: str
    template: str
    local: str | None
    description: str

    @property
    def local_present(self) -> bool:
        """True when a runnable local mirror (with task.yaml) exists."""
        return bool(self.local) and (BUNDLED_TASKS_DIR / self.local / "task.yaml").exists()

    @property
    def source(self) -> str:
        """The URI this task resolves to: local mirror first, else template."""
        if self.local_present:
            return f"bundled://{self.local}"
        return self.template


def load_registry() -> list[RegisteredTask]:
    """Parse tasks/registry.yaml into RegisteredTask rows (empty if absent)."""
    if not REGISTRY_PATH.exists():
        return []
    data = yaml.safe_load(REGISTRY_PATH.read_text()) or {}
    rows: list[RegisteredTask] = []
    for row in data.get("tasks", []) or []:
        rows.append(
            RegisteredTask(
                name=row["name"],
                template=row.get("template", ""),
                local=row.get("local"),
                description=row.get("description", ""),
            )
        )
    return rows


def list_registered_tasks() -> list[RegisteredTask]:
    """Registered tasks, sorted by name — backs ``retort tasks list``."""
    return sorted(load_registry(), key=lambda t: t.name)


def resolve_task_source(name_or_uri: str) -> str:
    """Resolve a task name to a source URI; explicit ``scheme://`` URIs pass through.

    A bare name is looked up in the registry (local mirror preferred over the
    GitHub template). For back-compat, a name matching a bundled directory
    resolves even without a registry row.
    """
    if "://" in name_or_uri:
        return name_or_uri
    for t in load_registry():
        if t.name == name_or_uri:
            return t.source
    if (BUNDLED_TASKS_DIR / name_or_uri / "task.yaml").exists():
        return f"bundled://{name_or_uri}"
    known = [t.name for t in list_registered_tasks()]
    raise ValueError(
        f"Unknown task {name_or_uri!r}. Registered: {known}. "
        f"Pass a registered name or an explicit URI "
        f"(bundled:// , local:// , git:// , github://)."
    )


def load_task(source: str) -> TaskSpec:
    """Load a task from a registered name or a source URI.

    A bare name (no ``://``) is resolved through the registry
    (see :func:`resolve_task_source`). Supported URI schemes:
    - bundled://<name>                    — load from the bundled tasks directory
    - local://<path>                      — load from a local directory
    - git://<url>                         — clone from a git repository
    - github://<owner>/<repo>[/<spec>]    — shorthand for github.com URLs.
                                            Optional trailing path points at
                                            the file to use as the prompt
                                            (defaults to task.yaml or README).
    """
    if "://" not in source:
        source = resolve_task_source(source)
    if source.startswith("bundled://"):
        name = source[len("bundled://"):]
        return _load_bundled(name)
    if source.startswith("local://"):
        path = Path(source[len("local://"):])
        return _load_from_dir(path)
    if source.startswith("git://"):
        url = source[len("git://"):]
        return _load_from_git(url)
    if source.startswith("github://"):
        return _load_from_github(source[len("github://"):])
    raise ValueError(f"Unsupported task source: {source!r}")


def _load_from_github(spec: str) -> TaskSpec:
    """Load a task from a github://owner/repo[/path/to/spec] URI.

    The optional spec path picks a specific file inside the repo to use
    as the prompt. Without it, the loader falls back to task.yaml or README
    (the same precedence as plain git:// sources).
    """
    parts = spec.split("/", 2)
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError(
            f"github:// requires owner/repo, got {spec!r}. "
            f"Example: github://brazil-bench/benchmark-template"
        )
    owner, repo = parts[0], parts[1]
    spec_path = parts[2] if len(parts) == 3 else None
    url = f"https://github.com/{owner}/{repo}.git"
    return _load_from_git(url, spec_path=spec_path)


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
        max_turns=data.get("max_turns"),
    )


def _load_from_git(url: str, *, spec_path: str | None = None) -> TaskSpec:
    """Clone a git repo and load the task spec from it.

    If spec_path is given, that file (relative to the repo root) is used as
    the prompt source. Otherwise the loader looks for task.yaml first, then
    falls back to a README.
    """
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

    # Explicit spec_path wins. The whole cloned repo travels with the
    # task as support_dir so the agent sees data files, supporting docs,
    # fixtures — anything the spec references. The cloned repo is
    # tempfile.mkdtemp-allocated and stays around for the process lifetime
    # (LocalRunner copies from it per run).
    if spec_path:
        target = repo_dir / spec_path
        if not target.exists():
            available = sorted(p.name for p in repo_dir.iterdir() if p.is_file())
            raise FileNotFoundError(
                f"Spec file {spec_path!r} not found in {url}. "
                f"Top-level files: {available}"
            )
        return TaskSpec(
            name=f"{repo_dir.name}#{spec_path}",
            description=f"Task from {url} (spec: {spec_path})",
            prompt=target.read_text(),
            timeout_minutes=30,
            support_dir=repo_dir,
        )

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
