"""BDD: at least 20 sample questions can be answered.

Feature: Answer natural-language style questions
  Scenario Outline: the server produces a sensible, non-empty answer

Each case maps a question to a callable producing a formatted answer and a
substring expected to appear in that answer.
"""

import pytest

from brazilian_soccer_mcp import formatters as fmt


def _answers(graph):
    """Build (question, answer, expected_substring) triples."""
    g = graph
    cases = []

    def add(q, answer, expect):
        cases.append((q, answer, expect))

    # --- Match queries ---
    add("Show me all Flamengo vs Fluminense matches",
        fmt.format_head_to_head(g.head_to_head("Flamengo", "Fluminense")),
        "Flamengo")
    add("What matches did Palmeiras play in 2023?",
        fmt.format_matches(g.find_matches(team="Palmeiras", season=2023,
                                          competition="Brasileirão")),
        "Palmeiras")
    add("When did Flamengo last play Corinthians?",
        fmt.format_matches(g.find_matches(team="Flamengo", opponent="Corinthians",
                                          limit=1)),
        "Flamengo")
    add("Show me Grêmio matches in 2018",
        fmt.format_matches(g.find_matches(team="Grêmio", season=2018,
                                          competition="Brasileirão")),
        "Grêmio")
    add("Find São Paulo home games in 2022",
        fmt.format_matches(g.find_matches(team="São Paulo", season=2022,
                                          competition="Brasileirão",
                                          venue="home")),
        "São Paulo")

    # --- Team queries ---
    add("What is Corinthians' home record in 2022?",
        fmt.format_team_record(
            g.team_record("Corinthians", season=2022, competition="Brasileirão",
                          venue="home"), season=2022, venue="home"),
        "Win rate")
    add("How did Palmeiras do in 2023?",
        fmt.format_team_record(
            g.team_record("Palmeiras", season=2023, competition="Brasileirão"),
            season=2023),
        "Palmeiras")
    add("Compare Palmeiras and Santos head-to-head",
        fmt.format_head_to_head(g.head_to_head("Palmeiras", "Santos")),
        "Head-to-head")
    add("Atlético-MG record in 2019",
        fmt.format_team_record(
            g.team_record("Atlético-MG", season=2019, competition="Brasileirão"),
            season=2019),
        "Matches")

    # --- Competition queries ---
    add("Who won the 2019 Brasileirão?",
        fmt.format_standings(g.standings("Brasileirão", 2019), "Brasileirão", 2019),
        "Champion")
    add("Show 2018 Brasileirão final standings",
        fmt.format_standings(g.standings("Brasileirão", 2018), "Brasileirão", 2018),
        "Standings")
    add("Who was champion in 2017?",
        f"{g.champion('Brasileirão', 2017).team}",
        "Corinthians")
    add("Copa do Brasil matches in 2019",
        fmt.format_matches(g.find_matches(competition="Copa do Brasil",
                                          season=2019, limit=5)),
        "-")

    # --- Player queries ---
    add("Who is Neymar?",
        fmt.format_players(g.search_players(name="Neymar", limit=1)),
        "Neymar")
    add("Find all Brazilian players in the dataset",
        fmt.format_players(g.search_players(nationality="Brazil", limit=10)),
        "Overall")
    add("Who are the highest-rated players at Flamengo?",
        fmt.format_players(g.players_at_club("Flamengo", limit=5)),
        "Flamengo")
    add("Top Brazilian players",
        fmt.format_players(g.top_brazilian_players(limit=5)),
        "Overall")
    add("Show me goalkeepers rated 85+",
        fmt.format_players(g.search_players(position="GK", min_overall=85,
                                            limit=5)),
        "GK")
    add("Who is Gabriel Barbosa?",
        fmt.format_players(g.search_players(name="Gabriel", limit=3)),
        "Gabriel")

    # --- Statistical analysis ---
    add("What's the average goals per match in the Brasileirão?",
        fmt.format_stats(g.average_goals("Brasileirão")),
        "Average goals per match")
    add("Show me the biggest wins in the dataset",
        fmt.format_biggest_wins(g.biggest_wins(limit=5)),
        "margin")
    add("Which team has the best home record in 2019?",
        "\n".join(f"{r.team}: {r.win_rate:.1f}%"
                  for r in g.best_record(competition="Brasileirão", season=2019,
                                         venue="home")[:5]),
        "%")
    add("Average goals in Libertadores",
        fmt.format_stats(g.average_goals("Libertadores")),
        "Average")
    add("Which team scored the most in 2019 Serie A?",
        f"{g.top_scoring_team(competition='Brasileirão', season=2019).team}",
        "")

    return cases


def test_at_least_20_sample_questions(graph):
    assert len(_answers(graph)) >= 20


def test_sample_questions_answers(graph):
    for question, answer, expect in _answers(graph):
        assert isinstance(answer, str) and answer.strip(), f"empty answer: {question}"
        assert "No matches found" not in answer, f"no data for: {question}"
        assert "No players found" not in answer, f"no data for: {question}"
        if expect:
            assert expect in answer, f"{question!r} -> missing {expect!r}\n{answer}"
