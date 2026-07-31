"""Offline driver for the query layer -- exercise the server without a client.

Context
-------
``python -m brazilian_soccer.cli demo`` answers the sample questions from
``TASK.md`` in one pass (also used as a smoke test), while the other
sub-commands map one-to-one onto the MCP tools so behaviour can be inspected
from a terminal.

Examples::

    python -m brazilian_soccer.cli overview
    python -m brazilian_soccer.cli h2h Flamengo Fluminense
    python -m brazilian_soccer.cli standings 2019
    python -m brazilian_soccer.cli players --nationality Brazil --limit 5
"""

from __future__ import annotations

import argparse
import time

from .formatting import (
    format_head_to_head,
    format_matches,
    format_player,
    format_players,
    format_record,
    format_standings,
    format_stats,
    format_team_profile,
)
from .queries import SoccerQueries

#: (question, callable) pairs -- the spec asks for at least 20 answerable ones.
DEMO_QUESTIONS = [
    (
        "Show me all Flamengo vs Fluminense matches",
        lambda q: format_head_to_head(q.head_to_head("Flamengo", "Fluminense"), limit=5),
    ),
    (
        "What matches did Palmeiras play in 2023?",
        lambda q: format_matches(
            q.search_matches(team="Palmeiras", season=2023, limit=None),
            "Palmeiras 2023:",
            limit=5,
        ),
    ),
    (
        "Find all Copa do Brasil finals",
        lambda q: format_matches(
            q.search_matches(competition="Copa do Brasil", stage="final", limit=None),
            "Copa do Brasil finals in the dataset:",
            limit=8,
        ),
    ),
    (
        "When did Flamengo last play Corinthians, and what was the score?",
        lambda q: format_matches(
            [q.last_meeting("Flamengo", "Corinthians")], "Last Flamengo-Corinthians:"
        ),
    ),
    (
        "What is Corinthians' home record in 2022?",
        lambda q: format_record(
            q.team_record(
                "Corinthians",
                season=2022,
                competition="Brasileirão Série A",
                venue="home",
            ),
            "Corinthians home record (2022 Brasileirão)",
        ),
    ),
    (
        "Which team scored the most goals in Serie A 2023?",
        lambda q: format_record(
            (top := q.top_scoring_teams("Brasileirão Série A", 2023, limit=1)[0]),
            f"Top scoring team of the 2023 Brasileirão Série A: {top.team_name}",
        ),
    ),
    (
        "Compare Palmeiras and Santos head-to-head",
        lambda q: format_head_to_head(q.head_to_head("Palmeiras", "Santos"), limit=3),
    ),
    (
        "Who won the 2019 Brasileirão?",
        lambda q: _champion(q, "Brasileirão Série A", 2019),
    ),
    (
        "Which teams were relegated in 2020?",
        lambda q: "\n".join(
            f"- {r['team']}: {r['points']} pts"
            for r in q.relegated(2020)["relegated"]
        ),
    ),
    (
        "Show the 2019 Copa Libertadores knockout bracket",
        lambda q: "\n".join(
            f"{stage}: {len(matches)} matches"
            for stage, matches in q.season_bracket("Copa Libertadores", 2019)["stages"].items()
        ),
    ),
    (
        "What's the average goals per match in the Brasileirão?",
        lambda q: format_stats(q.competition_stats("Brasileirão Série A")),
    ),
    (
        "Which team has the best away record?",
        lambda q: _ranking(q),
    ),
    (
        "Show me the biggest wins in the dataset",
        lambda q: format_matches(q.biggest_wins(limit=5), "Biggest victories:", limit=5),
    ),
    (
        "Who is Gabriel Barbosa?",
        lambda q: _player_answer(q, "Gabriel Barbosa"),
    ),
    (
        "Who is Thiago Silva?",
        lambda q: _player_answer(q, "Thiago Silva"),
    ),
    (
        "Find the top Brazilian players in the dataset",
        lambda q: format_players(
            q.search_players(nationality="Brazil", limit=5), "Top Brazilian players:"
        ),
    ),
    (
        "Which players play for Gremio?",
        lambda q: format_players(
            q.search_players(club="Gremio", limit=5), "Gremio squad (FIFA data):"
        ),
    ),
    (
        "Show me all forwards (ST) at Santos",
        lambda q: format_players(
            q.search_players(club="Santos", position="ST", limit=5), "Santos strikers:"
        ),
    ),
    (
        "What competitions has Palmeiras played in?",
        lambda q: format_team_profile(q.team_profile("Palmeiras")),
    ),
    (
        "Show me all derbies in 2023",
        lambda q: "\n".join(
            f"- [{row['derby']}] {row['match'].home_name} vs {row['match'].away_name}"
            for row in q.derbies(season=2023, limit=6)
        ),
    ),
    (
        "Compare the 2018 and 2019 seasons",
        lambda q: "\n\n".join(
            format_stats(s)
            for s in q.compare_seasons([2018, 2019], "Brasileirão Série A")
        ),
    ),
    (
        "Which teams had the best home record in 2022?",
        lambda q: "\n".join(
            f"- {r.team_name}: {r.points_per_game:.2f} pts/game"
            for r in q.best_records(season=2022, venue="home", limit=5)
        ),
    ),
    (
        "How many players from Brazil are in the FIFA dataset, and where do they play?",
        lambda q: "\n".join(
            f"- {row['club']}: {row['players']} players (avg {row['average_overall']})"
            for row in q.players_by_nationality_at_clubs("Brazil", limit=5)
        ),
    ),
]


