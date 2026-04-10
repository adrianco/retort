"""Integration test: design matrix → playpen run → score vector in SQLite.

Verifies the end-to-end flow from generating a design matrix through
executing runs (in simulation mode) to storing scored results.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from retort.design.factors import FactorRegistry
from retort.design.generator import generate_design
from retort.playpen.docker_runner import DockerRunner
from retort.playpen.runner import StackConfig, TaskSpec
from retort.playpen.task_loader import load_task
from retort.scoring.collector import ScoreCollector
from retort.storage.database import create_tables
from retort.storage.models import Base, ExperimentRun, RunResult, RunStatus


@pytest.fixture
def registry():
    reg = FactorRegistry()
    reg.add("language", ["python", "go"])
    reg.add("agent", ["claude-code", "cursor"])
    reg.add("framework", ["fastapi", "stdlib"])
    return reg


@pytest.fixture
def db_session(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    create_tables(engine)
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def task():
    return TaskSpec(
        name="integration-test",
        description="Test task for integration",
        prompt="Build a hello world app",
        timeout_minutes=5,
    )


class TestDesignToRun:
    def test_full_pipeline(self, registry, db_session, task, tmp_path):
        """End-to-end: design → execute → score → store."""
        # 1. Generate design matrix
        design = generate_design(registry, "screening")
        assert design.num_runs >= 4  # At least 2^2 runs for 3 factors

        # 2. Set up runner (simulation mode — no Docker needed)
        runner = DockerRunner(work_dir=tmp_path / "runs")
        collector = ScoreCollector(metrics=["build_time", "code_quality", "token_efficiency"])

        # 3. Execute each run
        runs_completed = 0
        for run_idx, run_config in enumerate(design.run_configs()):
            stack = StackConfig.from_run_config(run_config)

            env_id = runner.provision(stack, task)
            try:
                artifacts = runner.execute(env_id, stack, task)
                scores = collector.collect(artifacts, stack)

                # 4. Store in database
                status = RunStatus.completed if artifacts.succeeded else RunStatus.failed
                run = ExperimentRun(
                    replicate=1,
                    status=status,
                    run_config_json=json.dumps(run_config),
                )
                db_session.add(run)
                db_session.flush()

                for score in scores.scores:
                    result = RunResult(
                        run_id=run.id,
                        metric_name=score.metric_name,
                        value=score.value,
                    )
                    db_session.add(result)

                runs_completed += 1
            finally:
                runner.teardown(env_id)

        db_session.commit()

        # 5. Verify stored data
        stored_runs = db_session.query(ExperimentRun).all()
        assert len(stored_runs) == design.num_runs

        stored_results = db_session.query(RunResult).all()
        # Each run should have 3 scored metrics
        assert len(stored_results) == design.num_runs * 3

        # Verify metric names
        metric_names = {r.metric_name for r in stored_results}
        assert metric_names == {"build_time", "code_quality", "token_efficiency"}

        # Verify all scores are in valid range
        for result in stored_results:
            assert 0.0 <= result.value <= 1.0, (
                f"Score out of range: {result.metric_name}={result.value}"
            )

    def test_bundled_task_loading(self):
        """Verify bundled tasks load and can be used with the runner."""
        task = load_task("bundled://rest-api-crud")
        assert task.name == "rest-api-crud"
        assert task.prompt
        assert task.validation_script

    def test_design_deterministic_config(self, registry):
        """Verify design produces consistent factor assignments."""
        design = generate_design(registry, "screening")
        configs = design.run_configs()

        # Each config should have all factors
        for config in configs:
            assert "language" in config
            assert "agent" in config
            assert "framework" in config

        # All factor levels should appear
        languages = {c["language"] for c in configs}
        assert languages == {"python", "go"}
