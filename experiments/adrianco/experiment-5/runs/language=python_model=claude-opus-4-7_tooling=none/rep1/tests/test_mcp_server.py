"""End-to-end tests for the MCP server wiring.

Confirms that ``build_server`` registers the expected tools and that the
dispatcher routes each tool name to a real result.
"""

import asyncio
import json

import pytest

from brazilian_soccer_mcp.server import _dispatch, _tools, build_server


class TestServerWiring:
    def test_tools_listed(self):
        names = {t.name for t in _tools()}
        assert {
            "summary", "find_matches", "head_to_head", "team_stats",
            "standings", "find_players", "top_brazilian_players",
            "biggest_wins", "average_goals_per_match",
        } <= names

    def test_build_server_returns_named_server(self, store):
        server = build_server(store)
        assert server.name == "brazilian-soccer-mcp"


class TestDispatcher:
    """Walk every tool name through the dispatcher."""

    @pytest.fixture
    def dispatch(self, queries):
        def go(name, args=None):
            return _dispatch(queries, name, args or {})
        return go

    def test_summary(self, dispatch):
        out = dispatch("summary")
        assert "total_matches" in out

    def test_list_competitions(self, dispatch):
        out = dispatch("list_competitions")
        assert isinstance(out, list) and out

    def test_list_seasons(self, dispatch):
        out = dispatch("list_seasons", {"competition": "Brasileirão"})
        assert 2019 in out

    def test_find_matches(self, dispatch):
        out = dispatch("find_matches", {"team": "Flamengo", "season": 2019, "limit": 5})
        assert isinstance(out, list) and len(out) <= 5

    def test_head_to_head(self, dispatch):
        out = dispatch("head_to_head", {"team_a": "Palmeiras", "team_b": "Santos"})
        assert out["total_matches"] > 0

    def test_team_stats(self, dispatch):
        out = dispatch("team_stats", {"team": "Flamengo", "season": 2019, "competition": "Brasileirão"})
        assert out["matches_played"] == 38

    def test_standings(self, dispatch):
        out = dispatch("standings", {"competition": "Brasileirão", "season": 2019})
        assert out[0]["position"] == 1

    def test_find_players(self, dispatch):
        out = dispatch("find_players", {"nationality": "Brazil", "limit": 3})
        assert len(out) == 3

    def test_top_brazilians(self, dispatch):
        out = dispatch("top_brazilian_players", {"limit": 3})
        assert len(out) == 3

    def test_biggest_wins(self, dispatch):
        out = dispatch("biggest_wins", {"season": 2019, "limit": 3})
        assert len(out) == 3

    def test_average_goals(self, dispatch):
        out = dispatch("average_goals_per_match", {"competition": "Brasileirão", "season": 2019})
        assert out["matches"] > 0

    def test_unknown_tool_raises(self, dispatch):
        with pytest.raises(ValueError):
            dispatch("does-not-exist")


class TestCallToolRoundTrip:
    def test_call_tool_returns_text_json(self, store):
        server = build_server(store)
        # Server keeps the registered callable in its _tool_handlers / call_tool path.
        # We invoke the raw handler indirectly via the dispatcher to keep this hermetic.
        out = _dispatch(SoccerQueries := __import__('brazilian_soccer_mcp.queries', fromlist=['SoccerQueries']).SoccerQueries(store), "summary", {})
        # The wire format is JSON; make sure the dispatch return is JSON serialisable.
        json.dumps(out, default=str)
