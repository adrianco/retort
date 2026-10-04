"""MCP (Model Context Protocol) server exposing the Brazilian soccer data.

Implements the MCP stdio transport (newline-delimited JSON-RPC 2.0) with the
standard library only, so it runs without installing anything:

    python -m brazilian_soccer.server

Each tool returns human-readable text that an LLM can quote directly.
"""

from __future__ import annotations

import json
import sys

from . import service
from .data import Match
from .service import QueryError, SoccerData

SERVER_INFO = {"name": "brazilian-soccer", "version": "1.0.0"}
PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
MAX_LIMIT = 200

# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #


def format_match(m: Match) -> str:
    detail = m.competition
    if m.round:
        detail += f" Round {m.round}"
    if m.stage:
        detail += f", {m.stage}"
    if m.competition not in (str(m.season),):
        detail += f" {m.season}"
    if m.arena:
        detail += f", {m.arena}"
    when = m.date.isoformat() if m.date else "date unknown"
    return f"{when}: {m.home} {m.home_goals}-{m.away_goals} {m.away} ({detail})"


def _record_lines(r: dict) -> list[str]:
    return [
        f"- Matches: {r['matches']}",
        f"- Wins: {r['wins']}, Draws: {r['draws']}, Losses: {r['losses']}",
        f"- Goals For: {r['goals_for']}, Goals Against: {r['goals_against']} "
        f"(difference {r['goal_difference']:+d})",
        f"- Points: {r['points']} ({r['points_per_match']} per match)",
        f"- Win rate: {r['win_rate']}%",
    ]


def _scope(competition=None, season=None) -> str:
    parts = [str(p) for p in (season, competition) if p]
    return " ".join(parts) if parts else "all competitions and seasons"


def _limit(value, default: int) -> int:
    try:
        return max(1, min(MAX_LIMIT, int(value)))
    except (TypeError, ValueError):
        return default


def _player_line(p: dict) -> str:
    return (f"{p['name']} - Overall: {p['overall']}, Potential: {p['potential']}, "
            f"Position: {p['position'] or 'n/a'}, Age: {p['age']}, "
            f"Nationality: {p['nationality']}, Club: {p['club'] or 'free agent'}")


def _table_lines(rows: list[dict]) -> list[str]:
    return [f"{r['position']}. {r['team']} - {r['points']} pts "
            f"({r['wins']}W, {r['draws']}D, {r['losses']}L, "
            f"GF {r['goals_for']}, GA {r['goals_against']}, GD {r['goal_difference']:+d})"
            for r in rows]


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #

TOOLS: dict[str, dict] = {}

_TEAM = {"type": "string", "description": "Team name; any common spelling works "
         "(e.g. 'Flamengo', 'Palmeiras-SP', 'Sao Paulo', 'Atlético-MG')."}
_COMPETITION = {"type": "string", "description": "Competition: 'Brasileirão' (Serie A), "
                "'Copa do Brasil', 'Libertadores', 'Serie B' or 'Serie C'. Omit for all."}
_SEASON = {"type": "integer", "description": "Season year, e.g. 2019. Omit for all seasons."}
_VENUE = {"type": "string", "enum": ["home", "away", "either"],
          "description": "Restrict to the team's home or away matches (default either)."}
_LIMIT = {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT,
          "description": "Maximum number of results to list."}


def tool(name: str, description: str, properties: dict | None = None, required=()):
    def register(func):
        TOOLS[name] = {
            "handler": func,
            "spec": {
                "name": name,
                "description": description,
                "inputSchema": {"type": "object", "properties": properties or {},
                                "required": list(required)},
            },
        }
        return func
    return register


@tool("search_matches",
      "Find matches by team, opponent, competition, season, date range, venue or stage. "
      "Results are newest first, so limit=1 answers 'when did X last play Y?'.",
      {"team": _TEAM, "opponent": {**_TEAM, "description": "Optional second team."},
       "competition": _COMPETITION, "season": _SEASON,
       "date_from": {"type": "string", "description": "Earliest date (YYYY-MM-DD or DD/MM/YYYY)."},
       "date_to": {"type": "string", "description": "Latest date (YYYY-MM-DD or DD/MM/YYYY)."},
       "venue": _VENUE,
       "stage": {"type": "string", "description": "Round number or stage, e.g. '38', 'final', "
                 "'semifinals', 'group stage'."},
       "limit": _LIMIT})
