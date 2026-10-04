"""Brazilian Soccer MCP server (stdio transport, JSON-RPC 2.0).

Implements the MCP lifecycle (initialize, tools/list, tools/call, ping) directly so
no third-party SDK is required.  Run with:  python3 server.py
"""
from __future__ import annotations

import json
import sys
import traceback

from soccer_data import display_team, format_player, get_db

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "brazilian-soccer", "version": "1.0.0"}

S = "string"
I = "integer"


def _schema(props: dict, required=()):
    return {"type": "object",
            "properties": {k: {"type": t, "description": d} for k, (t, d) in props.items()},
            "required": list(required)}


COMMON = {
    "competition": (S, "Brasileirão, Copa do Brasil, Libertadores, Serie B or Serie C"),
    "season": (I, "Season year, e.g. 2019"),
}


# ------------------------------------------------------------------ tool impls
def _match_list(ms, limit):
    lines = [f"- {m.format()}" for m in ms[:limit]]
    if len(ms) > limit:
        lines.append(f"- ... ({len(ms) - limit} more matches in dataset)")
    return lines


def search_matches(team=None, opponent=None, venue="any", competition=None, season=None,
                   date_from=None, date_to=None, stage=None, limit=20):
    db = get_db()
    ms = db.find_matches(team, opponent, venue or "any", competition, season, date_from,
                         date_to, stage)
    if not ms:
        return "No matches found for those criteria."
    title = "Matches"
    if team and opponent:
        title = f"{display_team(db.resolve_team(team))} vs {display_team(db.resolve_team(opponent))}"
    elif team:
        title = f"{display_team(db.resolve_team(team))} matches"
    out = [f"{title} ({len(ms)} found):"] + _match_list(ms, limit)
    if team and opponent:
        h = db.head_to_head(team, opponent, competition, season)
        out.append(f"\nHead-to-head in dataset: {h['team_a']} {h['a_wins']} wins, "
                   f"{h['team_b']} {h['b_wins']} wins, {h['draws']} draws")
    return "\n".join(out)


def last_match(team, opponent=None):
    ms = get_db().find_matches(team, opponent, limit=1)
    return f"Most recent match: {ms[0].format()}" if ms else "No match found."


def head_to_head(team_a, team_b, competition=None, season=None, limit=10):
    h = get_db().head_to_head(team_a, team_b, competition, season)
    if not h["matches"]:
        return f"No matches found between {h['team_a']} and {h['team_b']}."
    out = [f"{h['team_a']} vs {h['team_b']} — {len(h['matches'])} matches:",
           f"{h['team_a']}: {h['a_wins']} wins ({h['a_goals']} goals)",
           f"{h['team_b']}: {h['b_wins']} wins ({h['b_goals']} goals)",
           f"Draws: {h['draws']}", "Recent matches:"] + _match_list(h["matches"], limit)
    return "\n".join(out)


def team_record(team, season=None, competition=None, venue="any"):
    r = get_db().team_record(team, season, competition, venue or "any")
    label = {"home": "home record", "away": "away record"}.get(venue, "record")
    scope = " ".join(str(x) for x in (season, competition) if x) or "all data"
    return (f"{r['team']} {label} ({scope}):\n- Matches: {r['matches']}\n"
            f"- Wins: {r['wins']}, Draws: {r['draws']}, Losses: {r['losses']}\n"
            f"- Goals For: {r['goals_for']}, Goals Against: {r['goals_against']}\n"
            f"- Points: {r['points']}\n- Win rate: {r['win_rate']}%")


def standings(season, competition="Brasileirão", limit=None):
    db = get_db()
    table = db.standings(season, competition or "Brasileirão")
    if not table:
        return f"No data for {competition} {season}."
    out = [f"{season} {competition or 'Brasileirão'} Final Standings (calculated from matches):"]
    n = len(table)
    for r in table[: limit or n]:
        note = ""
        if r["position"] == 1:
            note = " - Champion"
        elif (competition or "Brasileirão") == "Brasileirão" and r["position"] > n - 4:
            note = " - Relegated"
        out.append(f"{r['position']}. {r['team']} - {r['points']} pts ({r['wins']}W, {r['draws']}D, "
                   f"{r['losses']}L, GF {r['goals_for']}, GA {r['goals_against']}){note}")
    return "\n".join(out)


