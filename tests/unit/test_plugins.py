"""Tests for the pluggy-based plugin system."""

from __future__ import annotations

from pathlib import Path

import pluggy
import pytest
from click.testing import CliRunner

from retort.cli import main as cli
from retort.playpen.runner import (
    PlaypenRunner,
    RunArtifacts,
    RunnerRegistry,
    StackConfig,
    TaskSpec,
    create_default_runner_registry,
)
from retort.plugins import (
    PROJECT_NAME,
    RetortHookSpec,
    _create_plugin_manager,
    discover_runners,
    discover_scorers,
    get_plugin_manager,
    hookimpl,
)
from retort.scoring.registry import ScorerRegistry, create_default_registry


# ---------------------------------------------------------------------------
# Fixtures: fake scorer and runner for testing plugin hooks
# ---------------------------------------------------------------------------


class FakeScorer:
    """A minimal scorer for testing plugin discovery."""

    @property
    def name(self) -> str:
        return "fake_metric"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        return 0.42


class AnotherFakeScorer:
    @property
    def name(self) -> str:
        return "another_metric"

    def score(self, artifacts: RunArtifacts, stack: StackConfig) -> float:
        return 0.99


class FakeRunner:
    """A minimal runner for testing plugin discovery."""

    def provision(self, stack: StackConfig, task: TaskSpec) -> str:
        return "fake-env-1"

    def execute(self, env_id: str, stack: StackConfig, task: TaskSpec) -> RunArtifacts:
        return RunArtifacts(exit_code=0, duration_seconds=1.0)

    def teardown(self, env_id: str) -> None:
        pass


class SamplePlugin:
    """A plugin that registers one scorer and one runner."""

    @hookimpl
    def retort_register_scorers(self) -> list:
        return [FakeScorer()]

    @hookimpl
    def retort_register_runners(self) -> dict:
        return {"fake": FakeRunner()}


class MultiScorerPlugin:
    """A plugin that registers multiple scorers."""

    @hookimpl
    def retort_register_scorers(self) -> list:
        return [FakeScorer(), AnotherFakeScorer()]


class EmptyPlugin:
    """A plugin that returns empty lists."""

    @hookimpl
    def retort_register_scorers(self) -> list:
        return []

    @hookimpl
    def retort_register_runners(self) -> dict:
        return {}


@pytest.fixture
def pm_with_sample_plugin() -> pluggy.PluginManager:
    """PluginManager with the SamplePlugin registered."""
    pm = _create_plugin_manager()
    pm.register(SamplePlugin())
    return pm


@pytest.fixture
def pm_with_multi_scorer() -> pluggy.PluginManager:
    pm = _create_plugin_manager()
    pm.register(MultiScorerPlugin())
    return pm


@pytest.fixture
def pm_empty() -> pluggy.PluginManager:
    """PluginManager with no plugins registered."""
    return _create_plugin_manager()


# ---------------------------------------------------------------------------
# Tests: hook specifications
# ---------------------------------------------------------------------------


class TestHookSpecs:
    def test_project_name(self):
        assert PROJECT_NAME == "retort"

    def test_create_plugin_manager_has_hookspecs(self):
        pm = _create_plugin_manager()
        # Hookspec class should be registered
        assert pm.parse_hookimpl_opts is not None

    def test_hookimpl_marker_works(self):
        """Verify @hookimpl marks methods correctly."""
        plugin = SamplePlugin()
        # The hookimpl marker sets an attribute on the method
        marker_attr = f"{PROJECT_NAME}_impl"
        assert hasattr(plugin.retort_register_scorers, marker_attr)


# ---------------------------------------------------------------------------
# Tests: scorer discovery
# ---------------------------------------------------------------------------


class TestDiscoverScorers:
    def test_no_plugins_returns_empty(self, pm_empty):
        scorers = discover_scorers(pm_empty)
        assert scorers == []

    def test_discovers_single_scorer(self, pm_with_sample_plugin):
        scorers = discover_scorers(pm_with_sample_plugin)
        assert len(scorers) == 1
        assert scorers[0].name == "fake_metric"

    def test_discovers_multiple_scorers(self, pm_with_multi_scorer):
        scorers = discover_scorers(pm_with_multi_scorer)
        names = {s.name for s in scorers}
        assert names == {"fake_metric", "another_metric"}

    def test_empty_plugin_returns_empty(self):
        pm = _create_plugin_manager()
        pm.register(EmptyPlugin())
        scorers = discover_scorers(pm)
        assert scorers == []

    def test_multiple_plugins_combined(self):
        pm = _create_plugin_manager()
        pm.register(SamplePlugin())
        pm.register(MultiScorerPlugin())
        scorers = discover_scorers(pm)
        # SamplePlugin gives FakeScorer, MultiScorerPlugin gives FakeScorer + AnotherFakeScorer
        assert len(scorers) == 3

    def test_scorer_protocol_compliance(self, pm_with_sample_plugin):
        scorers = discover_scorers(pm_with_sample_plugin)
        scorer = scorers[0]
        stack = StackConfig(language="python", agent="test", framework="fastapi")
        artifacts = RunArtifacts(exit_code=0)
        score = scorer.score(artifacts, stack)
        assert score == 0.42


