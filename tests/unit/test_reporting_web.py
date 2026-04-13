"""Tests for the static-HTML web report generator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from retort.reporting.web import generate_web_report
from retort.storage.database import create_tables, get_engine, get_session_factory
from retort.storage.models import ExperimentRun, RunResult, RunStatus


@pytest.fixture
def populated_db(tmp_path):
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
                run_id=run.id, metric_name="code_quality", value=code_quality,
            ))

    for _ in range(3):
        add_run("go", "opus", RunStatus.completed, 0.9)
    for score in (0.4, 0.7):
        add_run("python", "sonnet", RunStatus.completed, score)

    session.commit()
    session.close()
    engine.dispose()
    return db_path


def test_writes_index_and_style(populated_db, tmp_path):
    out = tmp_path / "web"
    n = generate_web_report(db_path=populated_db, output_dir=out)
    assert n >= 1
    assert (out / "index.html").exists()
    assert (out / "style.css").exists()


def test_index_includes_stacks(populated_db, tmp_path):
    out = tmp_path / "web"
    generate_web_report(db_path=populated_db, output_dir=out)
    html = (out / "index.html").read_text()
    assert "language=go" in html
    assert "language=python" in html
    # Phase classification badges present
    assert "phase-" in html
    # Maturity column header
    assert "Maturity" in html


def test_public_creates_per_stack_pages(populated_db, tmp_path):
    out = tmp_path / "web"
    n = generate_web_report(
        db_path=populated_db, output_dir=out, visibility="public",
    )
    # 1 index + 2 stack drill-downs
    assert n == 3
    assert (out / "stacks").is_dir()
    stack_pages = list((out / "stacks").glob("*.html"))
    assert len(stack_pages) == 2


def test_private_skips_per_stack_pages(populated_db, tmp_path):
    out = tmp_path / "web"
    n = generate_web_report(
        db_path=populated_db, output_dir=out, visibility="private",
    )
    assert n == 1  # only index
    assert not (out / "stacks").exists()
    # Index includes a notice about redaction
    assert "private" in (out / "index.html").read_text()


def test_empty_database(tmp_path):
    db_path = tmp_path / "empty.db"
    engine = get_engine(db_path)
    create_tables(engine)
    engine.dispose()
    out = tmp_path / "web"
    n = generate_web_report(db_path=db_path, output_dir=out)
    assert n == 1
    html = (out / "index.html").read_text()
    assert "No stacks yet" in html


def test_custom_title(populated_db, tmp_path):
    out = tmp_path / "web"
    generate_web_report(
        db_path=populated_db, output_dir=out, title="My Experiment",
    )
    assert "My Experiment" in (out / "index.html").read_text()


class TestCLI:
    def test_report_web_command(self, populated_db, tmp_path):
        from click.testing import CliRunner
        from retort.cli import main as cli

        out = tmp_path / "web"
        runner = CliRunner()
        result = runner.invoke(cli, [
            "report", "web", "--db", str(populated_db), "--out", str(out),
        ])
        assert result.exit_code == 0, result.output
        assert (out / "index.html").exists()
