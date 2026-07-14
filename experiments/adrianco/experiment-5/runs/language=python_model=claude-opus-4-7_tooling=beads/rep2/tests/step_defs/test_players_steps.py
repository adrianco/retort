"""Step definitions for ``features/players.feature``."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from soccer_mcp import players as player_mod
from soccer_mcp.data import normalize_team_name

FEATURES = Path(__file__).resolve().parents[1] / "features"
scenarios(str(FEATURES / "players.feature"))


@pytest.fixture
def context() -> dict:
    return {}


@given("the player data is loaded")
def _player_loaded(data):
    assert len(data.fifa) > 0


@when(parsers.parse('I search for players named "{name}"'))
def _search(data, name, context):
    context["players"] = player_mod.search_players_by_name(data, name)
    context["query_name"] = name


@when(parsers.parse("I request the top {n:d} Brazilian players"))
def _top_brazil(data, n, context):
    context["players"] = player_mod.top_players(data, nationality="Brazil", limit=n)
    context["limit"] = n


@when(parsers.parse('I request players at "{club}"'))
def _players_at(data, club, context):
    context["players"] = player_mod.players_by_club(data, club)
    context["club"] = club


@then("at least one player should be returned")
def _non_empty(context):
    assert context["players"], "expected at least one player"


@then(parsers.parse('one of the returned players should be named "{name}"'))
def _has_player(context, name):
    names = {p["name"] for p in context["players"]}
    assert name in names, f"expected {name} in {names}"


@then(parsers.parse("I should receive {n:d} players"))
def _exact_count(context, n):
    assert len(context["players"]) == n


@then("every returned player should be Brazilian")
def _all_brazil(context):
    assert all((p.get("nationality") or "").lower() == "brazil" for p in context["players"])


@then("the players should be sorted by overall rating descending")
def _sorted(context):
    ratings = [p["overall"] for p in context["players"] if p.get("overall") is not None]
    assert ratings == sorted(ratings, reverse=True)


@then("every returned player should be at the requested club")
def _all_requested(context):
    target = normalize_team_name(context["club"])
    for p in context["players"]:
        assert target in normalize_team_name(p["club"] or ""), p
