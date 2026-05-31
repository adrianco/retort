"""
================================================================================
Brazilian Soccer MCP Server :: tests/test_sample_questions
================================================================================

Context
-------
Demonstrates that the server can answer the 20+ sample questions called for by
the specification's "Data Coverage" success criterion. Each case maps a natural
language question to the engine call that answers it and asserts a sensible,
non-empty result. This doubles as living documentation of how the LLM layer is
expected to route questions to tools.
================================================================================
"""

import pytest

# (question, callable(engine) -> result, assertion(result) -> bool)
QUESTIONS = [
    ("Show me all Flamengo vs Fluminense matches",
     lambda e: e.find_matches(team="Flamengo", opponent="Fluminense"),
     lambda r: r["count"] > 0),
    ("What matches did Palmeiras play in 2023?",
     lambda e: e.find_matches(team="Palmeiras", season=2023),
     lambda r: r["count"] > 0),
    ("Find all Copa do Brasil matches in 2022",
     lambda e: e.find_matches(competition="Copa do Brasil", season=2022),
     lambda r: r["count"] > 0),
    ("When did Flamengo last play Corinthians?",
     lambda e: e.find_matches(team="Flamengo", opponent="Corinthians", limit=1),
     lambda r: r["count"] > 0 and r["matches"][0]["date"] is not None),
    ("What is Corinthians' home record in 2022?",
     lambda e: e.team_record("Corinthians", season=2022, venue="home"),
     lambda r: r["played"] > 0),
    ("Which team scored the most goals in Serie A 2023?",
     lambda e: e.top_scoring_teams(competition="Brasileirão Série A", season=2023),
     lambda r: len(r["top_scorers"]) > 0),
    ("Compare Palmeiras and Santos head-to-head",
     lambda e: e.compare_teams("Palmeiras", "Santos"),
     lambda r: r["head_to_head"]["summary"]["matches"] > 0),
    ("Find all Brazilian players in the dataset",
     lambda e: e.search_players(nationality="Brazil", limit=2000),
     lambda r: r["count"] > 100),
    ("Who are the highest-rated Brazilian players?",
     lambda e: e.search_players(nationality="Brazil", sort_by="overall", limit=5),
     lambda r: r["players"][0]["overall"] >= r["players"][-1]["overall"]),
    ("Show me all goalkeepers from Brazil",
     lambda e: e.search_players(nationality="Brazil", position="GK", limit=50),
     lambda r: all(p["position"] == "GK" for p in r["players"]) and r["count"] > 0),
    ("Who is Neymar?",
     lambda e: e.search_players(name="Neymar"),
     lambda r: r["count"] >= 1),
    ("Who won the 2019 Brasileirão?",
     lambda e: e.champion("Brasileirão Série A", 2019),
     lambda r: r["champion"]["team"] == "Flamengo"),
    ("Show the 2018 Brasileirão standings",
     lambda e: e.standings("Brasileirão Série A", 2018),
     lambda r: r["teams"] == 20),
    ("Which teams were relegated in 2019?",
     lambda e: e.relegated("Brasileirão Série A", 2019, count=4),
     lambda r: len(r["relegated"]) == 4),
    ("What's the average goals per match in the Brasileirão?",
     lambda e: e.competition_stats(competition="Brasileirão Série A"),
     lambda r: 1.5 < r["avg_goals_per_match"] < 4.0),
    ("Which team has the best home record in 2019?",
     lambda e: e.best_record(competition="Brasileirão Série A", season=2019, venue="home"),
     lambda r: len(r["ranking"]) > 0),
    ("Which team has the best away record?",
     lambda e: e.best_record(competition="Brasileirão Série A", venue="away"),
     lambda r: len(r["ranking"]) > 0),
    ("Show me the biggest wins in the dataset",
     lambda e: e.biggest_wins(limit=5),
     lambda r: r["biggest_wins"][0]["margin"] >= 6),
    ("What competitions has Palmeiras played in?",
     lambda e: e.find_matches(team="Palmeiras"),
     lambda r: len({m["competition"] for m in r["matches"]}) >= 1),
    ("List available competitions",
     lambda e: {"competitions": e.graph.competitions},
     lambda r: len(r["competitions"]) >= 3),
    ("How did Grêmio do in 2018?",
     lambda e: e.team_record("Grêmio", season=2018),
     lambda r: r["played"] > 0),
    ("Head-to-head between São Paulo and Corinthians (Majestoso)",
     lambda e: e.head_to_head("São Paulo", "Corinthians"),
     lambda r: r["summary"]["matches"] > 0),
    ("Find Libertadores matches in 2019",
     lambda e: e.find_matches(competition="Copa Libertadores", season=2019),
     lambda r: r["count"] > 0),
    ("Top scoring teams in 2018 Brasileirão",
     lambda e: e.top_scoring_teams(competition="Brasileirão Série A", season=2018),
     lambda r: r["top_scorers"][0]["goals"] > r["top_scorers"][-1]["goals"]),
    ("Brazilian players grouped by club",
     lambda e: e.players_at_brazilian_clubs("Brazil"),
     lambda r: len(r["clubs"]) > 0),
]


@pytest.mark.parametrize("question,call,check", QUESTIONS, ids=[q[0] for q in QUESTIONS])
def test_sample_question(engine, question, call, check):
    result = call(engine)
    assert check(result), f"Failed to answer: {question} -> {result}"


def test_at_least_20_sample_questions():
    assert len(QUESTIONS) >= 20
