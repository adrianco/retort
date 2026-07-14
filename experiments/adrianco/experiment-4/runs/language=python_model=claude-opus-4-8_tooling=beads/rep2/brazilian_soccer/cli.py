"""
================================================================================
Brazilian Soccer MCP Server :: cli
================================================================================

Context
-------
A tiny command-line front-end over the QueryEngine for manual exploration and
demos without needing a full MCP client. It mirrors the most common tools and
prints the human-readable formatter output.

Examples
--------
  python -m brazilian_soccer.cli matches --team Flamengo --opponent Fluminense
  python -m brazilian_soccer.cli record --team Corinthians --season 2022 --venue home
  python -m brazilian_soccer.cli standings --competition "Brasileirão Série A" --season 2019
  python -m brazilian_soccer.cli players --nationality Brazil --limit 10
  python -m brazilian_soccer.cli stats --competition "Brasileirão Série A"
================================================================================
"""

from __future__ import annotations

import argparse
import json

from .data_loader import parse_date
from .knowledge_graph import KnowledgeGraph
from .queries import (
    QueryEngine,
    format_matches,
    format_players,
    format_standings,
    format_team_record,
)


def _engine() -> QueryEngine:
    return QueryEngine(KnowledgeGraph.from_data_dir())


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Brazilian Soccer knowledge-graph CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("matches", help="find matches")
    m.add_argument("--team")
    m.add_argument("--opponent")
    m.add_argument("--competition")
    m.add_argument("--season", type=int)
    m.add_argument("--start-date")
    m.add_argument("--end-date")
    m.add_argument("--venue", default="either")
    m.add_argument("--limit", type=int, default=20)

    r = sub.add_parser("record", help="team record")
    r.add_argument("--team", required=True)
    r.add_argument("--season", type=int)
    r.add_argument("--competition")
    r.add_argument("--venue", default="either")

    s = sub.add_parser("standings", help="league standings")
    s.add_argument("--competition", required=True)
    s.add_argument("--season", type=int, required=True)

    pl = sub.add_parser("players", help="search players")
    pl.add_argument("--name")
    pl.add_argument("--nationality")
    pl.add_argument("--club")
    pl.add_argument("--position")
    pl.add_argument("--min-overall", type=int)
    pl.add_argument("--limit", type=int, default=25)

    st = sub.add_parser("stats", help="competition statistics")
    st.add_argument("--competition")
    st.add_argument("--season", type=int)

    h = sub.add_parser("h2h", help="head-to-head")
    h.add_argument("--team-a", required=True)
    h.add_argument("--team-b", required=True)

    args = p.parse_args(argv)
    eng = _engine()

    if args.cmd == "matches":
        res = eng.find_matches(
            team=args.team, opponent=args.opponent, competition=args.competition,
            season=args.season, start_date=parse_date(args.start_date),
            end_date=parse_date(args.end_date), venue=args.venue, limit=args.limit,
        )
        print(format_matches(res))
    elif args.cmd == "record":
        res = eng.team_record(args.team, season=args.season,
                              competition=args.competition, venue=args.venue)
        print(format_team_record(res))
    elif args.cmd == "standings":
        print(format_standings(eng.standings(args.competition, args.season)))
    elif args.cmd == "players":
        res = eng.search_players(
            name=args.name, nationality=args.nationality, club=args.club,
            position=args.position, min_overall=args.min_overall, limit=args.limit,
        )
        print(format_players(res))
    elif args.cmd == "stats":
        print(json.dumps(eng.competition_stats(competition=args.competition,
                                               season=args.season), indent=2,
                         ensure_ascii=False))
    elif args.cmd == "h2h":
        print(json.dumps(eng.head_to_head(args.team_a, args.team_b)["summary"],
                         indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
