"""No-regression scorer.

For **modify-existing-codebase** tasks: the agent adds a capability to a seeded
project, and the project's PRE-EXISTING test suite must still pass. This is a
different shape from the greenfield tasks (bookshop), where all tests are the
agent's own — here we guard against a change that implements the new feature but
breaks something that already worked.

The task declares its baseline suite by seeding a ``.retort-regression.json`` into
the playpen (via the task's support dir):

    {"command": ["python", "-m", "pytest", "tests/existing", "-q"], "timeout": 180}

The scorer runs that command against the agent's MODIFIED tree and returns:

* **1.0** — the baseline suite still passes (or the task declares none → not
  applicable, same convention as bead_usage: don't penalise a task that never
  had a regression gate);
* **0.0** — a pre-existing test regressed (non-zero exit), i.e. the change broke
  working behaviour.

The command runs under the shared process-group reaper (a baseline suite may spin
up a server), so it can't leak a process that squats a port for the next cell.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from retort.playpen.runner import RunArtifacts, StackConfig
from retort.scoring.scorers.test_coverage import _run_reaped

logger = logging.getLogger(__name__)

_SPEC_FILE = ".retort-regression.json"


class NoRegressionScorer:
    """Scores whether the seed's pre-existing test suite still passes.

    Score range: 1.0 (no regression / not applicable) to 0.0 (a pre-existing
    test broke). Only meaningful on modify-existing tasks that seed a
    ``.retort-regression.json``; returns 1.0 (N/A) otherwise.
    """

    @property
    def name(self) -> str:
        return "no_regression"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        out = artifacts.output_dir
        if out is None or not out.exists():
            return 0.0
        spec_path = out / _SPEC_FILE
        if not spec_path.is_file():
            return 1.0  # no baseline gate declared → not applicable

        try:
            spec = json.loads(spec_path.read_text())
            cmd = spec["command"]
            timeout = int(spec.get("timeout", 180))
            if not isinstance(cmd, list) or not cmd:
                raise ValueError("command must be a non-empty list")
        except (ValueError, OSError, KeyError, TypeError) as exc:
            logger.warning("no_regression: bad %s: %s", _SPEC_FILE, exc)
            return 1.0  # a malformed gate must not falsely fail a run

        try:
            result = _run_reaped(cmd, cwd=out.resolve(), timeout=timeout)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            # A baseline suite that can't be run (missing runner, or it hangs past
            # the timeout) is a no-signal, not a proven regression — stay neutral
            # so a tooling gap doesn't masquerade as the model breaking the seed.
            logger.warning("no_regression: baseline suite did not run: %s", exc)
            return 1.0

        return 1.0 if result.returncode == 0 else 0.0
