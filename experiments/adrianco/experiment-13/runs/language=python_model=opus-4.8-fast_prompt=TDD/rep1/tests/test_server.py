"""Tests for the SoccerService (tool logic) and MCP server wiring."""
import asyncio

import pytest

from brazilian_soccer import data_loader, server as server_mod
from brazilian_soccer.queries import KnowledgeGraph
from brazilian_soccer.server import SoccerService, build_server


@pytest.fixture(scope="module")
def service(fixture_dir):
    matches = data_loader.load_matches(fixture_dir)
    players = data_loader.load_players(fixture_dir)
    return SoccerService(KnowledgeGraph(matches, players))


# --- tool logic returns formatted strings --------------------------------

def test_search_matches_text(service):
    out = service.search_matches(team="Flamengo", team2="Fluminense")
    assert "Flamengo" in out and "Fluminense" in out
    assert "2-1" in out  # m1 score
    assert "2019-05-19" in out


def test_search_matches_uses_canonical_competition_label(service):
    # The fixture Palmeiras-Corinthians match is labelled "Serie A" in source.
    out = service.search_matches(team="Palmeiras", team2="Corinthians")
    assert "Brasileirão" in out
    assert "Serie A" not in out


def test_search_matches_no_results(service):
    out = service.search_matches(team="Nonexistent FC")
    assert "No matches" in out


def test_head_to_head_text(service):
    out = service.head_to_head("Flamengo", "Fluminense")
    assert "Flamengo" in out
    assert "2" in out  # Flamengo 2 wins


def test_team_record_text(service):
    out = service.team_record("Flamengo", competition="Brasileirão")
    assert "Wins" in out
    assert "66.7" in out


def test_search_players_text(service):
    out = service.search_players(nationality="Brazil")
    assert "Neymar Jr" in out
    assert "Gabriel Barbosa" in out
    # Sorted by overall: Neymar before Gabriel.
    assert out.index("Neymar Jr") < out.index("Gabriel Barbosa")


def test_search_players_no_results(service):
    assert "No players" in service.search_players(name="zzzznope")


def test_standings_text(service):
    out = service.standings("Brasileirão", 2019)
    assert "Flamengo" in out
    assert "Champion" in out


def test_champion_text(service):
    out = service.competition_champion("Brasileirão", 2019)
    assert "Flamengo" in out


def test_statistics_text(service):
    out = service.statistics(competition="Brasileirão", season=2019)
    assert "Average goals" in out
    assert "Home win rate" in out


# --- MCP server wiring ---------------------------------------------------

def test_build_server_registers_tools(service):
    mcp = build_server(service)
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    expected = {
        "search_matches",
        "head_to_head",
        "team_record",
        "search_players",
        "standings",
        "competition_champion",
        "statistics",
    }
    assert expected <= names


def test_service_from_data_dir(real_data_dir):
    svc = server_mod.SoccerService.from_data_dir(real_data_dir)
    out = svc.search_players(name="Neymar")
    assert "Neymar" in out
    assert "Brazil" in out
