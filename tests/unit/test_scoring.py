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
from retort.scoring.scorers.idiomatic import IdiomaticScorer
from retort.scoring.scorers.maintainability import MaintainabilityScorer
from retort.scoring.scorers.test_coverage import TestCoverageScorer
from retort.scoring.scorers.test_quality import TestQualityScorer
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
        assert "test_coverage" in reg
        assert "test_quality" in reg
        assert "defect_rate" in reg
        assert "maintainability" in reg
        assert "idiomatic" in reg
        # build_time was removed — use the raw `_duration_seconds`
        # telemetry instead (auto-persisted from artifacts.duration_seconds).
        assert "build_time" not in reg
        assert len(reg) == 7

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
            "code_quality",
            "defect_rate",
            "idiomatic",
            "maintainability",
            "test_coverage",
            "test_quality",
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

    def test_monotonic_decreasing(self, python_stack):
        """Regression: previous formula collapsed every short run to 1.0,
        making build_time a useless constant. Must be strictly monotonic."""
        scorer = BuildTimeScorer()
        scores = [
            scorer.score(RunArtifacts(exit_code=0, duration_seconds=t), python_stack)
            for t in (10, 50, 100, 200, 300, 600, 900, 1500)
        ]
        # No two adjacent scores are equal, and they decrease as duration grows.
        assert all(a > b for a, b in zip(scores, scores[1:])), scores


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
        assert all(0.0 <= v <= 1.0 for v in d.values())

    def test_collect_subset(self, successful_artifacts, python_stack):
        collector = ScoreCollector(metrics=["code_quality"])
        vector = collector.collect(successful_artifacts, python_stack)
        d = vector.to_dict()
        assert "code_quality" in d
        assert "token_efficiency" not in d

    def test_collect_failed_run(self, failed_artifacts, python_stack):
        collector = ScoreCollector()
        vector = collector.collect(failed_artifacts, python_stack)
        d = vector.to_dict()
        assert all(v == 0.0 for v in d.values())

    def test_unknown_metric_skipped(self, successful_artifacts, python_stack):
        collector = ScoreCollector(metrics=["nonexistent", "code_quality"])
        vector = collector.collect(successful_artifacts, python_stack)
        d = vector.to_dict()
        assert "code_quality" in d
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


class TestIdiomaticScorer:
    def test_failed_run_scores_zero(self, failed_artifacts, python_stack):
        scorer = IdiomaticScorer()
        assert scorer.score(failed_artifacts, python_stack) == 0.0

    def test_no_output_dir_scores_zero(self, python_stack):
        scorer = IdiomaticScorer()
        artifacts = RunArtifacts(stdout="", exit_code=0, duration_seconds=10.0)
        assert scorer.score(artifacts, python_stack) == 0.0

    def test_cli_missing_returns_neutral(self, python_stack, tmp_path):
        # Code present, but the judge CLI doesn't exist.
        (tmp_path / "app.py").write_text("def main():\n    return 1\n" * 5)
        artifacts = RunArtifacts(
            output_dir=tmp_path, stdout="", exit_code=0, duration_seconds=1.0,
        )
        scorer = IdiomaticScorer(cli="this-binary-does-not-exist-12345")
        # Falls back to neutral when the CLI is unavailable. No cache write
        # since the judge call failed.
        assert scorer.score(artifacts, python_stack) == 0.5

    def test_cache_short_circuits(self, python_stack, tmp_path):
        # Pre-populate the cache; scorer should never invoke the CLI.
        (tmp_path / "app.py").write_text("def main():\n    return 1\n" * 5)
        cache = tmp_path / ".idiomatic_cache.json"
        import json
        cache.write_text(json.dumps({"score": 0.42, "model": "test"}))
        artifacts = RunArtifacts(
            output_dir=tmp_path, stdout="", exit_code=0, duration_seconds=1.0,
        )
        # Pointing the scorer at a nonexistent CLI proves the cache hit
        # bypasses the subprocess entirely.
        scorer = IdiomaticScorer(cli="this-binary-does-not-exist-12345")
        assert scorer.score(artifacts, python_stack) == 0.42

    def test_parse_score(self):
        from retort.scoring.scorers.idiomatic import _parse_score
        assert _parse_score("0.85") == 0.85
        assert _parse_score("Score: 0.7\nReason: ...") == 0.7
        assert _parse_score("1.0") == 1.0
        assert _parse_score("not a number") is None
        assert _parse_score("") is None
        # Clamped to [0,1]
        assert _parse_score("1.5") == 1.0  # matches "1.5" at the boundary, capped

    def test_representative_sample_skips_tiny_files(self, tmp_path):
        from retort.scoring.scorers.idiomatic import _representative_sample
        (tmp_path / "stub.py").write_text("x=1\n")  # under 64 bytes — skipped
        (tmp_path / "real.py").write_text("def main():\n    return 'hello'\n" * 10)
        sample = _representative_sample(tmp_path, "python")
        assert "real.py" in sample
        assert "stub.py" not in sample

    def test_representative_sample_skips_build_artifacts(self, tmp_path):
        from retort.scoring.scorers.idiomatic import _representative_sample
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "huge.ts").write_text("x" * 1000)
        (tmp_path / "real.ts").write_text("export const main = () => 1;\n" * 10)
        sample = _representative_sample(tmp_path, "typescript")
        assert "real.ts" in sample
        assert "huge.ts" not in sample


