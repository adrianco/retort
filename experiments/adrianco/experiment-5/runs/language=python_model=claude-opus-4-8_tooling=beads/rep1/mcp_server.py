"""
================================================================================
Module: mcp_server.py
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
Context
-------
The MCP (Model Context Protocol) server front-end. It exposes the
``SoccerGraph`` query engine as a set of MCP *tools* an LLM can call to answer
natural-language questions about Brazilian soccer.

The official ``mcp`` Python SDK is not installable in this sandbox (no network),
so this module implements the small slice of the MCP wire protocol we need
directly: newline-delimited JSON-RPC 2.0 over stdio, with the standard methods
``initialize``, ``tools/list`` and ``tools/call`` (plus ``ping``). This keeps
the server dependency-free while remaining compatible with any MCP client.

Design
------
* ``ToolRegistry`` maps tool name -> (schema, handler). Handlers receive the
  parsed arguments dict and the shared ``SoccerGraph`` and return display text.
* ``MCPServer.handle(request)`` is pure (dict in / dict-or-None out) so the
  protocol layer is unit-testable without real stdio.
* ``serve()`` runs the blocking stdio read/write loop.

Run as a stand-alone MCP server:   python mcp_server.py
================================================================================
"""

from __future__ import annotations

import json
import sys
from typing import Callable, Optional

from knowledge_graph import SoccerGraph, TeamResolutionError
from data_loader import SERIE_A, SERIE_B, SERIE_C, COPA_BRASIL, LIBERTADORES

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "brazilian-soccer-mcp"
SERVER_VERSION = "1.0.0"

# --------------------------------------------------------------------------- #
# Competition name resolution (accept many user spellings)                    #
# --------------------------------------------------------------------------- #
_COMPETITION_ALIASES = {
    "brasileirao": SERIE_A, "brasileirao serie a": SERIE_A, "serie a": SERIE_A,
    "campeonato brasileiro": SERIE_A, "brazilian league": SERIE_A,
    "serie b": SERIE_B, "brasileirao serie b": SERIE_B,
    "serie c": SERIE_C, "brasileirao serie c": SERIE_C,
    "copa do brasil": COPA_BRASIL, "brazilian cup": COPA_BRASIL,
    "cup": COPA_BRASIL,
    "libertadores": LIBERTADORES, "copa libertadores": LIBERTADORES,
}


def resolve_competition(name: Optional[str]) -> Optional[str]:
    """Map a free-text competition name to a canonical competition string."""
    if not name:
        return None
    from normalize import strip_accents
    key = strip_accents(name).lower().strip()
    if key in _COMPETITION_ALIASES:
        return _COMPETITION_ALIASES[key]
    # already canonical?
    for canon in (SERIE_A, SERIE_B, SERIE_C, COPA_BRASIL, LIBERTADORES):
        if strip_accents(canon).lower() == key:
            return canon
    return name  # pass through; engine will simply find nothing


# --------------------------------------------------------------------------- #
# Formatting helpers                                                          #
# --------------------------------------------------------------------------- #
def _fmt_matches(matches, header: str, max_show: int = 25) -> str:
    if not matches:
        return f"{header}\nNo matches found."
    lines = [header]
    for m in matches[:max_show]:
        lines.append("- " + m.summary())
    if len(matches) > max_show:
        lines.append(f"... ({len(matches) - max_show} more, {len(matches)} total)")
    else:
        lines.append(f"({len(matches)} total)")
    return "\n".join(lines)


def _fmt_record(r: dict) -> str:
    scope = []
    if r.get("competition"):
        scope.append(r["competition"])
    if r.get("season"):
        scope.append(str(r["season"]))
    if r.get("venue") and r["venue"] != "all":
        scope.append(f"{r['venue']} games")
    scope_str = (" (" + ", ".join(scope) + ")") if scope else ""
    return (
        f"{r['team']} record{scope_str}:\n"
        f"- Matches: {r['played']}\n"
        f"- Wins: {r['wins']}, Draws: {r['draws']}, Losses: {r['losses']}\n"
        f"- Goals For: {r['goals_for']}, Goals Against: {r['goals_against']} "
        f"(GD {r['goal_difference']:+d})\n"
        f"- Points: {r['points']}\n"
        f"- Win rate: {r['win_rate']}%"
    )