def search_matches(db: SoccerData, team=None, opponent=None, competition=None, season=None,
                   date_from=None, date_to=None, venue="either", stage=None, limit=20) -> str:
    matches = db.find_matches(team, opponent, competition, season, date_from, date_to, venue, stage)
    if not matches:
        return "No matches found for those criteria."
    limit = _limit(limit, 20)
    lines = [f"Found {len(matches)} match(es); showing the {min(limit, len(matches))} most recent:"]
    lines += [f"- {format_match(m)}" for m in matches[:limit]]
    if len(matches) > limit:
        lines.append(f"- ... ({len(matches) - limit} more matches in dataset)")
    return "\n".join(lines)


@tool("head_to_head", "Head-to-head record between two teams, with the match list.",
      {"team_a": _TEAM, "team_b": _TEAM, "competition": _COMPETITION, "season": _SEASON,
       "limit": _LIMIT}, required=("team_a", "team_b"))
def head_to_head(db: SoccerData, team_a, team_b, competition=None, season=None, limit=10) -> str:
    h = db.head_to_head(team_a, team_b, competition, season)
    a, b = h["team_a"], h["team_b"]
    title = f"{a} vs {b}" + (f" ({h['derby']} derby)" if h["derby"] else "")
    if not h["total"]:
        return f"{title}: no matches found in the dataset."
    limit = _limit(limit, 10)
    lines = [f"{title}:"] + [f"- {format_match(m)}" for m in h["matches"][:limit]]
    if h["total"] > limit:
        lines.append(f"- ... ({h['total'] - limit} more matches in dataset)")
    lines += ["", f"Head-to-head in dataset ({h['total']} matches): {a} {h['wins_a']} wins, "
                  f"{b} {h['wins_b']} wins, {h['draws']} draws",
              f"Goals: {a} {h['goals_a']}, {b} {h['goals_b']}"]
    return "\n".join(lines)


@tool("team_stats",
      "Win/draw/loss record, goals and win rate for a team, optionally by season, "
      "competition and home/away, with a per-competition breakdown.",
      {"team": _TEAM, "season": _SEASON, "competition": _COMPETITION, "venue": _VENUE},
      required=("team",))
def team_stats(db: SoccerData, team, season=None, competition=None, venue="either") -> str:
    s = db.team_stats(team, season, competition, venue)
    label = {"home": " home", "away": " away", "either": ""}[s["venue"]]
    lines = [f"{s['team']}{label} record ({_scope(s['competition'], s['season'])}):"]
    if not s["matches"]:
        return lines[0] + " no matches found."
    lines += _record_lines(s)
    if len(s["by_competition"]) > 1:
        lines.append("By competition:")
        lines += [f"- {c}: {r['matches']} matches, {r['wins']}W {r['draws']}D {r['losses']}L, "
                  f"goals {r['goals_for']}-{r['goals_against']}"
                  for c, r in s["by_competition"].items()]
    return "\n".join(lines)


@tool("team_profile",
      "Overview of a club combining match data (record, competitions played) with its "
      "FIFA squad (top-rated players).",
      {"team": _TEAM, "season": _SEASON}, required=("team",))
def team_profile(db: SoccerData, team, season=None) -> str:
    p = db.team_profile(team, season)
    lines = [f"{p['team']}" + (f" ({p['state']})" if p["state"] else ""),
             f"Record ({_scope(None, p['stats']['season'])}):"]
    lines += _record_lines(p["stats"]) if p["stats"]["matches"] else ["- no matches found"]
    lines.append("Competitions in dataset:")
    for competition, info in p["competitions"].items():
        seasons = info["seasons"]
        lines.append(f"- {competition}: {info['matches']} matches, "
                     f"{len(seasons)} season(s) {seasons[0]}-{seasons[-1]}")
    squad = p["squad"]
    if squad["total"]:
        lines.append(f"FIFA squad ({squad['total']} players), top rated:")
        lines += [f"- {_player_line(x)}" for x in squad["players"][:10]]
    else:
        lines.append("FIFA squad: this club is not in the FIFA player dataset.")
    return "\n".join(lines)