def champion(season, competition="Brasileirão"):
    db = get_db()
    comp = competition or "Brasileirão"
    if comp in ("Copa do Brasil", "Libertadores"):
        finals = [m for m in db.cup_finals(comp) if m.season == int(season)]
        if not finals:
            return f"No final found for {comp} {season}."
        teams = {finals[0].home, finals[0].away}
        agg = {t: sum(m.home_goal if m.home == t else m.away_goal for m in finals) for t in teams}
        lines = [f"{comp} {season} final:"] + [f"- {m.format()}" for m in finals]
        a, b = sorted(agg, key=lambda t: -agg[t])
        if agg[a] != agg[b]:
            lines.append(f"Winner (aggregate {agg[a]}-{agg[b]}): {display_team(a)}")
        else:
            lines.append(f"Aggregate level {agg[a]}-{agg[b]} (decided on penalties; not in data)")
        return "\n".join(lines)
    table = db.standings(season, comp)
    if not table:
        return f"No data for {comp} {season}."
    t = table[0]
    return (f"{t['team']} won the {season} {comp} with {t['points']} points "
            f"({t['wins']}W, {t['draws']}D, {t['losses']}L), calculated from match results.")


def relegated(season):
    table = get_db().standings(season)
    if not table:
        return f"No data for {season}."
    bottom = table[-4:]
    return f"Relegated from {season} Brasileirão (bottom 4, calculated):\n" + "\n".join(
        f"{r['position']}. {r['team']} - {r['points']} pts" for r in bottom)


def cup_finals(competition="Copa do Brasil", season=None):
    finals = get_db().cup_finals(competition or "Copa do Brasil")
    if season:
        finals = [m for m in finals if m.season == int(season)]
    if not finals:
        return "No finals found."
    return f"{competition or 'Copa do Brasil'} finals:\n" + "\n".join(f"- {m.format()}" for m in finals)


def bracket(season, competition="Libertadores"):
    db = get_db()
    comp = competition or "Libertadores"
    ms = [m for m in db.find_matches(competition=comp, season=season)]
    if comp == "Libertadores":
        stages = ["round of 16", "quarterfinals", "semifinals", "final"]
    else:
        stages = sorted({m.round for m in ms}, key=lambda r: int(r) if r.isdigit() else 99)
    out = [f"{season} {comp} knockout bracket:"]
    for st in stages:
        sm = sorted([m for m in ms if m.round == st], key=lambda m: m.date)
        if sm:
            out.append(f"\n{st.title() if not st.isdigit() else 'Round ' + st}:")
            out += [f"- {m.format()}" for m in sm]
    return "\n".join(out) if len(out) > 1 else f"No knockout data for {comp} {season}."


def derbies(season=None, team=None, limit=30):
    ds = get_db().derbies(season, team)
    if not ds:
        return "No derby matches found."
    out = [f"Derbies ({len(ds)} found):"] + [f"- [{n}] {m.format()}" for n, m in ds[:limit]]
    if len(ds) > limit:
        out.append(f"- ... ({len(ds) - limit} more)")
    return "\n".join(out)


def team_competitions(team):
    db = get_db()
    comps = db.competitions_for_team(team)
    name = display_team(db.resolve_team(team))
    if not comps:
        return f"No matches found for {name}."
    return f"{name} competitions in dataset:\n" + "\n".join(
        f"- {c}: {n} matches" for c, n in sorted(comps.items(), key=lambda x: -x[1]))


def league_stats(competition=None, season=None, team=None):
    s = get_db().stats(competition, season, team)
    if not s["matches"]:
        return "No matches for those criteria."
    scope = ", ".join(str(x) for x in (competition, season, team) if x) or "all competitions"
    return (f"Statistics ({scope}):\n- Matches: {s['matches']}\n- Total goals: {s['total_goals']}\n"
            f"- Average goals per match: {s['avg_goals']}\n- Home win rate: {s['home_win_rate']}%\n"
            f"- Away win rate: {s['away_win_rate']}%\n- Draw rate: {s['draw_rate']}%")


def compare_seasons(season_a, season_b, competition="Brasileirão"):
    db = get_db()
    lines = [f"{competition} {season_a} vs {season_b}:"]
    for s in (season_a, season_b):
        st = db.stats(competition, s)
        if not st["matches"]:
            lines.append(f"- {s}: no data")
            continue
        champ = db.standings(s, competition)[0]["team"] if competition in (
            "Brasileirão", "Serie B", "Serie C") else "n/a"
        lines.append(f"- {s}: {st['matches']} matches, {st['avg_goals']} goals/match, home wins "
                     f"{st['home_win_rate']}%, draws {st['draw_rate']}%, champion: {champ}")
    return "\n".join(lines)


