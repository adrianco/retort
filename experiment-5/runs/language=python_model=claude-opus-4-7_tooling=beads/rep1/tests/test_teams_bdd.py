"""BDD steps for ``tests/features/teams.feature``."""
from __future__ import annotations

from pytest_bdd import given, when, then, parsers, scenarios

from soccer_mcp import queries as q
from soccer_mcp.normalizer import matches_team

scenarios("features/teams.feature")


@given("the match data is loaded")
def _data_loaded(store):
    assert store.matches


@when(parsers.parse('I request the record for "{team}" in the "{comp}" season {season:d}'))
def record(store, team, comp, season, bdd_context):
    bdd_context["record"] = q.team_record(
        store, team, season=season, competition=comp,
    )
    bdd_context["team"] = team


@when(parsers.parse('I request the home record for "{team}" in the "{comp}" season {season:d}'))
def home_record(store, team, comp, season, bdd_context):
    bdd_context["record"] = q.team_record(
        store, team, season=season, competition=comp, venue="home",
    )
    bdd_context["team"] = team
    bdd_context["competition"] = comp
    bdd_context["season"] = season


@when(parsers.parse('I compare "{a}" and "{b}" in the "{comp}" season {season:d}'))
def compare(store, a, b, comp, season, bdd_context):
    bdd_context["compare"] = q.compare_teams(
        store, a, b, season=season, competition=comp,
    )


@then(parsers.parse("the team should have {n:d} matches played"))
def matches_played(bdd_context, n):
    assert bdd_context["record"]["matches"] == n


@then(parsers.parse("the team should have {n:d} points"))
def points(bdd_context, n):
    assert bdd_context["record"]["points"] == n


@then("wins draws and losses should sum to matches played")
def sums(bdd_context):
    r = bdd_context["record"]
    assert r["wins"] + r["draws"] + r["losses"] == r["matches"]


@then("every counted match should be a home match")
def venue_home(bdd_context, store):
    # Re-run the underlying search to inspect the matches that contributed.
    team = bdd_context["team"]
    raw = q.find_matches(
        store, team=team,
        season=bdd_context["season"],
        competition=bdd_context["competition"],
        home_only=True, limit=None,
    )
    assert raw, "expected at least one home match for the venue scenario"
    for m in raw:
        assert matches_team(m["home_team"], team)


@then("points should equal wins times three plus draws")
def points_formula(bdd_context):
    r = bdd_context["record"]
    assert r["points"] == r["wins"] * 3 + r["draws"]


@then("both teams should have a non-zero number of matches")
def both_nonzero(bdd_context):
    c = bdd_context["compare"]
    assert c["team_a"]["matches"] > 0
    assert c["team_b"]["matches"] > 0


@then("the comparison should include a head-to-head record")
def has_h2h(bdd_context):
    h = bdd_context["compare"]["head_to_head"]
    assert "matches_played" in h
    assert "team_a_wins" in h
