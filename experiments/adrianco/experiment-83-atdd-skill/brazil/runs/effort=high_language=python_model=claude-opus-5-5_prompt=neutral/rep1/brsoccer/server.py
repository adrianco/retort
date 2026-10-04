"""MCP (Model Context Protocol) server over stdio, implemented with the standard library only.

Speaks newline-delimited JSON-RPC 2.0 as described in the MCP specification
(https://modelcontextprotocol.io/specification): ``initialize``, ``ping``,
``tools/list`` and ``tools/call``.  Each tool wraps one function of
:mod:`brsoccer.queries`; results are returned as text content (plus
``structuredContent`` for clients that negotiate protocol 2025-06-18).

Run with ``python -m brsoccer`` (or ``python mcp_server.py``) and register that
command in an MCP client such as Claude Desktop / Claude Code.
"""

from __future__ import annotations

import inspect
import json
import sys
import time
import traceback
from dataclasses import dataclass
from typing import Any, Callable, TextIO

from . import __version__, queries
from .data import get_db

SUPPORTED_PROTOCOL_VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05"]
LATEST_PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[0]

PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR = (
    -32700, -32600, -32601, -32602, -32603)

INSTRUCTIONS = """\
Brazilian soccer knowledge base built from six Kaggle datasets: Brasileirão Série A 2003-2023
(plus Série B/C 2014-2023), Copa do Brasil 2012-2023, Copa Libertadores 2013-2022, and the
FIFA 19 player database (18k players). Team names are normalised, so 'Sao Paulo', 'São Paulo-SP'
and 'Sao Paulo FC' are the same club. Pick the most specific tool: head_to_head for rivalries,
standings for champions/relegation, team_record for W/D/L, search_players/player_profile for players.
Standings and titles are calculated from match results in the data."""


@dataclass
class Tool:
    name: str
    func: Callable[..., dict]
    description: str
    properties: dict[str, dict]
    required: tuple[str, ...] = ()

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {"type": "object", "properties": self.properties,
                            "required": list(self.required), "additionalProperties": False},
        }


def _s(desc: str, **extra) -> dict:
    return {"type": "string", "description": desc, **extra}


def _i(desc: str, **extra) -> dict:
    return {"type": "integer", "description": desc, **extra}


TEAM = _s("Team name in any spelling, e.g. 'Flamengo', 'Sao Paulo', 'Palmeiras-SP', 'Atletico Mineiro'.")
COMPETITION = _s("Competition: 'Brasileirão' (Série A), 'Série B', 'Série C', 'Copa do Brasil', "
                 "'Libertadores', or omit for all.")
SEASON = _i("Season year, e.g. 2019.")
VENUE = _s("'home', 'away' or 'all' (default).", enum=["home", "away", "all"])
LIMIT = _i("Maximum number of rows to list.", minimum=1, maximum=500)

