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
        assert "bead_usage_score" in reg
        assert "build_time" not in reg
        assert len(reg) == 9

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
            "bead_usage_score",
            "code_quality",
            "defect_rate",
            "findings",
            "idiomatic",
            "maintainability",
            "test_coverage",
            "test_quality",
            "token_efficiency",
        ]


class TestBeadUsageScorer:
    def _beads_stack(self):
        return StackConfig(language="python", agent="test", framework="none",
                           extra={"tooling": "beads"})

    def _no_beads_stack(self):
        return StackConfig(language="python", agent="test", framework="none",
                           extra={"tooling": "none"})

    def test_not_applicable_returns_one(self, tmp_path):
        from retort.scoring.scorers.bead_usage import BeadUsageScorer
        scorer = BeadUsageScorer()
        artifacts = RunArtifacts(output_dir=tmp_path, exit_code=0)
        assert scorer.score(artifacts, self._no_beads_stack()) == 1.0

    def test_no_beads_dir_scores_zero(self, tmp_path):
        from retort.scoring.scorers.bead_usage import BeadUsageScorer
        scorer = BeadUsageScorer()
        artifacts = RunArtifacts(output_dir=tmp_path, exit_code=0)
        assert scorer.score(artifacts, self._beads_stack()) == 0.0

    def test_empty_beads_dir_scores_zero(self, tmp_path):
        from retort.scoring.scorers.bead_usage import BeadUsageScorer
        (tmp_path / ".beads").mkdir()
        scorer = BeadUsageScorer()
        artifacts = RunArtifacts(output_dir=tmp_path, exit_code=0)
        assert scorer.score(artifacts, self._beads_stack()) == 0.0

    def test_interactions_log_counts_ops(self, tmp_path):
        from retort.scoring.scorers.bead_usage import BeadUsageScorer, EXPECTED_MIN_OPS
        beads_dir = tmp_path / ".beads"
        beads_dir.mkdir()
        interactions = beads_dir / "interactions.jsonl"
        interactions.write_text("\n".join(
            '{"id":"int-%d","kind":"field_change"}' % i
            for i in range(EXPECTED_MIN_OPS)
        ) + "\n")
        scorer = BeadUsageScorer()
        artifacts = RunArtifacts(output_dir=tmp_path, exit_code=0)
        assert scorer.score(artifacts, self._beads_stack()) == 1.0

    def test_partial_ops_score_proportional(self, tmp_path):
        from retort.scoring.scorers.bead_usage import BeadUsageScorer, EXPECTED_MIN_OPS
        beads_dir = tmp_path / ".beads"
        beads_dir.mkdir()
        interactions = beads_dir / "interactions.jsonl"
        half = EXPECTED_MIN_OPS // 2
        interactions.write_text("\n".join(
            '{"id":"int-%d","kind":"field_change"}' % i for i in range(half)
        ) + "\n")
        scorer = BeadUsageScorer()
        artifacts = RunArtifacts(output_dir=tmp_path, exit_code=0)
        score = scorer.score(artifacts, self._beads_stack())
        assert 0.0 < score < 1.0

    def test_many_ops_capped_at_one(self, tmp_path):
        from retort.scoring.scorers.bead_usage import BeadUsageScorer, EXPECTED_MIN_OPS
        beads_dir = tmp_path / ".beads"
        beads_dir.mkdir()
        interactions = beads_dir / "interactions.jsonl"
        interactions.write_text("\n".join(
            '{"id":"int-%d","kind":"field_change"}' % i
            for i in range(EXPECTED_MIN_OPS * 10)
        ) + "\n")
        scorer = BeadUsageScorer()
        artifacts = RunArtifacts(output_dir=tmp_path, exit_code=0)
        assert scorer.score(artifacts, self._beads_stack()) == 1.0

    def test_no_output_dir_scores_zero(self):
        from retort.scoring.scorers.bead_usage import BeadUsageScorer
        scorer = BeadUsageScorer()
        artifacts = RunArtifacts(exit_code=0)
        assert scorer.score(artifacts, self._beads_stack()) == 0.0

    def test_tooling_not_set_defaults_to_not_applicable(self, tmp_path):
        from retort.scoring.scorers.bead_usage import BeadUsageScorer
        scorer = BeadUsageScorer()
        stack = StackConfig(language="python", agent="test", framework="none")
        artifacts = RunArtifacts(output_dir=tmp_path, exit_code=0)
        assert scorer.score(artifacts, stack) == 1.0


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

    def test_parse_vitest_pass_rate_fallback(self):
        # Regression: a vitest suite with no @vitest/coverage-v8 has no coverage
        # %, so the pass-rate fallback must parse vitest's summary or the run
        # scores 0 (test-gate veto) despite passing tests.
        from retort.scoring.scorers.test_coverage import _parse_test_pass_rate
        assert _parse_test_pass_rate(" Test Files  7 passed (7)\n      Tests  40 passed (40)",
                                     "typescript") == 1.0
        assert _parse_test_pass_rate("      Tests  45 passed | 4 failed (49)",
                                     "typescript") == 45 / 49

    def test_clojure_runner_follows_project_layout(self, tmp_path):
        # Regression: a Leiningen project (project.clj, no deps.edn) must be
        # tested with `lein test`, not the clojure CLI's `-M:test` (which finds
        # no :test alias and silently REPLs → test_coverage=0 → false gate fail,
        # as seen for sonnet clojure runs in exp-1 and exp-9).
        from retort.scoring.scorers.test_coverage import _tests_only_commands
        (tmp_path / "project.clj").write_text("(defproject books \"0.1\")")
        assert _tests_only_commands("clojure", tmp_path) == [["lein", "test"]]
        (tmp_path / "deps.edn").write_text("{}")
        assert _tests_only_commands("clojure", tmp_path) == [
            ["clojure", "-M:test"], ["lein", "test"],
        ]

    def test_erlang_runner_adds_ct_for_common_test_suite(self, tmp_path):
        # Regression: an agent that writes a Common Test suite (test/*_SUITE.erl)
        # instead of EUnit must still be scored — `rebar3 eunit` reports such a
        # project as "0 tests" (test_coverage=0 -> false gate fail), so `rebar3
        # ct` is added as a fallback. eunit stays first so an EUnit project
        # short-circuits (seen for erlang/sonnet rep1 vs rep2 in exp-9).
        from retort.scoring.scorers.test_coverage import _tests_only_commands
        assert _tests_only_commands("erlang", tmp_path) == [["rebar3", "eunit"]]
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / "book_api_SUITE.erl").write_text("-module(book_api_SUITE).")
        assert _tests_only_commands("erlang", tmp_path) == [
            ["rebar3", "eunit"], ["rebar3", "ct"],
        ]

    def test_erlang_ct_output_parses(self):
        # `rebar3 ct` success line must parse so a passing CT suite scores 1.0.
        from retort.scoring.scorers.test_coverage import _parse_test_pass_rate
        assert _parse_test_pass_rate("%%% book_api_SUITE: ..........\nAll 10 tests passed.\n",
                                     "erlang") == 1.0

    def test_elixir_custom_result_summary_parses(self):
        # Regression: some elixir projects swap ExUnit's formatter and print
        # "Result: N passed" instead of "N tests, 0 failures" — the scorer must
        # still parse it or a passing suite scores 0 (exp-9 elixir false-fails).
        from retort.scoring.scorers.test_coverage import _parse_test_pass_rate
        assert _parse_test_pass_rate("Result: 19 passed", "elixir") == 1.0
        assert _parse_test_pass_rate("Result: 17 passed, 3 failed", "elixir") == 17 / 20
        # The standard ExUnit summary must still parse too.
        assert _parse_test_pass_rate("5 tests, 0 failures", "elixir") == 1.0

    def test_clojure_lein_test_output_parses(self):
        # `lein test` and `clojure -M:test` share the same summary format,
        # which the pass-rate fallback must recognise so a passing lein
        # project scores 1.0, not 0.0.
        from retort.scoring.scorers.test_coverage import _parse_test_pass_rate
        out = "lein test books.core-test\n\nRan 6 tests containing 23 assertions.\n0 failures, 0 errors.\n"
        assert _parse_test_pass_rate(out, "clojure") == 1.0
        bad = "Ran 6 tests containing 23 assertions.\n2 failures, 1 errors.\n"
        assert _parse_test_pass_rate(bad, "clojure") == pytest.approx(3 / 6)


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

    def test_beam_loc_counts_source_and_skips_build(self, tmp_path):
        # Regression: erlang/elixir were absent from _LOC_EXTENSIONS, so loc=0
        # forced defect_rate to 0 for every BEAM run. Source must now count and
        # the _build/deps dependency trees must be excluded.
        from retort.scoring.scorers.defect_rate import _count_source_lines
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "books.erl").write_text("-module(books).\nstart() -> ok.\n")
        (tmp_path / "lib").mkdir()
        (tmp_path / "lib" / "books.ex").write_text("defmodule Books do\n  def go, do: :ok\nend\n")
        # Dependency trees that must NOT be counted.
        for d in ("_build", "deps"):
            (tmp_path / d).mkdir()
            (tmp_path / d / "junk.erl").write_text("\n".join("x() -> y." for _ in range(500)))
            (tmp_path / d / "junk.ex").write_text("\n".join("def x, do: 1" for _ in range(500)))
        assert _count_source_lines(tmp_path, "erlang") == 2
        assert _count_source_lines(tmp_path, "elixir") == 3


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

    def test_beam_languages_score_above_zero(self, tmp_path):
        # Regression: erlang/elixir were absent from the function-pattern and
        # source-extension dicts, so every BEAM run scored maintainability 0.
        from retort.scoring.scorers.maintainability import _collect_files
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "books.erl").write_text(
            "-module(books).\n-export([start/0]).\n\n"
            "start() ->\n    ok.\n\n"
            "stop() ->\n    ok.\n"
        )
        (tmp_path / "test").mkdir()
        (tmp_path / "test" / "books_tests.erl").write_text("-module(books_tests).\n")
        erl_src, erl_tests = _collect_files(tmp_path, "erlang")
        assert len(erl_src) == 1 and len(erl_tests) == 1

        (tmp_path / "lib").mkdir()
        (tmp_path / "lib" / "books.ex").write_text(
            "defmodule Books do\n  def start, do: :ok\n  defp helper, do: 1\nend\n"
        )
        (tmp_path / "test" / "books_test.exs").write_text("defmodule BooksTest do\nend\n")
        ex_src, ex_tests = _collect_files(tmp_path, "elixir")
        assert len(ex_src) == 1 and len(ex_tests) == 1
        for lang in ("erlang", "elixir"):
            art = RunArtifacts(output_dir=tmp_path, stdout="", exit_code=0,
                               duration_seconds=1.0)
            st = StackConfig(language=lang, agent="x", framework="none")
            assert MaintainabilityScorer().score(art, st) > 0.0

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
        # Mock the coverage scorer: conftest.py causes pytest to traverse up to the
        # project rootdir and run all retort tests, producing a non-zero base score.
        from unittest.mock import patch
        (tmp_path / "conftest.py").write_text(
            "from pytest_bdd import given, when, then\n\n"
            "@given('the system is ready')\ndef ready():\n    pass\n"
        )
        (tmp_path / "TASK.md").write_text("Implement using pytest-bdd.\n")
        artifacts = RunArtifacts(
            output_dir=tmp_path, stdout="", exit_code=0, duration_seconds=1.0,
        )
        scorer = TestQualityScorer()
        with patch(
            "retort.scoring.scorers.test_coverage.TestCoverageScorer.score",
            return_value=0.0,
        ):
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


