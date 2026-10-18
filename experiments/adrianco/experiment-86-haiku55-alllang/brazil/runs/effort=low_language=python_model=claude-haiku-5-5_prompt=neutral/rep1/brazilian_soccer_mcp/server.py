# Context: MCP server over stdio (newline-delimited JSON-RPC 2.0). Implements initialize,
# tools/list and tools/call, which is all an LLM client needs to call the soccer tools. Each tool
# maps a structured request onto a SoccerKnowledgeBase query and returns formatted text.
# Run with: python -m brazilian_soccer_mcp.server [--data-dir PATH]

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, TextIO

from . import formatting as fmt
from .data import BRASILEIRAO_LABEL, parse_date
from .queries import SoccerKnowledgeBase
from .names import resolve_competition

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "brazilian-soccer-mcp", "version": "1.0.0"}
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

_COMPETITION = {
    "type": "string",
    "description": "Competition, e.g. 'Brasileirão' / 'Serie A', 'Serie B', 'Copa do Brasil', 'Libertadores'.",
}
_SEASON = {"type": "integer", "description": "Season year, e.g. 2023."}
_VENUE = {"type": "string", "enum": ["any", "home", "away"], "description": "Which side the team played on."}
_LIMIT = {"type": "integer", "minimum": 1, "maximum": 200, "description": "Maximum results to return."}
_DATE = {"type": "string", "description": "ISO (2023-09-03) or Brazilian (03/09/2023) date."}


def _schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or []}


class SoccerTools:
    """Tool registry bound to a loaded knowledge base."""

    def __init__(self, kb: SoccerKnowledgeBase):
        self.kb = kb
        self._tools: dict[str, tuple[dict[str, Any], Callable[[dict[str, Any]], str]]] = {
            "find_matches": (
                {
                    "description": "Find matches by team, opponent, date range, competition, season and venue.",
                    "inputSchema": _schema({
                        "team": {"type": "string"}, "opponent": {"type": "string"},
                        "start_date": _DATE, "end_date": _DATE, "competition": _COMPETITION,
                        "season": _SEASON, "venue": _VENUE, "limit": _LIMIT,
                    }),
                },
                self._find_matches,
            ),
            "team_record": (
                {
                    "description": "Wins, draws, losses, goals and win rate for a team, optionally by season, competition or venue.",
                    "inputSchema": _schema({
                        "team": {"type": "string"}, "season": _SEASON, "competition": _COMPETITION,
                        "venue": _VENUE, "start_date": _DATE, "end_date": _DATE,
                    }, ["team"]),
                },
                self._team_record,
            ),
            "head_to_head": (
                {
                    "description": "Head-to-head record between two teams in the match data.",
                    "inputSchema": _schema({
                        "team": {"type": "string"}, "opponent": {"type": "string"},
                        "competition": _COMPETITION,
                    }, ["team", "opponent"]),
                },
                self._head_to_head,
            ),
            "standings": (
                {
                    "description": "League table for a season calculated from match results (3 points for a win).",
                    "inputSchema": _schema({
                        "season": _SEASON, "competition": _COMPETITION,
                        "relegation_places": {"type": "integer", "minimum": 0, "description": "Bottom places to mark as relegated."},
                    }, ["season"]),
                },
                self._standings,
            ),
            "season_stats": (
                {
                    "description": "Aggregate statistics: goals per match, home/draw/away rates.",
                    "inputSchema": _schema({"season": _SEASON, "competition": _COMPETITION}),
                },
                self._season_stats,
            ),
            "biggest_wins": (
                {
                    "description": "Matches with the largest winning margins.",
                    "inputSchema": _schema({"season": _SEASON, "competition": _COMPETITION, "limit": _LIMIT}),
                },
                self._biggest_wins,
            ),
            "venue_ranking": (
                {
                    "description": "Teams ranked by win rate at home or away. Defaults to the Brasileirão Série A.",
                    "inputSchema": _schema({
                        "venue": {"type": "string", "enum": ["home", "away"]},
                        "season": _SEASON, "competition": _COMPETITION,
                        "min_matches": {"type": "integer", "minimum": 1},
                        "limit": _LIMIT,
                    }, ["venue"]),
                },
                self._venue_ranking,
            ),
            "search_players": (
                {
                    "description": "Search FIFA player data by (partial) name, highest overall first.",
                    "inputSchema": _schema({"name": {"type": "string"}, "limit": _LIMIT}, ["name"]),
                },
                self._search_players,
            ),
            "list_players": (
                {
                    "description": "Filter players by nationality, club, and position (goalkeeper, defender, midfielder, forward or a position code like ST).",
                    "inputSchema": _schema({
                        "nationality": {"type": "string"}, "club": {"type": "string"},
                        "position": {"type": "string"}, "limit": _LIMIT,
                    }),
                },
                self._list_players,
            ),
            "club_profile": (
                {
                    "description": "Squad size, average rating and top players for a club in the player data.",
                    "inputSchema": _schema({"team": {"type": "string"}}, ["team"]),
                },
                self._club_profile,
            ),
        }

    def describe(self) -> list[dict[str, Any]]:
        return [{"name": name, **meta} for name, (meta, _) in self._tools.items()]

    def call(self, name: str, arguments: dict[str, Any]) -> str:
        if name not in self._tools:
            raise ValueError(f"Unknown tool: {name}")
        _, handler = self._tools[name]
        return handler(arguments)

    # ---- handlers -------------------------------------------------------

    @staticmethod
    def _date(args: dict[str, Any], key: str):
        return parse_date(args[key]) if args.get(key) else None

    def _find_matches(self, args):
        all_matches = self.kb.find_matches(
            team=args.get("team"), opponent=args.get("opponent"),
            start=self._date(args, "start_date"), end=self._date(args, "end_date"),
            competition=args.get("competition"), season=args.get("season"),
            venue=args.get("venue", "any"), limit=None,
        )
        limit = int(args.get("limit") or 50)
        return fmt.format_matches("Matches found:", all_matches[:limit], total=len(all_matches))

    def _team_record(self, args):
        record = self.kb.team_record(
            args["team"], season=args.get("season"), competition=args.get("competition"),
            venue=args.get("venue", "any"), start=self._date(args, "start_date"),
            end=self._date(args, "end_date"),
        )
        scope = " ".join(
            part for part in (
                str(args["season"]) if args.get("season") else "",
                resolve_competition(args["competition"]) if args.get("competition") else "",
                f"({args['venue']} only)" if args.get("venue") not in (None, "any") else "",
            ) if part
        )
        return fmt.format_record(record, f"record{' (' + scope + ')' if scope else ''}")

    def _head_to_head(self, args):
        h2h = self.kb.head_to_head(args["team"], args["opponent"], competition=args.get("competition"))
        return fmt.format_head_to_head(h2h)

    def _standings(self, args):
        competition = args.get("competition") or BRASILEIRAO_LABEL
        title = f"{args['season']} {resolve_competition(competition)} standings (calculated from matches):"
        rows = self.kb.standings(int(args["season"]), competition)
        return fmt.format_standings(title, rows, relegation_places=int(args.get("relegation_places") or 0))

    def _season_stats(self, args):
        stats = self.kb.season_stats(season=args.get("season"), competition=args.get("competition"))
        label = " ".join(str(p) for p in (args.get("competition") or "", args.get("season") or "") if p)
        return fmt.format_season_stats(f"Statistics ({label or 'all data'}):", stats)

    def _biggest_wins(self, args):
        matches = self.kb.biggest_wins(
            competition=args.get("competition"), season=args.get("season"),
            limit=int(args.get("limit") or 5),
        )
        return fmt.format_matches("Biggest wins in dataset:", matches)

    def _venue_ranking(self, args):
        records = self.kb.venue_ranking(
            args["venue"], season=args.get("season"),
            competition=args.get("competition") or BRASILEIRAO_LABEL,
            min_matches=int(args.get("min_matches") or 10),
        )
        limit = int(args.get("limit") or 10)
        title = f"Best {args['venue']} win rates:"
        return fmt.format_venue_ranking(title, records[:limit])

    def _search_players(self, args):
        players = self.kb.search_players(args["name"], limit=int(args.get("limit") or 20))
        return fmt.format_players(f"Players matching '{args['name']}':", players)

    def _list_players(self, args):
        players = self.kb.list_players(
            nationality=args.get("nationality"), club=args.get("club"),
            position=args.get("position"), limit=int(args.get("limit") or 20),
        )
        return fmt.format_players("Players found:", players)

    def _club_profile(self, args):
        club, squad = self.kb.club_profile(args["team"])
        return fmt.format_club_profile(club, squad)


