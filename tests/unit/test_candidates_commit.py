"""The daily scan's ONLY pre-approved command must actually persist its edit.

scripts/candidates-commit.sh is the one command the unattended
daily-local-coding-model-scan is allowed to run. When it fails, the scan's
heartbeat never lands — and the heartbeat exists precisely so that a silently
stopped scanner is distinguishable from a quiet news week. A broken persist step
therefore takes out the outage detector too, which is how it went unnoticed.

Both scenarios here are real failures observed on 2026-08-22.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "candidates-commit.sh"
FILE = "docs/future-experiments.md"


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A clone with an origin, and the script rewired to point at it."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(origin), str(work)],
                   check=True, capture_output=True)
    _git("config", "user.email", "t@t", cwd=work)
    _git("config", "user.name", "t", cwd=work)

    (work / "docs").mkdir()
    (work / FILE).write_text("**Daily scan last completed: 2026-08-20**\n")
    (work / "other.txt").write_text("unrelated\n")
    (work / "scripts").mkdir()
    patched = SCRIPT.read_text().replace(
        'REPO="/Users/adriancockcroft/code/retort"', f'REPO="{work}"')
    dst = work / "scripts" / "candidates-commit.sh"
    dst.write_text(patched)
    dst.chmod(0o755)

    _git("add", "-A", cwd=work)
    _git("commit", "-qm", "init", cwd=work)
    _git("branch", "-M", "main", cwd=work)
    _git("push", "-q", "-u", "origin", "main", cwd=work)
    return work


def _run(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run([str(repo / "scripts" / "candidates-commit.sh"), "0"],
                          cwd=repo, capture_output=True, text=True)


def _heartbeat_on_origin(repo: Path) -> bool:
    _git("fetch", "-q", "origin", cwd=repo)
    log = _git("log", "origin/main", "--oneline", "-1", cwd=repo).stdout
    return "scan heartbeat" in log


def _move_remote(repo: Path, tmp_path: Path) -> None:
    other = tmp_path / "other"
    subprocess.run(["git", "clone", "-q", str(tmp_path / "origin.git"), str(other)],
                   check=True, capture_output=True)
    _git("config", "user.email", "t@t", cwd=other)
    _git("config", "user.name", "t", cwd=other)
    (other / "new.txt").write_text("someone else\n")
    _git("add", "-A", cwd=other)
    _git("commit", "-qm", "another session", cwd=other)
    _git("push", "-q", "origin", "main", cwd=other)


def test_persists_when_the_remote_moved_and_the_tree_is_dirty(repo, tmp_path):
    """The 2026-08-22 failure.

    The script used to stage the file and THEN run `pull --rebase --autostash`.
    Autostash pops without `--index`, so the staged file came back unstaged,
    `git commit` found an empty index and exited 1, and `set -e` killed the run
    before the push. The pull itself returns 0, so the conflict check never
    caught it — and the edit survived unstaged, so it looked like nothing had
    happened. That day's heartbeat was later swept into an unrelated commit.
    """
    _move_remote(repo, tmp_path)
    (repo / FILE).write_text("**Daily scan last completed: 2026-08-23**\n")
    (repo / "other.txt").write_text("dirty\n")

    result = _run(repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert _heartbeat_on_origin(repo), "the heartbeat never reached the remote"


def test_persists_when_another_session_has_files_staged(repo):
    """It used to refuse outright, losing the run — including the heartbeat.

    Refusing was the wrong response to the right concern. The commit is pinned to
    the one path, so unrelated staged work cannot ride along whatever the index
    holds; giving up bought no extra safety and cost the outage signal.
    """
    (repo / FILE).write_text("**Daily scan last completed: 2026-08-23**\n")
    (repo / "other.txt").write_text("their work in progress\n")
    _git("add", "other.txt", cwd=repo)

    result = _run(repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert _heartbeat_on_origin(repo)

    committed = _git("show", "--stat", "--oneline", "HEAD", cwd=repo).stdout
    assert "other.txt" not in committed, "swept up another session's staged work"
    still_staged = _git("diff", "--cached", "--name-only", cwd=repo).stdout
    assert "other.txt" in still_staged, "clobbered another session's index"


def test_nothing_to_do_is_not_a_failure(repo):
    result = _run(repo)
    assert result.returncode == 0
    assert not _heartbeat_on_origin(repo)
