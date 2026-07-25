"""repo-pr mode: worktree checkout + patch capture (real git, no network)."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from retort.playpen import repo_pr

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


def _git(*a, cwd):
    return subprocess.run(["git", *a], cwd=str(cwd), capture_output=True, text=True)


@pytest.fixture
def base_repo(tmp_path):
    """A local 'upstream' repo with a tagged baseline commit."""
    src = tmp_path / "upstream"
    (src / "lib").mkdir(parents=True)
    (src / "lib" / "core.py").write_text("def existing(): return 1\n")
    (src / "README.md").write_text("# upstream\n")
    _git("init", "-q", cwd=src)
    _git("-c", "user.email=t@t", "-c", "user.name=t", "add", "-A", cwd=src)
    _git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "base", cwd=src)
    _git("tag", "v1.0", cwd=src)
    return src


def test_cache_slug_is_filesystem_safe():
    assert repo_pr.cache_slug("https://github.com/adrianco/the-goodies.git") == "github.com-adrianco-the-goodies"
    assert "/" not in repo_pr.cache_slug("git@github.com:o/r.git")


def test_worktree_shares_objects_and_patch_holds_only_agent_work(base_repo, tmp_path, monkeypatch):
    monkeypatch.setattr(repo_pr, "REPO_CACHE", tmp_path / "cache")
    base = repo_pr.ensure_base_clone(str(base_repo), "v1.0")
    assert base is not None and (base / ".git").is_dir()

    wt = tmp_path / "playpen" / "attempt1"
    assert repo_pr.add_worktree(base, wt, "v1.0", "retort/t1")
    # the base tree is present WITHOUT being copied — it's a worktree (.git is a file)
    assert (wt / "lib" / "core.py").read_text() == "def existing(): return 1\n"
    assert (wt / ".git").is_file(), "worktree should have a .git FILE, not a copied repo"

    # retort scaffolding + the agent's new work
    (wt / "TASK.md").write_text("do the thing")
    (wt / "stack.json").write_text("{}")
    (wt / "newport").mkdir()
    (wt / "newport" / "main.py").write_text("def added(): return 2\n")

    patch = repo_pr.capture_patch(wt, "v1.0")
    assert patch is not None and patch.name == "attempt.patch"
    body = patch.read_text()
    assert "newport/main.py" in body, "the agent's new file must be in the patch"
    assert "TASK.md" not in body and "stack.json" not in body, "scaffolding must be excluded"
    assert "README.md" not in body, "untouched base files must not appear"

    repo_pr.remove_worktree(base, wt)
    assert not wt.exists()


def test_capture_patch_returns_none_when_agent_changed_nothing(base_repo, tmp_path, monkeypatch):
    monkeypatch.setattr(repo_pr, "REPO_CACHE", tmp_path / "cache2")
    base = repo_pr.ensure_base_clone(str(base_repo), "v1.0")
    wt = tmp_path / "pp" / "a2"
    assert repo_pr.add_worktree(base, wt, "v1.0", "retort/t2")
    (wt / "TASK.md").write_text("only scaffolding")   # no agent work
    assert repo_pr.capture_patch(wt, "v1.0") is None
    repo_pr.remove_worktree(base, wt)


def test_taskspec_repo_pr_flag_and_loader():
    from retort.playpen.runner import TaskSpec
    assert TaskSpec(name="x", description="", prompt="").is_repo_pr is False
    assert TaskSpec(name="x", description="", prompt="",
                    base_repo="https://h/o/r", base_ref="v1").is_repo_pr is True
