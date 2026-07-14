"""Step definitions for ``features/teams.feature``."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from soccer_mcp import teams as team_mod
from soccer_mcp.data import normalize_team_name

FEATURES = Path(__file__).resolve().parents[1] / "features"
scenarios(str(FEATURES / "teams.feature"))


@pytest.fixture
def context() -> dict:
    return {}


@given("the match data is loaded")
def _data_loaded(data):
    assert len(data.matches) > 0


@when(parsers.parse('I request statistics for "{team}" in season {season:d}'))
def _team_record(data, team, season, context):
    context["record"] = team_mod.team_record(data, team, season=season)


@when(parsers.parse('I request "{team}" home record in {season:d} Brasileirão'))
def _home_record(data, team, season, context):
    context["record"] = team_mod.team_record(data, team, season=season, competition="Brasileirão", side="home")
    context["team"] = team


@when(parsers.parse('I compare "{a}" and "{b}" in season {season:d}'))
def _compare(data, a, b, season, context):
    context["comparison"] = team_mod.compare_teams(data, a, b, season=season)
    context["season"] = season


@then("I should receive a positive number of matches")
def _positive(context):
    assert context["record"]["matches"] > 0


@then("wins + draws + losses should equal matches played")
def _sum_equals(context):
    r = context["record"]
    assert r["wins"] + r["draws"] + r["losses"] == r["matches"]


@then("every counted match should be a home match")
def _home_match(context):
    assert context["record"]["side"] == "home"
    assert context["record"]["matches"] > 0


@then("the points should equal wins*3 + draws")
def _points_formula(context):
    r = context["record"]
    assert r["points"] == r["wins"] * 3 + r["draws"]


@then("both team records should reference season 2022")
def _both_seasons(context):
    c = context["comparison"]
    assert c["team_a_record"]["season"] == 2022
    assert c["team_b_record"]["season"] == 2022
