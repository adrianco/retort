"""Worked examples: the sample questions from the specification.

Each entry maps a natural-language question to the MCP tool call an LLM would
make. Run the whole set with::

    python -m brazilian_soccer.demo            # all questions
    python -m brazilian_soccer.demo derby      # only questions matching "derby"

The same list is used by the test-suite to prove that at least twenty sample
questions can be answered end to end.
"""

from __future__ import annotations

import sys
import time

from . import server

#: (question, tool name, keyword arguments)
SAMPLE_QUESTIONS: tuple[tuple[str, str, dict], ...] = (
    # -- simple lookups ----------------------------------------------------- #
    ("When did Flamengo last play Corinthians, and what was the score?",
     "last_meeting", {"team_a": "Flamengo", "team_b": "Corinthians"}),
    ("Show me all Flamengo vs Fluminense matches",
     "head_to_head", {"team_a": "Flamengo", "team_b": "Fluminense", "limit": 10}),
    ("What matches did Palmeiras play in 2023?",
     "search_matches", {"team": "Palmeiras", "season": 2023, "limit": 10}),
    ("Find all Copa do Brasil finals",
     "search_matches", {"competition": "Copa do Brasil", "stage": "final",
                        "limit": 15}),
    ("Who is Gabriel Barbosa?", "player_profile", {"name": "Gabriel Barbosa"}),
    ("Which clubs are called Atlético?", "find_teams", {"query": "atletico"}),

    # -- team questions ----------------------------------------------------- #
    ("What is Corinthians' home record in 2022?",
     "team_statistics", {"team": "Corinthians", "season": 2022,
                         "competition": "Brasileirão", "venue": "home"}),
    ("Which team scored the most goals in Série A 2023?",
     "team_rankings", {"metric": "goals_for", "competition": "Brasileirão",
                       "season": 2023, "limit": 5}),
    ("Compare Palmeiras and Santos head-to-head",
     "compare_teams", {"team_a": "Palmeiras", "team_b": "Santos"}),
    ("What competitions has Palmeiras played in?",
     "team_profile", {"team": "Palmeiras"}),
    ("How does São Paulo perform at home versus away?",
     "home_away_split", {"team": "São Paulo", "competition": "Brasileirão"}),

    # -- player questions --------------------------------------------------- #
    ("Who are the top Brazilian players in the dataset?",
     "search_players", {"nationality": "Brazil", "limit": 10}),
    ("Brazilian players at Brazilian clubs?",
     "players_by_club", {"nationality": "Brazil", "limit": 10}),
    ("Who are the highest-rated players at Grêmio?",
     "club_squad", {"club": "Grêmio", "limit": 10}),
    ("Show me all forwards from Santos",
     "search_players", {"club": "Santos", "position": "forward", "limit": 10}),
    ("Which young Brazilian players have the highest potential?",
     "search_players", {"nationality": "Brazil", "max_age": 21,
                        "sort_by": "potential", "limit": 10}),

    # -- competition questions ---------------------------------------------- #
    ("Who won the 2019 Brasileirão?",
     "standings", {"competition": "Brasileirão", "season": 2019}),
    ("Which teams were relegated in 2020?",
     "standings", {"competition": "Brasileirão", "season": 2020}),
    ("Show the 2018 Copa Libertadores bracket",
     "knockout_bracket", {"competition": "Libertadores", "season": 2018}),
    ("What does the dataset cover?", "list_competitions", {}),
    ("How did the 2019 Copa do Brasil play out?",
     "competition_summary", {"competition": "Copa do Brasil", "season": 2019}),

    # -- analytical questions ----------------------------------------------- #
    ("What's the average goals per match in the Brasileirão?",
     "competition_summary", {"competition": "Brasileirão"}),
    ("Which team has the best home record?",
     "team_rankings", {"metric": "win_rate", "venue": "home",
                       "competition": "Brasileirão", "min_matches": 100,
                       "limit": 5}),
    ("Which team has the best away record?",
     "team_rankings", {"metric": "win_rate", "venue": "away",
                       "competition": "Brasileirão", "min_matches": 100,
                       "limit": 5}),
    ("Show me the biggest wins in the dataset",
     "biggest_wins", {"limit": 10}),
    ("Compare the 2018 and 2019 seasons",
     "compare_seasons", {"competition": "Brasileirão", "seasons": [2018, 2019]}),
    ("Show me all derbies in 2023", "derbies", {"season": 2023, "limit": 15}),
    ("What are the overall statistics of the dataset?",
     "dataset_statistics", {}),
)


def answer(question_entry: tuple[str, str, dict]) -> str:
    """Answer one sample question by invoking its MCP tool."""
    _, tool_name, kwargs = question_entry
    tool = getattr(server, tool_name)
    return tool(**kwargs)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    needle = argv[0].lower() if argv else ""

    start = time.perf_counter()
    server.get_graph()
    print(f"# knowledge graph loaded in {time.perf_counter() - start:.2f}s\n")

    for entry in SAMPLE_QUESTIONS:
        question = entry[0]
        if needle and needle not in question.lower():
            continue
        began = time.perf_counter()
        response = answer(entry)
        elapsed = time.perf_counter() - began
        print("=" * 78)
        print(f"Q: {question}   [{entry[1]} - {elapsed:.3f}s]")
        print("-" * 78)
        print(response)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