def _player_answer(queries: SoccerQueries, name: str) -> str:
    result = queries.lookup_player(name)
    if result["player"] is None:
        return f"No player matching '{name}' in the FIFA dataset."
    prefix = (
        ""
        if result["exact"]
        else f"No exact match for '{name}' (FIFA 19 snapshot). Closest match:\n"
    )
    return prefix + format_player(result["player"], detailed=True)


def _champion(queries: SoccerQueries, competition: str, season: int) -> str:
    result = queries.champion(competition, season)
    return f"{result['champion']} ({result['basis']})"


def _ranking(queries: SoccerQueries) -> str:
    return "\n".join(
        f"- {r.team_name}: {r.points_per_game:.2f} pts/game away ({r.played} away matches)"
        for r in queries.best_records(venue="away", min_matches=50, limit=5)
    )


def run_demo(queries: SoccerQueries) -> None:
    for index, (question, answer) in enumerate(DEMO_QUESTIONS, start=1):
        started = time.perf_counter()
        text = answer(queries)
        elapsed = time.perf_counter() - started
        print(f"\n=== Q{index}. {question}   [{elapsed * 1000:.0f} ms]")
        print(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="brazilian_soccer.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("demo", help="answer the sample questions from TASK.md")
    subparsers.add_parser("overview", help="dataset coverage summary")

    matches = subparsers.add_parser("matches", help="search matches")
    matches.add_argument("--team")
    matches.add_argument("--opponent")
    matches.add_argument("--competition")
    matches.add_argument("--season", type=int)
    matches.add_argument("--venue", default="any", choices=["any", "home", "away"])
    matches.add_argument("--stage")
    matches.add_argument("--limit", type=int, default=20)

    h2h = subparsers.add_parser("h2h", help="head-to-head between two clubs")
    h2h.add_argument("team_a")
    h2h.add_argument("team_b")

    team = subparsers.add_parser("team", help="club profile")
    team.add_argument("name")

    table = subparsers.add_parser("standings", help="league table for a season")
    table.add_argument("season", type=int)
    table.add_argument("--competition", default="Brasileirão Série A")

    players = subparsers.add_parser("players", help="search the FIFA player table")
    players.add_argument("--name")
    players.add_argument("--nationality")
    players.add_argument("--club")
    players.add_argument("--position")
    players.add_argument("--min-overall", type=int)
    players.add_argument("--limit", type=int, default=15)

    stats = subparsers.add_parser("stats", help="competition statistics")
    stats.add_argument("--competition")
    stats.add_argument("--season", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    queries = SoccerQueries()

    if args.command == "demo":
        run_demo(queries)
    elif args.command == "overview":
        overview = queries.dataset_overview()
        for key, value in overview.items():
            print(f"{key}: {value}")
    elif args.command == "matches":
        found = queries.search_matches(
            team=args.team,
            opponent=args.opponent,
            competition=args.competition,
            season=args.season,
            venue=args.venue,
            stage=args.stage,
            limit=None,
        )
        print(format_matches(found, f"{len(found)} matches:", limit=args.limit))
    elif args.command == "h2h":
        print(format_head_to_head(queries.head_to_head(args.team_a, args.team_b)))
    elif args.command == "team":
        print(format_team_profile(queries.team_profile(args.name)))
    elif args.command == "standings":
        table = queries.standings(args.competition, args.season)
        print(format_standings(table, args.competition, args.season))
    elif args.command == "players":
        found = queries.search_players(
            name=args.name,
            nationality=args.nationality,
            club=args.club,
            position=args.position,
            min_overall=args.min_overall,
            limit=args.limit,
        )
        print(format_players(found, f"{len(found)} players:", limit=args.limit))
    elif args.command == "stats":
        print(format_stats(queries.competition_stats(args.competition, args.season)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
