"""MCP tool definitions: JSON schemas plus handlers that format answers as text.

Each handler takes the shared ``SoccerData`` and the tool arguments and
returns a plain-text answer shaped like the examples in TASK.md, so the LLM
client can quote it directly. ``QueryError`` becomes a readable message
rather than a protocol error.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

from .models import Match
from .store import QueryError, SoccerData

ToolHandler = Callable[[SoccerData, dict[str, Any]], str]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler


def _obj(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or []}


_COMPETITION = {
    "type": "string",
    "description": "Brasileirão, Copa do Brasil, Libertadores (or full name).",
}
_SEASON = {"type": "integer", "description": "Season year, e.g. 2023."}
_TEAM = {"type": "string", "description": "Team name; state suffixes and accents are ignored."}


def _date_arg(args: dict[str, Any], key: str) -> date | None:
    value = args.get(key)
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise QueryError(f"{key} must be YYYY-MM-DD, got {value!r}") from exc


def _match_line(match: Match) -> str:
    return (
        f"- {match.date.isoformat()}: {match.home} {match.home_goals}-"
        f"{match.away_goals} {match.away} ({_label(match)})"
    )


def _label(match: Match) -> str:
    if match.stage:
        return f"{match.competition}, {match.stage}"
    if match.round:
        return f"{match.competition} Round {match.round}"
    return match.competition


def _fmt_record(record) -> str:
    return (
        f"Matches: {record.played}, Wins: {record.wins}, Draws: {record.draws}, "
        f"Losses: {record.losses}\n"
        f"Goals For: {record.goals_for}, Goals Against: {record.goals_against}\n"
        f"Win rate: {record.win_rate:.1f}%"
    )


def _find_matches(data: SoccerData, args: dict[str, Any]) -> str:
    if not args.get("team") and not args.get("opponent"):
        raise QueryError("provide at least one of: team, opponent")
    limit = int(args.get("limit", 20))
    matches = data.find_matches(
        team=args.get("team"),
        opponent=args.get("opponent"),
        venue=args.get("venue", "any"),
        competition=args.get("competition"),
        season=args.get("season"),
        start=_date_arg(args, "start_date"),
        end=_date_arg(args, "end_date"),
        limit=None,
    )
    if not matches:
        return "No matches found for those criteria."
    head = f"{len(matches)} matches found"
    shown = matches[:limit]
    lines = [head + (f" (showing {len(shown)}):" if len(shown) < len(matches) else ":")]
    lines += [_match_line(m) for m in shown]
    if len(matches) > len(shown):
        lines.append(f"... ({len(matches) - len(shown)} more matches in dataset)")
    return "\n".join(lines)


def _head_to_head(data: SoccerData, args: dict[str, Any]) -> str:
    h2h = data.head_to_head(args["team_a"], args["team_b"], args.get("competition"))
    a, b = data.team_name(h2h.a_key), data.team_name(h2h.b_key)
    if not h2h.matches:
        return f"No matches between {a} and {b} in the dataset."
    last = h2h.matches[0]
    lines = [f"{a} vs {b}:"]
    lines += [_match_line(m) for m in h2h.matches[:10]]
    if len(h2h.matches) > 10:
        lines.append(f"... ({len(h2h.matches) - 10} more matches in dataset)")
    lines.append("")
    lines.append(f"Last meeting: {last.date.isoformat()}")
    lines.append(
        f"Head-to-head in dataset: {a} {h2h.a_wins} wins, {b} {h2h.b_wins} wins, "
        f"{h2h.draws} draws; goals {h2h.a_goals}-{h2h.b_goals}"
    )
    return "\n".join(lines)


def _team_stats(data: SoccerData, args: dict[str, Any]) -> str:
    venue = args.get("venue", "any")
    competition = data.resolve_competition(args.get("competition"))
    record = data.team_record(
        args["team"], venue=venue, competition=competition, season=args.get("season"),
    )
    if record.played == 0:
        return "No matches found for that team and filter."
    scope = [data.team_name(data.resolve_team(args["team"]))]
    if args.get("season"):
        scope.append(str(args["season"]))
    if competition:
        scope.append(competition)
    if venue != "any":
        scope.append(f"{venue} matches")
    return f"{' '.join(scope)}:\n{_fmt_record(record)}"


def _standings(data: SoccerData, args: dict[str, Any]) -> str:
    competition = data.resolve_competition(args.get("competition")) or "Brasileirão Série A"
    rows = data.standings(int(args["season"]), competition)
    if not rows:
        return f"No {competition} matches for {args['season']} in the dataset."
    lines = [f"{args['season']} {competition} standings (calculated from matches):"]
    for pos, row in enumerate(rows, start=1):
        r = row.record
        lines.append(
            f"{pos}. {row.team} - {row.points} pts ({r.wins}W, {r.draws}D, {r.losses}L, "
            f"GD {row.goal_difference:+d})"
        )
    return "\n".join(lines)


def _league_stats(data: SoccerData, args: dict[str, Any]) -> str:
    competition = data.resolve_competition(args.get("competition"))
    season = args.get("season")
    goals = data.goals_per_match(competition, season)
    home = data.home_win_rate(competition, season)
    scope = " ".join(p for p in (competition or "All competitions", str(season or "")) if p)
    lines = [
        f"{scope}:",
        f"Average goals per match: {goals:.2f}",
        f"Home win rate: {home:.1f}%",
    ]
    if args.get("include_biggest_wins"):
        lines.append("Biggest victories (provided data):")
        for m in data.biggest_wins(5, competition):
            lines.append(
                f"- {m.date.isoformat()}: {m.home} {m.home_goals}-{m.away_goals} "
                f"{m.away} ({_label(m)})"
            )
    return "\n".join(lines)


def _best_away(data: SoccerData, args: dict[str, Any]) -> str:
    rows = data.best_away_records(
        competition=args.get("competition"),
        season=args.get("season"),
        min_matches=int(args.get("min_matches", 10)),
    )
    if not rows:
        return "No teams meet the minimum number of away matches for that filter."
    lines = ["Best away records (win rate):"]
    for i, (name, rec) in enumerate(rows, start=1):
        lines.append(
            f"{i}. {name} - {rec.win_rate:.1f}% ({rec.wins}W, {rec.draws}D, "
            f"{rec.losses}L in {rec.played} away matches)"
        )
    return "\n".join(lines)


def _search_players(data: SoccerData, args: dict[str, Any]) -> str:
    players = data.find_players(
        name=args.get("name"),
        nationality=args.get("nationality"),
        club=args.get("club"),
        position=args.get("position"),
        min_overall=args.get("min_overall"),
        limit=int(args.get("limit", 20)),
    )
    if not players:
        return "No players match those filters."
    lines = ["Players (sorted by overall rating):"]
    for i, p in enumerate(players, start=1):
        lines.append(
            f"{i}. {p.name} - Overall: {p.overall}, Position: {p.position or 'n/a'}, "
            f"Club: {p.club or 'n/a'}, Nationality: {p.nationality}, Age: {p.age}"
        )
    return "\n".join(lines)


def _brazilian_clubs(data: SoccerData, args: dict[str, Any]) -> str:
    rows = data.brazilian_players_by_club(limit=int(args.get("limit", 10)))
    if not rows:
        return "No Brazilian players found at Brazilian clubs."
    lines = ["Brazilian players at Brazilian clubs:"]
    lines += [f"- {club}: {count} players (avg rating: {avg:.0f})" for club, count, avg in rows]
    return "\n".join(lines)


TOOLS: tuple[Tool, ...] = (
    Tool(
        name="find_matches",
        description=(
            "Find matches by team (home, away or either), opponent, competition, season "
            "or date range. Returns newest first."
        ),
        input_schema=_obj({
            "team": _TEAM,
            "opponent": _TEAM,
            "venue": {"type": "string", "enum": ["any", "home", "away"]},
            "competition": _COMPETITION,
            "season": _SEASON,
            "start_date": {"type": "string", "description": "YYYY-MM-DD"},
            "end_date": {"type": "string", "description": "YYYY-MM-DD"},
            "limit": {"type": "integer", "default": 20},
        }),
        handler=_find_matches,
    ),
    Tool(
        name="head_to_head",
        description="Head-to-head record and meetings between two teams.",
        input_schema=_obj(
            {"team_a": _TEAM, "team_b": _TEAM, "competition": _COMPETITION},
            ["team_a", "team_b"],
        ),
        handler=_head_to_head,
    ),
    Tool(
        name="team_stats",
        description=(
            "Win/draw/loss record, goals for and against for a team, optionally filtered "
            "by season, competition or venue."
        ),
        input_schema=_obj(
            {
                "team": _TEAM,
                "season": _SEASON,
                "competition": _COMPETITION,
                "venue": {"type": "string", "enum": ["any", "home", "away"]},
            },
            ["team"],
        ),
        handler=_team_stats,
    ),
    Tool(
        name="standings",
        description="League table for a Brasileirão season, calculated from match results.",
        input_schema=_obj(
            {"season": _SEASON, "competition": _COMPETITION}, ["season"],
        ),
        handler=_standings,
    ),
    Tool(
        name="league_stats",
        description=(
            "Average goals per match and home win rate, optionally for one competition or "
            "season; can also list the biggest wins."
        ),
        input_schema=_obj({
            "competition": _COMPETITION,
            "season": _SEASON,
            "include_biggest_wins": {"type": "boolean", "default": False},
        }),
        handler=_league_stats,
    ),
    Tool(
        name="best_away_records",
        description="Teams with the best away win rate (minimum away matches applies).",
        input_schema=_obj({
            "competition": _COMPETITION,
            "season": _SEASON,
            "min_matches": {"type": "integer", "default": 10},
        }),
        handler=_best_away,
    ),
    Tool(
        name="search_players",
        description=(
            "Search FIFA player data by name, nationality, club, position (code like ST, "
            "or group: forward, midfielder, defender, goalkeeper) or minimum overall rating."
        ),
        input_schema=_obj({
            "name": {"type": "string"},
            "nationality": {"type": "string", "description": "e.g. Brazil"},
            "club": {"type": "string"},
            "position": {"type": "string"},
            "min_overall": {"type": "integer"},
            "limit": {"type": "integer", "default": 20},
        }),
        handler=_search_players,
    ),
    Tool(
        name="brazilian_players_by_club",
        description="Brazilian players per Brazilian club with average FIFA overall rating.",
        input_schema=_obj({"limit": {"type": "integer", "default": 10}}),
        handler=_brazilian_clubs,
    ),
)

TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}


def call_tool(data: SoccerData, name: str, args: dict[str, Any]) -> tuple[str, bool]:
    """Run a tool; returns ``(text, is_error)``. Never raises for bad input."""
    tool = TOOLS_BY_NAME.get(name)
    if tool is None:
        return f"Unknown tool: {name}", True
    try:
        return tool.handler(data, args or {}), False
    except QueryError as exc:
        return str(exc), True
    except (KeyError, TypeError, ValueError) as exc:
        return f"Invalid arguments for {name}: {exc}", True
