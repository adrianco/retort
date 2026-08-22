"""The suite must not be able to spend money without saying so.

`test_auto_evaluation_swallows_skill_failure` patched two functions that were no
longer on the code path. Its stubs therefore did nothing, and it shelled out to a
live judge — `claude -p Follow skill at …` — for 35-59 seconds of billed API time
on every `pytest tests/unit`. Nothing failed. It just looked like a slow test,
and stayed that way for weeks, because a stub that silently stops matching the
code it is stubbing is invisible.

These tests pin the guard that makes that mistake loud instead.
"""
from __future__ import annotations

import subprocess

import pytest


def test_launching_a_judge_cli_fails_the_test():
    with pytest.raises(AssertionError, match="billed CLI"):
        subprocess.run(["claude", "-p", "hello"], capture_output=True)


def test_it_also_catches_popen():
    with pytest.raises(AssertionError, match="billed CLI"):
        subprocess.Popen(["codex", "exec"], stdout=subprocess.PIPE)


def test_it_catches_an_absolute_path_to_the_binary():
    """The stale test invoked it by bare name, but a path must not slip past."""
    with pytest.raises(AssertionError, match="billed CLI"):
        subprocess.run(["/opt/homebrew/bin/claude", "-p", "x"], capture_output=True)


def test_ordinary_subprocesses_are_untouched():
    """The guard must not break the many tests that legitimately shell out to
    a real toolchain — go, npm, pytest — which is most of test_scoring.py."""
    r = subprocess.run(["echo", "fine"], capture_output=True, text=True)
    assert r.stdout.strip() == "fine"


@pytest.mark.allow_billed_cli
def test_an_integration_test_can_opt_out():
    """Escape hatch: a test that genuinely needs a CLI says so explicitly."""
    r = subprocess.run(["echo", "opted out"], capture_output=True, text=True)
    assert r.returncode == 0
