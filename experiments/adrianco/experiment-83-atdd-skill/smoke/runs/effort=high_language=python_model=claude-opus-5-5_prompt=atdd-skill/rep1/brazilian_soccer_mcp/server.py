"""
The MCP server: exposes the Brazilian football knowledge base as MCP tools
over stdio (newline-delimited JSON-RPC 2.0), for an LLM host to call.

Implements the parts of the Model Context Protocol a tools-only server
needs — initialize, ping, tools/list, tools/call — with no third-party
dependencies. Every tool returns readable text plus the same answer as
`structuredContent`. Data is loaded once at start-up (from
$SOCCER_DATA_DIR, defaulting to data/kaggle) so each question is answered
from memory.

Run with:  python -m brazilian_soccer_mcp
"""

import json
import sys
import time

from . import formatting
from .data import SoccerData
from .queries import QueryError, SoccerQueries

SERVER_NAME = "brazilian-soccer-mcp"
SERVER_VERSION = "1.0.0"
SUPPORTED_PROTOCOL_VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05"]

INSTRUCTIONS = (
    "Knowledge base of Brazilian football built from Kaggle datasets: Brasileirão Série A (2003-2023), "
    "Série B and C (2014-2023), Copa do Brasil (2012-2023), Copa Libertadores (2013-2022) and the FIFA 19 "
    "player database. Team names are matched loosely (accents, state suffixes and full club names are all "
    "understood). Standings and records are calculated from match results."
)

_TEAM = {"type": "string", "description": "Team name, e.g. 'Flamengo', 'São Paulo', 'Atletico-MG'"}
_COMPETITION = {"type": "string", "description": "Competition: 'Brasileirão' (Série A), 'Serie B', 'Serie C', "
                                                 "'Copa do Brasil' or 'Libertadores'. Omit for all."}
_SEASON = {"type": "integer", "description": "Season year, e.g. 2019"}
_VENUE = {"type": "string", "enum": ["all", "home", "away"], "description": "Home, away or all matches"}
_LIMIT = {"type": "integer", "minimum": 1, "maximum": 500}


def _schema(properties, required=()):
    return {"type": "object", "properties": properties, "required": list(required), "additionalProperties": False}