TOOLS: list[Tool] = [
    Tool("search_matches", queries.search_matches,
         "Find matches by team (home/away/either), opponent, competition, season, date range or stage "
         "(e.g. 'Final'). Use for 'What matches did Palmeiras play in 2023?' or 'When did Flamengo last "
         "play Corinthians?' (limit=1).",
         {"team": TEAM, "opponent": _s("Optional second team: only matches between team and opponent."),
          "competition": COMPETITION, "season": SEASON,
          "date_from": _s("Start date (YYYY-MM-DD or DD/MM/YYYY)."), "date_to": _s("End date."),
          "venue": VENUE, "stage": _s("Stage or round, e.g. 'Final', 'Semi-finals', 'Group stage', '38'."),
          "limit": LIMIT, "order": _s("'desc' (newest first, default) or 'asc'.", enum=["asc", "desc"])}),
    Tool("head_to_head", queries.head_to_head,
         "Head-to-head record between two teams: wins/draws, goals, last meeting, biggest win, split by "
         "competition, and recent matches. Recognises derbies (Fla-Flu, Grenal, Derby Paulista...).",
         {"team_a": TEAM, "team_b": TEAM, "competition": COMPETITION, "season": SEASON, "limit": LIMIT},
         ("team_a", "team_b")),
    Tool("team_record", queries.team_record,
         "A team's win/draw/loss record, goals for/against, win rate and points, filtered by season, "
         "competition and venue. E.g. 'Corinthians home record in 2022'.",
         {"team": TEAM, "season": SEASON, "competition": COMPETITION, "venue": VENUE}, ("team",)),
    Tool("team_profile", queries.team_profile,
         "Overview of a club across every file: competitions and seasons played, overall record, titles "
         "calculated from the data, and its FIFA squad (cross-file query).",
         {"team": TEAM}, ("team",)),
    Tool("standings", queries.standings,
         "League table for a season calculated from results (3 pts per win), with champion and relegated "
         "teams. Use for 'Who won the 2019 Brasileirão?' or 'Which teams were relegated in 2020?'.",
         {"season": SEASON, "competition": _s("'Brasileirão' (default), 'Série B' or 'Série C'."),
          "top": _i("Only show the top N rows (relegated teams are still listed).", minimum=1)},
         ("season",)),
    Tool("knockout_bracket", queries.knockout_bracket,
         "Knockout bracket (round of 16 → final) with aggregate scores for a Copa Libertadores or "
         "Copa do Brasil season.",
         {"season": SEASON, "competition": _s("'Libertadores' (default) or 'Copa do Brasil'.")}, ("season",)),
    Tool("finals", queries.finals,
         "All finals of Copa do Brasil (default) or Copa Libertadores in the data, with aggregate and winner.",
         {"competition": _s("'Copa do Brasil' (default) or 'Libertadores'."), "season": SEASON}),
    Tool("team_rankings", queries.team_rankings,
         "Rank teams by a metric over a competition/season/venue: win_rate, points, wins, goals_for, "
         "goals_against (fewest first), goal_difference. E.g. 'best away record', 'most goals in 2023'.",
         {"metric": _s("Metric to rank by.", enum=["win_rate", "points", "wins", "draws", "losses", "goals_for",
                                                     "goals_against", "goal_difference"]),
          "competition": _s("Competition (default Brasileirão Série A; 'all' for every competition)."),
          "season": SEASON, "venue": VENUE,
          "min_matches": _i("Minimum matches to qualify (default 10 for one season, 38 otherwise)."),
          "limit": LIMIT}),
    Tool("competition_stats", queries.competition_stats,
         "Aggregate statistics: goals per match, home/draw/away win rates, common scorelines, "
         "corners/shots where available. E.g. 'average goals per match in the Brasileirão'.",
         {"competition": COMPETITION, "season": SEASON}),
    Tool("biggest_wins", queries.biggest_wins,
         "Biggest victories by goal margin, optionally for one competition, season or winning team.",
         {"competition": COMPETITION, "season": SEASON, "team": _s("Only wins by this team."), "limit": LIMIT}),
    Tool("derbies", queries.derbies,
         "Matches between traditional rivals (Fla-Flu, Clássico dos Milhões, Derby Paulista, Choque-Rei, "
         "Majestoso, San-São, Grenal, Clássico Mineiro, Atletiba, Ba-Vi, Clássico-Rei, ...).",
         {"season": SEASON, "rivalry": _s("Optional derby name, e.g. 'Grenal' or 'Fla-Flu'."),
          "competition": COMPETITION, "limit": LIMIT}),
    Tool("compare_seasons", queries.compare_seasons,
         "Compare two seasons of a competition: goals, home/away rates, champion, best attack/defence, relegation.",
         {"season_a": SEASON, "season_b": SEASON, "competition": _s("Default Brasileirão Série A.")},
         ("season_a", "season_b")),
    Tool("search_players", queries.search_players,
         "Search FIFA 19 players by name, nationality ('Brazil'/'Brazilian'), club, position ('ST' or "
         "'forwards'/'midfielders'/'defenders'/'goalkeepers'), minimum overall and maximum age.",
         {"name": _s("Player name or part of it."), "nationality": _s("Nationality, e.g. 'Brazil'."),
          "club": _s("Club name, e.g. 'Santos', 'Grêmio', 'Real Madrid'."),
          "position": _s("Position code(s) or group, e.g. 'ST', 'CB,LB', 'forwards'."),
          "min_overall": _i("Minimum overall rating."), "max_age": _i("Maximum age."),
          "brazilian_clubs_only": {"type": "boolean", "description": "Only players at Brazilian clubs."},
          "sort_by": _s("Sort order.", enum=["overall", "potential", "age", "value", "name"]),
          "limit": LIMIT}),
    Tool("player_profile", queries.player_profile,
         "Detailed profile of one player (ratings, physical data, value, best attributes). "
         "Suggests similar names when the player is not in the data.",
         {"name": _s("Player name, e.g. 'Neymar', 'Casemiro'.")}, ("name",)),
    Tool("club_players", queries.club_players,
         "Players of a club in the FIFA data, best first, with the club's match record (cross-file).",
         {"team": TEAM, "position": _s("Optional position filter, e.g. 'forwards'."), "limit": LIMIT}, ("team",)),
    Tool("brazilian_players_overview", queries.brazilian_players_overview,
         "Top-rated Brazilian players and a per-club summary of Brazilian players at Brazilian clubs.",
         {"limit": LIMIT}),
    Tool("find_team", queries.find_team,
         "Resolve a team name (shows normalisation and alternative candidates).",
         {"name": _s("Team name to resolve.")}, ("name",)),
    Tool("dataset_info", queries.dataset_info,
         "Describe the loaded datasets: files, row counts, merged duplicates and season coverage.", {}),
]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}


