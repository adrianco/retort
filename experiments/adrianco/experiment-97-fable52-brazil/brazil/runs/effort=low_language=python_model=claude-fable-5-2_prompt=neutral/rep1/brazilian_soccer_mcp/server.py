"""MCP server (stdio, JSON-RPC 2.0) exposing the Brazilian soccer knowledge base.

Implemented with the standard library only, so it runs without extra packages:

    python -m brazilian_soccer_mcp.server

Each tool returns human-readable text ready for an LLM to relay.
"""
from __future__ import annotations

import json
import sys

from .queries import RANK_METRICS, KnowledgeBase, load_default, resolve_competition

PROTOCOL_VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05"]
SERVER_INFO = {"name": "brazilian-soccer", "version": "1.0.0"}


# ------------------------------------------------------------------ formatting
def fmt_match(m, stats=False) -> str:
    score = f"{m.home_goals}-{m.away_goals}" if m.played else "vs (no result in data)"
    rnd = m.round
    if rnd.isdigit():
        rnd = f"Round {rnd}"
    ctx = f"{m.competition} {m.season}" + (f", {rnd}" if rnd else "")
    if m.arena:
        ctx += f", {m.arena}"
    line = f"- {m.date or 'date unknown'}: {m.home} {score} {m.away} ({ctx})"
    if stats and m.stats:
        s = m.stats
        parts = [f"{label} {s[h]}-{s[a]}" for label, h, a in (
            ("corners", "home_corner", "away_corner"), ("shots", "home_shots", "away_shots"),
            ("attacks", "home_attack", "away_attack")) if h in s and a in s]
        if parts:
            line += " [" + ", ".join(parts) + "]"
    return line


def fmt_matches(ms, limit, stats=False) -> list:
    limit = int(limit) if limit else 20
    lines = [fmt_match(m, stats) for m in ms[:limit]]
    if len(ms) > limit:
        lines.append(f"- ... ({len(ms) - limit} more matches in dataset)")
    return lines


def fmt_record(r) -> list:
    return [
        f"- Matches: {r['matches']}",
        f"- Wins: {r['wins']}, Draws: {r['draws']}, Losses: {r['losses']}",
        f"- Goals For: {r['goals_for']}, Goals Against: {r['goals_against']}",
        f"- Win rate: {r['win_rate']}%",
    ]


def fmt_player(i, p) -> str:
    return (f"{i}. {p.name} - Overall: {p.overall}, Position: {p.position or 'n/a'}, "
            f"Club: {p.club or 'no club'}, Nationality: {p.nationality}, Age: {p.age}")


def _scope(competition=None, season=None, venue=None) -> str:
    parts = [str(x) for x in (season, resolve_competition(competition)) if x]
    if venue and venue != "either":
        parts.append(venue)
    return f" ({' '.join(parts)})" if parts else " (all data)"


# ----------------------------------------------------------------------- tools
def t_search_matches(kb, team=None, opponent=None, venue="either", competition=None,
                     season=None, date_from=None, date_to=None, stage=None, limit=20,
                     include_stats=False):
    ms = kb.search_matches(team, opponent, venue, competition, season, date_from, date_to, stage)
    if not ms:
        return "No matches found for those criteria."
    head = f"{len(ms)} match(es) found"
    if team:
        head += f" for {kb.team_name(team)}"
    if opponent:
        head += f" vs {kb.team_name(opponent)}"
    return "\n".join([head + " (most recent first):"] + fmt_matches(ms, limit, include_stats))


def t_head_to_head(kb, team_a, team_b, competition=None, season=None, limit=10):
    h = kb.head_to_head(team_a, team_b, competition, season)
    title = f"{h['team_a']} vs {h['team_b']}" + (f" ({h['rivalry']})" if h["rivalry"] else "")
    if not h["match_list"]:
        return f"{title}: no matches in dataset."
    return "\n".join(
        [title + ":"] + fmt_matches(h["match_list"], limit) + [
            "",
            f"Head-to-head in dataset ({h['matches']} played): {h['team_a']} {h['team_a_wins']} "
            f"wins, {h['team_b']} {h['team_b_wins']} wins, {h['draws']} draws",
            f"Goals: {h['team_a']} {h['team_a_goals']}, {h['team_b']} {h['team_b_goals']}",
        ])