TOOLS = [
    {
        "name": "find_matches",
        "description": "Find matches by team, opponent, home/away, competition, season, date range or stage. "
                       "Most recent first; with team and opponent also gives the head-to-head summary. "
                       "Use for 'show me Flamengo vs Fluminense', 'when did X last play Y', "
                       "'what matches did Palmeiras play in 2021'.",
        "inputSchema": _schema({
            "team": _TEAM, "opponent": dict(_TEAM, description="Second team (matches between team and opponent)"),
            "venue": dict(_VENUE, description="Where 'team' played: home, away or all"),
            "competition": _COMPETITION, "season": _SEASON,
            "date_from": {"type": "string", "description": "Earliest date, YYYY-MM-DD or DD/MM/YYYY"},
            "date_to": {"type": "string", "description": "Latest date, YYYY-MM-DD or DD/MM/YYYY"},
            "stage": {"type": "string", "description": "Cup stage or round, e.g. 'final', 'semifinals', '8'"},
            "limit": dict(_LIMIT, description="Maximum matches listed (default 20)"),
        }),
        "query": "find_matches", "format": formatting.find_matches,
    },
    {
        "name": "head_to_head",
        "description": "Head-to-head record between two teams: wins each, draws, goals and recent meetings.",
        "inputSchema": _schema({"team_a": _TEAM, "team_b": _TEAM, "competition": _COMPETITION, "season": _SEASON,
                                "limit": _LIMIT}, ["team_a", "team_b"]),
        "query": "head_to_head", "format": formatting.head_to_head,
    },
    {
        "name": "team_record",
        "description": "A team's win/draw/loss record, goals for/against, points and win rate — optionally "
                       "for one season, one competition, and home or away only.",
        "inputSchema": _schema({"team": _TEAM, "season": _SEASON, "competition": _COMPETITION, "venue": _VENUE},
                               ["team"]),
        "query": "team_record", "format": formatting.team_record,
    },
    {
        "name": "team_competitions",
        "description": "Which competitions a team has played in, with seasons and results in each.",
        "inputSchema": _schema({"team": _TEAM}, ["team"]),
        "query": "team_competitions", "format": formatting.team_competitions,
    },
    {
        "name": "team_profile",
        "description": "Everything about a team: overall/home/away record, competitions, recent results and "
                       "its players from the FIFA database (combines match and player data).",
        "inputSchema": _schema({"team": _TEAM, "squad_size": _LIMIT}, ["team"]),
        "query": "team_profile", "format": formatting.team_profile,
    },
    {
        "name": "standings",
        "description": "League table for a season calculated from results: points, W/D/L, goals, champion "
                       "and the relegated (bottom four) teams. Use for 'who won the 2019 Brasileirão', "
                       "'which teams were relegated in 2020'.",
        "inputSchema": _schema({"season": _SEASON, "competition": dict(_COMPETITION, description=
                                "League: 'Brasileirão' (default), 'Serie B' or 'Serie C'")}, ["season"]),
        "query": "standings", "format": formatting.standings,
    },
    {
        "name": "cup_finals",
        "description": "Finals of the Copa do Brasil or Copa Libertadores, with legs, aggregate and winner. "
                       "Omit season for every final in the data.",
        "inputSchema": _schema({"competition": dict(_COMPETITION, description="'Copa do Brasil' (default) or "
                                                                              "'Libertadores'"),
                                "season": _SEASON}),
        "query": "cup_finals", "format": formatting.cup_finals,
    },
    {
        "name": "knockout_bracket",
        "description": "Knockout bracket of a cup season: each stage's ties with legs, aggregate and who went "
                       "through. Libertadores by default; Copa do Brasil by round number.",
        "inputSchema": _schema({"season": _SEASON, "competition": dict(_COMPETITION, description=
                                "'Libertadores' (default) or 'Copa do Brasil'")}, ["season"]),
        "query": "knockout_bracket", "format": formatting.knockout_bracket,
    },
    {
        "name": "find_derbies",
        "description": "Traditional rivalry matches (Fla-Flu, Grenal, Derby Paulista, Clássico Mineiro, Ba-Vi, "
                       "Choque-Rei, Majestoso, San-São, Atletiba, Clássico-Rei and more).",
        "inputSchema": _schema({"season": _SEASON, "competition": _COMPETITION, "team": _TEAM,
                                "derby": {"type": "string", "description": "Derby name, e.g. 'Fla-Flu'"},
                                "limit": _LIMIT}),
        "query": "find_derbies", "format": formatting.find_derbies,
    },
    {
        "name": "competition_stats",
        "description": "Aggregate statistics: matches, goals, average goals per match, home/draw/away rates — "
                       "for a competition, season and/or team.",
        "inputSchema": _schema({"competition": _COMPETITION, "season": _SEASON, "team": _TEAM}),
        "query": "competition_stats", "format": formatting.competition_stats,
    },
    {
        "name": "biggest_wins",
        "description": "The biggest victories by goal margin, optionally by competition, season or winning team.",
        "inputSchema": _schema({"competition": _COMPETITION, "season": _SEASON, "team": _TEAM, "limit": _LIMIT}),
        "query": "biggest_wins", "format": formatting.biggest_wins,
    },
    {
        "name": "rank_teams",
        "description": "Rank teams by win rate, goals scored, goals conceded, points, wins or goals per match — "
                       "home, away or overall. Use for 'best home record', 'most goals in Serie A 2022'.",
        "inputSchema": _schema({
            "metric": {"type": "string", "enum": ["win_rate", "goals_scored", "goals_conceded", "points", "wins",
                                                  "goals_per_match"]},
            "venue": _VENUE, "competition": _COMPETITION, "season": _SEASON,
            "min_matches": {"type": "integer", "description": "Ignore teams with fewer matches "
                                                              "(default: 20% of the busiest team's matches)"},
            "limit": _LIMIT,
        }),
        "query": "rank_teams", "format": formatting.rank_teams,
    },
    {
        "name": "compare_seasons",
        "description": "Compare seasons of a competition: goals per match, result rates, champion, relegated "
                       "teams and top-scoring team.",
        "inputSchema": _schema({"seasons": {"type": "array", "items": {"type": "integer"}, "minItems": 1},
                                "competition": _COMPETITION}, ["seasons"]),
        "query": "compare_seasons", "format": formatting.compare_seasons,
    },
    {
        "name": "search_players",
        "description": "Search FIFA player data by name, nationality, club, position ('forward', 'midfielder', "
                       "'defender', 'goalkeeper' or a code like 'ST') and minimum rating. Highest rated first.",
        "inputSchema": _schema({
            "name": {"type": "string"}, "nationality": {"type": "string", "description": "e.g. 'Brazil'"},
            "club": {"type": "string"}, "position": {"type": "string"},
            "min_overall": {"type": "integer"},
            "sort_by": {"type": "string", "enum": ["overall", "potential", "age", "name"]}, "limit": _LIMIT,
        }),
        "query": "search_players", "format": formatting.search_players,
    },
    {
        "name": "player_profile",
        "description": "Full profile of one player by name: club, position, ratings, physical data, value and "
                       "best attributes.",
        "inputSchema": _schema({"name": {"type": "string"}}, ["name"]),
        "query": "player_profile", "format": formatting.player_profile,
    },
    {
        "name": "brazilian_club_players",
        "description": "Players at Brazilian clubs (clubs appearing in the Brazilian match data), grouped by "
                       "club with player count, average rating and top player. Filter by nationality.",
        "inputSchema": _schema({"nationality": {"type": "string"}, "limit": _LIMIT}),
        "query": "brazilian_club_players", "format": formatting.brazilian_club_players,
    },
    {
        "name": "dataset_info",
        "description": "Which data files are loaded, row counts, competitions and seasons covered.",
        "inputSchema": _schema({}),
        "query": "dataset_info", "format": formatting.dataset_info,
    },
]
_TOOLS_BY_NAME = {tool["name"]: tool for tool in TOOLS}