def handle_message(message: dict[str, Any], tools: SoccerTools) -> dict[str, Any] | None:
    """Handle one JSON-RPC message. Returns the response, or None for notifications."""
    method = message.get("method")
    request_id = message.get("id")
    if request_id is None:
        return None  # notifications such as notifications/initialized need no reply

    try:
        if method == "initialize":
            result: Any = {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": tools.describe()}
        elif method == "tools/call":
            params = message.get("params") or {}
            try:
                text = tools.call(params["name"], params.get("arguments") or {})
                result = {"content": [{"type": "text", "text": text}], "isError": False}
            except (KeyError, ValueError, TypeError) as exc:
                result = {"content": [{"type": "text", "text": f"Error: {exc}"}], "isError": True}
        else:
            return {"jsonrpc": "2.0", "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}}
    except Exception as exc:  # keep the server alive on unexpected failures
        return {"jsonrpc": "2.0", "id": request_id,
                "error": {"code": -32603, "message": f"Internal error: {exc}"}}
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def serve(stdin: TextIO, stdout: TextIO, tools: SoccerTools) -> None:
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            response = {"jsonrpc": "2.0", "id": None,
                        "error": {"code": -32700, "message": f"Parse error: {exc}"}}
        else:
            response = handle_message(message, tools)
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Brazilian soccer MCP server (stdio)")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args(argv)
    kb = SoccerKnowledgeBase.load(args.data_dir)
    serve(sys.stdin, sys.stdout, SoccerTools(kb))


if __name__ == "__main__":
    main()
