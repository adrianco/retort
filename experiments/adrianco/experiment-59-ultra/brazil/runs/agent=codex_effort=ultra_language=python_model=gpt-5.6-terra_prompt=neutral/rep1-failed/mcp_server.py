"""A dependency-free MCP stdio server for Brazilian soccer data.

The repository's Python environment currently has an incompatible `mcp`/Pydantic
installation.  This module implements the small MCP JSON-RPC surface needed by
standard clients directly, rather than making the server un-runnable because of that
environmental conflict.  It supports initialize, ping, tools/list, and tools/call.
"""

from __future__ import annotations

import argparse
import json
import sys
from io import TextIOBase
from typing import Any, Callable, Mapping

from soccer_data import NaturalLanguageQueryService, SoccerDataError, SoccerRepository, format_match


SERVER_NAME = "brazilian-soccer-mcp"
SERVER_VERSION = "1.0.0"
LATEST_PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOL_VERSIONS = {"2024-11-05", "2025-03-26", "2025-06-18", LATEST_PROTOCOL_VERSION}


def _schema(description: str, properties: Mapping[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": dict(properties),
            "required": required or [],
            "additionalProperties": False,
        },
    }


STRING = {"type": "string"}
INTEGER = {"type": "integer"}
BOOLEAN = {"type": "boolean"}