@tool("standings",
      "League table for a season, calculated from match results (3 points per win). "
      "Shows the champion and, for Serie A, the relegation zone.",
      {"season": _SEASON, "competition": _COMPETITION, "limit": _LIMIT}, required=("season",))
def standings(db: SoccerData, season, competition="Brasileirão", limit=30) -> str:
    rows = db.standings(season, competition)
    summary = db.season_summary(season, competition)
    if summary["competition"] not in service.LEAGUES:
        return season_summary(db, season, competition)
    lines = [f"{summary['season']} {summary['competition']} standings (calculated from matches):"]
    relegated = set(summary["relegated"])
    for row, line in zip(rows, _table_lines(rows[:_limit(limit, 30)])):
        if row["team"] == summary["champion"]:
            line += " - Champion"
        elif row["team"] in relegated:
            line += " - Relegated"
        lines.append(line)
    if not summary["complete"]:
        lines.append("Note: the dataset does not contain a complete double round-robin for this "
                     "season (or the competition used groups/play-offs), so positions are indicative.")
    return "\n".join(lines)


@tool("season_summary",
      "Who won a competition in a season: league champion and relegated teams, or the "
      "cup final result, plus goal statistics.",
      {"season": _SEASON, "competition": _COMPETITION}, required=("season",))
def season_summary(db: SoccerData, season, competition="Brasileirão") -> str:
    s = db.season_summary(season, competition)
    lines = [f"{s['season']} {s['competition']}:"]
    if "standings" in s:
        rows = s["standings"]
        if s["champion"]:
            lines.append(f"- Champion: {s['champion']} ({rows[0]['points']} pts, {rows[0]['wins']}W "
                         f"{rows[0]['draws']}D {rows[0]['losses']}L)")
            lines.append(f"- Runner-up: {rows[1]['team']} ({rows[1]['points']} pts)")
        else:
            lines.append(f"- Best overall record: {rows[0]['team']} ({rows[0]['points']} pts)")
        if s["relegated"]:
            lines.append(f"- Relegated (bottom four): {', '.join(s['relegated'])}")
        if not s["complete"]:
            lines.append("- Note: season data is incomplete or not a plain double round-robin; "
                         "results are indicative.")
    else:
        final = s["final"]
        if final is None:
            lines.append("- The final is not present in the dataset for this season.")
        else:
            lines += [f"- Final: {format_match(m)}" for m in final["legs"]]
            a, b = final["aggregate"]
            lines.append(f"- Aggregate: {a} {final['aggregate'][a]}-{final['aggregate'][b]} {b}")
            lines.append(f"- Champion: {final['winner']}" if final["winner"] else
                         "- Champion: level on aggregate; the tie-break (penalties/away goals) "
                         "is not recorded in the dataset.")
            if final["inferred"]:
                lines.append("- Note: final inferred from the last fixtures of the season.")
    lines.append(f"- Matches: {s['matches']}, goals: {s['goals']} ({s['goals_per_match']} per match)")
    lines.append(f"- Home wins {s['home_win_rate']}%, draws {s['draw_rate']}%, "
                 f"away wins {s['away_win_rate']}%")
    return "\n".join(lines)


@tool("competition_stats",
      "Aggregate statistics: matches, goals per match, home/draw/away rates. "
      "Omit competition and season for the whole dataset.",
      {"competition": _COMPETITION, "season": _SEASON})
def competition_stats(db: SoccerData, competition=None, season=None) -> str:
    s = db.competition_stats(competition, season)
    if not s["matches"]:
        return "No matches found for those criteria."
    return "\n".join([
        f"Statistics for {_scope(s['competition'], s['season'])}:",
        f"- Matches: {s['matches']}",
        f"- Goals: {s['goals']} (home {s['home_goals']}, away {s['away_goals']})",
        f"- Average goals per match: {s['goals_per_match']}",
        f"- Home win rate: {s['home_win_rate']}% ({s['home_wins']})",
        f"- Draw rate: {s['draw_rate']}% ({s['draws']})",
        f"- Away win rate: {s['away_win_rate']}% ({s['away_wins']})",
    ])