def biggest_wins(competition=None, season=None, team=None, limit=10):
    db = get_db()
    ms = db.biggest_wins(competition, season, team, limit)
    s = db.stats(competition, season, team)
    out = [f"Biggest victories ({competition or 'all competitions'}):"]
    out += [f"{i}. {m.format()}" for i, m in enumerate(ms, 1)]
    if s["matches"]:
        out.append(f"\nAverage goals per match: {s['avg_goals']}\nHome win rate: {s['home_win_rate']}%")
    return "\n".join(out)


def best_records(venue="home", competition="Brasileirão", season=None, limit=10):
    rows = get_db().best_records(venue or "home", competition or "Brasileirão", season,
                                 limit=limit)
    out = [f"Best {venue or 'home'} records ({competition or 'Brasileirão'}"
           f"{' ' + str(season) if season else ''}):"]
    out += [f"{i}. {r['team']} - {r['win_rate']}% wins ({r['wins']}W {r['draws']}D {r['losses']}L "
            f"in {r['matches']})" for i, r in enumerate(rows, 1)]
    return "\n".join(out)


def top_scoring_teams(season=None, competition="Brasileirão", limit=10):
    rows = get_db().top_scoring_teams(season, competition or "Brasileirão", limit)
    return f"Most goals scored ({competition or 'Brasileirão'} {season or 'all seasons'}):\n" + \
        "\n".join(f"{i}. {r['team']} - {r['goals_for']} goals in {r['matches']} matches"
                  for i, r in enumerate(rows, 1))


def search_players(name=None, nationality=None, club=None, position=None, min_overall=None,
                   brazilian_clubs_only=False, limit=20):
    db = get_db()
    ps = db.search_players(name, nationality, club, position, min_overall,
                           bool(brazilian_clubs_only), limit=None)
    if not ps:
        return "No players found." + (" (Note: FIFA 19 data does not license some Brazilian "
                                      "clubs such as Flamengo, Palmeiras, Corinthians, São Paulo.)"
                                      if club else "")
    out = [f"Players found: {len(ps)}"]
    out += [f"{i}. {format_player(p)}" for i, p in enumerate(ps[:limit], 1)]
    if len(ps) > limit:
        out.append(f"... ({len(ps) - limit} more)")
    return "\n".join(out)


def brazilian_clubs_players():
    rows = get_db().brazilian_club_summary()
    return "Brazilian players at Brazilian clubs (FIFA data):\n" + "\n".join(
        f"- {r['club']}: {r['players']} players (avg rating: {r['avg_rating']})" for r in rows)


def team_profile(team):
    p = get_db().team_profile(team)
    r = p["record"]
    out = [f"{p['team']} profile:",
           f"Overall record: {r['matches']} matches, {r['wins']}W {r['draws']}D {r['losses']}L, "
           f"GF {r['goals_for']} GA {r['goals_against']} ({r['win_rate']}% wins)",
           "Competitions: " + ", ".join(f"{c} ({n})" for c, n in p["competitions"].items())]
    if p["squad"]:
        out.append(f"FIFA squad ({len(p['squad'])} players), top rated:")
        out += [f"- {format_player(x)}" for x in p["squad"][:10]]
    else:
        out.append("No FIFA player data for this club.")
    return "\n".join(out)