def test_test_coverage_parses_elixir_erlang_pass_rate():
    """erlang (rebar3 eunit) + elixir (mix test) output -> pass-rate fallback,
    so those runs aren't falsely zeroed by the tests-gate."""
    from retort.scoring.scorers.test_coverage import _parse_test_pass_rate as p
    assert p("5 tests, 0 failures", "elixir") == 1.0
    assert abs(p("8 tests, 1 failure, 2 skipped", "elixir") - 5/8) < 1e-9
    assert p("  All 12 tests passed.", "erlang") == 1.0
    assert abs(p("Failed: 1.  Skipped: 0.  Passed: 11.", "erlang") - 11/12) < 1e-9
    from retort.scoring.scorers.test_coverage import _TESTS_ONLY_COMMANDS
    assert "elixir" in _TESTS_ONLY_COMMANDS and "erlang" in _TESTS_ONLY_COMMANDS


# --- Regression: cross-package (ATDD) go coverage + python dep/venv handling ---

import shutil  # noqa: E402


def _go_module(tmp_path: Path) -> RunArtifacts:
    """A module whose ONLY test lives in the root package and drives a sibling
    package (calc) through its public API — the acceptance/ATDD pattern that
    `go test -cover ./...` (no -coverpkg) miscounts as 0% for calc."""
    (tmp_path / "go.mod").write_text("module ex\ngo 1.21\n")
    (tmp_path / "calc").mkdir()
    (tmp_path / "calc" / "calc.go").write_text(
        "package calc\n"
        "func Add(a, b int) int { return a + b }\n"
        "func Sub(a, b int) int { return a - b }\n"
    )
    (tmp_path / "main.go").write_text("package main\nfunc main() {}\n")
    (tmp_path / "main_test.go").write_text(
        "package main\n\nimport (\n\t\"testing\"\n\n\t\"ex/calc\"\n)\n\n"
        "func TestAdd(t *testing.T) {\n"
        "\tif calc.Add(1, 2) != 3 {\n\t\tt.Fatal(\"add\")\n\t}\n}\n"
    )
    return RunArtifacts(
        output_dir=tmp_path, stdout="", exit_code=0, duration_seconds=1.0)


