"""Step definitions for ``features/stats.feature``."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

from soccer_mcp import matches as match_mod
from soccer_mcp import stats as stats_mod

FEATURES = Path(__file__).resolve().parents[1] / "features"
scenarios(str(FEATURES / "stats.feature"))


@pytest.fixture
def context() -> dict:
    return {}


@given("the match data is loaded")
def _data_loaded(data):
    assert len(data.matches) > 0


@when("I compute the average goals per match in the Brasileirão")
def _avg(data, context):
    context["avg"] = stats_mod.goals_per_match(data, competition="Brasileirão")


@when("I compute the home advantage in the Brasileirão")
def _home_adv(data, context):
    context["home_adv"] = stats_mod.home_advantage(data, competition="Brasileirão")


@when("I list the 10 biggest wins")
def _biggest(data, context):
    context["biggest"] = match_mod.biggest_wins(data, limit=10)


@then("the average should be between 1.5 and 4.0")
def _avg_range(context):
    assert 1.5 < context["avg"]["average_goals"] < 4.0


@then("the home win rate should exceed the away win rate")
def _home_beats_away(context):
    h = context["home_adv"]
    assert h["home_win_rate"] > h["away_win_rate"]


@then("the list should have at most 10 entries")
def _at_most_10(context):
    assert 0 < len(context["biggest"]) <= 10


@then("every entry should have a positive goal margin")
def _positive_margin(context):
    for m in context["biggest"]:
        assert m["margin"] > 0
