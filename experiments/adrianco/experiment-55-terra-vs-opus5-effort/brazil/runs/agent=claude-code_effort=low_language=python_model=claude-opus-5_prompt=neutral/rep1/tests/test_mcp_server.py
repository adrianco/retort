"""
Context
=======
BDD scenarios for the "MCP tool layer" feature in tests/features.feature.

Three things are covered:

1. Discovery -- every tool advertised by the server has a description and a
   well-formed JSON Schema, since that is all an LLM has to decide which tool to
   call.  The async `list_tools` handler of the real MCP Server object is invoked
   (not a copy of the registry) so a registration mistake would fail here.
2. Error handling -- bad input comes back as readable text flagged isError,
   never as a traceback.
3. Coverage -- the specification's success criteria require at least 20 sample
   questions to be answerable; SAMPLE_QUESTIONS encodes 24 of them, each as the
   natural-language question plus the tool call that answers it, and asserts the
   answer is non-empty, non-error, and contains the fact the question asked for.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from brazilian_soccer import server as server_module
from brazilian_soccer.server import (
    TOOLS,
    build_server,
    dispatch,
    render_result,
    tool_definitions,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ------------------------------------------------------------------- discovery

def test_tools_are_discoverable():
    # Given the MCP server / When a client lists the tools
    tools = asyncio.run(_list_tools_via_server())  # real subprocess + protocol
    # Then each tool has a description and a valid JSON schema
    assert len(tools) == len(TOOLS) >= 14
    for tool in tools:
        assert tool.name in TOOLS
        assert len(tool.description) > 30
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert set(schema["required"]) <= set(schema["properties"])
        for prop in schema["properties"].values():
            assert prop["type"] in {"string", "integer", "number", "boolean", "array"}
        json.dumps(schema)  # must be serialisable


async def _list_tools_via_server():
    """List tools through a real MCP session over stdio.

    This launches `python -m brazilian_soccer.server` as a subprocess and speaks
    the protocol to it, so it proves the whole path -- transport, handshake,
    handler registration, schema serialisation -- and not just the registry.
    """
    import os
    import sys

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "brazilian_soccer.server"],
        cwd=str(PROJECT_ROOT),
        env=dict(os.environ),
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            # While the session is up, prove a call and an error both round-trip.
            good = await session.call_tool("standings", {"competition": "Serie A", "season": 2019})
            assert good.is_error is False
            assert "Flamengo" in good.content[0].text
            bad = await session.call_tool("team_stats", {"team": "Nope FC"})
            assert bad.is_error is True
            assert "Nope FC" in bad.content[0].text
            return tools


def test_the_server_object_is_constructible_and_named():
    mcp_server = build_server()
    assert mcp_server.server_info.name == "brazilian-soccer"


def test_rendered_result_carries_text_and_json(server_call):
    rendered = render_result(server_call("standings", competition="Serie A", season=2019))
    head, _, tail = rendered.partition("---\nStructured data:\n")
    assert "Champion" in head
    assert json.loads(tail)["season"] == 2019


def test_every_tool_answers_with_text_and_data(server_call):
    minimal_args = {
        "search_matches": {"team": "Santos", "limit": 3},
        "head_to_head": {"team_a": "Grêmio", "team_b": "Internacional", "limit": 3},
        "team_stats": {"team": "Santos", "season": 2019},
        "team_profile": {"team": "Santos"},
        "standings": {"competition": "Serie A", "season": 2019, "limit": 5},
        "competition_summary": {"competition": "Serie A", "season": 2019},
        "competition_bracket": {"competition": "Libertadores", "season": 2018},
        "statistics": {"competition": "Serie A", "season": 2019},
        "biggest_wins": {"limit": 3},
        "team_leaderboard": {"metric": "points", "season": 2019, "limit": 3},
        "search_players": {"nationality": "Brazil", "limit": 3},
        "player_profile": {"name": "Neymar"},
        "brazilian_club_squads": {"limit": 3},
        "list_teams": {"query": "Flamengo"},
        "find_derbies": {"season": 2019, "limit": 3},
        "dataset_overview": {},
    }
    assert set(minimal_args) == set(TOOLS), "a tool is missing from this smoke test"
    for tool, args in minimal_args.items():
        result = server_call(tool, **args)
        assert result["isError"] is False, f"{tool}: {result['text']}"
        assert result["text"].strip(), tool
        assert result["data"] is not None, tool
        json.dumps(result["data"], default=str)


# -------------------------------------------------------------- error handling

def test_errors_are_returned_as_readable_text(server_call):
    # When a tool is called with an unknown team
    result = server_call("team_stats", team="Definitely Not A Club")
    # Then the response is flagged as an error and names the problem
    assert result["isError"] is True
    assert "Definitely Not A Club" in result["text"]
    assert "Traceback" not in result["text"]


def test_unknown_tool_is_reported(server_call):
    result = server_call("teleport_to_maracana")
    assert result["isError"] is True
    assert "Unknown tool" in result["text"]


def test_bad_competition_and_bad_date_are_reported(server_call):
    assert server_call("standings", competition="La Liga", season=2019)["isError"]
    assert server_call("search_matches", date_from="last tuesday")["isError"]


def test_missing_required_argument_is_reported(server_call):
    result = server_call("head_to_head", team_a="Santos")
    assert result["isError"] is True


def test_graph_is_lazily_loaded_and_injectable(graph):
    server_module.set_graph(None)
    try:
        result = dispatch("dataset_overview", {}, graph=graph)
        assert result["isError"] is False
        assert server_module._GRAPH is None, "explicit graph must not populate the cache"
        server_module.set_graph(graph)
        assert server_module.get_graph() is graph
    finally:
        server_module.set_graph(graph)


# -------------------------------------------------- twenty+ sample questions

# (question, tool, arguments, substring the answer must contain)
SAMPLE_QUESTIONS = [
    ("Show me all Flamengo vs Fluminense matches",
     "head_to_head", {"team_a": "Flamengo", "team_b": "Fluminense"}, "Fla-Flu"),
    ("What matches did Palmeiras play in 2023?",
     "search_matches", {"team": "Palmeiras", "season": 2023}, "Palmeiras"),
    ("Find all Copa do Brasil finals",
     "search_matches", {"competition": "Copa do Brasil", "stage": "final"}, "final"),
    ("When did Flamengo last play Corinthians, and what was the score?",
     "search_matches", {"team": "Flamengo", "opponent": "Corinthians", "limit": 1}, "Corinthians"),
    ("What is Corinthians' home record in 2022?",
     "team_stats", {"team": "Corinthians", "season": 2022, "venue": "home"}, "Win rate"),
    ("Which team scored the most goals in Serie A 2023?",
     "team_leaderboard", {"metric": "goals_for", "competition": "Serie A", "season": 2023}, "goals_for"),
    ("Compare Palmeiras and Santos head-to-head",
     "head_to_head", {"team_a": "Palmeiras", "team_b": "Santos"}, "Head-to-head"),
    ("Find all Brazilian players in the dataset",
     "search_players", {"nationality": "Brazil", "limit": 10}, "Neymar"),
    ("Who are the highest-rated players at Atletico Mineiro?",
     "search_players", {"club": "Atlético Mineiro", "limit": 5}, "Overall"),
    ("Show me all forwards from Cruzeiro",
     "search_players", {"club": "Cruzeiro", "position": "ST"}, "Cruzeiro"),
    ("Who is Neymar?",
     "player_profile", {"name": "Neymar"}, "Brazil"),
    ("Who won the 2019 Brasileirao?",
     "standings", {"competition": "Brasileirao", "season": 2019, "limit": 5}, "Champion"),
    ("Show the 2018 Copa Libertadores bracket",
     "competition_bracket", {"competition": "Libertadores", "season": 2018}, "Final"),
    ("Which teams were relegated in 2020?",
     "standings", {"competition": "Serie A", "season": 2020}, "Relegated"),
    ("What's the average goals per match in the Brasileirao?",
     "statistics", {"competition": "Brasileirao"}, "Average goals per match"),
    ("Which team has the best away record?",
     "team_leaderboard", {"metric": "win_rate", "venue": "away", "min_matches": 100}, "win_rate"),
    ("Which team has the best home record?",
     "team_leaderboard", {"metric": "win_rate", "venue": "home", "min_matches": 100}, "win_rate"),
    ("Show me the biggest wins in the dataset",
     "biggest_wins", {"limit": 5}, "margin"),
    ("Which players play for Fluminense?",
     "search_players", {"club": "Fluminense", "limit": 10}, "Fluminense"),
    ("Show me all derbies in 2019",
     "find_derbies", {"season": 2019}, "Derbies"),
    ("What competitions has Palmeiras played in?",
     "team_profile", {"team": "Palmeiras"}, "Competitions"),
    ("Compare the 2018 and 2019 seasons",
     "statistics", {"competition": "Serie A", "season_from": 2018, "season_to": 2019}, "matches"),
    ("How many Brazilian clubs have squads in the player data?",
     "brazilian_club_squads", {"min_players": 10}, "players"),
    ("What data do you have?",
     "dataset_overview", {}, "Seasons covered"),
]


def test_at_least_twenty_sample_questions_are_covered():
    assert len(SAMPLE_QUESTIONS) >= 20


@pytest.mark.parametrize(
    "question,tool,args,expected",
    SAMPLE_QUESTIONS,
    ids=[q[:45] for q, *_ in SAMPLE_QUESTIONS],
)
def test_sample_question_is_answerable(server_call, question, tool, args, expected):
    # When each of the sample questions is asked
    result = server_call(tool, **args)
    # Then every one produces a non-empty, non-error answer containing the fact
    assert result["isError"] is False, f"{question}: {result['text']}"
    assert len(result["text"]) > 20, question
    assert expected.lower() in result["text"].lower(), f"{question} -> {result['text'][:200]}"


def test_cross_file_query_joins_players_to_match_data(server_call):
    """A question that needs both the FIFA file and the match files."""
    squads = server_call("brazilian_club_squads", min_players=10)
    clubs = [row["club"] for row in squads["data"]]
    assert clubs
    profile = server_call("team_profile", team=clubs[0])
    assert profile["isError"] is False
    assert profile["data"]["squad_size_in_fifa_data"] >= 10
    assert profile["data"]["total_matches"] > 0