@pytest.mark.skipif(shutil.which("go") is None, reason="go toolchain not installed")
class TestGoCrossPackageCoverage:
    """The go scorer must credit cross-package (acceptance) test execution."""

    def test_crosspackage_execution_is_credited(self, tmp_path):
        art = _go_module(tmp_path)
        score = TestCoverageScorer().score(
            art, StackConfig(language="go", agent="t", framework="x"))
        # Root test covers calc.Add (1 of 2 funcs) through calc's public API.
        # Per-package `-cover` would score calc 0% (no in-package test); the
        # -coverpkg profile total credits it, so this must be well above 0.
        assert score >= 0.4, f"cross-package coverage not credited: {score}"

    def test_relative_output_dir_still_measures(self, tmp_path, monkeypatch):
        # Regression: -coverprofile must be absolute, so a RELATIVE output_dir
        # (rescore passes archive paths relative to cwd) must still score.
        _go_module(tmp_path)
        monkeypatch.chdir(tmp_path.parent)
        art = RunArtifacts(output_dir=Path(tmp_path.name), stdout="",
                           exit_code=0, duration_seconds=1.0)
        score = TestCoverageScorer().score(
            art, StackConfig(language="go", agent="t", framework="x"))
        assert score >= 0.4, f"relative output_dir scored 0: {score}"

    def test_no_stray_profile_left_behind(self, tmp_path):
        _go_module(tmp_path)
        TestCoverageScorer().score(
            RunArtifacts(output_dir=tmp_path, stdout="", exit_code=0,
                         duration_seconds=1.0),
            StackConfig(language="go", agent="t", framework="x"))
        assert not (tmp_path / ".retort-cover.out").exists()


