"""
Context
=======
Module: bsoccer.cli
Purpose: A thin command-line front end over bsoccer.queries for manual
         exploration and demos without an MCP client. Mirrors the MCP tools.

Examples
--------
  python -m bsoccer.cli matches --team Flamengo --opponent Fluminense
  python -m bsoccer.cli record --team Corinthians --season 2022 --venue home
  python -m bsoccer.cli h2h Palmeiras Santos
  python -m bsoccer.cli players --nationality Brazil --min-overall 85
  python -m bsoccer.cli standings --competition Brasileirão --season 2019
  python -m bsoccer.cli stats --competition Brasileirão
"""

from __future__ import annotations

import argparse

from . import format as fmt
from .data import get_data
from .queries import QueryEngine


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bsoccer", description="Brazilian Soccer data CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("matches", help="find matches")
    m.add_argument("--team")
    m.add_argument("--opponent")
    m.add_argument("--competition")
    m.add_argument("--season", type=int)
    m.add_argument("--from", dest="date_from")
    m.add_argument("--to", dest="date_to")
    m.add_argument("--side", default="either", choices=["home", "away", "either"])
    m.add_argument("--limit", type=int, default=20)

    r = sub.add_parser("record", help="team record")
    r.add_argument("--team", required=True)
    r.add_argument("--competition")
    r.add_argument("--season", type=int)
    r.add_argument("--venue", default="all", choices=["all", "home", "away"])

    h = sub.add_parser("h2h", help="head to head")
    h.add_argument("team_a")
    h.add_argument("team_b")
    h.add_argument("--competition")

    pl = sub.add_parser("players", help="search players")
    pl.add_argument("--name")
    pl.add_argument("--nationality")
    pl.add_argument("--club")
    pl.add_argument("--position")
    pl.add_argument("--min-overall", dest="min_overall", type=int)
    pl.add_argument("--limit", type=int, default=15)

    st = sub.add_parser("standings", help="competition standings")
    st.add_argument("--competition", default="Brasileirão")
    st.add_argument("--season", type=int)
    st.add_argument("--top", type=int)

    ch = sub.add_parser("champion", help="season champion")
    ch.add_argument("--competition", default="Brasileirão")
    ch.add_argument("--season", type=int)

    sub.add_parser("seasons", help="list competitions and seasons")

    ss = sub.add_parser("stats", help="competition statistics")
    ss.add_argument("--competition")
    ss.add_argument("--season", type=int)

    bw = sub.add_parser("biggest", help="biggest wins")
    bw.add_argument("--competition")
    bw.add_argument("--season", type=int)
    bw.add_argument("--limit", type=int, default=10)

    return p


def run(argv: list[str] | None = None) -> str:
    args = build_parser().parse_args(argv)
    eng = QueryEngine(get_data())

    if args.cmd == "matches":
        return fmt.format_matches(eng.find_matches(
            args.team, args.opponent, args.competition, args.season,
            args.date_from, args.date_to, args.side, args.limit))
    if args.cmd == "record":
        return fmt.format_record(eng.team_record(
            args.team, args.competition, args.season, args.venue))
    if args.cmd == "h2h":
        return fmt.format_head_to_head(eng.head_to_head(
            args.team_a, args.team_b, args.competition))
    if args.cmd == "players":
        return fmt.format_players(eng.search_players(
            args.name, args.nationality, args.club, args.position,
            args.min_overall, limit=args.limit))
    if args.cmd == "standings":
        return fmt.format_standings(eng.standings(
            args.competition, args.season, args.top))
    if args.cmd == "champion":
        return fmt.format_champion(eng.champion(args.competition, args.season))
    if args.cmd == "seasons":
        res = eng.seasons_available()
        return ("Competitions: " + ", ".join(res["competitions"]) +
                "\nSeasons: " + ", ".join(str(s) for s in res["seasons"]))
    if args.cmd == "stats":
        return fmt.format_competition_stats(eng.competition_stats(
            args.competition, args.season))
    if args.cmd == "biggest":
        return fmt.format_biggest_wins(eng.biggest_wins(
            args.competition, args.season, args.limit))
    return "Unknown command"


def main() -> None:
    print(run())


if __name__ == "__main__":
    main()
