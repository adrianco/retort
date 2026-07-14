"""Demonstration runner: answers a battery of sample questions.

Run ``python -m brazilian_soccer.demo`` to see the knowledge graph answer the
sample questions from the specification using the bundled data.
"""
from __future__ import annotations

from typing import Callable, List, Tuple

from .server import SoccerService

# Each entry is (question text, lambda(service) -> answer text).
SAMPLE_QUESTIONS: List[Tuple[str, Callable[[SoccerService], str]]] = [
    ("Show me all Flamengo vs Fluminense matches",
     lambda s: s.search_matches(team="Flamengo", team2="Fluminense")),
    ("What matches did Palmeiras play in 2023?",
     lambda s: s.search_matches(team="Palmeiras", season=2023)),
    ("Find all Copa do Brasil matches in 2019",
     lambda s: s.search_matches(competition="Copa do Brasil", season=2019)),
    ("When did Flamengo last play Corinthians?",
     lambda s: s.search_matches(team="Flamengo", team2="Corinthians")),
    ("Flamengo vs Fluminense head-to-head",
     lambda s: s.head_to_head("Flamengo", "Fluminense")),
    ("Compare Palmeiras and Santos head-to-head",
     lambda s: s.head_to_head("Palmeiras", "Santos")),
    ("What is Corinthians' home record in 2022?",
     lambda s: s.team_record("Corinthians", season=2022,
                             competition="Brasileirão", venue="home")),
    ("What is Flamengo's record in the 2019 Brasileirão?",
     lambda s: s.team_record("Flamengo", season=2019, competition="Brasileirão")),
    ("What is Santos' away record in 2019?",
     lambda s: s.team_record("Santos", season=2019,
                             competition="Brasileirão", venue="away")),
    ("Find all Brazilian players in the dataset (top 10)",
     lambda s: s.search_players(nationality="Brazil", limit=10)),
    ("Who are the highest-rated players at Flamengo?",
     lambda s: s.search_players(club="Flamengo")),
    ("Who is Neymar?",
     lambda s: s.search_players(name="Neymar")),
    ("Show me all forwards (ST) rated 85+",
     lambda s: s.search_players(position="ST", min_overall=85)),
    ("Show me goalkeepers rated 88+",
     lambda s: s.search_players(position="GK", min_overall=88)),
    ("Who won the 2019 Brasileirão?",
     lambda s: s.competition_champion("Brasileirão", 2019)),
    ("Who won the 2018 Brasileirão?",
     lambda s: s.competition_champion("Brasileirão", 2018)),
    ("Show the 2019 Brasileirão final standings",
     lambda s: s.standings("Brasileirão", 2019, limit=10)),
    ("Show the 2017 Brasileirão final standings",
     lambda s: s.standings("Brasileirão", 2017, limit=10)),
    ("What's the average goals per match in the 2019 Brasileirão?",
     lambda s: s.statistics(competition="Brasileirão", season=2019)),
    ("What are the biggest wins and key stats in the 2018 Brasileirão?",
     lambda s: s.statistics(competition="Brasileirão", season=2018)),
    ("Compare the 2018 and 2019 Brasileirão seasons",
     lambda s: s.statistics(competition="Brasileirão", season=2018)
     + "\n---\n" + s.statistics(competition="Brasileirão", season=2019)),
    ("What competitions has Palmeiras played in (2019)?",
     lambda s: s.search_matches(team="Palmeiras", season=2019)),
]


def run_question(service: SoccerService, item: Tuple[str, Callable]) -> str:
    question, fn = item
    return f"Q: {question}\n{fn(service)}"


def run_all(service: SoccerService) -> str:
    blocks = [run_question(service, item) for item in SAMPLE_QUESTIONS]
    return ("\n\n" + "=" * 70 + "\n\n").join(blocks)


def main() -> None:
    service = SoccerService.from_data_dir()
    print(run_all(service))


if __name__ == "__main__":
    main()