def _fmt_standings(table: list[dict], competition: str, season: int) -> str:
    if not table:
        return f"No standings available for {competition} {season}."
    lines = [f"{competition} {season} — Final Standings (calculated from matches):"]
    for r in table:
        tag = "  ← Champion" if r["position"] == 1 else ""
        lines.append(
            f"{r['position']:2}. {r['team']:<18} {r['points']:>3} pts "
            f"({r['wins']}W {r['draws']}D {r['losses']}L, GD {r['goal_difference']:+d}){tag}"
        )
    return "\n".join(lines)


def _fmt_players(players, header: str) -> str:
    if not players:
        return f"{header}\nNo players found."
    lines = [header]
    for i, p in enumerate(players, 1):
        bits = []
        if p.overall is not None:
            bits.append(f"Overall: {p.overall}")
        if p.position:
            bits.append(f"Position: {p.position}")
        if p.club:
            bits.append(f"Club: {p.club}")
        if p.nationality:
            bits.append(p.nationality)
        lines.append(f"{i}. {p.name} - " + ", ".join(bits))
    return "\n".join(lines)


def _fmt_h2h(h: dict) -> str:
    lines = [
        f"Head-to-head: {h['team_a']} vs {h['team_b']}",
        f"- Matches: {h['total_matches']}",
        f"- {h['team_a']} wins: {h['team_a_wins']}, "
        f"{h['team_b']} wins: {h['team_b_wins']}, Draws: {h['draws']}",
        f"- Goals: {h['team_a']} {h['team_a_goals']} - {h['team_b_goals']} {h['team_b']}",
    ]
    if h["matches"]:
        lines.append("Recent meetings:")
        for m in h["matches"][:10]:
            lines.append("  - " + m.summary())
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool handlers                                                               #
# --------------------------------------------------------------------------- #
def _h_find_matches(g: SoccerGraph, a: dict) -> str:
    matches = g.find_matches(
        team=a.get("team"), team2=a.get("opponent"),
        competition=resolve_competition(a.get("competition")),
        season=a.get("season"), date_from=a.get("date_from"),
        date_to=a.get("date_to"), venue=a.get("venue", "either"),
        limit=a.get("limit", 25),
    )
    parts = [p for p in (a.get("team"), a.get("opponent")) if p]
    header = "Matches" + (": " + " vs ".join(parts) if parts else "")
    return _fmt_matches(matches, header)


def _h_head_to_head(g: SoccerGraph, a: dict) -> str:
    h = g.head_to_head(a["team_a"], a["team_b"],
                       competition=resolve_competition(a.get("competition")))
    return _fmt_h2h(h)


def _h_team_record(g: SoccerGraph, a: dict) -> str:
    r = g.team_record(a["team"], season=a.get("season"),
                      competition=resolve_competition(a.get("competition")),
                      venue=a.get("venue", "all"))
    return _fmt_record(r)


def _h_compare_teams(g: SoccerGraph, a: dict) -> str:
    c = g.compare_teams(a["team_a"], a["team_b"], season=a.get("season"),
                        competition=resolve_competition(a.get("competition")))
    return "\n\n".join([
        _fmt_h2h(c["head_to_head"]),
        _fmt_record(c["team_a_record"]),
        _fmt_record(c["team_b_record"]),
    ])


def _h_find_players(g: SoccerGraph, a: dict) -> str:
    players = g.find_players(
        name=a.get("name"), nationality=a.get("nationality"),
        club=a.get("club"), position=a.get("position"),
        min_overall=a.get("min_overall"), sort_by=a.get("sort_by", "overall"),
        limit=a.get("limit", 25),
    )
    crit = []
    for k in ("name", "nationality", "club", "position"):
        if a.get(k):
            crit.append(f"{k}={a[k]}")
    header = "Players" + (" (" + ", ".join(crit) + ")" if crit else "") + ":"
    return _fmt_players(players, header)


def _h_standings(g: SoccerGraph, a: dict) -> str:
    comp = resolve_competition(a.get("competition")) or SERIE_A
    season = a["season"]
    return _fmt_standings(g.standings(comp, season), comp, season)