class BrazilianSoccerMCPServer:
    """Maps MCP tool calls to the tested repository service layer."""

    def __init__(self, repository: SoccerRepository | None = None) -> None:
        self.repository = repository or SoccerRepository.from_default_data()
        self.questions = NaturalLanguageQueryService(self.repository)
        self._handlers: dict[str, Callable[..., dict[str, Any]]] = {
            "ask_soccer": self.questions.ask,
            "search_matches": self.repository.search_matches,
            "team_statistics": self.repository.team_statistics,
            "head_to_head": self.repository.head_to_head,
            "search_players": self.repository.search_players,
            "competition_standings": self.repository.competition_standings,
            "analyze_statistics": self.repository.analyze_statistics,
            "team_leaderboard": self.repository.team_leaderboard,
            "competition_matches_by_stage": self.repository.competition_matches_by_stage,
            "team_profile": self.repository.team_profile,
            "knowledge_graph": self.repository.knowledge_graph,
            "dataset_summary": self.repository.source_summary,
        }

    @staticmethod
    def tool_definitions() -> list[dict[str, Any]]:
        return [
            {
                "name": "ask_soccer",
                **_schema(
                    "Answer a common natural-language Brazilian soccer question deterministically. "
                    "Use this for convenience; precise tools below provide fuller filtering.",
                    {"question": STRING, "limit": {**INTEGER, "minimum": 1, "maximum": 500}},
                    ["question"],
                ),
            },
            {
                "name": "search_matches",
                **_schema(
                    "Find completed or incomplete matches across all bundled match sources. "
                    "Default results select one authoritative source per competition and season to avoid overlap double-counting.",
                    {
                        "team": STRING,
                        "opponent": STRING,
                        "home_team": STRING,
                        "away_team": STRING,
                        "competition": STRING,
                        "season": INTEGER,
                        "date_from": STRING,
                        "date_to": STRING,
                        "round_or_stage": STRING,
                        "source": STRING,
                        "include_incomplete": BOOLEAN,
                        "include_duplicates": BOOLEAN,
                        "limit": {**INTEGER, "minimum": 1, "maximum": 500},
                    },
                ),
            },
            {
                "name": "team_statistics",
                **_schema(
                    "Calculate a team's wins, draws, losses, goals, points, and win rate. "
                    "Team-name normalization handles accents, state suffixes, and common full-name variants.",
                    {
                        "team": STRING,
                        "competition": STRING,
                        "season": INTEGER,
                        "venue": {"type": "string", "enum": ["all", "home", "away"]},
                        "source": STRING,
                        "include_duplicates": BOOLEAN,
                    },
                    ["team"],
                ),
            },
            {
                "name": "head_to_head",
                **_schema(
                    "Compare two teams' direct meetings, including each team's win/draw/loss record and recent matches.",
                    {
                        "team_one": STRING,
                        "team_two": STRING,
                        "competition": STRING,
                        "season": INTEGER,
                        "source": STRING,
                        "limit": {**INTEGER, "minimum": 1, "maximum": 500},
                    },
                    ["team_one", "team_two"],
                ),
            },
            {
                "name": "search_players",
                **_schema(
                    "Search the bundled FIFA player dataset by name, nationality, club, position, and rating. "
                    "Results include overall/potential ratings and core skill attributes.",
                    {
                        "name": STRING,
                        "nationality": STRING,
                        "club": STRING,
                        "position": STRING,
                        "min_overall": INTEGER,
                        "limit": {**INTEGER, "minimum": 1, "maximum": 500},
                    },
                ),
            },
            {
                "name": "competition_standings",
                **_schema(
                    "Calculate a competition table from completed match results. Ties sort by wins, goal difference, and goals scored.",
                    {"competition": STRING, "season": INTEGER, "source": STRING},
                    ["competition", "season"],
                ),
            },
            {
                "name": "analyze_statistics",
                **_schema(
                    "Calculate aggregate goals, home-win rate, biggest wins, best away record, or top scoring teams.",
                    {
                        "metric": {
                            "type": "string",
                            "enum": [
                                "summary",
                                "average_goals",
                                "goals_per_match",
                                "home_win_rate",
                                "biggest_wins",
                                "best_away_record",
                                "top_scoring_teams",
                            ],
                        },
                        "competition": STRING,
                        "season": INTEGER,
                        "limit": {**INTEGER, "minimum": 1, "maximum": 500},
                    },
                ),
            },
            {
                "name": "team_leaderboard",
                **_schema(
                    "Rank teams by goals, wins, points, win rate, goals against, or goal difference.",
                    {
                        "metric": STRING,
                        "competition": STRING,
                        "season": INTEGER,
                        "venue": {"type": "string", "enum": ["all", "home", "away"]},
                        "limit": {**INTEGER, "minimum": 1, "maximum": 500},
                    },
                ),
            },
            {
                "name": "competition_matches_by_stage",
                **_schema(
                    "Group a competition's match results by supplied stage or round. The datasets do not contain an official bracket diagram.",
                    {
                        "competition": STRING,
                        "season": INTEGER,
                        "limit": {**INTEGER, "minimum": 1, "maximum": 500},
                    },
                    ["competition", "season"],
                ),
            },
            {
                "name": "team_profile",
                **_schema(
                    "Join a normalized team's match statistics/recent results with FIFA club-player results. "
                    "The response reports the two source views separately so different dataset snapshots are never conflated.",
                    {
                        "team": STRING,
                        "competition": STRING,
                        "season": INTEGER,
                        "match_limit": {**INTEGER, "minimum": 1, "maximum": 500},
                        "player_limit": {**INTEGER, "minimum": 1, "maximum": 500},
                    },
                    ["team"],
                ),
            },
            {
                "name": "knowledge_graph",
                **_schema(
                    "Return explicit team, match, competition, player, and club nodes plus their source-derived edges.",
                    {
                        "team": STRING,
                        "player_name": STRING,
                        "competition": STRING,
                        "season": INTEGER,
                        "limit": {**INTEGER, "minimum": 1, "maximum": 500},
                    },
                ),
            },
            {
                "name": "dataset_summary",
                **_schema("Report each bundled CSV's loaded record count and its provenance role.", {}),
            },
        ]

    @staticmethod
    def _human_readable_result(result: Mapping[str, Any]) -> str:
        if result.get("answer"):
            return str(result["answer"])
        if "matches" in result:
            matches = result["matches"]
            if not matches:
                return "No matches matched those criteria."
            lines = [f"{result.get('count', len(matches))} match(es) matched:"]
            lines.extend(f"- {format_match(match)}" for match in matches[:10])
            if len(matches) > 10:
                lines.append(f"- … {len(matches) - 10} more returned in structured data.")
            return "\n".join(lines)
        if "players" in result:
            players = result["players"]
            if not players:
                return "No players matched those criteria."
            return "\n".join(
                [f"{result.get('count', len(players))} player(s) matched:"]
                + [f"- {player['name']} — Overall {player['overall']}, {player['position']}, {player['club']}" for player in players[:10]]
            )
        if "standings" in result:
            rows = result["standings"]
            if not rows:
                return "No completed matches were available for a standings table."
            return "\n".join(
                [f"{result['competition']} {result['season']} standings:"]
                + [f"{row['position']}. {row['team']} — {row['points']} pts" for row in rows[:10]]
            )
        if "leaders" in result:
            rows = result["leaders"]
            if not rows:
                return "No teams matched those criteria."
            return "\n".join(
                [f"{result.get('metric', 'Team')} leaders:"]
                + [f"- {row['team']}" for row in rows[:10]]
            )
        return json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)

    def call_tool(self, name: str, arguments: Mapping[str, Any] | None = None) -> dict[str, Any]:
        handler = self._handlers.get(name)
        if not handler:
            return self._tool_error(f"Unknown tool: {name}")
        if arguments is not None and not isinstance(arguments, Mapping):
            return self._tool_error("Tool arguments must be an object")
        try:
            result = handler(**dict(arguments or {}))
        except (SoccerDataError, TypeError, ValueError) as exc:
            return self._tool_error(str(exc))
        except Exception as exc:  # pragma: no cover - protects the JSON-RPC process from unexpected faults
            return self._tool_error(f"Unexpected server error: {exc}")
        return {
            "content": [{"type": "text", "text": self._human_readable_result(result)}],
            "structuredContent": result,
            "isError": False,
        }

    @staticmethod
    def _tool_error(message: str) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": message}], "isError": True}

    @staticmethod
    def _response(request_id: str | int, result: Mapping[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": dict(result)}

    @staticmethod
    def _error(request_id: str | int | None, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    def handle_message(self, message: object) -> dict[str, Any] | None:
        """Handle one JSON-RPC message; notifications intentionally yield no response."""

        if not isinstance(message, Mapping):
            return self._error(None, -32600, "Invalid Request")
        request_id = message.get("id")
        has_request_id = "id" in message
        method = message.get("method")
        params = message.get("params")
        if params is None:
            params = {}
        if not isinstance(method, str):
            return self._error(request_id if has_request_id else None, -32600, "Invalid Request")
        if not isinstance(params, Mapping):
            return self._error(request_id if has_request_id else None, -32602, "params must be an object")

        def reply(result: Mapping[str, Any]) -> dict[str, Any] | None:
            return self._response(request_id, result) if has_request_id else None

        if method == "initialize":
            requested = str(params.get("protocolVersion", ""))
            negotiated = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else LATEST_PROTOCOL_VERSION
            return reply(
                {
                    "protocolVersion": negotiated,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                    "instructions": "Use the soccer tools to query the six bundled Brazilian football datasets. Results include source provenance.",
                }
            )
        if method == "ping":
            return reply({})
        if method == "tools/list":
            return reply({"tools": self.tool_definitions()})
        if method == "tools/call":
            name = params.get("name")
            if not isinstance(name, str):
                return self._error(request_id if has_request_id else None, -32602, "tools/call requires a string name")
            result = self.call_tool(name, params.get("arguments"))
            return reply(result)
        if method in {"notifications/initialized", "notifications/cancelled"}:
            return None
        return self._error(request_id if has_request_id else None, -32601, f"Method not found: {method}") if has_request_id else None

    def run_stdio(self, input_stream: TextIOBase = sys.stdin, output_stream: TextIOBase = sys.stdout) -> None:
        """Serve newline-delimited MCP JSON-RPC requests over standard I/O."""

        for raw_line in input_stream:
            line = raw_line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                response = self._error(None, -32700, "Parse error")
            else:
                response = self.handle_message(message)
            if response is not None:
                output_stream.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
                output_stream.flush()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Brazilian Soccer MCP server")
    parser.add_argument("--data-dir", help="Directory containing the six supplied CSV files")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    repository = SoccerRepository(args.data_dir) if args.data_dir else SoccerRepository.from_default_data()
    BrazilianSoccerMCPServer(repository).run_stdio()


if __name__ == "__main__":
    main()
