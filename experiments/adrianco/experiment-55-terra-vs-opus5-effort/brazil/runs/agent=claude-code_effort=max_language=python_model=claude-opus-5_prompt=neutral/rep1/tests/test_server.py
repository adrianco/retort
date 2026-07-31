"""The MCP tool surface.

Context
-------
Feature: MCP server

  Scenario: An LLM client discovers and calls the tools
    Given the server is running
    When the client lists tools
    Then every capability in the specification is exposed with a schema
    And calling a tool returns readable text rather than raw records

These tests drive the real server object through `call_tool`, so the whole path
-- schema validation, query, formatting -- is exercised.
"""

from __future__ import annotations

import json

import anyio
import pytest

from brazilian_soccer.server import build_server

EXPECTED_TOOLS = {
    "dataset_overview",
    "search_teams",
    "find_matches",
    "head_to_head",
    "biggest_wins",
    "derbies",
    "team_stats",
    "team_profile",
    "team_rankings",
    "search_players",
    "player_profile",
    "team_squad",
    "standings",
    "knockout_bracket",
    "competition_stats",
    "compare_seasons",
    "graph_neighbours",
}


@pytest.fixture(scope="module")
def tools(server):
    async def _list():
        return await server.list_tools()

    return {tool.name: tool for tool in anyio.run(_list)}


class TestToolSurface:
    """Scenario: Discovering the tools."""

    def test_given_the_server_when_tools_are_listed_then_all_capabilities_are_exposed(
        self, tools
    ):
        """
        Given the server is running
        When the client lists tools
        Then every capability from the specification is present
        """
        assert set(tools) == EXPECTED_TOOLS

    def test_given_each_tool_when_inspected_then_it_documents_itself(self, tools):
        """
        Given a client that has never seen this server
        When it inspects the tools
        Then each has a description and a JSON schema for its arguments
        """
        for name, tool in tools.items():
            assert tool.description, f"{name} has no description"
            assert tool.input_schema["type"] == "object"

    def test_given_required_arguments_when_declared_then_they_are_marked(self, tools):
        """
        Given tools that cannot work without an argument
        When their schema is read
        Then those arguments are required and optional ones are not
        """
        assert tools["standings"].input_schema["required"] == ["competition", "season"]
        assert set(tools["head_to_head"].input_schema["required"]) == {"team_a", "team_b"}
        assert "required" not in tools["dataset_overview"].input_schema or not tools[
            "dataset_overview"
        ].input_schema["required"]