def t_team_stats(kb, team, season=None, competition=None, venue="either"):
    r = kb.team_stats(team, season, competition, venue)
    if not r["matches"]:
        return f"No played matches found for {r['team']}{_scope(r['competition'], season, r['venue'])}."
    label = {"home": "home record", "away": "away record"}.get(r["venue"], "record")
    return "\n".join([f"{r['team']} {label}{_scope(r['competition'], season)}:"] + fmt_record(r)
                     + [f"- Goal difference: {r['goal_difference']:+d}, Points: {r['points']}"])


def t_team_profile(kb, team):
    p = kb.team_profile(team)
    lines = [f"{p['team']} - profile from all datasets:", "Overall record:"] + fmt_record(p["overall"])
    for label in ("home", "away"):
        r = p[label]
        lines.append(f"{label.title()}: {r['wins']}W {r['draws']}D {r['losses']}L in "
                     f"{r['matches']} ({r['win_rate']}% wins)")
    lines.append("Competitions played:")
    for c in p["competitions"]:
        lines.append(f"- {c['competition']}: seasons {c['seasons'][0]}-{c['seasons'][-1]}, "
                     f"{c['matches']} matches, {c['wins']}W {c['draws']}D {c['losses']}L, "
                     f"goals {c['goals_for']}-{c['goals_against']}")
    if p["players"]:
        lines.append(f"FIFA squad ({len(p['players'])} players):")
        lines += [fmt_player(i, pl) for i, pl in enumerate(p["players"][:15], 1)]
    else:
        lines.append("FIFA squad: no players for this club in the FIFA dataset.")
    return "\n".join(lines)


def t_standings(kb, season, competition="Brasileirão", limit=None):
    s = kb.standings(season, competition)
    lines = [f"{s['season']} {s['competition']} standings (calculated from matches):"]
    rows = s["table"][: int(limit)] if limit else s["table"]
    for r in rows:
        note = f" - {r['note']}" if r["note"] else ""
        lines.append(f"{r['position']}. {r['team']} - {r['points']} pts ({r['wins']}W, "
                     f"{r['draws']}D, {r['losses']}L, GF {r['goals_for']}, GA "
                     f"{r['goals_against']}, GD {r['goal_difference']:+d}){note}")
    if not s["complete"]:
        lines.append("Note: the data for this season/competition is incomplete or not a single "
                     "round-robin league, so no champion/relegation labels are shown.")
    else:
        lines.append("Note: relegation = bottom places by points; point deductions and tribunal "
                     "decisions are not in the data.")
    return "\n".join(lines)


def t_bracket(kb, season, competition="Libertadores", limit_per_stage=40):
    b = kb.bracket(season, competition)
    lines = [f"{b['season']} {b['competition']} - matches by stage:"]
    for stage, ms in b["stages"]:
        lines.append(f"\n{stage.title()} ({len(ms)} matches):")
        lines += fmt_matches(ms, limit_per_stage)
    return "\n".join(lines)


def t_competition_stats(kb, competition=None, season=None):
    s = kb.competition_stats(competition, season)
    if not s["matches"]:
        return "No played matches found for those criteria."
    return "\n".join([
        f"Statistics for {s['competition']}" + (f" {s['season']}" if s["season"] else "") + ":",
        f"- Matches played: {s['matches']}",
        f"- Total goals: {s['goals']} (home {s['home_goals']}, away {s['away_goals']})",
        f"- Average goals per match: {s['avg_goals']}",
        f"- Home win rate: {s['home_win_rate']}%, Draws: {s['draw_rate']}%, "
        f"Away win rate: {s['away_win_rate']}%",
    ])


def t_compare_seasons(kb, seasons, competition="Brasileirão"):
    lines = [f"Season comparison ({competition}):"]
    for s in kb.compare_seasons(seasons, competition):
        lines.append(f"{s['season']}: {s['matches']} matches, {s['goals']} goals "
                     f"({s['avg_goals']} per match), home wins {s['home_win_rate']}%, draws "
                     f"{s['draw_rate']}%, away wins {s['away_win_rate']}%")
        if s.get("leader"):
            lines.append(f"  Top of table: {s['leader']} ({s['leader_points']} pts); most goals: "
                         f"{s['top_scoring_team']} ({s['top_scoring_goals']})")
    return "\n".join(lines)


