"""
================================================================================
tests.test_server_tools
================================================================================

CONTEXT
-------
BDD scenarios verifying the MCP server layer: every required tool is registered
and each returns a well-formed, non-empty text answer. The parametrised
"sample questions" scenario demonstrates the Success Criterion that at least 20
sample questions from the spec can be answered end-to-end through the tools.
================================================================================
"""

import asyncio

import pytest

from brazilian_soccer_mcp import server


def test_all_expected_tools_are_registered():
    # Given the MCP server, When listing its tools
    tools = asyncio.run(server.mcp.list_tools())
    names = {t.name for t in tools}
    # Then all required capability tools are present
    expected = {
        "find_matches", "last_meeting", "team_record", "head_to_head",
        "search_players", "standings", "champion", "relegated",
        "competition_statistics", "biggest_wins", "best_record",
        "list_competitions", "list_seasons",
    }
    assert expected.issubset(names)


def test_every_tool_has_a_description():
    tools = asyncio.run(server.mcp.list_tools())
    assert all(t.description for t in tools)


# Each tuple is (callable, kwargs, substring that must appear in the answer).
SAMPLE_QUESTIONS = [
    # --- Simple lookups ---
    (server.find_matches, dict(team="Flamengo", opponent="Fluminense"), "Flamengo"),
    (server.find_matches, dict(team="Palmeiras", season=2019), "Palmeiras"),
    (server.last_meeting, dict(team1="Flamengo", team2="Corinthians"), "Flamengo"),
    (server.find_matches, dict(team="Corinthians", competition="Copa do Brasil"), "Copa do Brasil"),
    (server.find_matches, dict(team="Grêmio", competition="Libertadores"), "Libertadores"),
    # --- Team queries ---
    (server.team_record, dict(team="Corinthians", season=2022, venue="home"), "record"),
    (server.team_record, dict(team="Palmeiras", season=2019, competition="Brasileirão"), "Points"),
    (server.head_to_head, dict(team1="Palmeiras", team2="Santos"), "head-to-head"),
    (server.head_to_head, dict(team1="Atletico Mineiro", team2="Cruzeiro"), "head-to-head"),
    # --- Player queries ---
    (server.search_players, dict(name="Neymar"), "Neymar"),
    (server.search_players, dict(nationality="Brazil", limit=10), "Overall"),
    (server.search_players, dict(club="Internacional"), "Internacional"),
    (server.search_players, dict(nationality="Brazil", position="GK", limit=5), "GK"),
    # --- Competition queries ---
    (server.standings, dict(competition="Brasileirão Série A", season=2019), "Flamengo"),
    (server.champion, dict(competition="Brasileirão Série A", season=2019), "Flamengo"),
    (server.relegated, dict(competition="Brasileirão Série A", season=2019), "relegation"),
    (server.standings, dict(competition="Brasileirão Série A", season=2018), "standings"),
    # --- Statistical analysis ---
    (server.competition_statistics, dict(competition="Brasileirão Série A"), "Average goals"),
    (server.competition_statistics, dict(competition="Brasileirão Série A", season=2019), "win rate"),
    (server.biggest_wins, dict(competition="Brasileirão Série A", limit=5), "Biggest"),
    (server.best_record, dict(competition="Brasileirão Série A", season=2019, venue="home"), "record"),
    (server.best_record, dict(competition="Brasileirão Série A", season=2019, venue="away"), "record"),
    # --- Discovery ---
    (server.list_competitions, dict(), "Brasileirão"),
    (server.list_seasons, dict(competition="Brasileirão Série A"), "2019"),
]


@pytest.mark.parametrize("func,kwargs,needle", SAMPLE_QUESTIONS)
def test_sample_question_answered(func, kwargs, needle):
    # When the corresponding MCP tool is invoked
    answer = func(**kwargs)
    # Then a non-empty text answer is produced containing the expected content
    assert isinstance(answer, str) and answer.strip()
    assert needle.lower() in answer.lower()


def test_at_least_twenty_sample_questions_covered():
    # Success Criterion: at least 20 sample questions can be answered.
    assert len(SAMPLE_QUESTIONS) >= 20
