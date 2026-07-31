"""Feature: Sample questions from the specification.

Context
-------
``TASK.md`` requires that "at least 20 sample questions can be answered".  This
module is the acceptance test for that criterion: every question listed in the
spec -- simple lookups, relationship queries and analytical queries -- is asked
through the MCP tool layer (the same path an LLM takes) and the answer is
checked for the substance the question demands, not merely for non-emptiness.
"""

from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("mcp", reason="the MCP SDK is not installed")

from brazilian_soccer import server  # noqa: E402


def ask(tool: str, **arguments) -> str:
    result = asyncio.run(server.mcp.call_tool(tool, arguments))
    content = result.content if hasattr(result, "content") else result[0]
    if isinstance(content, list):
        return "\n".join(getattr(block, "text", str(block)) for block in content)
    return getattr(content, "text", str(content))


#: (question, tool, arguments, substrings that must appear in the answer)
SAMPLE_QUESTIONS = [
    # -- simple lookups ---------------------------------------------------
    (
        "Show me all Flamengo vs Fluminense matches",
        "head_to_head",
        {"team_a": "Flamengo", "team_b": "Fluminense"},
        ["Flamengo-RJ vs Fluminense-RJ", "Head-to-head in dataset:"],
    ),
    (
        "What matches did Palmeiras play in 2023?",
        "search_matches",
        {"team": "Palmeiras", "season": 2023, "limit": 10},
        ["Palmeiras", "2023-"],
    ),
    (
        "Find all Copa do Brasil finals",
        "search_matches",
        {"competition": "Copa do Brasil", "stage": "final", "limit": 20},
        ["final", "Cruzeiro"],
    ),
    (
        "When did Flamengo last play Corinthians?",
        "last_meeting",
        {"team_a": "Flamengo", "team_b": "Corinthians"},
        ["Most recent meeting:", "Corinthians"],
    ),
    (
        "What was the score?",
        "last_meeting",
        {"team_a": "Flamengo", "team_b": "Corinthians"},
        ["1-1"],
    ),
    (
        "Who is Gabriel Barbosa?",
        "get_player",
        {"name": "Gabriel Barbosa"},
        ["No exact match", "Overall:"],
    ),
    (
        "Who is Neymar?",
        "get_player",
        {"name": "Neymar"},
        ["Neymar Jr", "Overall: 92", "Nationality: Brazil"],
    ),
    # -- relationship queries ---------------------------------------------
    (
        "Which players play for Gremio?",
        "club_squad",
        {"club": "Gremio", "limit": 10},
        ["squad in the FIFA dataset", "Grêmio"],
    ),
    (
        "Show me all derbies in 2023",
        "find_derbies",
        {"season": 2023, "limit": 10},
        ["Derby matches in 2023"],
    ),
    (
        "What competitions has Palmeiras played in?",
        "team_profile",
        {"team": "Palmeiras"},
        ["Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"],
    ),
    (
        "Show me all strikers at Santos",
        "search_players",
        {"club": "Santos", "position": "ST", "limit": 10},
        ["Santos", "Position: ST"],
    ),
    (
        "Find all Brazilian players in the dataset",
        "search_players",
        {"nationality": "Brazil", "limit": 10},
        ["Neymar Jr", "Nationality: Brazil"],
    ),
    # -- team and competition queries -------------------------------------
    (
        "What is Corinthians' home record in 2022?",
        "team_statistics",
        {
            "team": "Corinthians",
            "season": 2022,
            "competition": "Brasileirao",
            "venue": "home",
        },
        ["- Matches: 19", "Win rate:"],
    ),
    (
        "Which team scored the most goals in Serie A 2023?",
        "team_rankings",
        {
            "competition": "Serie A",
            "season": 2023,
            "metric": "goals_for",
            "min_matches": 30,
            "limit": 3,
        },
        ["Top teams by goals_for", "1. "],
    ),
    (
        "Compare Palmeiras and Santos head-to-head",
        "compare_teams",
        {"team_a": "Palmeiras", "team_b": "Santos"},
        ["Comparison", "Head-to-head in dataset:"],
    ),
    (
        "Who won the 2019 Brasileirão?",
        "season_champion",
        {"season": 2019},
        ["champion: Flamengo-RJ", "90 pts"],
    ),
    (
        "Show me the 2019 Brasileirão final standings",
        "standings",
        {"season": 2019},
        ["1. Flamengo-RJ - 90 pts", "Champion"],
    ),
    (
        "Show the 2019 Copa Libertadores bracket",
        "competition_bracket",
        {"season": 2019, "competition": "Libertadores"},
        ["group stage", "semifinals", "final"],
    ),
    (
        "Which teams were relegated in 2020?",
        "relegated_teams",
        {"season": 2020},
        ["Botafogo-RJ", "calculated from match results"],
    ),
    # -- analytical queries -----------------------------------------------
    (
        "What's the average goals per match in the Brasileirão?",
        "competition_statistics",
        {"competition": "Brasileirao"},
        ["Average goals per match: 2."],
    ),
    (
        "Which team has the best away record?",
        "team_rankings",
        {"venue": "away", "min_matches": 100, "limit": 5},
        ["away matches", "pts/game"],
    ),
    (
        "Which team has the best home record?",
        "team_rankings",
        {"venue": "home", "min_matches": 100, "limit": 5},
        ["home matches", "pts/game"],
    ),
    (
        "Show me the biggest wins in the dataset",
        "biggest_wins",
        {"limit": 5},
        ["Biggest victories"],
    ),
    (
        "Compare the 2018 and 2019 seasons",
        "compare_seasons",
        {"seasons": [2018, 2019], "competition": "Brasileirao"},
        ["2018 statistics", "2019 statistics"],
    ),
    (
        "How has Flamengo performed season by season?",
        "team_season_trend",
        {"team": "Flamengo", "competition": "Serie A"},
        ["2019:", "90 pts"],
    ),
    (
        "Where do Brazilian players play?",
        "players_by_club",
        {"nationality": "Brazil", "limit": 5},
        ["players:", "average_overall"],
    ),
    (
        "What data is available?",
        "dataset_overview",
        {},
        ["Matches (de-duplicated):", "Copa Libertadores"],
    ),
]


@pytest.mark.parametrize(
    "question,tool,arguments,expected",
    SAMPLE_QUESTIONS,
    ids=[question for question, _, _, _ in SAMPLE_QUESTIONS],
)
def test_sample_question_is_answered(
    question: str, tool: str, arguments: dict, expected: list[str]
) -> None:
    # Given the MCP server with the datasets loaded
    # When the question is asked through its tool
    answer = ask(tool, **arguments)
    # Then the answer contains the substance the question asked for
    assert answer, question
    for fragment in expected:
        assert fragment in answer, f"{question!r} -> missing {fragment!r} in:\n{answer}"


def test_at_least_twenty_sample_questions_are_covered() -> None:
    # The spec requires at least 20 answerable sample questions
    assert len(SAMPLE_QUESTIONS) >= 20