def t_rank_teams(kb, metric="win_rate", competition=None, season=None, venue="either",
                 min_matches=10, limit=10):
    rows = kb.rank_teams(metric, competition, season, venue, min_matches, limit)
    if not rows:
        return "No teams meet those criteria (try lowering min_matches)."
    lines = [f"Teams ranked by {metric}{_scope(competition, season, venue)}, "
             f"min {min_matches} matches:"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. {r['team']} - {r['wins']}W {r['draws']}D {r['losses']}L in "
                     f"{r['matches']}, win rate {r['win_rate']}%, goals {r['goals_for']}-"
                     f"{r['goals_against']}, {r['points']} pts")
    return "\n".join(lines)


def t_biggest_wins(kb, competition=None, season=None, team=None, limit=10):
    ms = kb.biggest_wins(competition, season, team, limit)
    if not ms:
        return "No decisive matches found for those criteria."
    lines = [f"Biggest victories{_scope(competition, season)}:"]
    for i, m in enumerate(ms, 1):
        lines.append(f"{i}. {m.date}: {m.home} {m.home_goals}-{m.away_goals} {m.away} "
                     f"({m.competition} {m.season})")
    return "\n".join(lines)


def t_derbies(kb, season=None, competition=None, limit=50):
    ds = kb.derbies(season, competition)
    if not ds:
        return "No derbies found for those criteria."
    limit = int(limit or 50)
    lines = [f"{len(ds)} derby match(es){_scope(competition, season)}:"]
    lines += [f"{fmt_match(m)} [{name}]" for name, m in ds[:limit]]
    if len(ds) > limit:
        lines.append(f"- ... ({len(ds) - limit} more)")
    return "\n".join(lines)


def t_search_players(kb, name=None, nationality=None, club=None, position=None,
                     min_overall=None, limit=20):
    ps = kb.search_players(name, nationality, club, position, min_overall, None)
    if not ps:
        msg = "No players found for those criteria."
        if club:
            msg += (" Note: the FIFA dataset does not license every Brazilian club "
                    "(e.g. Flamengo, Palmeiras, Corinthians, São Paulo and Vasco are absent).")
        return msg
    limit = int(limit or 20)
    lines = [f"{len(ps)} player(s) found (sorted by overall rating):"]
    lines += [fmt_player(i, p) for i, p in enumerate(ps[:limit], 1)]
    if len(ps) > limit:
        lines.append(f"... ({len(ps) - limit} more players in dataset)")
    return "\n".join(lines)


def t_player_details(kb, player):
    p = kb.get_player(player)
    if p is None:
        return f"No player matching {player!r} in the FIFA dataset."
    top = sorted(p.skills.items(), key=lambda kv: -kv[1])[:8]
    return "\n".join([
        f"{p.name} (FIFA ID {p.id})",
        f"- Age: {p.age}, Nationality: {p.nationality}",
        f"- Club: {p.club or 'no club'}, Position: {p.position or 'n/a'}, Jersey: {p.jersey}",
        f"- Overall: {p.overall}, Potential: {p.potential}",
        f"- Height: {p.height}, Weight: {p.weight}, Preferred foot: {p.foot}",
        f"- Value: {p.value}, Wage: {p.wage}",
        "- Best attributes: " + ", ".join(f"{k} {v}" for k, v in top),
    ])


def t_club_summary(kb, nationality="Brazil", brazilian_clubs_only=True, limit=30):
    rows = kb.club_summary(nationality, brazilian_clubs_only)
    if not rows:
        return "No players found for those criteria."
    where = "Brazilian clubs" if brazilian_clubs_only else "all clubs"
    lines = [f"{nationality} players at {where}:"]
    lines += [f"- {r['club']}: {r['players']} players (avg rating: {r['avg_overall']}, "
              f"best: {r['best_player']})" for r in rows[: int(limit or 30)]]
    return "\n".join(lines)