def _h_average_goals(g: SoccerGraph, a: dict) -> str:
    comp = resolve_competition(a.get("competition"))
    s = g.average_goals(comp, a.get("season"))
    scope = " / ".join(str(x) for x in (s["competition"], s["season"]) if x) or "all data"
    return (
        f"Statistics ({scope}):\n"
        f"- Matches analysed: {s['matches']}\n"
        f"- Average goals per match: {s['avg_goals_per_match']}\n"
        f"- Home win rate: {s['home_win_rate']}%\n"
        f"- Away win rate: {s['away_win_rate']}%\n"
        f"- Draw rate: {s['draw_rate']}%"
    )


def _h_biggest_wins(g: SoccerGraph, a: dict) -> str:
    comp = resolve_competition(a.get("competition"))
    matches = g.biggest_wins(comp, a.get("season"), limit=a.get("limit", 10))
    return _fmt_matches(matches, "Biggest victories (by goal margin):", max_show=a.get("limit", 10))


def _h_best_record(g: SoccerGraph, a: dict) -> str:
    comp = resolve_competition(a.get("competition"))
    recs = g.best_record(venue=a.get("venue", "all"), competition=comp,
                         season=a.get("season"), min_matches=a.get("min_matches", 10),
                         by=a.get("by", "win_rate"), limit=a.get("limit", 10))
    if not recs:
        return "No teams matched the criteria."
    venue = a.get("venue", "all")
    lines = [f"Best {venue} records (min {a.get('min_matches', 10)} matches):"]
    for i, r in enumerate(recs, 1):
        lines.append(
            f"{i}. {r['team']:<18} win rate {r['win_rate']}% "
            f"({r['wins']}W {r['draws']}D {r['losses']}L, {r['points']} pts)"
        )
    return "\n".join(lines)


def _h_list_teams(g: SoccerGraph, a: dict) -> str:
    comp = resolve_competition(a.get("competition"))
    teams = g.list_teams(comp)
    return f"{len(teams)} teams:\n" + ", ".join(teams)


def _h_list_competitions(g: SoccerGraph, a: dict) -> str:
    return "Competitions:\n- " + "\n- ".join(g.list_competitions())


def _h_list_seasons(g: SoccerGraph, a: dict) -> str:
    comp = resolve_competition(a.get("competition"))
    seasons = g.list_seasons(comp)
    label = comp or "all competitions"
    return f"Seasons for {label}: " + ", ".join(str(s) for s in seasons)


# --------------------------------------------------------------------------- #
# Tool registry                                                               #
# --------------------------------------------------------------------------- #
def _tool(name, description, properties, required, handler):
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
        "handler": handler,
    }


_STR = {"type": "string"}
_INT = {"type": "integer"}
_VENUE = {"type": "string", "enum": ["all", "home", "away", "either"]}

TOOLS = [
    _tool("find_matches",
          "Find matches by team, opponent, competition, season and/or date range. "
          "Use 'venue' (home/away/either) relative to 'team'.",
          {"team": _STR, "opponent": _STR, "competition": _STR, "season": _INT,
           "date_from": _STR, "date_to": _STR, "venue": _VENUE, "limit": _INT},
          [], _h_find_matches),
    _tool("head_to_head",
          "Head-to-head record and recent meetings between two teams.",
          {"team_a": _STR, "team_b": _STR, "competition": _STR},
          ["team_a", "team_b"], _h_head_to_head),
    _tool("team_record",
          "Win/draw/loss and goals record for a team, optionally filtered by "
          "season, competition and venue (home/away/all).",
          {"team": _STR, "season": _INT, "competition": _STR, "venue": _VENUE},
          ["team"], _h_team_record),
    _tool("compare_teams",
          "Compare two teams: head-to-head plus each team's record.",
          {"team_a": _STR, "team_b": _STR, "season": _INT, "competition": _STR},
          ["team_a", "team_b"], _h_compare_teams),
    _tool("find_players",
          "Search FIFA players by name, nationality, club, position and minimum "
          "overall rating. sort_by: overall|potential|age|name.",
          {"name": _STR, "nationality": _STR, "club": _STR, "position": _STR,
           "min_overall": _INT, "sort_by": _STR, "limit": _INT},
          [], _h_find_players),
    _tool("standings",
          "Compute the league table for a competition+season from match results "
          "(3 pts win, 1 draw).",
          {"competition": _STR, "season": _INT}, ["season"], _h_standings),
    _tool("average_goals",
          "Goals-per-match average and home/away/draw rates for a competition "
          "and/or season (omit both for all data).",
          {"competition": _STR, "season": _INT}, [], _h_average_goals),
    _tool("biggest_wins",
          "Largest victories by goal margin, optionally scoped to a competition "
          "and/or season.",
          {"competition": _STR, "season": _INT, "limit": _INT}, [], _h_biggest_wins),
    _tool("best_record",
          "Rank teams by record. venue: all|home|away; by: win_rate|points.",
          {"venue": _VENUE, "competition": _STR, "season": _INT,
           "min_matches": _INT, "by": _STR, "limit": _INT}, [], _h_best_record),
    _tool("list_teams", "List all teams (optionally within a competition).",
          {"competition": _STR}, [], _h_list_teams),
    _tool("list_competitions", "List all competitions available in the data.",
          {}, [], _h_list_competitions),
    _tool("list_seasons", "List seasons available (optionally for a competition).",
          {"competition": _STR}, [], _h_list_seasons),
]


