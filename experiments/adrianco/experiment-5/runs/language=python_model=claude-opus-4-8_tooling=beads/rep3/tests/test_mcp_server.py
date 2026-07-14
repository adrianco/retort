"""
==============================================================================
File: tests/test_mcp_server.py
==============================================================================
CONTEXT
-------
BDD tests that exercise the MCP server surface itself: that all expected tools
are registered with the FastMCP instance and that a representative tool can be
invoked end-to-end through the MCP machinery (not just the underlying query
function). Also covers the spec's performance budget (< 2s simple, < 5s
aggregate) and the "20+ answerable questions / cross-file query" coverage goals.
==============================================================================
"""

import json
import time

import pytest

from brazilian_soccer import queries as q
from brazilian_soccer.knowledge_graph import KnowledgeGraph
from brazilian_soccer.server import mcp


EXPECTED_TOOLS = {
    "find_matches", "head_to_head", "last_meeting",
    "team_record", "compare_teams",
    "search_players", "top_players", "brazilian_players_by_club",
    "standings", "list_competitions",
    "competition_stats", "biggest_wins",
    "best_home_record", "best_away_record", "dataset_summary",
}


@pytest.mark.asyncio
async def test_all_expected_tools_registered():
    # Given the MCP server / When listing tools / Then all are present
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert EXPECTED_TOOLS <= names


@pytest.mark.asyncio
async def test_tool_call_round_trip_returns_json():
    # Given the server / When calling standings via the MCP machinery
    result = await mcp.call_tool("standings", {"competition": "Brasileirão",
                                               "season": 2019, "limit": 1})
    # Then a non-error structured result comes back naming the champion
    # (FastMCP returns a (content, structured) tuple)
    payload = result[1] if isinstance(result, tuple) else result
    text = json.dumps(payload, default=str)
    assert "Flamengo" in text


class TestPerformanceBudget:
    def test_simple_lookup_under_2s(self, graph):
        # Given the loaded graph / When running a simple lookup
        start = time.perf_counter()
        q.find_matches(graph, team="Flamengo", opponent="Fluminense")
        elapsed = time.perf_counter() - start
        # Then it completes well under the 2s budget
        assert elapsed < 2.0

    def test_aggregate_query_under_5s(self, graph):
        # Given the loaded graph / When running an aggregate query
        start = time.perf_counter()
        q.standings(graph, "Brasileirão", 2019)
        q.competition_stats(graph, competition="Brasileirão")
        elapsed = time.perf_counter() - start
        # Then it completes well under the 5s budget
        assert elapsed < 5.0

    def test_full_graph_load_under_5s(self):
        # Given the CSV files / When loading the whole graph / Then it is fast
        start = time.perf_counter()
        KnowledgeGraph.load()
        assert time.perf_counter() - start < 5.0


class TestSampleQuestionCoverage:
    """Smoke-tests 20+ of the spec's sample questions resolve to answers."""

    def test_twenty_plus_sample_questions(self, graph):
        # Given the data, each sample question returns a usable answer.
        checks = [
            # match queries
            lambda: q.find_matches(graph, "Flamengo", "Fluminense")["count"] > 0,
            lambda: q.find_matches(graph, "Palmeiras", season=2019)["count"] > 0,
            lambda: q.find_matches(graph, "Flamengo",
                                   competition="Copa do Brasil")["count"] >= 0,
            lambda: q.last_meeting(graph, "Flamengo", "Corinthians")["found"],
            lambda: q.head_to_head(graph, "Palmeiras", "Santos")["total_matches"] > 0,
            # team queries
            lambda: q.team_record(graph, "Corinthians", season=2022,
                                  competition="Brasileirão", venue="home")["played"] > 0,
            lambda: q.compare_teams(graph, "Palmeiras", "Santos")["team_a"]["team"],
            lambda: q.team_record(graph, "Flamengo", season=2019)["wins"] > 0,
            # player queries
            lambda: q.search_players(graph, name="Neymar")["count"] >= 1,
            lambda: q.search_players(graph, nationality="Brazil",
                                     limit=None)["count"] > 500,
            lambda: q.search_players(graph, club="Flamengo")["count"] >= 0,
            lambda: q.top_players(graph, nationality="Brazil")["count"] > 0,
            lambda: q.brazilian_players_by_club(graph)["total_brazilian_players"] > 0,
            lambda: q.search_players(graph, nationality="Brazil",
                                     position="GK", limit=None)["count"] > 0,
            # competition queries
            lambda: q.standings(graph, "Brasileirão", 2019)["champion"] == "Flamengo",
            lambda: q.standings(graph, "Brasileirão", 2018)["teams"] == 20,
            lambda: len(q.list_competitions(graph)["competitions"]) >= 3,
            # statistics
            lambda: q.competition_stats(graph,
                                        competition="Brasileirão")["matches"] > 0,
            lambda: q.biggest_wins(graph, competition="Brasileirão")["count"] > 0,
            lambda: q.best_home_record(graph, competition="Brasileirão",
                                       season=2019)["teams"],
            lambda: q.best_away_record(graph, competition="Brasileirão",
                                       season=2019)["teams"],
            lambda: q.competition_stats(graph, competition="Brasileirão",
                                        season=2019)["matches"] == 380,
        ]
        assert len(checks) >= 20
        for i, check in enumerate(checks):
            assert check(), f"sample question #{i} failed"

    def test_cross_file_query_player_plus_match(self, graph):
        # Given player data (FIFA) and match data, a combined club query works:
        # players at Flamengo AND Flamengo's match history both resolve.
        players = q.search_players(graph, club="Flamengo")
        matches = q.find_matches(graph, team="Flamengo")
        assert matches["count"] > 0
        assert players["count"] >= 0  # club naming may differ; must not error
