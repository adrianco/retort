"""
Command-line demo for the Brazilian Soccer knowledge graph.

Context
-------
A thin CLI over :class:`knowledge_graph.KnowledgeGraph` that exercises the same
query functions the MCP server exposes, without needing an MCP client.  Useful
for manual exploration and for quickly confirming the data layer answers the
specification's sample questions.

Usage
-----
    python demo.py                      # run a scripted tour of sample queries
    python demo.py standings Brasileirao 2019
    python demo.py matches Flamengo --opponent Fluminense
    python demo.py h2h Palmeiras Santos
    python demo.py team Corinthians --season 2019 --competition Brasileirao
    python demo.py players --nationality Brazil --club Santos
    python demo.py top-brazilians 10
    python demo.py avg-goals --competition Brasileirao
    python demo.py biggest-wins --competition Brasileirao
"""

from __future__ import annotations

import argparse

import formatters as fmt
from knowledge_graph import KnowledgeGraph


def _tour(kg: KnowledgeGraph) -> None:
    """Print answers to a representative selection of the spec's questions."""
    sections = [
        ("Who won the 2019 Brasileirao?",
         fmt.format_standings(kg.standings("Brasileirao", 2019), "Brasileirao", 2019)),
        ("Flamengo vs Fluminense (Fla-Flu) head-to-head",
         fmt.format_head_to_head(kg.head_to_head("Flamengo", "Fluminense"))),
        ("Corinthians 2019 Brasileirao record",
         fmt.format_team_record(kg.team_record("Corinthians", season=2019,
                                               competition="Brasileirao"))),
        ("Top Brazilian players",
         fmt.format_players(kg.top_brazilian_players(8),
                            header="Top-rated Brazilian players:")),
        ("Brazilian players by club",
         fmt.format_players_by_club(kg.brazilian_players_by_club(8),
                                    header="Brazilian players by club:")),
        ("Average goals in the Brasileirao",
         fmt.format_average_goals(kg.average_goals(competition="Brasileirao"))),
        ("Biggest victories",
         fmt.format_matches(kg.biggest_wins(limit=8), limit=8,
                            header="Biggest victories in dataset:")),
    ]
    for title, body in sections:
        print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")
        print(body)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Brazilian Soccer KG demo")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("standings"); p.add_argument("competition"); p.add_argument("season", type=int)
    p = sub.add_parser("matches"); p.add_argument("team")
    p.add_argument("--opponent"); p.add_argument("--competition")
    p.add_argument("--season", type=int); p.add_argument("--limit", type=int, default=20)
    p = sub.add_parser("h2h"); p.add_argument("team1"); p.add_argument("team2")
    p = sub.add_parser("team"); p.add_argument("team")
    p.add_argument("--season", type=int); p.add_argument("--competition")
    p.add_argument("--venue", default="either")
    p = sub.add_parser("players")
    p.add_argument("--name"); p.add_argument("--nationality"); p.add_argument("--club")
    p.add_argument("--position"); p.add_argument("--min-overall", type=int)
    p.add_argument("--limit", type=int, default=25)
    p = sub.add_parser("top-brazilians"); p.add_argument("limit", type=int, nargs="?", default=10)
    p = sub.add_parser("avg-goals"); p.add_argument("--competition"); p.add_argument("--season", type=int)
    p = sub.add_parser("biggest-wins"); p.add_argument("--competition"); p.add_argument("--season", type=int)
    p.add_argument("--limit", type=int, default=10)

    args = parser.parse_args(argv)
    kg = KnowledgeGraph.load()

    if args.cmd is None:
        _tour(kg)
    elif args.cmd == "standings":
        print(fmt.format_standings(kg.standings(args.competition, args.season),
                                   args.competition, args.season))
    elif args.cmd == "matches":
        ms = kg.find_matches(team=args.team, opponent=args.opponent,
                             competition=args.competition, season=args.season)
        print(fmt.format_matches(ms, limit=args.limit, header="Matches:"))
    elif args.cmd == "h2h":
        print(fmt.format_head_to_head(kg.head_to_head(args.team1, args.team2)))
    elif args.cmd == "team":
        print(fmt.format_team_record(kg.team_record(
            args.team, season=args.season, competition=args.competition, venue=args.venue)))
    elif args.cmd == "players":
        ms = kg.find_players(name=args.name, nationality=args.nationality,
                             club=args.club, position=args.position,
                             min_overall=args.min_overall, limit=args.limit)
        print(fmt.format_players(ms, header="Players:"))
    elif args.cmd == "top-brazilians":
        print(fmt.format_players(kg.top_brazilian_players(args.limit),
                                 header="Top-rated Brazilian players:"))
    elif args.cmd == "avg-goals":
        print(fmt.format_average_goals(kg.average_goals(
            competition=args.competition, season=args.season)))
    elif args.cmd == "biggest-wins":
        print(fmt.format_matches(kg.biggest_wins(
            competition=args.competition, season=args.season, limit=args.limit),
            limit=args.limit, header="Biggest victories:"))


if __name__ == "__main__":
    main()
