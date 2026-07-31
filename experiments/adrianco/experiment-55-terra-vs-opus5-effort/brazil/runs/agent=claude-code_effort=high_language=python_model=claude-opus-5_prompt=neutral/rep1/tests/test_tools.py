"""Tests for the MCP tool catalogue, argument handling and rendering.

Context
-------
The tool layer is what an LLM actually sees, so its schemas have to be
well-formed and its errors have to be recoverable: a bad club name must come
back as an ``isError`` tool result carrying a suggestion, not as an exception
that kills the request.
"""

from __future__ import annotations

import json

import pytest

from brazilian_soccer.formatting import FORMATTERS
from brazilian_soccer.tools import TOOLS, TOOLS_BY_NAME, call_tool, list_tools


def test_every_tool_has_a_well_formed_schema():
    for tool in TOOLS:
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert isinstance(schema["properties"], dict)
        for name, spec in schema["properties"].items():
            assert "type" in spec, f"{tool.name}.{name}"
            assert "description" in spec, f"{tool.name}.{name}"
        for required in schema["required"]:
            assert required in schema["properties"]
        assert len(tool.description) > 60, tool.name


def test_tool_list_is_json_serialisable():
    payload = list_tools()
    assert len(payload) == 16
    assert json.loads(json.dumps(payload))


def test_every_tool_has_a_formatter():
    assert set(TOOLS_BY_NAME) == set(FORMATTERS)


def test_call_tool_returns_text_and_structured_content(graph):
    result = call_tool("standings", {"season": 2019}, graph=graph)
    assert result["isError"] is False
    assert result["content"][0]["type"] == "text"
    assert "Flamengo" in result["content"][0]["text"]
    assert result["structuredContent"]["champion"] == "Flamengo"


def test_unknown_tool_is_reported(graph):
    result = call_tool("no_such_tool", {}, graph=graph)
    assert result["isError"]
    assert "Available tools" in result["content"][0]["text"]


def test_unknown_argument_is_reported(graph):
    result = call_tool("standings", {"season": 2019, "yeer": 2019}, graph=graph)
    assert result["isError"]
    assert "yeer" in result["content"][0]["text"]


def test_missing_required_argument_is_reported(graph):
    result = call_tool("head_to_head", {"team_a": "Flamengo"}, graph=graph)
    assert result["isError"]
    assert "team_b" in result["content"][0]["text"]


def test_unknown_club_returns_a_recoverable_error(graph):
    result = call_tool("team_stats", {"team": "Real Madrid"}, graph=graph)
    assert result["isError"]
    assert "No team matching" in result["content"][0]["text"]


def test_unknown_competition_lists_the_valid_ones(graph):
    result = call_tool("find_matches", {"competition": "premier league"},
                       graph=graph)
    assert result["isError"]
    assert "libertadores" in result["content"][0]["text"]


def test_enum_violations_are_rejected(graph):
    result = call_tool("find_matches", {"team": "Santos", "venue": "somewhere"},
                       graph=graph)
    assert result["isError"]
    assert "home" in result["content"][0]["text"]


def test_string_numbers_are_coerced(graph):
    """LLM clients frequently send "2019" instead of 2019."""
    coerced = call_tool("standings", {"season": "2019"}, graph=graph)
    native = call_tool("standings", {"season": 2019}, graph=graph)
    assert not coerced["isError"]
    assert coerced["structuredContent"]["champion"] == \
        native["structuredContent"]["champion"]


def test_non_numeric_season_is_rejected_clearly(graph):
    result = call_tool("standings", {"season": "last year"}, graph=graph)
    assert result["isError"]
    assert "whole number" in result["content"][0]["text"]


def test_inverted_season_range_is_rejected(graph):
    result = call_tool("team_stats",
                       {"team": "Flamengo", "season_from": 2020, "season_to": 2019},
                       graph=graph)
    assert result["isError"]
    assert "after season_to" in result["content"][0]["text"]


def test_an_unknown_position_lists_the_valid_codes(graph):
    result = call_tool("search_players", {"position": "XYZ"}, graph=graph)
    assert not result["isError"]
    text = result["content"][0]["text"]
    assert "no players found" in text
    assert "GK, DEF, MID, FWD" in text and "CDM" in text


@pytest.mark.parametrize("arguments,fragment", [
    ({"team": ["Flamengo"]}, "must be text"),
    ({"team": {"name": "Flamengo"}}, "must be text"),
    ({"team": True}, "must be text"),
    ({"team": "Santos", "season": True}, "whole number"),
    ({"team": "Santos", "season": [2019]}, "whole number"),
])
def test_wrong_argument_types_get_a_usable_message(graph, arguments, fragment):
    """Never surface a raw AttributeError from deep in the query layer."""
    result = call_tool("team_stats", arguments, graph=graph)
    assert result["isError"]
    text = result["content"][0]["text"]
    assert fragment in text
    assert "failed unexpectedly" not in text


def test_numbers_in_string_fields_are_coerced_then_reported(graph):
    result = call_tool("team_stats", {"team": 2019}, graph=graph)
    assert result["isError"]
    assert "No team matching '2019'" in result["content"][0]["text"]


def test_array_arguments_accept_a_scalar(graph):
    result = call_tool("compare_seasons", {"seasons": 2019}, graph=graph)
    assert not result["isError"]
    assert result["structuredContent"]["seasons"] == [2019]


@pytest.mark.parametrize("name", sorted(TOOLS_BY_NAME))
def test_every_tool_runs_with_sensible_arguments(graph, name):
    """Smoke-test the whole catalogue with valid minimal arguments."""
    arguments = {
        "find_matches": {"team": "Santos", "limit": 3},
        "head_to_head": {"team_a": "Santos", "team_b": "Palmeiras", "limit": 3},
        "team_stats": {"team": "Santos"},
        "team_profile": {"team": "Santos"},
        "standings": {"season": 2019},
        "team_rankings": {"competition": "serie-a", "season": 2019, "limit": 3},
        "competition_stats": {"competition": "serie-a", "season": 2019},
        "biggest_wins": {"limit": 3},
        "compare_seasons": {"seasons": [2018, 2019]},
        "find_derbies": {"season": 2019, "limit": 3},
        "search_players": {"nationality": "Brazil", "limit": 3},
        "player_profile": {"name": "Neymar"},
        "club_squad": {"club": "Santos", "limit": 3},
        "brazilian_players_by_club": {"limit": 3},
        "resolve_team": {"name": "Atletico-MG"},
        "dataset_summary": {},
    }[name]
    result = call_tool(name, arguments, graph=graph)
    assert not result["isError"], result["content"][0]["text"]
    assert result["content"][0]["text"].strip()
    assert json.loads(json.dumps(result["structuredContent"], default=str))
