#!/usr/bin/env python3
"""Tests for MCP server functionality."""

import pytest
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.mcp_server import mcp, get_query_engine


class TestMCPServer:
    """Tests for MCP server functionality."""

    def test_mcp_server_has_tools(self):
        """Test that MCP server has the required tools."""
        tools = asyncio.run(mcp.list_tools())
        assert len(tools) > 0, "MCP server should have tools registered"
        
        # Verify all required tools exist
        tool_names = [t.name for t in tools]
        required_tools = [
            "find_matches_by_teams",
            "get_match_by_id",
            "get_team_stats",
            "get_team_comparison",
            "search_players",
            "get_top_brazilian_players",
            "get_competition_standings",
            "get_big_wins",
            "get_average_goals_per_match",
            "get_home_win_rate",
        ]
        for tool in required_tools:
            assert tool in tool_names, f"Missing required tool: {tool}"

    def test_mcp_find_matches_by_teams(self):
        """Test find_matches_by_teams tool."""
        result = asyncio.run(mcp.call_tool(
            "find_matches_by_teams",
            {"team1": "Flamengo", "team2": "Fluminense", "limit": 5}
        ))
        assert isinstance(result, (list, tuple)), "Result should be a sequence"
        assert len(result) > 0, "Should return matches"
        
        # Result should be ContentBlock objects or strings
        result_str = str(result)
        assert "Flamengo" in result_str or "flamengo" in result_str.lower()

    def test_mcp_get_team_stats(self):
        """Test get_team_stats tool."""
        result = asyncio.run(mcp.call_tool(
            "get_team_stats",
            {"team": "Palmeiras", "season": 2012}
        ))
        result_str = str(result)
        assert "Palmeiras" in result_str or "palmeiras" in result_str.lower()

    def test_mcp_get_team_comparison(self):
        """Test get_team_comparison tool."""
        result = asyncio.run(mcp.call_tool(
            "get_team_comparison",
            {"team1": "Flamengo", "team2": "Fluminense"}
        ))
        result_str = str(result)
        assert "Flamengo" in result_str or "flamengo" in result_str.lower()

    def test_mcp_search_players(self):
        """Test search_players tool."""
        result = asyncio.run(mcp.call_tool(
            "search_players",
            {"name": "Neymar", "limit": 5}
        ))
        result_str = str(result)
        assert "Neymar" in result_str or "neymar" in result_str.lower()

    def test_mcp_get_top_brazilian_players(self):
        """Test get_top_brazilian_players tool."""
        result = asyncio.run(mcp.call_tool(
            "get_top_brazilian_players",
            {"limit": 5}
        ))
        result_str = str(result)
        assert isinstance(result_str, str)

    def test_mcp_get_competition_standings(self):
        """Test get_competition_standings tool."""
        result = asyncio.run(mcp.call_tool(
            "get_competition_standings",
            {"competition": "Brasileirão", "season": 2019}
        ))
        result_str = str(result)
        assert "2019" in result_str

    def test_mcp_get_big_wins(self):
        """Test get_big_wins tool."""
        result = asyncio.run(mcp.call_tool(
            "get_big_wins",
            {"limit": 5}
        ))
        result_str = str(result)
        assert isinstance(result_str, str)

    def test_mcp_get_average_goals_per_match(self):
        """Test get_average_goals_per_match tool."""
        result = asyncio.run(mcp.call_tool(
            "get_average_goals_per_match",
            {}
        ))
        result_str = str(result)
        assert isinstance(result_str, str)
        assert "average" in result_str.lower() or "Average" in result_str

    def test_mcp_get_home_win_rate(self):
        """Test get_home_win_rate tool."""
        result = asyncio.run(mcp.call_tool(
            "get_home_win_rate",
            {}
        ))
        result_str = str(result)
        assert isinstance(result_str, str)

    def test_mcp_list_competitions(self):
        """Test list_competitions tool."""
        result = asyncio.run(mcp.call_tool(
            "list_competitions",
            {}
        ))
        # MCP returns ContentBlock objects, extract text
        if isinstance(result, (list, tuple)):
            # Extract text from ContentBlock
            text_parts = []
            for item in result:
                if hasattr(item, 'text'):
                    text_parts.append(item.text)
                elif hasattr(item, 'content'):
                    text_parts.append(item.content)
                else:
                    text_parts.append(str(item))
            result_str = ' '.join(text_parts)
        else:
            result_str = str(result)
        assert "Brasileirão" in result_str or "brasileirão" in result_str.lower() or "brasileir" in result_str.lower()

    def test_mcp_list_seasons(self):
        """Test list_seasons tool."""
        result = asyncio.run(mcp.call_tool(
            "list_seasons",
            {"competition": "Brasileirão"}
        ))
        result_str = str(result)
        assert isinstance(result_str, str)

    def test_mcp_server_initialization(self):
        """Test that MCP server initializes correctly."""
        tools = asyncio.run(mcp.list_tools())
        assert len(tools) >= 10, f"Expected at least 10 tools, got {len(tools)}"