class RpcError(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.code, self.message, self.data = code, message, data


class MCPServer:
    def __init__(self) -> None:
        self.protocol_version = LATEST_PROTOCOL_VERSION
        self.initialized = False

    # ---- dispatch

    def handle(self, message: Any) -> Any:
        """Handle one decoded JSON-RPC message (or batch). Returns the response object or None."""
        if isinstance(message, list):
            if not message:
                return self._error(None, INVALID_REQUEST, "Empty batch")
            responses = [r for r in (self.handle(m) for m in message) if r is not None]
            return responses or None
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return self._error(message.get("id") if isinstance(message, dict) else None,
                               INVALID_REQUEST, "Invalid JSON-RPC 2.0 message")
        if "method" not in message:
            return None  # a response to a server->client request; we never send any
        msg_id = message.get("id")
        is_notification = "id" not in message
        try:
            result = self._dispatch(message["method"], message.get("params") or {})
        except RpcError as e:
            return None if is_notification else self._error(msg_id, e.code, e.message, e.data)
        except Exception as e:  # pragma: no cover - defensive
            traceback.print_exc(file=sys.stderr)
            return None if is_notification else self._error(msg_id, INTERNAL_ERROR, f"Internal error: {e}")
        if is_notification:
            return None
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    def _dispatch(self, method: str, params: dict) -> Any:
        if not isinstance(params, dict):
            raise RpcError(INVALID_PARAMS, "params must be an object")
        if method == "initialize":
            return self._initialize(params)
        if method in ("notifications/initialized", "notifications/cancelled", "notifications/progress"):
            if method == "notifications/initialized":
                self.initialized = True
            return None
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [t.schema() for t in TOOLS]}
        if method == "tools/call":
            return self._call_tool(params)
        raise RpcError(METHOD_NOT_FOUND, f"Method not found: {method}")

    def _initialize(self, params: dict) -> dict:
        requested = params.get("protocolVersion")
        self.protocol_version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else LATEST_PROTOCOL_VERSION
        get_db()  # load the data up front so the first query is fast
        return {
            "protocolVersion": self.protocol_version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "brazilian-soccer", "title": "Brazilian Soccer Knowledge Base",
                           "version": __version__},
            "instructions": INSTRUCTIONS,
        }

    def _call_tool(self, params: dict) -> dict:
        name = params.get("name")
        tool = TOOLS_BY_NAME.get(name)
        if tool is None:
            raise RpcError(INVALID_PARAMS, f"Unknown tool: {name}")
        args = params.get("arguments") or {}
        if not isinstance(args, dict):
            raise RpcError(INVALID_PARAMS, "arguments must be an object")
        unknown = sorted(set(args) - set(tool.properties))
        if unknown:
            return self._tool_error(f"Unknown argument(s) for {name}: {', '.join(unknown)}. "
                                    f"Valid: {', '.join(tool.properties) or 'none'}.")
        missing = [r for r in tool.required if args.get(r) in (None, "")]
        if missing:
            return self._tool_error(f"Missing required argument(s) for {name}: {', '.join(missing)}.")
        start = time.perf_counter()
        try:
            out = tool.func(**{k: v for k, v in args.items() if v is not None})
        except queries.QueryError as e:
            return self._tool_error(str(e))
        except (TypeError, ValueError) as e:
            return self._tool_error(f"Invalid arguments for {name}: {e}")
        elapsed = time.perf_counter() - start
        print(f"[brsoccer] {name} {json.dumps(args, ensure_ascii=False)} {elapsed * 1000:.0f}ms", file=sys.stderr)
        result = {"content": [{"type": "text", "text": out["text"]}], "isError": False}
        if self.protocol_version >= "2025-06-18":
            result["structuredContent"] = _jsonable(out["data"])
        return result

    @staticmethod
    def _tool_error(message: str) -> dict:
        return {"content": [{"type": "text", "text": message}], "isError": True}

    @staticmethod
    def _error(msg_id: Any, code: int, message: str, data: Any = None) -> dict:
        err = {"code": code, "message": message}
        if data is not None:
            err["data"] = data
        return {"jsonrpc": "2.0", "id": msg_id, "error": err}

    # ---- transport

    def serve(self, stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout) -> None:
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError as e:
                response = self._error(None, PARSE_ERROR, f"Parse error: {e}")
            else:
                response = self.handle(message)
            if response is not None:
                stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                stdout.flush()


def _jsonable(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def tool_signature_check() -> list[str]:
    """Return mismatches between declared tool properties and the wrapped function parameters."""
    problems = []
    for t in TOOLS:
        params = set(inspect.signature(t.func).parameters) - {"db"}
        if set(t.properties) - params:
            problems.append(f"{t.name}: {sorted(set(t.properties) - params)}")
    return problems


def main() -> None:
    # Make sure stdout carries UTF-8 regardless of the platform default.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    print(f"[brsoccer] MCP server {__version__} ready on stdio", file=sys.stderr)
    MCPServer().serve()


if __name__ == "__main__":
    main()
