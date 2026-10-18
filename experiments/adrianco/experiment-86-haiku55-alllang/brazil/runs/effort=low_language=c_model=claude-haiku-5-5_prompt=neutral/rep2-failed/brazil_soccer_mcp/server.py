"""Minimal MCP server (JSON-RPC 2.0 over stdio) exposing Brazilian soccer queries.

Implements the subset of the Model Context Protocol needed for tools:
`initialize`, `ping`, `tools/list`, `tools/call`. No third-party SDK is
required, so the server runs with the Python standard library alone.

`handle_message` is a pure function (message in, response out) so tests can
drive the protocol without spawning a process.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from . import formatting as fmt
from .dataset import Dataset
from .dates import parse_date_arg
from .loaders import SERIES_A

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "brazilian-soccer"
SERVER_VERSION = "0.1.0"
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

_DATE = {"type": "string", "description": "YYYY-MM-DD or DD/MM/YYYY"}
_SEASON = {"type": "integer", "description": "Season year, e.g. 2023"}
_COMPETITION = {
    "type": "string",
    "description": "Competition text, e.g. 'brasileirao serie a', 'brasileirao', 'copa do brasil', 'libertadores'",
}
_TEAM = {"type": "string", "description": "Team name, e.g. 'Flamengo', 'Atletico-MG', 'Palmeiras-SP'"}
_VENUE = {"type": "string", "enum": ["any", "home", "away"]}
_LIMIT = {"type": "integer", "minimum": 1, "maximum": 100}


def _schema(properties: Dict[str, Any], required=()) -> Dict[str, Any]:
    return {"type": "object", "properties": properties, "required": list(required), "additionalProperties": False}


TOOLS = [
    {
        "name": "dataset_info",
        "description": "Describe the loaded datasets: match and player counts, seasons and competitions covered.",
        "inputSchema": _schema({}),
    },
    {
        "name": "search_matches",
        "description": "Find matches by team, opponent, venue, competition, season or date range. Newest first.",
        "inputSchema": _schema(
            {
                "team": _TEAM,
                "opponent": _TEAM,
                "venue": _VENUE,
                "competition": _COMPETITION,
                "season": _SEASON,
                "start_date": _DATE,
                "end_date": _DATE,
                "limit": _LIMIT,
            }
        ),
    },
    {
        "name": "team_record",
        "description": "Win/draw/loss record, goals and win rate for a team, optionally filtered.",
        "inputSchema": _schema(
            {
                "team": _TEAM,
                "venue": _VENUE,
                "competition": _COMPETITION,
                "season": _SEASON,
                "start_date": _DATE,
                "end_date": _DATE,
            },
            required=["team"],
        ),
    },
    {
        "name": "head_to_head",
        "description": "Head-to-head record between two teams across the dataset (or a filtered subset).",
        "inputSchema": _schema(
            {
                "team_a": _TEAM,
                "team_b": _TEAM,
                "competition": _COMPETITION,
                "season": _SEASON,
            },
            required=["team_a", "team_b"],
        ),
    },
    {
        "name": "standings",
        "description": "League table for one season, calculated from match results (3 pts win, 1 draw).",
        "inputSchema": _schema(
            {"season": _SEASON, "competition": {"type": "string", "description": "Default 'brasileirao serie a'"}},
            required=["season"],
        ),
    },
    {
        "name": "league_stats",
        "description": "Aggregate statistics: matches, goals per match, home/draw/away result rates.",
        "inputSchema": _schema({"competition": _COMPETITION, "season": _SEASON}),
    },
    {
        "name": "rank_teams",
        "description": "Rank teams by win_rate, home_win_rate, away_win_rate, goals_for or goal_difference.",
        "inputSchema": _schema(
            {
                "metric": {"type": "string", "enum": ["win_rate", "home_win_rate", "away_win_rate", "goals_for", "goal_difference"]},
                "competition": _COMPETITION,
                "season": _SEASON,
                "min_matches": {"type": "integer", "minimum": 1},
                "limit": _LIMIT,
            },
            required=["metric"],
        ),
    },
    {
        "name": "biggest_wins",
        "description": "Matches with the largest winning margin.",
        "inputSchema": _schema({"competition": _COMPETITION, "season": _SEASON, "limit": _LIMIT}),
    },
    {
        "name": "search_players",
        "description": "Search FIFA player data by name, nationality, club, position or minimum overall rating.",
        "inputSchema": _schema(
            {
                "name": {"type": "string"},
                "nationality": {"type": "string", "description": "e.g. 'Brazil'"},
                "club": {"type": "string", "description": "e.g. 'Flamengo'"},
                "position": {"type": "string", "description": "e.g. 'ST', 'GK'"},
                "min_overall": {"type": "integer"},
                "sort": {"type": "string", "enum": ["overall", "name"]},
                "limit": _LIMIT,
            }
        ),
    },
    {
        "name": "club_summary",
        "description": "Players per club and average overall rating, optionally for one nationality.",
        "inputSchema": _schema({"nationality": {"type": "string"}}),
    },
]


class ToolError(Exception):
    """Raised for bad tool arguments; reported to the client as an error result."""


def _text_result(text: str, is_error: bool = False) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def _dates(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return {"start": parse_date_arg(args.get("start_date")), "end": parse_date_arg(args.get("end_date"))}
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


def _filters(args: Dict[str, Any]) -> Dict[str, Any]:
    out = {"competition": args.get("competition"), "season": args.get("season")}
    out.update(_dates(args))
    return out


class Tools:
    """Dispatches tool calls to the Dataset and formats the answers."""

    def __init__(self, dataset: Dataset):
        self.ds = dataset

    def dispatch(self, name: str, args: Dict[str, Any]) -> str:
        handler: Optional[Callable[[Dict[str, Any]], str]] = getattr(self, f"_tool_{name}", None)
        if handler is None:
            raise ToolError(f"Unknown tool: {name}")
        try:
            return handler(args)
        except (ValueError, KeyError) as exc:
            raise ToolError(str(exc)) from exc

    def _tool_dataset_info(self, args):
        matches = self.ds.matches
        seasons = sorted({m.season for m in matches})
        competitions = sorted({m.competition for m in matches})
        return "\n".join(
            [
                f"Matches: {len(matches)} (seasons {seasons[0]}-{seasons[-1]})" if matches else "Matches: 0",
                f"Competitions: {', '.join(competitions)}",
                f"Players: {len(self.ds.players)}",
            ]
        )

    def _tool_search_matches(self, args):
        result = self.ds.find_matches(
            team=args.get("team"),
            opponent=args.get("opponent"),
            venue=args.get("venue", "any"),
            limit=args.get("limit", 20),
            **_filters(args),
        )
        label = " vs ".join(x for x in (args.get("team"), args.get("opponent")) if x) or "all teams"
        return fmt.format_matches(result, f"Matches for {label}:")

    def _tool_team_record(self, args):
        record = self.ds.team_record(args["team"], venue=args.get("venue", "any"), **_filters(args))
        context = ", ".join(str(x) for x in (args.get("competition"), args.get("season")) if x) or "all data"
        return fmt.format_record(fmt.team_label(args["team"]), record, context)

    def _tool_head_to_head(self, args):
        result = self.ds.head_to_head(
            args["team_a"],
            args["team_b"],
            competition=args.get("competition"),
            season=args.get("season"),
        )
        return fmt.format_head_to_head(result)

    def _tool_standings(self, args):
        competition = args.get("competition") or SERIES_A
        rows = self.ds.standings(args["season"], competition=competition)
        return fmt.format_standings(rows, args["season"], competition)

    def _tool_league_stats(self, args):
        stats = self.ds.league_stats(**_filters(args))
        label = " ".join(str(x) for x in (args.get("competition"), args.get("season")) if x) or "All data"
        return fmt.format_league_stats(stats, label)

    def _tool_rank_teams(self, args):
        rows = self.ds.rank_teams(
            args["metric"],
            min_matches=args.get("min_matches", 1),
            limit=args.get("limit", 10),
            **_filters(args),
        )
        return fmt.format_rankings(rows, args["metric"])

    def _tool_biggest_wins(self, args):
        matches = self.ds.biggest_wins(limit=args.get("limit", 10), **_filters(args))
        return fmt.format_biggest_wins(matches)

    def _tool_search_players(self, args):
        result = self.ds.search_players(
            name=args.get("name"),
            nationality=args.get("nationality"),
            club=args.get("club"),
            position=args.get("position"),
            min_overall=args.get("min_overall"),
            sort=args.get("sort", "overall"),
            limit=args.get("limit", 20),
        )
        return fmt.format_players(result, "Players in dataset:")

    def _tool_club_summary(self, args):
        rows = self.ds.club_summary(nationality=args.get("nationality"))
        return fmt.format_club_summary(rows, args.get("nationality") or "all nationalities")


def handle_message(tools: Tools, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process one JSON-RPC message. Returns the response, or None for notifications."""
    method = message.get("method")
    msg_id = message.get("id")
    if msg_id is None:
        return None  # notifications such as notifications/initialized need no reply

    if method == "initialize":
        result = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = message.get("params") or {}
        try:
            text = tools.dispatch(params.get("name", ""), params.get("arguments") or {})
            result = _text_result(text)
        except ToolError as exc:
            result = _text_result(str(exc), is_error=True)
    else:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def serve(stdin=sys.stdin, stdout=sys.stdout, data_dir: Optional[Path] = None) -> None:
    data_dir = Path(data_dir or os.environ.get("BRAZIL_SOCCER_DATA", DEFAULT_DATA_DIR))
    tools = Tools(Dataset.load(data_dir))
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            response = handle_message(tools, message)
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()
