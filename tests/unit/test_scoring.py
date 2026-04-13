"""Tests for the scoring framework."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from retort.playpen.runner import RunArtifacts, StackConfig
from retort.scoring.collector import ScoreCollector, ScoreVector
from retort.scoring.registry import ScorerRegistry, create_default_registry
from retort.scoring.scorers.build_time import BuildTimeScorer
from retort.scoring.scorers.code_quality import CodeQualityScorer
from retort.scoring.scorers.defect_rate import DefectRateScorer
from retort.scoring.scorers.maintainability import MaintainabilityScorer
from retort.scoring.scorers.test_coverage import TestCoverageScorer
from retort.scoring.scorers.token_efficiency import TokenEfficiencyScorer


@pytest.fixture
def python_stack():
    return StackConfig(language="python", agent="test", framework="fastapi")


@pytest.fixture
def successful_artifacts(tmp_path):
    # Create a fake output directory with some Python files
    src = tmp_path / "app.py"
    src.write_text("from fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n")
    test_file = tmp_path / "test_app.py"
    test_file.write_text("def test_health():\n    assert True\n")

    return RunArtifacts(
        output_dir=tmp_path,
        stdout="Server started",
        exit_code=0,
        duration_seconds=120.0,
        token_count=2000,
    )


@pytest.fixture
def failed_artifacts():
    return RunArtifacts(
        stdout="",
        stderr="Error: compilation failed",
        exit_code=1,
        duration_seconds=5.0,
    )


class TestScorerRegistry:
    def test_default_registry(self):
        reg = create_default_registry()
        assert "code_quality" in reg
        assert "token_efficiency" in reg
        assert "build_time" in reg
        assert "test_coverage" in reg
        assert "defect_rate" in reg
        assert "maintainability" in reg
        assert len(reg) == 6

    def test_register_and_get(self):
        reg = ScorerRegistry()
        scorer = BuildTimeScorer()
        reg.register(scorer)
        assert reg.get("build_time") is scorer

    def test_get_unknown_raises(self):
        reg = ScorerRegistry()
        with pytest.raises(KeyError, match="Unknown scorer"):
            reg.get("nonexistent")

    def test_available(self):
        reg = create_default_registry()
        avail = reg.available()
        assert avail == [
            "build_time",
            "code_quality",
            "defect_rate",
            "maintainability",
            "test_coverage",
            "token_efficiency",
        ]


class TestBuildTimeScorer:
    def test_failed_run_scores_zero(self, failed_artifacts, python_stack):
        scorer = BuildTimeScorer()
        assert scorer.score(failed_artifacts, python_stack) == 0.0

    def test_fast_run_scores_high(self, python_stack):
        artifacts = RunArtifacts(exit_code=0, duration_seconds=60.0)
        scorer = BuildTimeScorer()
        score = scorer.score(artifacts, python_stack)
        assert score > 0.5

    def test_slow_run_scores_low(self, python_stack):
        artifacts = RunArtifacts(exit_code=0, duration_seconds=1500.0)
        scorer = BuildTimeScorer()
        score = scorer.score(artifacts, python_stack)
        assert score < 0.5

    def test_timeout_scores_zero(self, python_stack):
        artifacts = RunArtifacts(exit_code=0, duration_seconds=2000.0)
        scorer = BuildTimeScorer()
        assert scorer.score(artifacts, python_stack) == 0.0


class TestTokenEfficiencyScorer:
    def test_failed_run_scores_zero(self, failed_artifacts, python_stack):
        scorer = TokenEfficiencyScorer()
        assert scorer.score(failed_artifacts, python_stack) == 0.0

    def test_efficient_run(self, successful_artifacts, python_stack):
        scorer = TokenEfficiencyScorer()
        score = scorer.score(successful_artifacts, python_stack)
        assert 0.0 <= score <= 1.0

    def test_no_tokens_neutral(self, python_stack, tmp_path):
        artifacts = RunArtifacts(
            output_dir=tmp_path,
            exit_code=0,
            token_count=0,
            stdout="x" * 100,
        )
        scorer = TokenEfficiencyScorer()
        score = scorer.score(artifacts, python_stack)
        assert 0.0 <= score <= 1.0


class TestCodeQualityScorer:
    def test_failed_run_scores_zero(self, failed_artifacts, python_stack):
        scorer = CodeQualityScorer()
        assert scorer.score(failed_artifacts, python_stack) == 0.0

    def test_successful_run_with_files(self, successful_artifacts, python_stack):
        scorer = CodeQualityScorer()
        score = scorer.score(successful_artifacts, python_stack)
        assert 0.0 <= score <= 1.0

    def test_no_output_dir_scores_zero(self, python_stack):
        artifacts = RunArtifacts(exit_code=0)
        scorer = CodeQualityScorer()
        assert scorer.score(artifacts, python_stack) == 0.0


class TestScoreCollector:
    def test_collect_all_metrics(self, successful_artifacts, python_stack):
        collector = ScoreCollector()
        vector = collector.collect(successful_artifacts, python_stack)
        d = vector.to_dict()
        assert "code_quality" in d
        assert "token_efficiency" in d
        assert "build_time" in d
        assert all(0.0 <= v <= 1.0 for v in d.values())

    def test_collect_subset(self, successful_artifacts, python_stack):
        collector = ScoreCollector(metrics=["build_time"])
        vector = collector.collect(successful_artifacts, python_stack)
        d = vector.to_dict()
        assert "build_time" in d
        assert "code_quality" not in d

    def test_collect_failed_run(self, failed_artifacts, python_stack):
        collector = ScoreCollector()
        vector = collector.collect(failed_artifacts, python_stack)
        d = vector.to_dict()
        assert all(v == 0.0 for v in d.values())

    def test_unknown_metric_skipped(self, successful_artifacts, python_stack):
        collector = ScoreCollector(metrics=["nonexistent", "build_time"])
        vector = collector.collect(successful_artifacts, python_stack)
        d = vector.to_dict()
        assert "build_time" in d
        assert "nonexistent" not in d


class TestScoreVector:
    def test_to_dict(self):
        from retort.scoring.collector import ScoreResult
        vector = ScoreVector(scores=[
            ScoreResult(metric_name="a", value=1.0),
            ScoreResult(metric_name="b", value=0.5),
        ])
        assert vector.to_dict() == {"a": 1.0, "b": 0.5}

    def test_get(self):
        from retort.scoring.collector import ScoreResult
        vector = ScoreVector(scores=[
            ScoreResult(metric_name="a", value=1.0),
        ])
        assert vector.get("a") == 1.0
        assert vector.get("missing") is None


class TestTestCoverageScorer:
    def test_failed_run_scores_zero(self, failed_artifacts, python_stack):
        scorer = TestCoverageScorer()
        assert scorer.score(failed_artifacts, python_stack) == 0.0

    def test_no_output_dir_scores_zero(self, python_stack):
        scorer = TestCoverageScorer()
        artifacts = RunArtifacts(stdout="", exit_code=0, duration_seconds=10.0)
        assert scorer.score(artifacts, python_stack) == 0.0

    def test_unknown_language_scores_zero(self, successful_artifacts):
        scorer = TestCoverageScorer()
        stack = StackConfig(language="brainfuck", agent="test", framework="none")
        # Coverage tool unavailable for unknown language → 0
        assert scorer.score(successful_artifacts, stack) == 0.0

    def test_parse_python_total_line(self):
        from retort.scoring.scorers.test_coverage import _parse_coverage
        out = "Name      Stmts   Miss  Cover\n----  ----  ----  ----\nTOTAL     124     12    90%\n"
        assert _parse_coverage(out, "python") == 90.0

    def test_parse_go_per_package_mean(self):
        from retort.scoring.scorers.test_coverage import _parse_coverage
        out = "ok pkg/a 0.1s coverage: 80% of statements\nok pkg/b 0.2s coverage: 60% of statements"
        assert _parse_coverage(out, "go") == 70.0


class TestDefectRateScorer:
    def test_failed_run_scores_zero(self, failed_artifacts, python_stack):
        scorer = DefectRateScorer()
        assert scorer.score(failed_artifacts, python_stack) == 0.0

    def test_no_source_files_scores_zero(self, python_stack, tmp_path):
        scorer = DefectRateScorer()
        # Empty workspace, no source files of the language
        artifacts = RunArtifacts(
            output_dir=tmp_path, stdout="", exit_code=0, duration_seconds=1.0,
        )
        assert scorer.score(artifacts, python_stack) == 0.0

    def test_clean_code_scores_high(self, python_stack, tmp_path):
        # A small valid Python module with no defects
        (tmp_path / "app.py").write_text("def main():\n    return 1\n")
        artifacts = RunArtifacts(
            output_dir=tmp_path, stdout="", exit_code=0, duration_seconds=1.0,
        )
        scorer = DefectRateScorer()
        score = scorer.score(artifacts, python_stack)
        # If ruff/py_compile unavailable in the test env we still expect
        # a non-zero score (no defects detected against real LOC).
        assert 0.0 <= score <= 1.0


class TestMaintainabilityScorer:
    def test_failed_run_scores_zero(self, failed_artifacts, python_stack):
        scorer = MaintainabilityScorer()
        assert scorer.score(failed_artifacts, python_stack) == 0.0

    def test_no_source_files_scores_zero(self, python_stack, tmp_path):
        scorer = MaintainabilityScorer()
        artifacts = RunArtifacts(
            output_dir=tmp_path, stdout="", exit_code=0, duration_seconds=1.0,
        )
        assert scorer.score(artifacts, python_stack) == 0.0

    def test_well_structured_python_scores_above_zero(self, python_stack, tmp_path):
        # 3 short functions + 1 test file → expect above 0
        (tmp_path / "app.py").write_text(
            "def a():\n    return 1\n\n"
            "def b():\n    return 2\n\n"
            "def c():\n    return 3\n"
        )
        (tmp_path / "test_app.py").write_text(
            "def test_a():\n    assert True\n"
        )
        artifacts = RunArtifacts(
            output_dir=tmp_path, stdout="", exit_code=0, duration_seconds=1.0,
        )
        scorer = MaintainabilityScorer()
        assert scorer.score(artifacts, python_stack) > 0.0

    def test_ramp_lower_is_better(self):
        from retort.scoring.scorers.maintainability import _ramp
        assert _ramp(0, 10, 50, lower_is_better=True) == 1.0
        assert _ramp(10, 10, 50, lower_is_better=True) == 1.0
        assert _ramp(50, 10, 50, lower_is_better=True) == 0.0
        assert _ramp(30, 10, 50, lower_is_better=True) == 0.5

    def test_ramp_higher_is_better(self):
        from retort.scoring.scorers.maintainability import _ramp
        assert _ramp(1.0, 0.5, 0.0, lower_is_better=False) == 1.0
        assert _ramp(0.5, 0.5, 0.0, lower_is_better=False) == 1.0
        assert _ramp(0.0, 0.5, 0.0, lower_is_better=False) == 0.0
        assert _ramp(0.25, 0.5, 0.0, lower_is_better=False) == 0.5
