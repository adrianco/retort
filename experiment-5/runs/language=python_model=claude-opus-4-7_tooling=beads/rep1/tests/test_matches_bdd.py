"""BDD steps for ``tests/features/matches.feature``.

Each scenario exercises :mod:`soccer_mcp.queries` against the real Kaggle
corpus loaded by ``conftest.store``. The Given/When/Then steps are kept tight
so the .feature file remains the authoritative behavioural specification.
"""
from __future__ import annotations

from pytest_bdd import given, when, then, parsers, scenarios

from soccer_mcp import queries as q
from soccer_mcp.normalizer import matches_team

scenarios("features/matches.feature")


# ---- Given -----------------------------------------------------------------
@given("the match data is loaded")
def _data_loaded(store):
    assert store.matches, "expected at least one match row in the store"


# ---- When ------------------------------------------------------------------
@when(parsers.parse('I search for matches between "{a}" and "{b}"'))
def search_h2h(store, a, b, bdd_context):
    bdd_context["matches"] = q.find_matches(store, team=a, opponent=b, limit=None)


@when(parsers.parse('I search for matches in "{competition}" during season {season:d}'))
def search_comp_season(store, competition, season, bdd_context):
    bdd_context["matches"] = q.find_matches(
        store, competition=competition, season=season, limit=None,
    )


@when(parsers.parse('I search for home matches of "{team}" in season {season:d}'))
def search_home(store, team, season, bdd_context):
    bdd_context["matches"] = q.find_matches(
        store, team=team, season=season, home_only=True, limit=None,
    )
    bdd_context["team"] = team


@when(parsers.parse('I request the head-to-head record between "{a}" and "{b}"'))
def request_h2h(store, a, b, bdd_context):
    bdd_context["h2h"] = q.head_to_head(store, a, b, limit=20)


# ---- Then ------------------------------------------------------------------
@then(parsers.parse("I should receive at least {n:d} matches"))
def at_least(bdd_context, n):
    assert len(bdd_context["matches"]) >= n


@then(parsers.parse("I should receive exactly {n:d} matches"))
def exactly(bdd_context, n):
    assert len(bdd_context["matches"]) == n


@then(parsers.parse('every match should involve both "{a}" and "{b}"'))
def both_involved(bdd_context, a, b):
    for m in bdd_context["matches"]:
        sides = (m["home_team"], m["away_team"])
        assert any(matches_team(s, a) for s in sides), m
        assert any(matches_team(s, b) for s in sides), m


@then("every match should have a date, scores, and competition")
def has_required_fields(bdd_context):
    for m in bdd_context["matches"]:
        assert m.get("date"), m
        assert m.get("competition"), m
        assert m.get("home_goal") is not None
        assert m.get("away_goal") is not None


@then(parsers.parse('every match should be from the "{competition}" competition'))
def every_from_comp(bdd_context, competition):
    for m in bdd_context["matches"]:
        assert m["competition"] == competition, m


@then(parsers.parse("every match should be from season {season:d}"))
def every_from_season(bdd_context, season):
    for m in bdd_context["matches"]:
        assert m["season"] == season, m


@then(parsers.parse('every match should have "{team}" as the home team'))
def home_is_team(bdd_context, team):
    for m in bdd_context["matches"]:
        assert matches_team(m["home_team"], team), m


@then("the total wins draws and losses should equal the number of matches played")
def h2h_totals(bdd_context):
    h = bdd_context["h2h"]
    assert h["team_a_wins"] + h["team_b_wins"] + h["draws"] == h["matches_played"]


@then("the recent matches should be ordered from newest to oldest")
def recent_sorted(bdd_context):
    dates = [m["date"] for m in bdd_context["h2h"]["recent_matches"] if m.get("date")]
    assert dates == sorted(dates, reverse=True)
