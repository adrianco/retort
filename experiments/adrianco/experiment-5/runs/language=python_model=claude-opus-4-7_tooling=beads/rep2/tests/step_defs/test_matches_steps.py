"""Step definitions for ``features/matches.feature``."""

from __future__ import annotations

from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

from soccer_mcp import matches as match_mod
from soccer_mcp.data import normalize_team_name

FEATURES = Path(__file__).resolve().parents[1] / "features"
scenarios(str(FEATURES / "matches.feature"))


@given("the match data is loaded")
def _data_loaded(data):
    assert len(data.matches) > 0


@when(parsers.parse('I search for matches between "{a}" and "{b}"'))
def _search_h2h(data, a, b, context):
    context["matches"] = match_mod.find_matches(data, team=a, opponent=b)
    context["team_a"], context["team_b"] = a, b


@when(parsers.parse('I search for matches where "{team}" played in {season:d}'))
def _search_team_season(data, team, season, context):
    context["matches"] = match_mod.find_matches(data, team=team, season=season)
    context["team"] = team
    context["season"] = season


@when(parsers.parse('I compute the head-to-head between "{a}" and "{b}"'))
def _compute_h2h(data, a, b, context):
    context["h2h"] = match_mod.head_to_head(data, a, b)


@when(parsers.parse('I ask for the last match between "{a}" and "{b}"'))
def _last_match(data, a, b, context):
    context["last_match"] = match_mod.last_match_between(data, a, b)
    context["team_a"], context["team_b"] = a, b


@then("I should receive a non-empty list of matches")
def _non_empty(context):
    assert context["matches"], "Expected at least one match"


@then("each match should have a date, scores, and competition")
def _shape(context):
    for m in context["matches"]:
        assert m["date"] is not None
        assert m["home_goal"] is not None and m["away_goal"] is not None
        assert m["competition"]


@then(parsers.parse('every returned match should feature "{team}"'))
def _features_team(context, team):
    norm = normalize_team_name(team)
    for m in context["matches"]:
        assert norm in (normalize_team_name(m["home_team"]), normalize_team_name(m["away_team"]))


@then(parsers.parse("every returned match should be from season {season:d}"))
def _from_season(context, season):
    for m in context["matches"]:
        assert m["season"] == season


@then("wins, losses, and draws should sum to the total matches played")
def _h2h_sum(context):
    h = context["h2h"]
    assert h["team_a_wins"] + h["team_b_wins"] + h["draws"] == h["matches_played"]
    assert h["matches_played"] > 0


@then("I should receive a match featuring both teams")
def _both_teams(context):
    m = context["last_match"]
    assert m is not None
    norms = {normalize_team_name(m["home_team"]), normalize_team_name(m["away_team"])}
    assert normalize_team_name(context["team_a"]) in norms
    assert normalize_team_name(context["team_b"]) in norms


# ---- shared context -----------------------------------------------------------------


import pytest


@pytest.fixture
def context() -> dict:
    return {}