def t_data_summary(kb):
    s = kb.summary()
    lines = ["Brazilian soccer knowledge base:", "Source files (rows loaded):"]
    lines += [f"- {f}: {n}" for f, n in s["source_rows"].items()]
    lines.append(f"- fifa_data.csv: {s['players']} players")
    lines.append(f"Unique matches after merging duplicates across files: {s['unique_matches']}")
    lines += [f"- {c}: {v['matches']} matches, seasons {v['seasons']}"
              for c, v in s["competitions"].items()]
    lines.append(f"Teams: {s['teams']}")
    lines.append("Not available: individual goal scorers (top-scorer queries cannot be answered).")
    return "\n".join(lines)


_S, _I, _B = {"type": "string"}, {"type": "integer"}, {"type": "boolean"}
_TEAM = {**_S, "description": "Team name; any spelling works (Flamengo, Flamengo-RJ, Sao Paulo, Atlético Mineiro)"}
_COMP = {**_S, "description": "Brasileirão / Serie A, Serie B, Serie C, Copa do Brasil or Libertadores"}
_SEASON = {**_I, "description": "Season year, e.g. 2019"}
_VENUE = {"type": "string", "enum": ["home", "away", "either"], "default": "either"}
_LIMIT = {**_I, "description": "Maximum rows to return"}


def _tool(fn, description, props, required=()):
    return {"fn": fn, "description": description,
            "inputSchema": {"type": "object", "properties": props, "required": list(required)}}


TOOLS = {
    "search_matches": _tool(
        t_search_matches,
        "Find matches by team, opponent, venue, competition, season, date range and/or stage "
        "(stage='final' gives cup finals). Most recent first, so limit=1 answers 'when did X "
        "last play Y?'.",
        {"team": _TEAM, "opponent": _TEAM, "venue": _VENUE, "competition": _COMP,
         "season": _SEASON, "date_from": {**_S, "description": "YYYY-MM-DD or DD/MM/YYYY"},
         "date_to": {**_S, "description": "YYYY-MM-DD or DD/MM/YYYY"},
         "stage": {**_S, "description": "Round number or stage: final, semifinals, quarterfinals, round of 16, group stage"},
         "limit": _LIMIT, "include_stats": {**_B, "description": "Add corners/shots/attacks when available"}}),
    "head_to_head": _tool(
        t_head_to_head, "Head-to-head record and recent matches between two teams.",
        {"team_a": _TEAM, "team_b": _TEAM, "competition": _COMP, "season": _SEASON, "limit": _LIMIT},
        ["team_a", "team_b"]),
    "team_stats": _tool(
        t_team_stats, "Win/draw/loss record and goals for a team, optionally by season, "
        "competition and home/away venue.",
        {"team": _TEAM, "season": _SEASON, "competition": _COMP, "venue": _VENUE}, ["team"]),
    "team_profile": _tool(
        t_team_profile, "Everything about a team across all files: overall/home/away record, "
        "competitions and seasons played, and its players in the FIFA dataset.",
        {"team": _TEAM}, ["team"]),
    "standings": _tool(
        t_standings, "League table for a season calculated from match results (champion and "
        "relegated teams for Serie A).",
        {"season": _SEASON, "competition": _COMP, "limit": _LIMIT}, ["season"]),
    "competition_bracket": _tool(
        t_bracket, "All matches of a cup season (Libertadores or Copa do Brasil) grouped by stage.",
        {"season": _SEASON, "competition": _COMP, "limit_per_stage": _LIMIT}, ["season"]),
    "competition_stats": _tool(
        t_competition_stats, "Aggregate statistics: matches, goals per match, home/draw/away rates.",
        {"competition": _COMP, "season": _SEASON}),
    "compare_seasons": _tool(
        t_compare_seasons, "Compare aggregate statistics of several seasons of one competition.",
        {"seasons": {"type": "array", "items": _I}, "competition": _COMP}, ["seasons"]),
    "rank_teams": _tool(
        t_rank_teams, "Rank teams by a metric (best home/away record, most goals scored, "
        "fewest conceded...).",
        {"metric": {"type": "string", "enum": sorted(RANK_METRICS), "default": "win_rate"},
         "competition": _COMP, "season": _SEASON, "venue": _VENUE,
         "min_matches": {**_I, "default": 10}, "limit": _LIMIT}),
    "biggest_wins": _tool(
        t_biggest_wins, "Largest winning margins, optionally by competition, season or team.",
        {"competition": _COMP, "season": _SEASON, "team": _TEAM, "limit": _LIMIT}),
    "derbies": _tool(
        t_derbies, "Matches between traditional rivals (Fla-Flu, Grenal, Derby Paulista...).",
        {"season": _SEASON, "competition": _COMP, "limit": _LIMIT}),
    "search_players": _tool(
        t_search_players, "Search FIFA players by name, nationality, club and position "
        "(code such as ST, or goalkeeper/defender/midfielder/forward). Sorted by rating.",
        {"name": _S, "nationality": {**_S, "description": "e.g. Brazil"}, "club": _S,
         "position": _S, "min_overall": _I, "limit": _LIMIT}),
    "player_details": _tool(
        t_player_details, "Full FIFA profile of one player (by name or FIFA ID).",
        {"player": _S}, ["player"]),
    "players_by_club": _tool(
        t_club_summary, "Player count and average rating per club for a nationality "
        "(default: Brazilian players at Brazilian clubs).",
        {"nationality": _S, "brazilian_clubs_only": _B, "limit": _LIMIT}),
    "data_summary": _tool(t_data_summary, "What data is loaded: files, competitions, seasons.", {}),
}