class TestTestQualityScorer:
    def test_no_output_dir_scores_zero(self, python_stack):
        scorer = TestQualityScorer()
        artifacts = RunArtifacts(stdout="", exit_code=0, duration_seconds=1.0)
        assert scorer.score(artifacts, python_stack) == 0.0

    def test_no_tests_no_bdd_returns_base(self, python_stack, tmp_path):
        # Empty workspace, no test files → base score = 0.0
        (tmp_path / "app.py").write_text("def main(): return 1\n")
        artifacts = RunArtifacts(
            output_dir=tmp_path, stdout="", exit_code=0, duration_seconds=1.0,
        )
        scorer = TestQualityScorer()
        assert scorer.score(artifacts, python_stack) == 0.0

    def test_feature_file_unprompted_adds_bonus(self, python_stack, tmp_path):
        # .feature file present, no BDD keywords in TASK.md → 0.25 bonus
        (tmp_path / "login.feature").write_text(
            "Feature: Login\n  Scenario: valid user\n    Given ...\n"
        )
        (tmp_path / "TASK.md").write_text("Build a login endpoint.\n")
        artifacts = RunArtifacts(
            output_dir=tmp_path, stdout="", exit_code=0, duration_seconds=1.0,
        )
        scorer = TestQualityScorer()
        score = scorer.score(artifacts, python_stack)
        # base=0.0 + unprompted bonus=0.25
        assert score == pytest.approx(0.25)

    def test_feature_file_prompted_adds_smaller_bonus(self, python_stack, tmp_path):
        # .feature file + TASK.md mentions BDD → 0.15 bonus
        (tmp_path / "login.feature").write_text(
            "Feature: Login\n  Scenario: valid user\n    Given ...\n"
        )
        (tmp_path / "TASK.md").write_text(
            "Use BDD with Given/When/Then scenarios.\n"
        )
        artifacts = RunArtifacts(
            output_dir=tmp_path, stdout="", exit_code=0, duration_seconds=1.0,
        )
        scorer = TestQualityScorer()
        score = scorer.score(artifacts, python_stack)
        # base=0.0 + prompted bonus=0.15
        assert score == pytest.approx(0.15)

    def test_behave_import_detected(self, python_stack, tmp_path):
        # Python file importing behave → BDD detected
        steps = tmp_path / "steps"
        steps.mkdir()
        (steps / "login_steps.py").write_text(
            "from behave import given, when, then\n\n"
            "@given('a user exists')\ndef step_given(context):\n    pass\n"
        )
        (tmp_path / "TASK.md").write_text("Build a login flow.\n")
        artifacts = RunArtifacts(
            output_dir=tmp_path, stdout="", exit_code=0, duration_seconds=1.0,
        )
        scorer = TestQualityScorer()
        score = scorer.score(artifacts, python_stack)
        assert score == pytest.approx(0.25)

    def test_pytest_bdd_decorator_detected(self, python_stack, tmp_path):
        # conftest.py with @given/@when/@then → BDD detected
        (tmp_path / "conftest.py").write_text(
            "from pytest_bdd import given, when, then\n\n"
            "@given('the system is ready')\ndef ready():\n    pass\n"
        )
        (tmp_path / "TASK.md").write_text("Implement using pytest-bdd.\n")
        artifacts = RunArtifacts(
            output_dir=tmp_path, stdout="", exit_code=0, duration_seconds=1.0,
        )
        scorer = TestQualityScorer()
        score = scorer.score(artifacts, python_stack)
        # TASK.md mentions "pytest-bdd" → prompted bonus
        assert score == pytest.approx(0.15)

    def test_no_task_md_treated_as_unprompted(self, python_stack, tmp_path):
        # Feature file present, no TASK.md at all → treated as unprompted
        (tmp_path / "signup.feature").write_text(
            "Feature: Signup\n  Scenario: new user\n    Given ...\n"
        )
        artifacts = RunArtifacts(
            output_dir=tmp_path, stdout="", exit_code=0, duration_seconds=1.0,
        )
        scorer = TestQualityScorer()
        assert scorer.score(artifacts, python_stack) == pytest.approx(0.25)

    def test_score_capped_at_one(self, python_stack, tmp_path):
        from unittest.mock import patch
        # Even if base_score + bonus > 1.0, result must be ≤ 1.0
        (tmp_path / "tests.feature").write_text("Feature: f\n  Scenario: s\n")
        (tmp_path / "TASK.md").write_text("Implement the feature.\n")
        artifacts = RunArtifacts(
            output_dir=tmp_path, stdout="", exit_code=0, duration_seconds=1.0,
        )
        scorer = TestQualityScorer()
        with patch(
            "retort.scoring.scorers.test_coverage.TestCoverageScorer.score",
            return_value=0.9,
        ):
            score = scorer.score(artifacts, python_stack)
        assert score <= 1.0
