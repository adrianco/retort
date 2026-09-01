"""A graphify cell that never opened the graph is a `none` cell in disguise.

The queue entry states the hazard exactly: "Smoke-test that the agent actually
consults the graph — else `graphify` is silently identical to `none` and we
publish a false null." The hook already refuses to pretend when graphify is not
installed (it marks the cell UNAVAILABLE); this covers the other half — the graph
was built, but did the agent open it?
"""
from __future__ import annotations

from pathlib import Path

from retort.playpen.runner import RunArtifacts, StackConfig
from retort.scoring.scorers.graph_usage import GraphUsageScorer


def _stack(tooling: str) -> StackConfig:
    return StackConfig(language="python", agent="hermes", framework="none",
                       extra={"tooling": tooling})


def _artifacts(d: Path) -> RunArtifacts:
    return RunArtifacts(output_dir=d, stdout="", exit_code=0, duration_seconds=1.0)


def test_not_applicable_when_tooling_is_not_graphify(tmp_path):
    """Never penalise a run that was not asked to use the graph."""
    assert GraphUsageScorer().score(_artifacts(tmp_path), _stack("none")) == 1.0
    assert GraphUsageScorer().score(_artifacts(tmp_path), _stack("beads")) == 1.0


def test_consulting_the_graph_scores_one(tmp_path):
    (tmp_path / "_agent_stdout.log").write_text(
        'reading graphify-out/GRAPH_REPORT.md to find the god nodes\n')
    assert GraphUsageScorer().score(_artifacts(tmp_path), _stack("graphify")) == 1.0


def test_ignoring_the_graph_scores_zero(tmp_path):
    """The finding that invalidates a graphify arm — it must be visible."""
    (tmp_path / "_agent_stdout.log").write_text("just grepping around\n")
    assert GraphUsageScorer().score(_artifacts(tmp_path), _stack("graphify")) == 0.0


def test_no_transcript_is_NULL_not_zero(tmp_path):
    """A missing log is not evidence the agent ignored the graph.

    Scoring 0.0 here would put "we could not tell" and "the agent ignored it" in
    one column — the single mistake this harness keeps making, and the reason
    runtime returns None rather than 0.
    """
    assert GraphUsageScorer().score(_artifacts(tmp_path), _stack("graphify")) is None


def test_a_hermes_transcript_counts_too(tmp_path):
    """Hermes logs tool calls to _hermes_session.jsonl, not stdout — a detector
    that only reads stdout would score every local graphify run 0."""
    (tmp_path / "_hermes_session.jsonl").write_text(
        '{"role":"tool","content":"opened graphify-out/graph.json"}\n')
    assert GraphUsageScorer().score(_artifacts(tmp_path), _stack("graphify")) == 1.0


def test_missing_output_dir_is_NULL(tmp_path):
    a = RunArtifacts(stdout="", exit_code=1, duration_seconds=1.0)
    assert GraphUsageScorer().score(a, _stack("graphify")) is None


def test_a_graphify_design_without_the_detector_is_warned_about():
    """A graphify arm whose agent never opened the graph is a `none` arm.

    ScoreCollector runs ONLY the metrics named in `responses:`, so a workspace
    that varies `tooling: graphify` but omits `graph_usage_score` skips the one
    check that makes the arm interpretable — and its null becomes unfalsifiable.

    This exact shape already bit the project one level down: `agent_consulted()`
    had the right three-state semantics and a docstring naming this use case, and
    was wired to nothing but a test. Registering a detector is not the same as
    running it.
    """
    import inspect

    from retort import cli

    src = inspect.getsource(cli.run_experiments.callback)
    assert "graph_usage_score" in src, "the responses guard is gone"
    i = src.index("graph_usage_score")
    window = src[max(0, i - 500):i + 500]
    assert "graphify" in window and "responses" in window

    # And it must sit BEFORE the dry-run exit. The first version did not, so
    # `--dry-run` — the moment someone is actually checking their design — said
    # nothing, and the warning only appeared once they had committed to a run.
    assert src.index("graph_usage_score") < src.index("if dry_run:"), (
        "the guard is after the dry-run exit, so --dry-run never surfaces it")