@tool("compare_seasons", "Compare two seasons of a competition side by side.",
      {"season_a": _SEASON, "season_b": _SEASON, "competition": _COMPETITION},
      required=("season_a", "season_b"))
def compare_seasons(db: SoccerData, season_a, season_b, competition="Brasileirão") -> str:
    c = db.compare_seasons(season_a, season_b, competition)
    lines = [f"{c['competition']} season comparison:"]
    for season, s in c["seasons"].items():
        lines += [f"{season}:",
                  f"- Matches: {s['matches']}, goals: {s['goals']} ({s['goals_per_match']} per match)",
                  f"- Home wins {s['home_win_rate']}%, draws {s['draw_rate']}%, "
                  f"away wins {s['away_win_rate']}%",
                  f"- Best record: {s['leader']} ({s['leader_points']} pts)",
                  f"- Top attack: {s['top_attack']} ({s['top_attack_goals']} goals)",
                  f"- Biggest win: {format_match(s['biggest_win'])}"]
    return "\n".join(lines)


@tool("rank_teams",
      "Rank teams by a metric: best home/away record (win_rate), most goals scored "
      "(goals_for), best defence (goals_against), points, etc.",
      {"metric": {"type": "string",
                  "enum": ["win_rate", "points", "points_per_match", "wins", "goals_for",
                           "goals_against", "goal_difference"],
                  "description": "Ranking metric (default win_rate)."},
       "competition": _COMPETITION, "season": _SEASON, "venue": _VENUE,
       "min_matches": {"type": "integer", "description": "Ignore teams with fewer matches "
                       "(default 10)."},
       "limit": _LIMIT})
def rank_teams(db: SoccerData, metric="win_rate", competition=None, season=None, venue="either",
               min_matches=10, limit=10) -> str:
    rows = db.rank_teams(metric, competition, season, venue, min_matches, _limit(limit, 10))
    if not rows:
        return "No teams match those criteria."
    label = {"home": "home ", "away": "away ", "either": ""}[db._venue(venue)]
    lines = [f"Teams ranked by {label}{metric.replace('_', ' ')} "
             f"({_scope(db._competition(competition), season)}, min {min_matches} matches):"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. {r['team']} - {r['matches']} matches, {r['wins']}W {r['draws']}D "
                     f"{r['losses']}L, goals {r['goals_for']}-{r['goals_against']}, "
                     f"win rate {r['win_rate']}%, {r['points']} pts")
    return "\n".join(lines)


@tool("biggest_wins", "Largest margins of victory, optionally by competition, season or team.",
      {"competition": _COMPETITION, "season": _SEASON, "team": _TEAM, "limit": _LIMIT})
def biggest_wins(db: SoccerData, competition=None, season=None, team=None, limit=10) -> str:
    matches = db.biggest_wins(competition, season, team, _limit(limit, 10))
    if not matches:
        return "No matches found for those criteria."
    lines = [f"Biggest victories ({_scope(db._competition(competition), season)}):"]
    lines += [f"{i}. {format_match(m)}" for i, m in enumerate(matches, 1)]
    return "\n".join(lines)


@tool("list_derbies", "Matches between traditional rivals (Fla-Flu, Gre-Nal, Derby Paulista...).",
      {"season": _SEASON, "competition": _COMPETITION, "limit": _LIMIT})
def list_derbies(db: SoccerData, season=None, competition=None, limit=50) -> str:
    found = db.derbies(season, competition)
    if not found:
        return "No derby matches found for those criteria."
    limit = _limit(limit, 50)
    lines = [f"Derbies ({_scope(db._competition(competition), season)}): {len(found)} match(es)"]
    lines += [f"- {name}: {format_match(m)}" for name, m in found[:limit]]
    if len(found) > limit:
        lines.append(f"- ... ({len(found) - limit} more)")
    return "\n".join(lines)


@tool("team_competitions", "Which competitions and seasons a team appears in.",
      {"team": _TEAM}, required=("team",))
def team_competitions(db: SoccerData, team) -> str:
    c = db.team_competitions(team)
    lines = [f"Competitions played by {c['team']} in the dataset:"]
    for competition, info in c["competitions"].items():
        lines.append(f"- {competition}: {info['matches']} matches, seasons "
                     f"{', '.join(map(str, info['seasons']))}")
    return "\n".join(lines)


