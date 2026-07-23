"""Orchestration logic for the metaharness LOCAL backend (mocked — no model run)."""
from __future__ import annotations

import pytest

from retort import cli
from retort_metaharness import factors as fz
from retort_metaharness.local_runner import LocalModelRunner
from retort_metaharness.runner import CellSpec

STACKS = "experiments/adrianco/experiment-41-repair-80b-fullctx/bookshop/stacks.yaml"


def _spec(harness, scaffold="none", model="qwen-80b-local"):
    return CellSpec("c", {fz.F_MODEL: model, fz.F_HARNESS: harness,
                          fz.F_SCAFFOLD: scaffold, fz.F_LANGUAGE: "python"})


@pytest.fixture
def runner(monkeypatch, tmp_path):
    r = LocalModelRunner(stacks_yaml=STACKS)
    monkeypatch.setattr(cli, "_spec_conformance_passes", lambda *a, **k: (True, 1.0))
    calls = []

    def fake_attempt(model, language, scaffold):
        calls.append({"model": model, "scaffold": scaffold})
        tcov = 0.0 if "35B" in model else 0.9   # 35B "fails" → drives routed escalation
        return (tmp_path, None, 0.8, tcov)

    monkeypatch.setattr(r, "_one_attempt", fake_attempt)
    r._calls = calls
    return r


def test_base_react_one_attempt(runner):
    res = runner.run(_spec("base-ReAct"))
    assert len(runner._calls) == 1
    assert res.requirement_coverage == 1.0 and res.status == "pass"
    assert res.runner == "local" and res.cost_per_task == 0.0


def test_self_consistency_runs_n_and_keeps_best(runner):
    res = runner.run(_spec("self-consistency-N"))
    assert len(runner._calls) == 5  # default n
    assert res.requirement_coverage == 1.0


def test_routed_escalates_on_draft_failure(runner):
    res = runner.run(_spec("routed"))
    models = [c["model"] for c in runner._calls]
    assert any("35B" in m for m in models) and any("Next" in m for m in models)  # 35B then 80B
    assert "escalated" in res.notes


def test_scaffold_is_passed_through(runner):
    runner.run(_spec("base-ReAct", scaffold="reflexion"))
    assert runner._calls[0]["scaffold"] == "reflexion"


def test_memory_genome_marked_na_locally(runner):
    res = runner.run(_spec("+agenticow-memory"))
    assert "N/A" in res.notes and len(runner._calls) == 1  # falls back to base-ReAct