TOOLS = {
    "search_matches": (search_matches, "Find matches by team, opponent, venue, competition, "
                       "season, date range (YYYY-MM-DD or DD/MM/YYYY) or stage/round.",
                       _schema({"team": (S, "Team name (any variation)"),
                                "opponent": (S, "Opponent team"),
                                "venue": (S, "home, away or any"), **COMMON,
                                "date_from": (S, "Start date"), "date_to": (S, "End date"),
                                "stage": (S, "Stage/round, e.g. final"), "limit": (I, "Max rows")})),
    "last_match": (last_match, "Most recent match of a team (optionally vs an opponent).",
                   _schema({"team": (S, "Team"), "opponent": (S, "Opponent")}, ["team"])),
    "head_to_head": (head_to_head, "Head-to-head record between two teams.",
                     _schema({"team_a": (S, "First team"), "team_b": (S, "Second team"),
                              **COMMON, "limit": (I, "Matches to list")}, ["team_a", "team_b"])),
    "team_record": (team_record, "Win/draw/loss and goals record for a team.",
                    _schema({"team": (S, "Team"), **COMMON, "venue": (S, "home, away or any")},
                            ["team"])),
    "standings": (standings, "League table for a season calculated from match results.",
                  _schema({"season": (I, "Season"), "competition": COMMON["competition"],
                           "limit": (I, "Rows")}, ["season"])),
    "champion": (champion, "Who won a competition in a season.",
                 _schema({"season": (I, "Season"), "competition": COMMON["competition"]},
                         ["season"])),
    "relegated": (relegated, "Teams relegated from the Brasileirão in a season.",
                  _schema({"season": (I, "Season")}, ["season"])),
    "cup_finals": (cup_finals, "List Copa do Brasil or Libertadores finals.",
                   _schema({"competition": COMMON["competition"], "season": COMMON["season"]})),
    "bracket": (bracket, "Knockout bracket of a cup competition for a season.",
                _schema({"season": (I, "Season"), "competition": COMMON["competition"]},
                        ["season"])),
    "derbies": (derbies, "Traditional rivalry matches (Fla-Flu, Grenal, ...).",
                _schema({"season": COMMON["season"], "team": (S, "Team"), "limit": (I, "Rows")})),
    "team_competitions": (team_competitions, "Competitions a team played in, with match counts.",
                          _schema({"team": (S, "Team")}, ["team"])),
    "league_stats": (league_stats, "Goals per match, home/away/draw rates.",
                     _schema({**COMMON, "team": (S, "Team")})),
    "compare_seasons": (compare_seasons, "Compare aggregate statistics of two seasons.",
                        _schema({"season_a": (I, "Season"), "season_b": (I, "Season"),
                                 "competition": COMMON["competition"]}, ["season_a", "season_b"])),
    "biggest_wins": (biggest_wins, "Largest victory margins.",
                     _schema({**COMMON, "team": (S, "Team"), "limit": (I, "Rows")})),
    "best_records": (best_records, "Teams with best home/away/overall win rate.",
                     _schema({"venue": (S, "home, away or any"), **COMMON, "limit": (I, "Rows")})),
    "top_scoring_teams": (top_scoring_teams, "Teams that scored the most goals.",
                          _schema({**COMMON, "limit": (I, "Rows")})),
    "search_players": (search_players, "Search FIFA player data by name, nationality, club, "
                       "position (or group: forward/midfielder/defender/goalkeeper), rating.",
                       _schema({"name": (S, "Player name"), "nationality": (S, "e.g. Brazil"),
                                "club": (S, "Club"), "position": (S, "Position or group"),
                                "min_overall": (I, "Minimum overall rating"),
                                "brazilian_clubs_only": ("boolean", "Only players at Brazilian clubs"),
                                "limit": (I, "Rows")})),
    "brazilian_clubs_players": (brazilian_clubs_players,
                                "Count/avg rating of Brazilian players per Brazilian club.",
                                _schema({})),
    "team_profile": (team_profile, "Cross-dataset profile: match record + FIFA squad.",
                     _schema({"team": (S, "Team")}, ["team"])),
}


def call_tool(name: str, args: dict | None) -> str:
    if name not in TOOLS:
        raise KeyError(f"Unknown tool: {name}")
    fn = TOOLS[name][0]
    return fn(**{k: v for k, v in (args or {}).items() if v is not None})


def handle(msg: dict) -> dict | None:
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:  # notification
        return None
    try:
        if method == "initialize":
            result = {"protocolVersion": msg.get("params", {}).get("protocolVersion", PROTOCOL_VERSION),
                      "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": [{"name": n, "description": d, "inputSchema": s}
                                for n, (_, d, s) in TOOLS.items()]}
        elif method == "tools/call":
            p = msg.get("params", {})
            try:
                text, err = call_tool(p.get("name"), p.get("arguments")), False
            except Exception as e:  # tool errors are reported in-band per MCP
                text, err = f"Error: {e}", True
            result = {"content": [{"type": "text", "text": text}], "isError": err}
        else:
            return {"jsonrpc": "2.0", "id": mid,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}}
        return {"jsonrpc": "2.0", "id": mid, "result": result}
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": str(e)}}


def main():
    get_db()  # warm the cache
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
