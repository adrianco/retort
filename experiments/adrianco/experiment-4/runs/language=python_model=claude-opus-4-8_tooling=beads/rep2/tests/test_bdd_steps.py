"""
================================================================================
Brazilian Soccer MCP Server :: tests/test_bdd_steps
================================================================================

Context
-------
Given-When-Then step definitions binding the Gherkin feature files under
tests/features/ to the QueryEngine. Uses pytest-bdd. A per-scenario `context`
dict carries state between steps (the engine itself is a session fixture).

These BDD scenarios exercise the spec's functional requirements end to end:
match search + name normalisation, team statistics, computed standings/champion,
head-to-head, and player search/filter/sort.
================================================================================
"""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

# Bind all feature files in the features directory.
scenarios("features/match_queries.feature")
scenarios("features/team_and_competition.feature")
scenarios("features/player_queries.feature")


@pytest.fixture
def context():
    return {}


# --------------------------------------------------------------------------- #
# Given
# --------------------------------------------------------------------------- #
@given("the knowledge graph is loaded")
def _loaded(engine, context):
    context["engine"] = engine
    assert len(engine.graph.matches) > 0


# --------------------------------------------------------------------------- #
# When — match queries
# --------------------------------------------------------------------------- #
@when(parsers.parse('I search for matches between "{team_a}" and "{team_b}"'))
def _matches_between(context, team_a, team_b):
    context["result"] = context["engine"].find_matches(team=team_a, opponent=team_b)


@when(parsers.parse('I search for matches for "{team}" in season {season:d}'))
def _matches_for_team_season(context, team, season):
    context["team"] = team
    context["season"] = season
    context["result"] = context["engine"].find_matches(team=team, season=season)


# --------------------------------------------------------------------------- #
# When — team / competition queries
# --------------------------------------------------------------------------- #
@when(parsers.parse('I request statistics for "{team}" in season {season:d}'))
def _team_stats(context, team, season):
    context["result"] = context["engine"].team_record(team, season=season)


@when(parsers.parse('I request the "{competition}" standings for season {season:d}'))
def _standings(context, competition, season):
    context["result"] = context["engine"].standings(competition, season)


@when(parsers.parse('I request the head-to-head between "{team_a}" and "{team_b}"'))
def _h2h(context, team_a, team_b):
    context["team_a"] = team_a
    context["team_b"] = team_b
    context["result"] = context["engine"].head_to_head(team_a, team_b)


# --------------------------------------------------------------------------- #
# When — player queries
# --------------------------------------------------------------------------- #
@when(parsers.parse('I search for players named "{name}"'))
def _players_named(context, name):
    context["result"] = context["engine"].search_players(name=name)


@when(parsers.parse('I search for players with nationality "{nat}"'))
def _players_nat(context, nat):
    context["result"] = context["engine"].search_players(nationality=nat, limit=1000)


@when(parsers.parse('I search for players with nationality "{nat}" and position "{pos}"'))
def _players_nat_pos(context, nat, pos):
    context["result"] = context["engine"].search_players(
        nationality=nat, position=pos, limit=1000
    )


# --------------------------------------------------------------------------- #
# Then — match queries
# --------------------------------------------------------------------------- #
@then("I should receive a list of matches")
def _have_matches(context):
    assert context["result"]["count"] > 0
    assert len(context["result"]["matches"]) > 0


@then("each match should have a date, scores and a competition")
def _match_shape(context):
    for m in context["result"]["matches"]:
        assert "date" in m and "competition" in m
        assert "home_goal" in m and "away_goal" in m


@then("the head-to-head summary should include wins and draws")
def _h2h_summary(context):
    summary = context["result"]["head_to_head"]
    assert "draws" in summary
    assert any(k.endswith("_wins") for k in summary)


@then(parsers.parse('every match should involve "{team}"'))
def _involves(context, team):
    key = context["engine"].graph.resolve_team(team)
    for m in context["result"]["matches"]:
        hk = context["engine"].graph.resolve_team(m["home_team"])
        ak = context["engine"].graph.resolve_team(m["away_team"])
        assert key in (hk, ak)


@then(parsers.parse("every match should be in season {season:d}"))
def _in_season(context, season):
    for m in context["result"]["matches"]:
        assert m["season"] == season


@then(parsers.parse('I should receive the same number of matches as for "{team}" in season {season:d}'))
def _same_count(context, team, season):
    other = context["engine"].find_matches(team=team, season=season)
    assert context["result"]["count"] == other["count"]


# --------------------------------------------------------------------------- #
# Then — team / competition queries
# --------------------------------------------------------------------------- #
@then("I should receive wins, losses, draws and goals")
def _record_fields(context):
    r = context["result"]
    for f in ("wins", "losses", "draws", "goals_for", "goals_against"):
        assert f in r


@then("the number of matches should equal wins plus draws plus losses")
def _record_consistency(context):
    r = context["result"]
    assert r["played"] == r["wins"] + r["draws"] + r["losses"]


@then("the standings should be ordered by points descending")
def _standings_ordered(context):
    pts = [row["points"] for row in context["result"]["standings"]]
    assert pts == sorted(pts, reverse=True)


@then(parsers.parse('the champion should be "{team}"'))
def _champion_is(context, team):
    assert context["result"]["standings"][0]["team"] == team


@then("the total of wins and draws should equal the number of matches played")
def _h2h_consistency(context):
    s = context["result"]["summary"]
    wins = sum(v for k, v in s.items() if k.endswith("_wins"))
    assert wins + s["draws"] == s["matches"]


# --------------------------------------------------------------------------- #
# Then — player queries
# --------------------------------------------------------------------------- #
@then("I should receive at least one player")
def _at_least_one(context):
    assert context["result"]["count"] >= 1


@then(parsers.parse('every returned player\'s name should contain "{name}"'))
def _name_contains(context, name):
    for p in context["result"]["players"]:
        assert name.lower() in p["name"].lower()


@then(parsers.parse("I should receive more than {n:d} players"))
def _more_than(context, n):
    assert context["result"]["count"] > n


@then("the players should be ordered by overall rating descending")
def _players_ordered(context):
    ratings = [p["overall"] or 0 for p in context["result"]["players"]]
    assert ratings == sorted(ratings, reverse=True)


@then(parsers.parse('every returned player should play position "{pos}"'))
def _position_is(context, pos):
    assert context["result"]["players"]  # non-empty
    for p in context["result"]["players"]:
        assert p["position"] == pos
