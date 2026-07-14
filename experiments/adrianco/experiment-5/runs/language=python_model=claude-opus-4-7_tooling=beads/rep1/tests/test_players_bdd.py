"""BDD steps for ``tests/features/players.feature``."""
from __future__ import annotations

from pytest_bdd import given, when, then, parsers, scenarios

from soccer_mcp import queries as q

scenarios("features/players.feature")


@given("the player data is loaded")
def _players_loaded(store):
    assert store.players, "expected at least one player row in the store"


@when(parsers.parse('I search for players named "{name}"'))
def search_name(store, name, bdd_context):
    bdd_context["players"] = q.find_players(store, name=name, limit=None)
    bdd_context["name"] = name


@when(parsers.parse("I request the top {n:d} Brazilian players"))
def top_brazilian(store, n, bdd_context):
    bdd_context["players"] = q.top_brazilian_players(store, limit=n)
    bdd_context["count"] = n


@when(parsers.parse('I request the players at "{club}"'))
def at_club(store, club, bdd_context):
    bdd_context["roster"] = q.players_by_club(store, club, limit=50)


@when(parsers.parse("I search for players with a minimum overall rating of {threshold:d}"))
def by_min_overall(store, threshold, bdd_context):
    bdd_context["players"] = q.find_players(
        store, min_overall=threshold, limit=None,
    )
    bdd_context["threshold"] = threshold


@then("I should receive at least one player")
def at_least_one(bdd_context):
    assert len(bdd_context["players"]) >= 1


@then(parsers.parse('every player should have "{token}" in their name'))
def name_match(bdd_context, token):
    lower = token.lower()
    for p in bdd_context["players"]:
        assert lower in p["name"].lower(), p


@then(parsers.parse("I should receive {n:d} players"))
def expected_count(bdd_context, n):
    assert len(bdd_context["players"]) == n


@then(parsers.parse('every player should have nationality "{country}"'))
def nationality_match(bdd_context, country):
    for p in bdd_context["players"]:
        assert p["nationality"] == country, p


@then("the players should be sorted by overall rating descending")
def sorted_overall(bdd_context):
    overalls = [p["overall"] or 0 for p in bdd_context["players"]]
    assert overalls == sorted(overalls, reverse=True)


@then("the club roster should not be empty")
def roster_nonempty(bdd_context):
    assert bdd_context["roster"]["player_count"] > 0


@then("the average overall rating should be greater than 0")
def avg_overall(bdd_context):
    assert bdd_context["roster"]["average_overall"] > 0


@then(parsers.parse("every returned player should have an overall rating of at least {n:d}"))
def all_above(bdd_context, n):
    for p in bdd_context["players"]:
        assert (p["overall"] or 0) >= n, p
