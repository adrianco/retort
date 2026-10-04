"""MCP server (JSON-RPC 2.0 over stdio, newline-delimited) exposing Brazilian soccer tools.

Run: python3 server.py
"""
from __future__ import annotations

import json
import sys
import traceback

import soccer

PROTOCOL_VERSION = "2024-11-05"
S, I = {"type": "string"}, {"type": "integer"}


def _schema(props: dict, required=()):
    return {"type": "object", "properties": props, "required": list(required)}


VENUE = {"type": "string", "enum": ["any", "home", "away"]}
COMP = {"type": "string", "description": "Brasileirão / Serie A, Serie B, Serie C, Copa do Brasil, Libertadores"}

TOOLS = {
    "search_matches": (soccer.search_matches, "Find matches by team, opponent, competition, season, date range, venue or stage (e.g. 'final').",
                       _schema(dict(team=S, opponent=S, competition=COMP, season=I, date_from=S, date_to=S,
                                    venue=VENUE, stage=S, limit=I))),
    "last_match": (soccer.last_match, "Most recent match of a team, optionally against a given opponent.",
                   _schema(dict(team=S, opponent=S), ["team"])),
    "head_to_head": (soccer.head_to_head, "Head-to-head record and match list between two teams.",
                     _schema(dict(team_a=S, team_b=S, competition=COMP, limit=I), ["team_a", "team_b"])),
    "team_record": (soccer.team_record, "Win/draw/loss and goals record for a team, filterable by season, competition and home/away.",
                    _schema(dict(team=S, season=I, competition=COMP, venue=VENUE), ["team"])),
    "standings": (soccer.standings, "Brasileirão league table for a season, calculated from match results.",
                  _schema(dict(season=I, top=I), ["season"])),
    "champion": (soccer.champion, "Brasileirão champion for a season (calculated).", _schema(dict(season=I), ["season"])),
    "relegated": (soccer.relegated, "Bottom-4 (relegated) teams for a Brasileirão season (calculated).",
                  _schema(dict(season=I), ["season"])),
    "league_stats": (soccer.league_stats, "Average goals per match, home/away win and draw rates.",
                     _schema(dict(competition=COMP, season=I))),
    "biggest_wins": (soccer.biggest_wins, "Largest victory margins, optionally by competition, season or team.",
                     _schema(dict(competition=COMP, season=I, team=S, limit=I))),
    "best_records": (soccer.best_records, "Rank teams by win rate, goals or points per game (overall/home/away).",
                     _schema(dict(competition=COMP, season=I, venue=VENUE, min_matches=I, limit=I,
                                  sort_by={"type": "string", "enum": ["win_rate", "goals", "points_per_game"]}))),
    "top_scoring_teams": (soccer.top_scoring_teams, "Teams that scored the most goals in a season/competition.",
                          _schema(dict(season=I, competition=COMP, limit=I))),
    "team_competitions": (soccer.team_competitions, "Which competitions/seasons a team appears in across all files.",
                          _schema(dict(team=S), ["team"])),
    "derbies": (soccer.derbies, "Traditional rivalry matches (Fla-Flu, Grenal, Derby Paulista...).",
                _schema(dict(season=I, competition=COMP, limit=I))),
    "compare_seasons": (soccer.compare_seasons, "Compare aggregate statistics across seasons.",
                        _schema(dict(seasons={"type": "array", "items": I}, competition=COMP), ["seasons"])),
    "libertadores_bracket": (soccer.libertadores_bracket, "Knockout-stage results of a Copa Libertadores season.",
                             _schema(dict(season=I), ["season"])),
    "search_players": (soccer.search_players, "Search FIFA player data by name, nationality, club, position (or group: forward, midfielder, defender, goalkeeper) and min rating.",
                       _schema(dict(name=S, nationality=S, club=S, position=S, min_overall=I, limit=I))),
    "brazilian_clubs_summary": (soccer.brazilian_clubs_summary, "Player counts and average ratings for Brazilian clubs in the FIFA data.",
                                _schema({})),
    "club_profile": (soccer.club_profile, "Cross-dataset profile: match record, competitions and FIFA squad for a club.",
                     _schema(dict(team=S), ["team"])),
    "dataset_info": (soccer.dataset_info, "Summary of loaded datasets.", _schema({})),
}


def call_tool(name: str, args: dict) -> str:
    if name not in TOOLS:
        raise KeyError(f"Unknown tool: {name}")
    fn, _, schema = TOOLS[name]
    clean = {k: v for k, v in (args or {}).items() if k in schema["properties"] and v not in (None, "")}
    return fn(**clean)


def handle(msg: dict) -> dict | None:
    mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if mid is None:  # notification
        return None
    try:
        if method == "initialize":
            result = {"protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
                      "capabilities": {"tools": {}},
                      "serverInfo": {"name": "brazilian-soccer", "version": "1.0.0"}}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": [{"name": n, "description": d, "inputSchema": s} for n, (_, d, s) in TOOLS.items()]}
        elif method == "tools/call":
            try:
                text, err = call_tool(params.get("name"), params.get("arguments") or {}), False
            except Exception as e:  # report tool errors in-band per MCP spec
                text, err = f"Error: {e}", True
            result = {"content": [{"type": "text", "text": text}], "isError": err}
        else:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Method not found: {method}"}}
        return {"jsonrpc": "2.0", "id": mid, "result": result}
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": str(e)}}


def main():
    soccer.KB.get()  # preload data
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            resp = handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