class TestToolCalls:
    """Scenario: Calling the tools."""

    def test_given_a_standings_request_when_called_then_a_readable_table_returns(
        self, call_tool
    ):
        """
        Given the question "who won the 2019 Brasileirão?"
        When the standings tool is called
        Then a formatted table naming the champion comes back
        """
        text = call_tool("standings", competition="Brasileirão", season=2019)

        assert "1. Flamengo" in text
        assert "90 pts" in text
        assert "Champion" in text
        assert "Relegated" in text

    def test_given_a_match_search_when_called_then_matches_are_listed(self, call_tool):
        """
        Given the question "show me all Flamengo vs Fluminense matches"
        When find_matches is called
        Then a dated list and a head-to-head summary come back
        """
        text = call_tool("find_matches", team="Flamengo", opponent="Fluminense", limit=5)

        assert "Fla-Flu" in text
        assert "Head-to-head in dataset" in text
        assert text.count("\n- ") >= 5

    def test_given_a_player_search_when_called_then_players_are_listed(self, call_tool):
        """
        Given the question "find all Brazilian players"
        When search_players is called
        Then rated players are listed with clubs and positions
        """
        text = call_tool("search_players", nationality="Brazil", limit=3)

        assert "Neymar Jr" in text
        assert "Overall:" in text and "Club:" in text

    def test_given_a_graph_walk_when_called_then_json_is_returned(self, call_tool):
        """
        Given a client that wants to explore the graph itself
        When graph_neighbours is called
        Then valid JSON describing the node and its relations is returned
        """
        payload = json.loads(call_tool("graph_neighbours", node_id="team:flamengo"))

        assert payload["node"]["kind"] == "team"
        assert payload["counts"]["played_home"] > 300
        assert payload["relations"]["competed_in"]

    def test_given_an_unknown_node_when_walked_then_an_error_object_returns(self, call_tool):
        """
        Given a node id that does not exist
        When graph_neighbours is called
        Then a JSON error is returned instead of an exception
        """
        payload = json.loads(call_tool("graph_neighbours", node_id="team:nope"))

        assert "error" in payload

    def test_given_a_bad_club_name_when_called_then_the_tool_explains_itself(self, call_tool):
        """
        Given a club that is not in the data
        When a tool is called with it
        Then the text answer explains the problem and suggests alternatives
        """
        text = call_tool("team_stats", team="Manchester United")

        assert "No team" in text or "Did you mean" in text

    def test_given_every_tool_when_called_with_defaults_then_none_raise(self, call_tool):
        """
        Given all the tools the server exposes
        When each is called with a reasonable set of arguments
        Then every one returns non-empty text
        """
        calls = {
            "dataset_overview": {},
            "search_teams": {"query": "Sport"},
            "find_matches": {"team": "Santos", "limit": 3},
            "head_to_head": {"team_a": "Gremio", "team_b": "Internacional"},
            "biggest_wins": {"limit": 3},
            "derbies": {"season": 2022, "limit": 5},
            "team_stats": {"team": "Bahia", "season": 2019},
            "team_profile": {"team": "Vitória"},
            "team_rankings": {"metric": "points", "season": 2019, "limit": 3},
            "search_players": {"nationality": "Brazil", "limit": 3},
            "player_profile": {"name": "Alisson"},
            "team_squad": {"team": "Chapecoense"},
            "standings": {"competition": "Serie A", "season": 2018},
            "knockout_bracket": {"competition": "Libertadores", "season": 2019},
            "competition_stats": {"competition": "Copa do Brasil"},
            "compare_seasons": {"competition": "Serie A", "seasons": [2018, 2019]},
            "graph_neighbours": {"node_id": "competition:serie-a"},
        }

        assert set(calls) == EXPECTED_TOOLS
        for name, arguments in calls.items():
            text = call_tool(name, **arguments)
            assert text.strip(), f"{name} returned nothing"


class TestServerConstruction:
    """Scenario: Building the server."""

    def test_given_a_prebuilt_graph_when_building_then_no_reload_happens(self, graph):
        """
        Given a knowledge graph that is already in memory
        When the server is built with it
        Then the same graph object is reused instead of re-reading the CSVs
        """
        instance = build_server(graph=graph)

        async def _call():
            return await instance.call_tool("dataset_overview", {})

        text = anyio.run(_call).content[0].text
        assert "Brazilian soccer knowledge graph" in text

    def test_given_the_server_when_created_then_it_advertises_its_scope(self):
        """
        Given a fresh server
        When its instructions are read
        Then they describe the data and its limitations for the model
        """
        instance = build_server()

        assert "Brasileirão" in instance.instructions
        assert "goalscorers" in instance.instructions

    def test_given_the_entry_point_when_run_then_stdio_is_the_default_transport(
        self, monkeypatch
    ):
        """
        Given `python -m brazilian_soccer.server`
        When the entry point runs
        Then it serves the default MCP transport without touching the data first
        """
        from brazilian_soccer import server as server_module

        started: list[str] = []
        monkeypatch.setattr(
            server_module.server, "run", lambda transport: started.append(transport)
        )

        server_module.main([])

        assert started == ["stdio"]

    def test_given_a_data_directory_argument_when_run_then_it_is_honoured(
        self, monkeypatch, data_dir
    ):
        """
        Given --data-dir pointing at the CSVs
        When the entry point runs
        Then a server bound to that directory is served
        """
        from brazilian_soccer import server as server_module

        started: list[str] = []

        def _fake_build(graph=None, data_dir=None, name=server_module.SERVER_NAME):
            assert str(data_dir).endswith("kaggle")

            class _Stub:
                def run(self, transport):
                    started.append(transport)

            return _Stub()

        monkeypatch.setattr(server_module, "build_server", _fake_build)
        server_module.main(["--data-dir", str(data_dir), "--transport", "sse"])

        assert started == ["sse"]
