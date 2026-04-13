"""Tests for stack maturity scoring."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from retort.analysis.maturity import (
    classify_phase,
    compute_stack_maturity,
    render_json,
    render_text,
)
from retort.storage.database import create_tables, get_engine, get_session_factory
from retort.storage.models import ExperimentRun, RunResult, RunStatus


@pytest.fixture
def session_with_runs(tmp_path):
    """Build a small db with three stacks at different maturity levels."""
    db_path = tmp_path / "retort.db"
    engine = get_engine(db_path)
    create_tables(engine)
    session = get_session_factory(engine)()

    def add_run(language, model, status, code_quality):
        run = ExperimentRun(
            replicate=1,
            status=status,
            run_config_json=json.dumps({"language": language, "model": model}),
        )
        session.add(run)
        session.flush()
        if code_quality is not None:
            session.add(RunResult(
                run_id=run.id,
                metric_name="code_quality",
                value=code_quality,
            ))

    # Mature stack: 3 reps, all completed, consistent high score
    for _ in range(3):
        add_run("go", "opus", RunStatus.completed, 0.95)

    # Variable stack: 3 reps, completed, large variance
    for score in (0.4, 0.7, 0.95):
        add_run("python", "sonnet", RunStatus.completed, score)

    # Failing stack: 1 of 3 completed
    add_run("rust", "opus", RunStatus.completed, 0.6)
    add_run("rust", "opus", RunStatus.failed, None)
    add_run("rust", "opus", RunStatus.failed, None)

    session.commit()
    yield session
    session.close()
    engine.dispose()


class TestComputeStackMaturity:
    def test_returns_one_entry_per_stack(self, session_with_runs):
        report = compute_stack_maturity(session_with_runs)
        assert len(report) == 3

    def test_sorted_by_maturity_descending(self, session_with_runs):
        report = compute_stack_maturity(session_with_runs)
        scores = [s.maturity for s in report]
        assert scores == sorted(scores, reverse=True)

    def test_mature_stack_scores_high(self, session_with_runs):
        report = compute_stack_maturity(session_with_runs)
        # Mature go/opus should top the chart
        top = report[0]
        assert top.factors == {"language": "go", "model": "opus"}
        assert top.maturity > 0.9
        assert top.completion_rate == 1.0
        assert top.replicate_agreement == pytest.approx(1.0, abs=0.01)
        assert top.headline_mean == pytest.approx(0.95)

    def test_variable_stack_low_agreement(self, session_with_runs):
        report = compute_stack_maturity(session_with_runs)
        py = next(s for s in report if s.factors.get("language") == "python")
        # CV is large (stdev/mean of 0.4/0.7/0.95)
        assert py.replicate_agreement < 0.5
        assert py.completion_rate == 1.0  # all completed despite variance

    def test_failing_stack_low_completion(self, session_with_runs):
        report = compute_stack_maturity(session_with_runs)
        rust = next(s for s in report if s.factors.get("language") == "rust")
        assert rust.completion_rate == pytest.approx(1 / 3)
        assert rust.n_failed == 2
        # Coverage is fractional too (only 1 successful replicate)
        assert rust.coverage == pytest.approx(1 / 3)

    def test_empty_db(self, tmp_path):
        db_path = tmp_path / "empty.db"
        engine = get_engine(db_path)
        create_tables(engine)
        session = get_session_factory(engine)()
        try:
            assert compute_stack_maturity(session) == []
        finally:
            session.close()
            engine.dispose()

    def test_custom_weights_normalize(self, session_with_runs):
        # Weights need not sum to 1 — should normalize internally.
        report1 = compute_stack_maturity(
            session_with_runs,
            weights={"replicate_agreement": 1.0, "completion_rate": 1.0,
                     "score_level": 1.0, "coverage": 1.0},
        )
        report2 = compute_stack_maturity(
            session_with_runs,
            weights={"replicate_agreement": 0.25, "completion_rate": 0.25,
                     "score_level": 0.25, "coverage": 0.25},
        )
        # Equal weights — same result regardless of absolute values.
        assert [s.maturity for s in report1] == [s.maturity for s in report2]


class TestClassifyPhase:
    def test_thresholds(self):
        assert classify_phase(0.95) == "production"
        assert classify_phase(0.85) == "production"
        assert classify_phase(0.84) == "trial"
        assert classify_phase(0.65) == "trial"
        assert classify_phase(0.50) == "screening"
        assert classify_phase(0.40) == "screening"
        assert classify_phase(0.20) == "candidate"
        assert classify_phase(0.0) == "candidate"


class TestRendering:
    def test_render_text_includes_factors(self, session_with_runs):
        report = compute_stack_maturity(session_with_runs)
        out = render_text(report)
        assert "language=go" in out
        assert "language=python" in out
        assert "Maturity" in out

    def test_render_text_empty(self):
        assert "No stacks" in render_text([])

    def test_render_json_round_trip(self, session_with_runs):
        report = compute_stack_maturity(session_with_runs)
        rendered = render_json(report)
        data = json.loads(rendered)
        assert len(data) == 3
        assert all("maturity" in s for s in data)
        assert all("components" in s for s in data)


class TestCLI:
    def test_maturity_command_runs(self, session_with_runs, tmp_path):
        from click.testing import CliRunner
        from retort.cli import main as cli

        # Find the db file the fixture used.
        # session_with_runs.bind has the engine; engine.url.database is the path.
        db_path = session_with_runs.bind.url.database

        runner = CliRunner()
        result = runner.invoke(cli, ["maturity", "--db", db_path])
        assert result.exit_code == 0, result.output
        assert "Maturity" in result.output
        assert "language=go" in result.output

    def test_maturity_filter(self, session_with_runs):
        from click.testing import CliRunner
        from retort.cli import main as cli

        db_path = session_with_runs.bind.url.database
        runner = CliRunner()
        result = runner.invoke(cli, [
            "maturity", "--db", db_path, "--stack", "language=go",
        ])
        assert result.exit_code == 0
        assert "language=go" in result.output
        assert "language=python" not in result.output

    def test_maturity_json_output(self, session_with_runs, tmp_path):
        from click.testing import CliRunner
        from retort.cli import main as cli

        db_path = session_with_runs.bind.url.database
        runner = CliRunner()
        result = runner.invoke(cli, [
            "maturity", "--db", db_path, "--format", "json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 3
