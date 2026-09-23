"""Brazilian Soccer MCP server (stdio JSON-RPC 2.0, no external dependencies).

Run: python3 mcp_server.py   (configure as a stdio MCP server in your client)
"""
from __future__ import annotations

import json
import sys

from soccer_data import get_db

PROTOCOL_VERSION = "2024-11-05"


def _fmt_record(title: str, r: dict) -> str:
    return (f"{title}:\n- Matches: {r['matches']}\n- Wins: {r['wins']}, Draws: {r['draws']}, "
            f"Losses: {r['losses']}\n- Goals For: {r['goals_for']}, Goals Against: {r['goals_against']}\n"
            f"- Points: {r['points']}\n- Win rate: {r['win_rate']}%")


def _fmt_matches(ms, limit: int) -> str:
    lines = [f"- {m.format()}" for m in ms[:limit]]
    if len(ms) > limit:
        lines.append(f"- ... ({len(ms) - limit} more matches in dataset)")
    return "\n".join(lines) if lines else "No matches found."


def t_search_matches(team=None, opponent=None, venue="any", competition=None, season=None,
                     date_from=None, date_to=None, round_contains=None, limit=20):
    db = get_db()
    ms = db.find_matches(team, opponent, venue, competition, season, date_from, date_to, round_contains)
    return f"Found {len(ms)} matches:\n" + _fmt_matches(ms, int(limit))


def t_head_to_head(team_a, team_b, competition=None, limit=15):
    h = get_db().head_to_head(team_a, team_b, competition)
    title = f"{h['team_a']} vs {h['team_b']}" + (f" ({h['rivalry']})" if h["rivalry"] else "")
    return (f"{title}:\n{_fmt_matches(h['matches'], int(limit))}\n\n"
            f"Head-to-head in dataset: {h['team_a']} {h['a_wins']} wins, {h['team_b']} {h['b_wins']} wins, "
            f"{h['draws']} draws (goals {h['a_goals']}-{h['b_goals']})")


def t_team_stats(team, season=None, competition=None, venue="any"):
    s = get_db().team_stats(team, season, competition, venue)
    parts = [p for p in ((venue + " record") if venue != "any" else "record",
                         str(season) if season else None, competition) if p]
    return _fmt_record(f"{s['team']} " + " ".join(parts), s)


def t_standings(season, limit=20):
    table = get_db().standings(int(season))
    if not table:
        return f"No Brasileirão data for {season}."
    lines = [f"{season} Brasileirão Final Standings (calculated from matches):"]
    for r in table[: int(limit)]:
        tag = " - Champion" if r["position"] == 1 else (" - Relegation zone" if r["position"] > len(table) - 4 else "")
        lines.append(f"{r['position']}. {r['team']} - {r['points']} pts ({r['wins']}W, {r['draws']}D, "
                     f"{r['losses']}L, GF {r['goals_for']}, GA {r['goals_against']}){tag}")
    return "\n".join(lines)


def t_team_rankings(metric="home_win_rate", competition="Brasileirão", season=None, min_matches=10, limit=10):
    rows = get_db().rankings(metric, competition, season, int(min_matches), int(limit))
    lines = [f"Team rankings by {metric} ({competition or 'all competitions'}{', ' + str(season) if season else ''}):"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. {r['team']} - {r['matches']} matches, {r['wins']}W {r['draws']}D {r['losses']}L, "
                     f"GF {r['goals_for']}, GA {r['goals_against']}, win rate {r['win_rate']}%")
    return "\n".join(lines)


def t_competition_stats(competition=None, season=None):
    a = get_db().aggregate(competition, season)
    if not a["matches"]:
        return "No matches found."
    return (f"Statistics ({competition or 'all competitions'}{', ' + str(season) if season else ''}):\n"
            f"- Matches: {a['matches']}\n- Total goals: {a['total_goals']}\n"
            f"- Average goals per match: {a['avg_goals']}\n- Home win rate: {a['home_win_rate']}%\n"
            f"- Away win rate: {a['away_win_rate']}%\n- Draw rate: {a['draw_rate']}%")


def t_biggest_wins(competition=None, season=None, team=None, limit=10):
    ms = get_db().biggest_wins(competition, season, team, int(limit))
    return "Biggest victories:\n" + "\n".join(f"{i}. {m.format()}" for i, m in enumerate(ms, 1))


def t_derbies(season=None, competition=None, limit=30):
    return "Derby matches:\n" + _fmt_matches(get_db().derbies(season, competition), int(limit))


def t_team_competitions(team):
    db = get_db()
    comps = db.competitions_for(team)
    name = db.team_name(db.resolve_team(team))
    return f"{name} competitions in dataset:\n" + "\n".join(
        f"- {c}: seasons {', '.join(map(str, s))}" for c, s in sorted(comps.items())) if comps else f"No matches for {team}."