class TestPythonEnvPreparation:
    """The python scorer must prepare deps without polluting the workspace."""

    def test_throwaway_venv_is_outside_output_dir(self, tmp_path):
        from retort.scoring.scorers._venv import ensure_python_env
        (tmp_path / "app.py").write_text("x = 1\n")
        env, cleanup = ensure_python_env(tmp_path)
        try:
            # A venv inside output_dir would be collected/measured by
            # `pytest --cov=.` and corrupt the score — it must be elsewhere.
            assert not (tmp_path / ".retort-venv").exists()
            if cleanup is not None:
                assert cleanup != tmp_path
                assert tmp_path not in cleanup.parents
        finally:
            if cleanup is not None:
                shutil.rmtree(cleanup, ignore_errors=True)

    def test_code_but_no_tests_scores_zero(self, tmp_path):
        # Regression: with no shipped venv the scorer creates a throwaway one;
        # a workspace with code but no tests must still score 0, not pick up
        # coverage from the venv's own site-packages.
        (tmp_path / "app.py").write_text("def main():\n    return 1\n")
        score = TestCoverageScorer().score(
            RunArtifacts(output_dir=tmp_path, stdout="", exit_code=0,
                         duration_seconds=1.0),
            StackConfig(language="python", agent="t", framework="x"))
        assert score == 0.0

    def test_tests_importing_project_package_are_collected(self, tmp_path):
        # `python -m pytest` (not the bare script) puts the run dir on sys.path,
        # so a test importing the project's OWN top-level package collects
        # without it being pip-installed. The bare script -> ModuleNotFoundError
        # -> false 0. (No external deps, so this only exercises the -m fix.)
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "calc.py").write_text("def add(a, b):\n    return a + b\n")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_calc.py").write_text(
            "from mypkg.calc import add\n\n\n"
            "def test_add():\n    assert add(1, 2) == 3\n")
        score = TestCoverageScorer().score(
            RunArtifacts(output_dir=tmp_path, stdout="", exit_code=0,
                         duration_seconds=1.0),
            StackConfig(language="python", agent="t", framework="x"))
        assert score > 0.0, "tests importing the project package weren't collected"

    def test_relative_output_dir_python(self, tmp_path, monkeypatch):
        # Regression: a RELATIVE output_dir (rescore passes archive paths) must
        # not break `-r requirements.txt`/cwd path resolution -> 0.
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "calc.py").write_text("def add(a, b):\n    return a + b\n")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_calc.py").write_text(
            "from mypkg.calc import add\n\n\n"
            "def test_add():\n    assert add(1, 2) == 3\n")
        monkeypatch.chdir(tmp_path.parent)
        art = RunArtifacts(output_dir=Path(tmp_path.name), stdout="",
                           exit_code=0, duration_seconds=1.0)
        score = TestCoverageScorer().score(
            art, StackConfig(language="python", agent="t", framework="x"))
        assert score > 0.0, "relative output_dir scored 0"