@tool("search_players",
      "Search the FIFA player database by name, nationality, club, position "
      "(code like 'ST' or group: goalkeeper/defender/midfielder/forward), rating or age.",
      {"name": {"type": "string", "description": "Full or partial player name."},
       "nationality": {"type": "string", "description": "Country, e.g. 'Brazil'."},
       "club": {"type": "string", "description": "Club name, e.g. 'Santos', 'Grêmio'."},
       "position": {"type": "string", "description": "Position code or group."},
       "min_overall": {"type": "integer", "description": "Minimum FIFA overall rating."},
       "max_age": {"type": "integer", "description": "Maximum age."},
       "brazilian_clubs_only": {"type": "boolean",
                                "description": "Only players at Brazilian clubs."},
       "sort_by": {"type": "string", "enum": ["overall", "potential", "age", "name"]},
       "limit": _LIMIT})
def search_players(db: SoccerData, name=None, nationality=None, club=None, position=None,
                   min_overall=None, max_age=None, brazilian_clubs_only=False,
                   sort_by="overall", limit=20) -> str:
    found = db.search_players(name, nationality, club, position, min_overall, max_age,
                              brazilian_clubs_only, sort_by, _limit(limit, 20))
    if not found["total"]:
        hint = (" Note: the FIFA dataset only licenses some Brazilian clubs (e.g. Santos, Grêmio, "
                "Cruzeiro, Internacional); Flamengo, Palmeiras, Corinthians and São Paulo are absent."
                if club else "")
        return "No players found for those criteria." + hint
    lines = [f"Found {found['total']} player(s); showing {len(found['players'])} "
             f"sorted by {sort_by}:"]
    lines += [f"{i}. {_player_line(p)}" for i, p in enumerate(found["players"], 1)]
    return "\n".join(lines)


@tool("player_details", "Full FIFA profile (ratings, physique, skills) of a player by name.",
      {"name": {"type": "string", "description": "Full or partial player name."}},
      required=("name",))
def player_details(db: SoccerData, name) -> str:
    found = db.search_players(name=name, limit=5)
    if not found["total"]:
        return f"No player matching {name!r} was found."
    p = found["players"][0]
    top = sorted(p["skills"].items(), key=lambda kv: -kv[1])[:8]
    lines = [
        f"{p['name']} (FIFA id {p['id']})",
        f"- Age: {p['age']}, Nationality: {p['nationality']}",
        f"- Club: {p['club'] or 'free agent'}, Position: {p['position'] or 'n/a'}, "
        f"Jersey: {p['jersey_number'] if p['jersey_number'] is not None else 'n/a'}",
        f"- Overall: {p['overall']}, Potential: {p['potential']}",
        f"- Height: {p['height'] or 'n/a'}, Weight: {p['weight'] or 'n/a'}, "
        f"Preferred foot: {p['preferred_foot'] or 'n/a'}",
        f"- Value: {p['value'] or 'n/a'}, Wage: {p['wage'] or 'n/a'}",
        "- Best attributes: " + ", ".join(f"{k} {v}" for k, v in top),
    ]
    if found["total"] > 1:
        others = ", ".join(f"{x['name']} ({x['club'] or 'free agent'})" for x in found["players"][1:])
        lines.append(f"Other matches ({found['total'] - 1}): {others}")
    return "\n".join(lines)


@tool("players_by_club",
      "Number of players and average rating per club, e.g. Brazilian players at Brazilian clubs.",
      {"nationality": {"type": "string", "description": "Country filter, e.g. 'Brazil'."},
       "brazilian_clubs_only": {"type": "boolean", "description": "Default true."},
       "limit": _LIMIT})
def players_by_club(db: SoccerData, nationality=None, brazilian_clubs_only=True, limit=20) -> str:
    rows = db.players_by_club(nationality, brazilian_clubs_only, _limit(limit, 20))
    if not rows:
        return "No players found for those criteria."
    who = f"{nationality} players" if nationality else "Players"
    where = " at Brazilian clubs" if brazilian_clubs_only else " by club"
    lines = [f"{who}{where}:"]
    lines += [f"- {r['club']}: {r['players']} players (avg rating: {r['average_overall']}, "
              f"best: {r['best_player']})" for r in rows]
    return "\n".join(lines)