# --------------------------------------------------------------------------- #
# JSON-RPC / MCP server                                                       #
# --------------------------------------------------------------------------- #
class MCPServer:
    """Minimal MCP server: pure dict-in/dict-out request handling."""

    def __init__(self, graph: Optional[SoccerGraph] = None,
                 data_dir: Optional[str] = None):
        self.graph = graph or SoccerGraph.from_data_dir(data_dir)
        self.handlers: dict[str, Callable] = {t["name"]: t["handler"] for t in TOOLS}
        self._tool_list = [
            {k: t[k] for k in ("name", "description", "inputSchema")} for t in TOOLS
        ]

    # -- tool dispatch (used by tests directly) -------------------------- #
    def call_tool(self, name: str, arguments: dict) -> str:
        if name not in self.handlers:
            raise KeyError(f"Unknown tool: {name}")
        return self.handlers[name](self.graph, arguments or {})

    # -- JSON-RPC handling ---------------------------------------------- #
    def handle(self, req: dict) -> Optional[dict]:
        """Handle one JSON-RPC request. Returns a response dict, or None for
        notifications (which must not be answered)."""
        method = req.get("method")
        req_id = req.get("id")
        is_notification = "id" not in req

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                }
            elif method in ("notifications/initialized", "initialized"):
                return None
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": self._tool_list}
            elif method == "tools/call":
                params = req.get("params") or {}
                name = params.get("name")
                args = params.get("arguments") or {}
                text = self.call_tool(name, args)
                result = {"content": [{"type": "text", "text": text}],
                          "isError": False}
            else:
                if is_notification:
                    return None
                return self._error(req_id, -32601, f"Method not found: {method}")
        except (TeamResolutionError, KeyError, ValueError) as e:
            if method == "tools/call":
                # Tool errors are reported in-band per MCP convention.
                return self._result(req_id, {
                    "content": [{"type": "text", "text": f"Error: {e}"}],
                    "isError": True,
                })
            return self._error(req_id, -32602, str(e))
        except Exception as e:  # pragma: no cover - defensive
            return self._error(req_id, -32603, f"Internal error: {e}")

        if is_notification:
            return None
        return self._result(req_id, result)

    @staticmethod
    def _result(req_id, result) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    @staticmethod
    def _error(req_id, code, message) -> dict:
        return {"jsonrpc": "2.0", "id": req_id,
                "error": {"code": code, "message": message}}

    # -- stdio transport ------------------------------------------------- #
    def serve(self, stdin=None, stdout=None):
        """Blocking newline-delimited JSON-RPC loop over stdio."""
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError:
                continue
            resp = self.handle(req)
            if resp is not None:
                stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                stdout.flush()


def main():
    server = MCPServer()
    print(f"[{SERVER_NAME}] ready: {len(server.graph.ds.matches)} matches, "
          f"{len(server.graph.ds.players)} players loaded.", file=sys.stderr)
    server.serve()


if __name__ == "__main__":
    main()
