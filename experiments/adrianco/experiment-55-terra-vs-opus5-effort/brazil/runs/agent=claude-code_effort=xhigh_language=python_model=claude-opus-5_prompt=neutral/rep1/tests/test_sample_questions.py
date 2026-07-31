"""
The sample questions from the specification, answered end to end.

Context
-------
TASK.md sets an explicit success criterion: "At least 20 sample questions can be
answered".  Every question it lists appears below, together with the tool call
an LLM would make and the substrings the rendered answer must contain.  A few
extra questions cover cross-file joins and the honest-failure paths.

Run ``pytest tests/test_sample_questions.py -v`` to see the whole catalogue, or
``pytest tests/test_sample_questions.py -s -k demo`` to print the answers.
"""

from __future__ import annotations

import pytest

from brazilian_soccer.tools import call_tool

#: (question, tool, arguments, substrings the answer must contain)
SAMPLE_QUESTIONS: list[tuple[str, str, dict, list[str]]] = [
    # -- Simple lookups ----------------------------------------------------
    (
        "Show me all Flamengo vs Fluminense matches",
        "head_to_head", {"team_a": "Flamengo", "team_b": "Fluminense", "limit": 5},
        ["Fla-Flu", "Head-to-head in dataset", "Flamengo"],
    ),
    (
        "When did Flamengo last play Corinthians, and what was the score?",
        "search_matches", {"team": "Flamengo", "opponent": "Corinthians", "limit": 1},
        ["Flamengo", "Corinthians", "20"],
    ),
    (
        "What matches did Palmeiras play in 2023?",
        "search_matches", {"team": "Palmeiras", "season": 2023, "limit": 10},
        ["Palmeiras", "2023"],
    ),
    (
        "Find all Copa do Brasil finals",
        "search_matches", {"competition": "copa do brasil", "stage": "final", "limit": 30},
        ["Copa do Brasil", "Final"],
    ),
    (
        "Who is Neymar?",
        "player_profile", {"name": "Neymar"},
        ["Neymar Jr", "Overall: 92", "Brazil"],
    ),
    (
        "Who is Gabriel Barbosa?",
        "player_profile", {"name": "Gabriel Barbosa"},
        ["No player named", "Closest names", "unlicensed"],
    ),
    # -- Team questions ----------------------------------------------------
    (
        "What is Corinthians' home record in 2022?",
        "team_stats",
        {"team": "Corinthians", "competition": "brasileirao", "season": 2022,
         "scope": "home"},
        ["Matches: 19", "Wins:", "Goals For:", "Win rate:"],
    ),
    (
        "Which team scored the most goals in Serie A 2019?",
        "top_scoring_teams", {"competition": "brasileirao", "season": 2019, "limit": 5},
        ["Flamengo", "86 goals"],
    ),
    (
        "Compare Palmeiras and Santos head-to-head",
        "compare_teams", {"team_a": "Palmeiras", "team_b": "Santos"},
        ["Palmeiras", "Santos", "Head-to-head in dataset"],
    ),
    (
        "What competitions has Palmeiras played in?",
        "team_profile", {"team": "Palmeiras"},
        ["Campeonato Brasileiro Série A", "Copa Libertadores", "Copa do Brasil"],
    ),
    (
        "Which team has the best home record?",
        "best_records",
        {"competition": "brasileirao", "scope": "home", "metric": "points_per_game",
         "min_matches": 200, "limit": 5},
        ["Best home records", "win rate"],
    ),
    (
        "Which team has the best away record?",
        "best_records",
        {"competition": "brasileirao", "scope": "away", "metric": "points_per_game",
         "min_matches": 200, "limit": 5},
        ["Best away records", "win rate"],
    ),
    # -- Player questions --------------------------------------------------
    (
        "Find all Brazilian players in the dataset",
        "search_players", {"nationality": "Brazil", "limit": 10},
        ["Neymar Jr", "Overall", "more players match"],
    ),
    (
        "Who are the top Brazilian players?",
        "search_players", {"nationality": "Brazil", "min_overall": 85, "limit": 10},
        ["Neymar Jr", "Casemiro"],
    ),
    (
        "Who are the highest-rated players at Grêmio?",
        "search_players", {"club": "Grêmio", "limit": 5},
        ["Overall", "Grêmio"],
    ),
    (
        "Which players play for Flamengo?",
        "club_squad", {"club": "Flamengo"},
        ["no players in the FIFA 19 dataset", "match graph"],
    ),
    (
        "Show me all forwards from São Paulo FC",
        "search_players", {"club": "São Paulo", "position": "forward", "limit": 10},
        ["No players in the FIFA dataset match", "unlicensed"],
    ),
    (
        "Show me all forwards from Santos",
        "search_players", {"club": "Santos", "position": "forward", "limit": 10},
        ["Overall", "Santos"],
    ),
    (
        "Which Brazilian clubs have the strongest squads?",
        "brazilian_club_squads", {"limit": 10},
        ["avg rating", "players"],
    ),
    # -- Competition questions ---------------------------------------------
    (
        "Who won the 2019 Brasileirão?",
        "competition_standings", {"competition": "brasileirao", "season": 2019},
        ["1. Flamengo (RJ) - 90 pts (28W, 6D, 4L)", "Champion"],
    ),
    (
        "Who won the 2019 Copa Libertadores?",
        "competition_champion", {"competition": "libertadores", "season": 2019},
        ["Flamengo", "Champion:"],
    ),
    (
        "Show the 2018 Copa Libertadores knockout rounds",
        "search_matches",
        {"competition": "libertadores", "season": 2018, "stage": "semifinals", "limit": 10},
        ["Libertadores", "Semifinals"],
    ),
    (
        "Which teams were relegated in 2020?",
        "relegated_teams", {"competition": "brasileirao", "season": 2020},
        ["Relegated", "Botafogo", "Coritiba"],
    ),
    (
        "Which competitions and seasons does the knowledge graph cover?",
        "list_competitions", {},
        ["Campeonato Brasileiro Série A", "Copa Libertadores", "seasons"],
    ),
    # -- Statistical questions ---------------------------------------------
    (
        "What's the average goals per match in the Brasileirão?",
        "competition_stats", {"competition": "brasileirao"},
        ["Average goals per match", "Home win rate"],
    ),
    (
        "Show me the biggest wins in the dataset",
        "biggest_wins", {"limit": 5},
        ["Biggest victories", "-"],
    ),
    (
        "Compare the 2018 and 2019 seasons",
        "compare_seasons", {"seasons": [2018, 2019], "competition": "brasileirao"},
        ["2018", "2019", "Champion", "Goals per match"],
    ),
    (
        "Show me all derbies in 2023",
        "find_derbies", {"season": 2023, "limit": 3},
        ["Fla-Flu", "Flamengo"],
    ),
    (
        "How much data is behind these answers?",
        "dataset_summary", {},
        ["Brasileirao_Matches.csv", "fifa_data.csv", "duplicate rows merged"],
    ),
    (
        "Which clubs from São Paulo state are in the graph?",
        "list_teams", {"state": "SP", "limit": 10},
        ["Palmeiras", "Corinthians", "matches"],
    ),
    (
        "Is 'Botafogo' ambiguous?",
        "resolve_team", {"query": "Botafogo"},
        ["Botafogo", "matches"],
    ),
]


def test_the_specification_target_of_twenty_questions_is_exceeded():
    assert len(SAMPLE_QUESTIONS) >= 20


@pytest.mark.parametrize(
    "question, tool, arguments, expected",
    SAMPLE_QUESTIONS,
    ids=[question for question, _, _, _ in SAMPLE_QUESTIONS],
)
def test_sample_question(graph, question, tool, arguments, expected):
    result = call_tool(tool, arguments, graph=graph)
    assert result.text.strip(), f"{question!r} produced an empty answer"
    for needle in expected:
        assert needle in result.text, (
            f"{question!r} -> expected {needle!r} in:\n{result.text}"
        )


def test_demo_prints_every_answer(graph, capsys):
    """Not an assertion so much as living documentation -- run with ``-s``."""

    with capsys.disabled():
        pass
    for question, tool, arguments, _ in SAMPLE_QUESTIONS:
        answer = call_tool(tool, arguments, graph=graph).text
        print(f"\nQ: {question}\nA: {answer}\n{'-' * 70}")
    assert True
