"""Post-run orphan reaping: processes an agent leaves running in its playpen.

Real processes, not mocks — the failure this guards against (a daemonised server
outliving its run for 68 days) is only reproduced by an actual detached child.
"""

from __future__ import annotations

import subprocess
import sys
import time

import pytest

from retort.playpen.local_runner import LocalRunner, _pid_alive, _reap_orphans_under

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX process model")


def _detached_sleeper(cwd) -> subprocess.Popen:
    # start_new_session mirrors `setsid`/`nohup ... &`: the child leaves our
    # process group, which is exactly why a process-group kill misses it.
    return subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(120)"],
        cwd=cwd, start_new_session=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _wait_dead(proc: subprocess.Popen, secs: float = 5.0) -> bool:
    deadline = time.monotonic() + secs
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return True
        time.sleep(0.1)
    return False


def test_reaps_a_detached_process_left_in_the_playpen(tmp_path):
    playpen = tmp_path / "retort-abc"
    (playpen / "server").mkdir(parents=True)
    orphan = _detached_sleeper(playpen / "server")  # cwd nested inside the playpen
    try:
        reaped = _reap_orphans_under(playpen)
        assert orphan.pid in reaped
        assert _wait_dead(orphan)
    finally:
        orphan.kill()


def test_leaves_processes_outside_the_playpen_alone(tmp_path):
    playpen = tmp_path / "retort-abc"
    sibling = tmp_path / "retort-abcdef"  # shares a name prefix; must not match
    playpen.mkdir()
    sibling.mkdir()
    bystander = _detached_sleeper(sibling)
    try:
        assert _reap_orphans_under(playpen) == []
        assert _pid_alive(bystander.pid)
    finally:
        bystander.kill()
        bystander.wait()


def test_teardown_reaps_the_runs_playpen(tmp_path):
    runner = LocalRunner(work_dir=tmp_path)
    ws = tmp_path / "retort-run1"
    ws.mkdir()

    class _Info:
        workspace = ws

    runner._envs["run1"] = _Info()
    orphan = _detached_sleeper(ws)
    try:
        runner.teardown("run1")
        assert _wait_dead(orphan)
    finally:
        orphan.kill()
