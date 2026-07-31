"""
Unit tests for the transport-independent tool layer.

Context
-------
The MCP server, the CLI and the BDD scenarios all go through
:func:`brazilian_soccer.tools.call_tool`, so this is where the contract that
every tool honours is enforced: a non-empty rendered answer, a
JSON-serialisable payload, and graceful (never exceptional) handling of the
bad arguments a language model will inevitably produce.
"""

from __future__ import annotations

import json

import pytest

from brazilian_soccer.tools import TOOLS, call_tool, list_tools, tool_names

#: Minimal arguments that make each tool return a real answer.
MINIMAL_ARGUMENTS: dict[str, dict] = {
    "search_matches": {"team": "Flamengo", "limit": 3},
    "head_to_head": {"team_a": "Flamengo", "team_b": "Fluminense", "limit": 3},
    "find_derbies": {"season": 2019, "limit": 2},
    "team_stats": {"team": "Palmeiras", "season": 2022},
    "team_profile": {"team": "Santos"},
    "compare_teams": {"team_a": "Palmeiras", "team_b": "Santos"},
    "best_records": {"competition": "brasileirao", "season": 2019, "limit": 3},
    "top_scoring_teams": {"competition": "brasileirao", "season": 2019, "limit": 3},
    "competition_standings": {"competition": "brasileirao", "season": 2019},
    "competition_champion": {"competition": "brasileirao", "season": 2019},
    "relegated_teams": {"competition": "brasileirao", "season": 2019},
    "competition_stats": {"competition": "brasileirao", "season": 2019},
    "biggest_wins": {"competition": "brasileirao", "limit": 3},
    "compare_seasons": {"seasons": [2018, 2019]},
    "search_players": {"nationality": "Brazil", "limit": 3},
    "player_profile": {"name": "Neymar"},
    "club_squad": {"club": "Cruzeiro", "limit": 3},
    "brazilian_club_squads": {"limit": 3},
    "resolve_team": {"query": "Botafogo"},
    "list_teams": {"limit": 5},
    "list_competitions": {},
    "dataset_summary": {},
    "graph_neighbors": {"node_id": "team:flamengo-rj", "limit": 5},
    "position_groups": {},
}


def test_every_tool_has_minimal_arguments_defined():
    assert set(MINIMAL_ARGUMENTS) == set(tool_names())


@pytest.mark.parametrize("name", sorted(MINIMAL_ARGUMENTS))
def test_every_tool_returns_text_and_serialisable_data(graph, name):
    result = call_tool(name, MINIMAL_ARGUMENTS[name], graph=graph)
    assert result.text.strip(), f"{name} returned an empty answer"
    assert "error" not in result.data, result.text
    encoded = json.dumps(result.data, default=str)
    assert json.loads(encoded) is not None


@pytest.mark.parametrize("name", sorted(MINIMAL_ARGUMENTS))
def test_every_tool_is_documented(name):
    spec = TOOLS[name]
    assert spec.description and len(spec.description) > 30
    assert isinstance(spec.parameters, dict)


def test_tool_catalogue_is_sorted_and_complete():
    catalogue = list_tools()
    assert [entry["name"] for entry in catalogue] == sorted(TOOLS)
    assert len(catalogue) >= 20


def test_unknown_tool_raises(graph):
    with pytest.raises(KeyError) as error:
        call_tool("no_such_tool", {}, graph=graph)
    assert "available" in str(error.value)


def test_unknown_club_answers_with_suggestions(graph):
    result = call_tool("team_stats", {"team": "Manchester United"}, graph=graph)
    assert result.data.get("error") == "TeamNotFound" or result.data.get("played") == 0


def test_unknown_competition_answers_helpfully(graph):
    result = call_tool("competition_standings",
                       {"competition": "Premier League", "season": 2019}, graph=graph)
    assert result.data["error"] == "CompetitionNotFound"
    assert "Copa Libertadores" in result.text


def test_unexpected_argument_is_reported_not_raised(graph):
    result = call_tool("team_stats", {"team": "Santos", "nonsense": 1}, graph=graph)
    assert result.data["error"] == "InvalidArguments"
    assert "Expected" in result.text


def test_missing_required_argument_is_reported(graph):
    result = call_tool("head_to_head", {"team_a": "Santos"}, graph=graph)
    assert result.data["error"] == "InvalidArguments"


def test_none_valued_arguments_are_dropped(graph):
    with_none = call_tool("team_stats", {"team": "Santos", "season": None}, graph=graph)
    without = call_tool("team_stats", {"team": "Santos"}, graph=graph)
    assert with_none.text == without.text


def test_season_accepts_a_string(graph):
    as_int = call_tool("competition_standings",
                       {"competition": "brasileirao", "season": 2019}, graph=graph)
    as_str = call_tool("competition_standings",
                       {"competition": "brasileirao", "season": "2019"}, graph=graph)
    assert as_int.data["standings"][0] == as_str.data["standings"][0]


def test_standings_without_a_season_explains_itself(graph):
    result = call_tool("competition_standings",
                       {"competition": "brasileirao", "season": "not a year"}, graph=graph)
    assert result.data["error"] == "ValueError"
    assert "season" in result.text


def test_search_matches_reports_the_full_count_and_the_shown_subset(graph):
    result = call_tool("search_matches",
                       {"team": "Flamengo", "competition": "brasileirao", "limit": 5},
                       graph=graph)
    assert result.data["returned"] == 5
    assert result.data["count"] > 5
    assert "more match" in result.text


def test_answers_use_the_formats_from_the_specification(graph):
    matches = call_tool("head_to_head",
                        {"team_a": "Flamengo", "team_b": "Fluminense", "limit": 3},
                        graph=graph).text
    assert "Fla-Flu derby" in matches
    assert "Head-to-head in dataset" in matches

    record = call_tool("team_stats",
                       {"team": "Corinthians", "competition": "brasileirao",
                        "season": 2022, "scope": "home"}, graph=graph).text
    for label in ("Matches:", "Wins:", "Goals For:", "Win rate:"):
        assert label in record

    table = call_tool("competition_standings",
                      {"competition": "brasileirao", "season": 2019}, graph=graph).text
    assert "1. Flamengo (RJ) - 90 pts (28W, 6D, 4L)" in table
    assert "Champion" in table

    players = call_tool("search_players", {"nationality": "Brazil", "limit": 3},
                        graph=graph).text
    assert "1. Neymar Jr - Overall: 92 - Position: LW" in players


def test_graph_neighbors_reports_unknown_nodes(graph):
    result = call_tool("graph_neighbors", {"node_id": "team:nope"}, graph=graph)
    assert result.data["error"] == "unknown_node"
