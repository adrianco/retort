"""A dependency-free MCP stdio server exposing the soccer query layer."""
from __future__ import annotations
import json
import sys
from typing import Any
from soccer_mcp import SoccerData


TOOLS = [
    ("find_matches", "Find matches by team, opponent, competition, season, or date range."),
    ("team_stats", "Calculate a team's wins, draws, losses, goals, and win rate."),
    ("head_to_head", "Compare two teams and return their matches and record."),
    ("search_players", "Search FIFA players by name, nationality, club, or position."),
    ("standings", "Calculate competition standings for a season."),
    ("statistics", "Calculate aggregate match statistics."),
    ("biggest_wins", "Return the largest score margins in the data."),
]


def schemas() -> dict[str, Any]:
    return {"find_matches": {"type": "object", "properties": {"team": {"type": "string"}, "opponent": {"type": "string"}, "competition": {"type": "string"}, "season": {"type": "integer"}, "date_from": {"type": "string"}, "date_to": {"type": "string"}, "limit": {"type": "integer"}}},
            "team_stats": {"type": "object", "required": ["team"], "properties": {"team": {"type": "string"}, "season": {"type": "integer"}, "competition": {"type": "string"}, "home_only": {"type": "boolean"}, "away_only": {"type": "boolean"}}},
            "head_to_head": {"type": "object", "required": ["team_a", "team_b"], "properties": {"team_a": {"type": "string"}, "team_b": {"type": "string"}, "competition": {"type": "string"}, "season": {"type": "integer"}}},
            "search_players": {"type": "object", "properties": {"name": {"type": "string"}, "nationality": {"type": "string"}, "club": {"type": "string"}, "position": {"type": "string"}, "limit": {"type": "integer"}}},
            "standings": {"type": "object", "required": ["season"], "properties": {"season": {"type": "integer"}, "competition": {"type": "string"}}},
            "statistics": {"type": "object", "properties": {"competition": {"type": "string"}, "season": {"type": "integer"}}},
            "biggest_wins": {"type": "object", "properties": {"competition": {"type": "string"}, "limit": {"type": "integer"}}}}


def dispatch(data: SoccerData, name: str, args: dict[str, Any]) -> Any:
    if name == "search_players": return data.players_search(**args)
    if name == "standings": return data.standings(**args)
    if name == "statistics": return data.statistics(**args)
    if name == "biggest_wins": return data.biggest_wins(**args)
    if name == "team_stats": return data.team_stats(**args)
    if name == "head_to_head": return data.head_to_head(**args)
    if name == "find_matches": return data.find_matches(**args)
    raise ValueError(f"Unknown tool: {name}")


def main() -> None:
    data = SoccerData()
    for line in sys.stdin:
        try:
            request = json.loads(line)
            method, request_id = request.get("method"), request.get("id")
            if method == "initialize": result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "brazilian-soccer", "version": "1.0.0"}}
            elif method == "notifications/initialized": continue
            elif method == "tools/list": result = {"tools": [{"name": n, "description": d, "inputSchema": schemas()[n]} for n, d in TOOLS]}
            elif method == "tools/call":
                params = request.get("params", {}); result = {"content": [{"type": "text", "text": json.dumps(dispatch(data, params["name"], params.get("arguments", {})), ensure_ascii=False)}]}
            else: raise ValueError(f"Unsupported method: {method}")
            if request_id is not None: print(json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result}, ensure_ascii=False), flush=True)
        except Exception as exc:
            if request.get("id") is not None: print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "error": {"code": -32603, "message": str(exc)}}, ensure_ascii=False), flush=True)


if __name__ == "__main__": main()
