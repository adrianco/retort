"""Shared test fixtures for retort tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from retort.design.factors import FactorRegistry, FactorType
from retort.storage.models import Base


@pytest.fixture
def db_engine(tmp_path: Path):
    """Create a fresh in-memory SQLite engine with all tables."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Session:
    """Provide a transactional session that rolls back after each test."""
    factory = sessionmaker(bind=db_engine)
    session = factory()
    yield session
    session.close()


@pytest.fixture
def two_level_registry() -> FactorRegistry:
    """Registry with 3 factors, each having 2 levels."""
    reg = FactorRegistry()
    reg.add("language", ["python", "go"])
    reg.add("agent", ["claude-code", "copilot"])
    reg.add("framework", ["fastapi", "stdlib"])
    return reg


@pytest.fixture
def mixed_level_registry() -> FactorRegistry:
    """Registry with factors having different numbers of levels."""
    reg = FactorRegistry()
    reg.add("language", ["python", "typescript", "rust", "go"])
    reg.add("agent", ["claude-code", "cursor", "copilot"])
    reg.add("framework", ["fastapi", "nextjs", "axum"])
    return reg


@pytest.fixture
def large_registry() -> FactorRegistry:
    """Registry with 6 factors (the full retort use case)."""
    reg = FactorRegistry()
    reg.add("language", ["python", "typescript", "rust", "go"])
    reg.add("agent", ["claude-code", "cursor", "copilot", "aider"])
    reg.add("framework", ["fastapi", "nextjs", "axum", "stdlib"])
    reg.add("app_type", ["rest-api", "cli-tool", "react-frontend"])
    reg.add("orchestration", ["single-agent", "swarm", "hive-mind"])
    reg.add("constraint_style", ["rfc-2119", "bdd", "unconstrained"])
    return reg


# ---------------------------------------------------------------------------
# No unit test may shell out to a judge / agent CLI
# ---------------------------------------------------------------------------

#: Binaries that cost money and need the network when invoked for real.
_BILLED_CLIS = {"claude", "codex", "gemini", "opencode", "hermes", "omp"}


@pytest.fixture(autouse=True)
def _no_billed_cli_subprocesses(request, monkeypatch):
    """Fail loudly if a test launches a real agent/judge CLI.

    `test_auto_evaluation_swallows_skill_failure` patched two functions that
    were no longer on the code path, so its stubs did nothing and it shelled out
    to a live judge — `claude -p Follow skill at …` — for 35-59 seconds of billed
    API time on every run of the unit suite. Nothing failed; it just looked like
    a slow test, for weeks.

    A stub that silently stops matching the code is invisible. This makes it
    loud: the mistake now fails the test that made it, naming the command, rather
    than showing up as a number in --durations that nobody reads.

    Integration tests that genuinely need a CLI opt out with
    `@pytest.mark.allow_billed_cli`.
    """
    import subprocess

    if request.node.get_closest_marker("allow_billed_cli"):
        return

    real_run, real_popen = subprocess.run, subprocess.Popen

    def _binary_of(cmd) -> str:
        if isinstance(cmd, (list, tuple)) and cmd:
            return os.path.basename(str(cmd[0]))
        if isinstance(cmd, str):
            return os.path.basename(cmd.split()[0]) if cmd.split() else ""
        return ""

    def _guard(fn, cmd, *a, **kw):
        if _binary_of(cmd) in _BILLED_CLIS:
            shown = " ".join(map(str, cmd))[:120] if isinstance(cmd, (list, tuple)) else str(cmd)[:120]
            raise AssertionError(
                f"unit test launched a real billed CLI: {shown}\n"
                "Patch the function the code actually calls, or mark the test "
                "@pytest.mark.allow_billed_cli if it genuinely needs one.")
        return fn(cmd, *a, **kw)

    monkeypatch.setattr(subprocess, "run",
                        lambda cmd, *a, **kw: _guard(real_run, cmd, *a, **kw))
    monkeypatch.setattr(subprocess, "Popen",
                        lambda cmd, *a, **kw: _guard(real_popen, cmd, *a, **kw))


# ---------------------------------------------------------------------------
# One venv for the whole session, instead of one per test
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def shared_pytest_venv(tmp_path_factory) -> Path:
    """A venv with pytest + pytest-cov, built ONCE for the session.

    `ensure_python_env` builds a throwaway venv per call and pip-installs the
    project's inferred imports into it. That is right in production — sharing
    one there would let a project that forgot to declare a dependency pass on a
    neighbour's install — but in the suite it meant a real `pip install fastapi`
    per test, and test_scoring.py alone was creating eleven of them.

    Tests reuse this by dropping a `venv` symlink into their temp project, which
    `find_venv` picks up; `ensure_test_deps` then early-returns because pytest
    already imports. Nothing installs into it, so it cannot accumulate state
    between tests — the reuse path in `ensure_python_env` never installs.

    NOT for tests of the venv machinery itself (`TestPythonEnvPreparation`):
    the reuse path deliberately skips dependency inference, which is the thing
    those tests exist to exercise.
    """
    import subprocess
    import sys

    root = tmp_path_factory.mktemp("shared-venv")
    venv = root / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)],
                   capture_output=True, timeout=180, check=True)
    subprocess.run([str(venv / "bin" / "pip"), "install", "-q",
                    "pytest", "pytest-cov"],
                   capture_output=True, timeout=300, check=True)
    return venv
