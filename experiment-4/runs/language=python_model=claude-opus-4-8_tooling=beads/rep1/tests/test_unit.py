"""
================================================================================
Module: tests.test_unit
Project: Brazilian Soccer MCP Server - test suite
--------------------------------------------------------------------------------
CONTEXT
  Given-When-Then style unit tests that complement the Gherkin BDD scenarios.
  They cover normalization edge cases, date parsing, additional spec sample
  questions, and the MCP server tool layer (tool registration + invocation),
  bringing the suite well past the spec's "20 sample questions" bar.
================================================================================
"""

import asyncio

import pytest

from brazilian_soccer_mcp import queries
from brazilian_soccer_mcp.data_loader import get_data, parse_date
from brazilian_soccer_mcp.normalize import (
    resolve_team, team_matches, strip_accents, canonical_key,
)


@pytest.fixture(scope="module")
def data():
    return get_data()


# --------------------------------------------------------------------------
# Normalization
# --------------------------------------------------------------------------
@pytest.mark.parametrize("raw, expected_key, expected_name", [
    ("Palmeiras-SP", "palmeiras", "Palmeiras"),
    ("Flamengo-RJ", "flamengo", "Flamengo"),
    ("São Paulo", "sao paulo", "São Paulo"),
    ("Sao Paulo", "sao paulo", "São Paulo"),
    ("Grêmio", "gremio", "Grêmio"),
    ("Atlético-MG", "atletico mg", "Atlético Mineiro"),
    ("Atletico Mineiro", "atletico mg", "Atlético Mineiro"),
    ("Athletico", "atletico pr", "Athletico Paranaense"),
    ("Atletico-GO", "atletico go", "Atlético Goianiense"),
    ("Vasco da Gama", "vasco", "Vasco da Gama"),
    ("EC Bahia", "bahia", "Bahia"),
    ("Fortaleza FC", "fortaleza", "Fortaleza"),
])
def test_team_normalization(raw, expected_key, expected_name):
    """Given a raw team name, When resolved, Then key and display are canonical."""
    key, name = resolve_team(raw)
    assert key == expected_key
    assert name == expected_name


def test_distinct_atleticos_are_not_merged():
    """Different Atléticos must keep distinct identities."""
    assert canonical_key("Atletico-MG") != canonical_key("Atletico-GO")
    assert canonical_key("Atletico-MG") != canonical_key("Athletico-PR")


def test_strip_accents():
    assert strip_accents("São Grêmio Avaí") == "Sao Gremio Avai"


def test_team_matches_handles_suffixes():
    assert team_matches("Flamengo", canonical_key("Flamengo-RJ"))
    assert team_matches("Atletico", canonical_key("Atletico-MG"))  # ambiguous prefix
    assert not team_matches("Santos", canonical_key("Flamengo-RJ"))


@pytest.mark.parametrize("raw, iso", [
    ("2023-09-24", "2023-09-24"),
    ("2012-05-19 18:30:00", "2012-05-19"),
    ("29/03/2003", "2003-03-29"),
])
def test_parse_date_formats(raw, iso):
    assert parse_date(raw).isoformat() == iso


# --------------------------------------------------------------------------
# Spec sample questions
# --------------------------------------------------------------------------
def test_average_goals_per_match_matches_spec(data):
    """Spec states avg goals per Brasileirão match ~= 2.47."""
    stats = queries.competition_stats(competition="Brasileirão Série A", data=data)
    assert 2.3 <= stats["avg_goals_per_match"] <= 2.6


def test_2019_brasileirao_champion(data):
    assert queries.standings(2019, data=data)["champion"] == "Flamengo"


def test_2015_brasileirao_champion(data):
    assert queries.standings(2015, data=data)["champion"] == "Corinthians"


def test_head_to_head_fla_flu(data):
    h2h = queries.head_to_head("Flamengo", "Fluminense", data=data)
    assert h2h["total_matches"] >= 20
    s = h2h["summary"]
    assert s["Flamengo_wins"] > 0 and s["Fluminense_wins"] > 0


def test_top_brazilian_player_is_neymar(data):
    res = queries.find_players(nationality="Brazil", limit=1, data=data)
    assert res["players"][0]["name"].startswith("Neymar")


def test_get_player_includes_skills(data):
    p = queries.get_player("Casemiro", data=data)
    assert p["found"] is True
    assert p["nationality"] == "Brazil"
    assert isinstance(p.get("skills"), dict) and p["skills"]


def test_biggest_win_has_large_margin(data):
    res = queries.biggest_wins(competition="Libertadores", limit=1, data=data)
    assert res["results"][0]["margin"] >= 5


def test_competitions_cover_all_three_majors(data):
    comps = queries.list_competitions(data=data)["competitions"]
    assert "Brasileirão Série A" in comps
    assert "Copa do Brasil" in comps
    assert "Copa Libertadores" in comps


def test_compare_teams_includes_h2h(data):
    res = queries.compare_teams("Palmeiras", "Santos", data=data)
    assert res["team_a_record"]["matches"] > 0
    assert res["team_b_record"]["matches"] > 0
    assert res["head_to_head"]


def test_unknown_team_returns_not_found(data):
    res = queries.team_record("Nonexistent United", data=data)
    assert res["found"] is False


def test_best_away_records_rankable(data):
    res = queries.best_records(venue="away", season=2019, data=data)
    assert len(res["results"]) > 1


# --------------------------------------------------------------------------
# MCP server tool layer
# --------------------------------------------------------------------------
def test_mcp_server_registers_all_tools():
    from brazilian_soccer_mcp.server import mcp
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    expected = {
        "find_matches", "head_to_head", "team_record", "team_summary",
        "compare_teams", "find_players", "get_player", "club_squad",
        "standings", "season_results", "list_competitions",
        "competition_stats", "biggest_wins", "best_records",
        "top_scoring_teams",
    }
    assert expected.issubset(names)


def test_mcp_tool_invocation_returns_structured_data():
    import json
    from brazilian_soccer_mcp.server import mcp
    result = asyncio.run(mcp.call_tool("standings", {"season": 2019}))
    # FastMCP returns a list of content blocks; the tool's dict is serialized
    # as JSON in the first TextContent block.
    payload = json.loads(result[0].text)
    assert payload["champion"] == "Flamengo"
    assert payload["teams"] == 20
