"""`go test ./...` must run where the module actually is.

A greenfield task puts `go.mod` at the workspace root. A REPO-PR task does not:
it checks out a large existing repo and the agent adds its port as a NEW
subdirectory. exp-63's first cell wrote 21 Go files into `wombat-go/` inside
the-goodies (a Python + TypeScript repo) — and scored test_coverage 0, because
the scorer ran `go test ./...` at the repo root where there is no module.

In the results that is indistinguishable from "the agent wrote nothing", which
is the confusion this harness exists to prevent. It also would have failed all
six cells identically at $1.47 each.
"""
from __future__ import annotations

from pathlib import Path

from retort.scoring.scorers.test_coverage import _go_module_root


def test_root_module_is_used_when_present(tmp_path):
    (tmp_path / "go.mod").write_text("module x\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "go.mod").write_text("module y\n")
    assert _go_module_root(tmp_path) == tmp_path, "a root module must win"


def test_a_single_submodule_is_found(tmp_path):
    """The exp-63 shape: no module at the root, the port in one subdirectory."""
    (tmp_path / "funkygibbon").mkdir()      # existing python package
    (tmp_path / "wombat-go").mkdir()
    (tmp_path / "wombat-go" / "go.mod").write_text("module wombat\n")
    assert _go_module_root(tmp_path) == tmp_path / "wombat-go"


def test_ambiguity_stays_at_the_root_rather_than_guessing(tmp_path):
    """Two candidate modules and no root one: which is the deliverable is not
    knowable, and guessing would silently score the wrong tree."""
    for name in ("port-a", "port-b"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "go.mod").write_text(f"module {name}\n")
    assert _go_module_root(tmp_path) == tmp_path


def test_no_module_anywhere_stays_at_the_root(tmp_path):
    (tmp_path / "src").mkdir()
    assert _go_module_root(tmp_path) == tmp_path


def test_hidden_directories_are_ignored(tmp_path):
    """.git worktrees and caches must not be mistaken for the deliverable."""
    (tmp_path / ".cache").mkdir()
    (tmp_path / ".cache" / "go.mod").write_text("module cached\n")
    assert _go_module_root(tmp_path) == tmp_path
