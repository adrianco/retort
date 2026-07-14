"""BDD steps for ``tests/features/competitions.feature``."""
from __future__ import annotations

from pytest_bdd import given, when, then, parsers, scenarios

from soccer_mcp import queries as q
from soccer_mcp.normalizer import matches_team

scenarios("features/competitions.feature")


@given("the match data is loaded")
def _data_loaded(store):
    assert store.matches


@when(parsers.parse('I request the "{comp}" standings for season {season:d}'))
def standings(store, comp, season, bdd_context):
    bdd_context["standings"] = q.competition_standings(store, season, competition=comp)


@when(parsers.parse('I request the "{comp}" summary for season {season:d}'))
def summary(store, comp, season, bdd_context):
    bdd_context["summary"] = q.competition_summary(store, season, competition=comp)


@then(parsers.parse('position {pos:d} should be "{team}"'))
def position_team(bdd_context, pos, team):
    row = bdd_context["standings"][pos - 1]
    assert matches_team(row["team"], team), row


@then(parsers.parse("the champion should have at least {n:d} points"))
def champion_points(bdd_context, n):
    assert bdd_context["standings"][0]["points"] >= n


@then("the summary should name a champion")
def has_champion(bdd_context):
    assert bdd_context["summary"]["champion"]


@then("the summary should include a top 3")
def has_top3(bdd_context):
    assert len(bdd_context["summary"]["top_3"]) == 3


@then(parsers.parse("the summary should report at least {n:d} matches played"))
def matches_played_summary(bdd_context, n):
    assert bdd_context["summary"]["matches_played"] >= n