def t_search_players(name=None, nationality=None, club=None, position=None, min_overall=None, limit=20):
    ps = get_db().search_players(name, nationality, club, position, min_overall, int(limit))
    if not ps:
        return "No players found."
    return f"Players ({len(ps)} shown):\n" + "\n".join(
        f"{i}. {p['Name']} - Overall: {p['Overall']}, Potential: {p['Potential']}, Position: {p['Position']}, "
        f"Age: {p['Age']}, Nationality: {p['Nationality']}, Club: {p['Club'] or 'Free agent'}"
        for i, p in enumerate(ps, 1))


def t_brazilian_club_players():
    rows = get_db().brazilian_club_players()
    return "Brazilian players at Brazilian clubs:\n" + "\n".join(
        f"- {r['club']}: {r['players']} players (avg rating: {r['avg_rating']})" for r in rows)


def t_club_profile(team):
    p = get_db().club_profile(team)
    out = [_fmt_record(f"{p['team']} overall record (all competitions)", p["record"]),
           "Competitions: " + ", ".join(sorted(p["competitions"])),
           f"FIFA players at club: {len(p['players'])}"]
    out += [f"- {x['Name']} ({x['Position']}, {x['Overall']})" for x in p["players"][:15]]
    return "\n".join(out)


S, I = {"type": "string"}, {"type": "integer"}
COMP = {"type": "string", "description": "Brasileirão / Copa do Brasil / Libertadores / Serie B / Serie C"}
VENUE = {"type": "string", "enum": ["any", "home", "away"]}

TOOLS = {
    "search_matches": (t_search_matches, "Find matches by team, opponent, venue, competition, season, date range (YYYY-MM-DD) or round/stage text (e.g. 'final').",
                       {"team": S, "opponent": S, "venue": VENUE, "competition": COMP, "season": I,
                        "date_from": S, "date_to": S, "round_contains": S, "limit": I}, []),
    "head_to_head": (t_head_to_head, "Head-to-head matches and record between two teams.",
                     {"team_a": S, "team_b": S, "competition": COMP, "limit": I}, ["team_a", "team_b"]),
    "team_stats": (t_team_stats, "Win/draw/loss and goals record for a team, optionally by season, competition, venue.",
                   {"team": S, "season": I, "competition": COMP, "venue": VENUE}, ["team"]),
    "league_standings": (t_standings, "Brasileirão table for a season, computed from match results (champion, relegation).",
                         {"season": I, "limit": I}, ["season"]),
    "team_rankings": (t_team_rankings, "Rank teams by metric: home_win_rate, away_win_rate, win_rate, goals_for, goals_against, points.",
                      {"metric": S, "competition": COMP, "season": I, "min_matches": I, "limit": I}, []),
    "competition_stats": (t_competition_stats, "Aggregate stats: average goals per match, home/away/draw rates.",
                          {"competition": COMP, "season": I}, []),
    "biggest_wins": (t_biggest_wins, "Largest victory margins, optionally filtered.",
                     {"competition": COMP, "season": I, "team": S, "limit": I}, []),
    "derbies": (t_derbies, "Traditional rivalry matches (Fla-Flu, Grenal, Derby Paulista, ...).",
                {"season": I, "competition": COMP, "limit": I}, []),
    "team_competitions": (t_team_competitions, "Which competitions and seasons a team appears in.", {"team": S}, ["team"]),
    "search_players": (t_search_players, "Search FIFA player data by name, nationality, club, position (code or 'forward'), min rating.",
                       {"name": S, "nationality": S, "club": S, "position": S, "min_overall": I, "limit": I}, []),
    "brazilian_club_players": (t_brazilian_club_players, "Count and average rating of Brazilian players at Brazilian clubs.", {}, []),
    "club_profile": (t_club_profile, "Cross-dataset club profile: match record, competitions and FIFA players.", {"team": S}, ["team"]),
}


def list_tools() -> list[dict]:
    return [{"name": n, "description": d, "inputSchema": {"type": "object", "properties": p, "required": r}}
            for n, (_, d, p, r) in TOOLS.items()]


def call_tool(name: str, args: dict | None = None) -> str:
    if name not in TOOLS:
        raise KeyError(f"Unknown tool: {name}")
    fn, _, props, _ = TOOLS[name]
    args = {k: v for k, v in (args or {}).items() if k in props and v not in (None, "")}
    return fn(**args)


def handle(req: dict) -> dict | None:
    method, rid = req.get("method"), req.get("id")
    if rid is None:  # notification
        return None
    try:
        if method == "initialize":
            result = {"protocolVersion": PROTOCOL_VERSION, "capabilities": {"tools": {}},
                      "serverInfo": {"name": "brazilian-soccer", "version": "1.0.0"}}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": list_tools()}
        elif method == "tools/call":
            p = req.get("params", {})
            try:
                text, err = call_tool(p.get("name"), p.get("arguments", {})), False
            except Exception as e:  # tool errors are reported in-band
                text, err = f"Error: {e}", True
            result = {"content": [{"type": "text", "text": text}], "isError": err}
        else:
            return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Method not found: {method}"}}
        return {"jsonrpc": "2.0", "id": rid, "result": result}
    except Exception as e:
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32603, "message": str(e)}}


def main():
    get_db()  # preload data
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            resp = handle(json.loads(line))
        except json.JSONDecodeError:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