@tool("dataset_summary", "What the knowledge base contains: files, competitions, seasons, counts.")
def dataset_summary(db: SoccerData) -> str:
    s = db.summary()
    lines = [f"Brazilian soccer dataset: {s['matches']} unique matches "
             f"({s['first_date']} to {s['last_date']}), {s['teams']} teams, {s['players']} players.",
             "Matches by competition:"]
    for competition, count in s["by_competition"].items():
        seasons = s["seasons"][competition]
        lines.append(f"- {competition}: {count} matches, seasons {seasons[0]}-{seasons[-1]}")
    lines.append("Source files (rows read / unusable or repeated rows / merged as duplicates "
                 "of another file):")
    lines += [f"- {name}: {c['rows']} / {c['skipped']} / {c['merged']}"
              for name, c in s["files"].items()]
    lines.append(f"- fifa_data.csv: {s['players']} players")
    return "\n".join(lines)


def call_tool(name: str, arguments: dict | None = None, db: SoccerData | None = None) -> str:
    """Run a tool by name and return its text answer.  Raises QueryError on bad input."""
    if name not in TOOLS:
        raise QueryError(f"Unknown tool: {name}")
    arguments = dict(arguments or {})
    allowed = TOOLS[name]["spec"]["inputSchema"]
    unknown = set(arguments) - set(allowed["properties"])
    if unknown:
        raise QueryError(f"Unknown argument(s) for {name}: {', '.join(sorted(unknown))}")
    missing = [k for k in allowed["required"] if arguments.get(k) in (None, "")]
    if missing:
        raise QueryError(f"Missing required argument(s) for {name}: {', '.join(missing)}")
    try:
        return TOOLS[name]["handler"](db or service.load_default(), **arguments)
    except (TypeError, ValueError) as exc:
        if isinstance(exc, QueryError):
            raise
        raise QueryError(f"Invalid arguments for {name}: {exc}") from exc


# --------------------------------------------------------------------------- #
# JSON-RPC / MCP plumbing
# --------------------------------------------------------------------------- #


def _error(request_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_message(message, db: SoccerData | None = None) -> dict | None:
    """Handle one decoded JSON-RPC message; returns the response (None for notifications)."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or "method" not in message:
        return _error(message.get("id") if isinstance(message, dict) else None,
                      -32600, "Invalid Request")
    method, request_id = message["method"], message.get("id")
    params = message.get("params") or {}
    if "id" not in message:
        return None  # notification (e.g. notifications/initialized)

    if method == "initialize":
        requested = params.get("protocolVersion")
        version = requested if requested in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
        result = {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
            "instructions": "Tools for querying Brazilian soccer matches (Brasileirão, Copa do "
                            "Brasil, Libertadores, Serie B/C, 2003-2023) and FIFA player data. "
                            "Team names are normalised, so any common spelling works.",
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [t["spec"] for t in TOOLS.values()]}
    elif method == "tools/call":
        name = params.get("name")
        if name not in TOOLS:
            return _error(request_id, -32602, f"Unknown tool: {name}")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return _error(request_id, -32602, "Tool arguments must be an object")
        try:
            text, is_error = call_tool(name, arguments, db), False
        except QueryError as exc:
            text, is_error = str(exc), True
        result = {"content": [{"type": "text", "text": text}], "isError": is_error}
    else:
        return _error(request_id, -32601, f"Method not found: {method}")
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def serve(stdin=None, stdout=None, db: SoccerData | None = None) -> None:
    """Serve MCP over stdio until EOF."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            response = _error(None, -32700, "Parse error")
        else:
            try:
                response = handle_message(message, db)
            except Exception as exc:  # keep the server alive on unexpected failures
                print(f"internal error: {exc!r}", file=sys.stderr)
                response = _error(message.get("id") if isinstance(message, dict) else None,
                                  -32603, "Internal error")
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()


def main() -> None:
    for stream in (sys.stdin, sys.stdout):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    serve()


if __name__ == "__main__":
    main()