def call_tool(name: str, arguments: dict | None = None, kb: KnowledgeBase | None = None) -> str:
    """Run a tool and return its text. Raises ValueError for bad input."""
    if name not in TOOLS:
        raise KeyError(name)
    args = {k: v for k, v in (arguments or {}).items() if v is not None}
    spec = TOOLS[name]
    unknown = set(args) - set(spec["inputSchema"]["properties"])
    if unknown:
        raise ValueError(f"Unknown argument(s) for {name}: {sorted(unknown)}")
    missing = [k for k in spec["inputSchema"]["required"] if k not in args]
    if missing:
        raise ValueError(f"Missing required argument(s) for {name}: {missing}")
    return spec["fn"](kb or load_default(), **args)


# -------------------------------------------------------------------- protocol
def handle(msg: dict, kb: KnowledgeBase | None = None):
    """Handle one JSON-RPC message; returns the response dict or None."""
    mid, method = msg.get("id"), msg.get("method")
    if method is None or "id" not in msg:
        return None  # notification or a response: nothing to send

    def ok(result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def err(code, message):
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}

    params = msg.get("params") or {}
    if method == "initialize":
        wanted = params.get("protocolVersion")
        return ok({
            "protocolVersion": wanted if wanted in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
            "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO,
            "instructions": "Brazilian soccer data (Brasileirão, Copa do Brasil, Libertadores, "
                            "FIFA players). Call data_summary to see coverage.",
        })
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": [{"name": n, "description": t["description"],
                              "inputSchema": t["inputSchema"]} for n, t in TOOLS.items()]})
    if method == "tools/call":
        name = params.get("name")
        if name not in TOOLS:
            return err(-32602, f"Unknown tool: {name}")
        try:
            text, is_error = call_tool(name, params.get("arguments"), kb), False
        except (ValueError, TypeError) as exc:
            text, is_error = f"Error: {exc}", True
        return ok({"content": [{"type": "text", "text": text}], "isError": is_error})
    return err(-32601, f"Method not found: {method}")


def serve(stdin=None, stdout=None) -> None:
    stdin, stdout = stdin or sys.stdin, stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            if not isinstance(msg, dict):
                resp = {"jsonrpc": "2.0", "id": None,
                        "error": {"code": -32600, "message": "Invalid request"}}
            else:
                try:
                    resp = handle(msg)
                except Exception as exc:  # keep the server alive on unexpected failures
                    resp = {"jsonrpc": "2.0", "id": msg.get("id"),
                            "error": {"code": -32603, "message": f"Internal error: {exc}"}}
        if resp is not None:
            stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            stdout.flush()


def main() -> None:
    for stream in (sys.stdin, sys.stdout):
        stream.reconfigure(encoding="utf-8")
    serve()


if __name__ == "__main__":
    main()