# ---------------------------------------------------------------------------
# Tests: runner discovery
# ---------------------------------------------------------------------------


class TestDiscoverRunners:
    def test_no_plugins_returns_empty(self, pm_empty):
        runners = discover_runners(pm_empty)
        assert runners == {}

    def test_discovers_runner(self, pm_with_sample_plugin):
        runners = discover_runners(pm_with_sample_plugin)
        assert "fake" in runners
        assert isinstance(runners["fake"], FakeRunner)

    def test_empty_plugin_returns_empty(self):
        pm = _create_plugin_manager()
        pm.register(EmptyPlugin())
        runners = discover_runners(pm)
        assert runners == {}

    def test_runner_protocol_compliance(self, pm_with_sample_plugin):
        runners = discover_runners(pm_with_sample_plugin)
        runner = runners["fake"]
        assert isinstance(runner, PlaypenRunner)

        stack = StackConfig(language="python", agent="test", framework="fastapi")
        task = TaskSpec(name="test", description="test", prompt="test")
        env_id = runner.provision(stack, task)
        assert env_id == "fake-env-1"
        artifacts = runner.execute(env_id, stack, task)
        assert artifacts.exit_code == 0
        runner.teardown(env_id)


# ---------------------------------------------------------------------------
# Tests: RunnerRegistry
# ---------------------------------------------------------------------------


class TestRunnerRegistry:
    def test_register_and_get(self):
        reg = RunnerRegistry()
        runner = FakeRunner()
        reg.register("fake", runner)
        assert reg.get("fake") is runner

    def test_get_unknown_raises(self):
        reg = RunnerRegistry()
        with pytest.raises(KeyError, match="Unknown runner"):
            reg.get("nonexistent")

    def test_available(self):
        reg = RunnerRegistry()
        reg.register("b_runner", FakeRunner())
        reg.register("a_runner", FakeRunner())
        assert reg.available() == ["a_runner", "b_runner"]

    def test_contains(self):
        reg = RunnerRegistry()
        reg.register("fake", FakeRunner())
        assert "fake" in reg
        assert "missing" not in reg

    def test_len(self):
        reg = RunnerRegistry()
        assert len(reg) == 0
        reg.register("fake", FakeRunner())
        assert len(reg) == 1

    def test_default_registry_has_docker(self):
        reg = create_default_runner_registry()
        assert "docker" in reg


# ---------------------------------------------------------------------------
# Tests: ScorerRegistry with plugins integrated
# ---------------------------------------------------------------------------


class TestScorerRegistryWithPlugins:
    def test_default_registry_has_builtins(self):
        reg = create_default_registry()
        assert "code_quality" in reg
        assert "token_efficiency" in reg
        assert "test_coverage" in reg

    def test_default_registry_length_at_least_builtins(self):
        reg = create_default_registry()
        assert len(reg) >= 3


# ---------------------------------------------------------------------------
# Tests: get_plugin_manager (entry-point loading)
# ---------------------------------------------------------------------------


class TestGetPluginManager:
    def test_returns_plugin_manager(self):
        pm = get_plugin_manager()
        assert isinstance(pm, pluggy.PluginManager)

    def test_hookspecs_registered(self):
        pm = get_plugin_manager()
        # Should be able to call hooks without error
        scorers = pm.hook.retort_register_scorers()
        assert isinstance(scorers, list)


# ---------------------------------------------------------------------------
# Tests: CLI plugin commands
# ---------------------------------------------------------------------------


class TestPluginCLI:
    def test_plugin_list_text(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["plugin", "list"])
        assert result.exit_code == 0
        assert "Scorers:" in result.output
        assert "Runners:" in result.output
        assert "Total scorers:" in result.output

    def test_plugin_list_json(self):
        import json as json_mod

        runner = CliRunner()
        result = runner.invoke(cli, ["plugin", "list", "--format", "json"])
        assert result.exit_code == 0
        data = json_mod.loads(result.output)
        assert "scorers" in data
        assert "runners" in data
        assert isinstance(data["scorers"], list)
        assert isinstance(data["runners"], list)

    def test_plugin_show_builtin_scorer(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["plugin", "show", "code_quality"])
        assert result.exit_code == 0
        assert "Scorer: code_quality" in result.output
        assert "Module:" in result.output

    def test_plugin_show_builtin_runner(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["plugin", "show", "docker"])
        assert result.exit_code == 0
        assert "Runner: docker" in result.output
        assert "Module:" in result.output

    def test_plugin_show_unknown(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["plugin", "show", "nonexistent"])
        assert result.exit_code != 0
        assert "No scorer or runner named" in result.output