class InvalidParams(Exception):
    pass


class SoccerMcpServer:
    def __init__(self, data=None):
        self.queries = SoccerQueries(data or SoccerData())

    def list_tools(self):
        return [{k: tool[k] for k in ("name", "description", "inputSchema")} for tool in TOOLS]

    def call_tool(self, name, arguments):
        tool = _TOOLS_BY_NAME.get(name)
        if tool is None:
            raise InvalidParams(f"Unknown tool: {name}")
        arguments = arguments or {}
        allowed = tool["inputSchema"]["properties"]
        unexpected = sorted(set(arguments) - set(allowed))
        missing = [p for p in tool["inputSchema"]["required"] if arguments.get(p) in (None, "")]
        if unexpected or missing:
            problem = "; ".join(filter(None, [
                f"unexpected argument(s) {', '.join(unexpected)}" if unexpected else "",
                f"missing required argument(s) {', '.join(missing)}" if missing else ""]))
            return _tool_result(f"Invalid arguments for {name}: {problem}.",
                                {"error": "invalid_arguments", "message": problem}, is_error=True)
        try:
            result = getattr(self.queries, tool["query"])(**arguments)
        except QueryError as error:
            return _tool_result(error.message, dict({"error": error.code, "message": error.message},
                                                    **error.details), is_error=True)
        except (TypeError, ValueError) as error:
            return _tool_result(f"Invalid arguments for {name}: {error}",
                                {"error": "invalid_arguments", "message": str(error)}, is_error=True)
        return _tool_result(tool["format"](result), result)

    def handle(self, message):
        """Handle one JSON-RPC message; return the response dict, or None for notifications."""
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or "method" not in message:
            return _error(message.get("id") if isinstance(message, dict) else None, -32600, "Invalid Request")
        method, params, request_id = message["method"], message.get("params") or {}, message.get("id")
        if "id" not in message:
            return None
        try:
            if method == "initialize":
                requested = params.get("protocolVersion")
                version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else SUPPORTED_PROTOCOL_VERSIONS[0]
                result = {"protocolVersion": version, "capabilities": {"tools": {"listChanged": False}},
                          "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                          "instructions": INSTRUCTIONS}
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": self.list_tools()}
            elif method == "tools/call":
                result = self.call_tool(params.get("name"), params.get("arguments"))
            else:
                return _error(request_id, -32601, f"Method not found: {method}")
        except InvalidParams as error:
            return _error(request_id, -32602, str(error))
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def serve(self, stdin=sys.stdin, stdout=sys.stdout):
        for line in stdin:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                response = _error(None, -32700, "Parse error")
            else:
                if isinstance(message, list):
                    responses = [r for r in (self._safe_handle(m) for m in message) if r]
                    response = responses or None
                else:
                    response = self._safe_handle(message)
            if response is not None:
                stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                stdout.flush()

    def _safe_handle(self, message):
        try:
            return self.handle(message)
        except Exception as error:  # keep serving; report the failure to the client
            request_id = message.get("id") if isinstance(message, dict) else None
            return _error(request_id, -32603, f"Internal error: {error}")


def _tool_result(text, structured, is_error=False):
    return {"content": [{"type": "text", "text": text}], "structuredContent": structured, "isError": is_error}


def _error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def main():
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    started = time.perf_counter()
    server = SoccerMcpServer()
    data = server.queries.data
    print(f"{SERVER_NAME}: loaded {len(data.matches)} matches and {len(data.players)} players from "
          f"{data.data_dir} in {time.perf_counter() - started:.2f}s", file=sys.stderr)
    server.serve()


if __name__ == "__main__":
    main()
