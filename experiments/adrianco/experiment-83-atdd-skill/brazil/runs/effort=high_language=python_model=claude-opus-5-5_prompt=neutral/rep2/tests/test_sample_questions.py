"""The spec's sample questions, each answered through the MCP protocol.

Each entry maps a natural-language question to the tool call an LLM would
make and checks the answer contains the expected facts.
"""

import asyncio

import pytest

import server
from mcp import Client

SAMPLE_QUESTIONS = [
    # --- match queries
    ("Show me all Flamengo vs Fluminense matches",
     "head_to_head", {"team_a": "Flamengo", "team_b": "Fluminense"},
     ["Flamengo vs Fluminense (Fla-Flu derby)", "Head-to-head in dataset", "wins", "draws"]),
    ("What matches did Palmeiras play in 2023?",
     "search_matches", {"team": "Palmeiras", "season": 2023},
     ["Matches — Palmeiras, season 2023", "Brasileirão Série A", "Copa do Brasil"]),
    ("Find all Copa do Brasil finals",
     "knockout_results", {"competition": "Copa do Brasil", "stage": "final"},
     ["2012 final", "2023 final", "Flamengo 0-1 São Paulo", "São Paulo champion"]),
    ("When did Flamengo last play Corinthians? What was the score?",
     "search_matches", {"team": "Flamengo", "opponent": "Corinthians", "limit": 1},
     ["2023-10-08: Corinthians 1-1 Flamengo"]),
    ("Which Libertadores matches were played between 1 and 30 November 2019?",
     "search_matches", {"competition": "Libertadores", "date_from": "2019-11-01", "date_to": "30/11/2019"},
     ["2019-11-23: Flamengo 2-1 River Plate"]),
    # --- team queries
    ("What is Corinthians' home record in 2022?",
     "team_record", {"team": "Corinthians", "season": 2022, "competition": "Brasileirão", "venue": "home"},
     ["Corinthians home record (2022, Brasileirão Série A)", "- Matches: 19", "Win rate:"]),
    ("Which team scored the most goals in Serie A 2023?",
     "team_rankings", {"metric": "goals_for", "season": 2023, "competition": "Serie A", "limit": 5},
     ["1. Grêmio - 63 goals scored"]),
    ("Compare Palmeiras and Santos head-to-head",
     "head_to_head", {"team_a": "Palmeiras", "team_b": "Santos"},
     ["Palmeiras vs Santos (Clássico da Saudade derby)", "Head-to-head in dataset"]),
    ("What competitions has Palmeiras played in?",
     "team_overview", {"team": "Palmeiras"},
     ["Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"]),
    ("How has Vasco performed season by season?",
     "team_trend", {"team": "Vasco"},
     ["Vasco da Gama — Brasileirão Série A season by season", "2020: 17th of 20"]),
    # --- player queries
    ("Who is Gabriel Barbosa?",
     "player_profile", {"name": "Gabriel Barbosa"},
     ["No player named 'Gabriel Barbosa'", "Closest names"]),
    ("Who is Neymar?",
     "player_profile", {"name": "Neymar"},
     ["Neymar Jr", "Overall: 92", "Paris Saint-Germain"]),
    ("Find all Brazilian players in the dataset",
     "search_players", {"nationality": "Brazilian", "limit": 5},
     ["827 found", "1. Neymar Jr - Overall: 92"]),
    ("Who are the highest-rated players at Flamengo?",
     "search_players", {"club": "Flamengo"},
     ["FIFA 19 has no squad for Flamengo"]),
    ("Which players play for Grêmio?",
     "search_players", {"club": "Gremio"},
     ["Players (club=Gremio): 20 found", "Club: Grêmio"]),
    ("Show me all forwards from Santos",
     "search_players", {"club": "Santos", "position": "forward"},
     ["Position: ST", "Club: Santos"]),
    ("Who are the top Brazilian players?",
     "player_club_summary", {"nationality": "Brazil"},
     ["Top-rated:", "1. Neymar Jr - Overall: 92", "Brazil players at Brazilian clubs:"]),
    # --- competition queries
    ("Who won the 2019 Brasileirão?",
     "standings", {"season": 2019, "top": 5},
     ["1. Flamengo - 90 pts (28W, 6D, 4L", "Champion"]),
    ("Show the 2018 Copa Libertadores bracket",
     "knockout_results", {"competition": "Libertadores", "season": 2018},
     ["2018 round of 16", "2018 semifinals", "River Plate champion"]),
    ("Which teams were relegated in 2020?",
     "standings", {"season": 2020},
     ["Vasco da Gama - 41 pts", "Relegated", "Botafogo - 27 pts"]),
    ("Show me all derbies in 2023",
     "derby_matches", {"season": 2023},
     ["Fla-Flu", "Grenal", "Derby Paulista", "Choque-Rei"]),
    # --- statistical analysis
    ("What's the average goals per match in the Brasileirão?",
     "competition_stats", {"competition": "Brasileirão"},
     ["Average goals per match: 2.", "Home win rate:"]),
    ("Which team has the best away record?",
     "team_rankings", {"metric": "win_rate", "venue": "away"},
     ["away matches only", "1. "]),
    ("Which team has the best home record?",
     "team_rankings", {"metric": "win_rate", "venue": "home"},
     ["home matches only", "1. "]),
    ("Show me the biggest wins in the dataset",
     "biggest_wins", {},
     ["Biggest victories", "margin 8", "Average goals per match:"]),
    ("Compare the 2018 and 2019 seasons",
     "compare_seasons", {"seasons": [2018, 2019]},
     ["2018:", "2019:", "Champion (calculated): Palmeiras", "Champion (calculated): Flamengo"]),
    ("What does the dataset contain?",
     "dataset_info", {},
     ["fifa_data.csv: 18207 rows", "Copa Libertadores"]),
]


def test_at_least_twenty_questions():
    assert len(SAMPLE_QUESTIONS) >= 20


@pytest.fixture(scope="module")
def answers():
    async def run_all():
        async with Client(server.mcp) as client:
            out = []
            for _, tool, args, _ in SAMPLE_QUESTIONS:
                out.append(await client.call_tool(tool, args))
            return out
    return asyncio.run(run_all())


@pytest.mark.parametrize("idx", range(len(SAMPLE_QUESTIONS)), ids=[q for q, *_ in SAMPLE_QUESTIONS])
def test_sample_question(answers, idx):
    question, tool, args, expected = SAMPLE_QUESTIONS[idx]
    result = answers[idx]
    assert not result.is_error, result.content[0].text
    text = result.content[0].text
    for fragment in expected:
        assert fragment in text, f"{question!r}: expected {fragment!r} in:\n{text}"
