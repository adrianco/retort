"""
Transport-independent tool layer.

Context
-------
The MCP server, the CLI and the test-suite all call the *same* functions from
here, so behaviour cannot drift between them.  Each tool returns a
:class:`ToolResult` carrying both:

* ``text``  -- the answer rendered in the formats TASK.md specifies, ready for
  an LLM to quote;
* ``data``  -- the same information as JSON-serialisable structures for
  programmatic use.

Argument handling is intentionally forgiving because the caller is a language
model: seasons may be ``2019`` or ``"2019"``, competitions may be
``"brasileirao"``/``"Série A"``/``"serie-a"``, clubs may be ``"flamengo"``,
``"Flamengo-RJ"`` or ``"Mengão"``.  Unresolvable names come back as a helpful
message listing suggestions rather than an exception, so the model can retry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from . import formatting as fmt
from . import queries as q
from .graph import KnowledgeGraph, load_knowledge_graph
from .loaders import POSITION_GROUPS
from .models import COMPETITIONS

__all__ = ["ToolResult", "ToolSpec", "TOOLS", "call_tool", "list_tools", "tool_names"]


@dataclass(slots=True)
class ToolResult:
    """Rendered answer plus structured payload."""

    text: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "data": self.data}


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    handler: Callable[..., ToolResult]
    parameters: dict[str, str]


TOOLS: dict[str, ToolSpec] = {}


def tool(name: str, description: str, parameters: dict[str, str]):
    def decorator(handler: Callable[..., ToolResult]) -> Callable[..., ToolResult]:
        TOOLS[name] = ToolSpec(name=name, description=description,
                               handler=handler, parameters=parameters)
        return handler

    return decorator


def _matches_payload(graph: KnowledgeGraph, matches) -> list[dict[str, Any]]:
    names = graph.team_names()
    return [match.to_dict(names) for match in matches]


# ---------------------------------------------------------------------------
# Match tools
# ---------------------------------------------------------------------------


@tool(
    "search_matches",
    "Find matches by team, opponent, competition, season, date range, stage or "
    "round. Use it for questions like 'what matches did Palmeiras play in 2023' "
    "or 'find all Copa do Brasil finals'.",
    {
        "team": "Club name, e.g. 'Flamengo' (optional)",
        "opponent": "Second club to restrict to meetings between the two (optional)",
        "competition": "brasileirao | serie-b | serie-c | copa do brasil | libertadores",
        "season": "Season year, e.g. 2019",
        "date_from": "ISO or DD/MM/YYYY lower bound",
        "date_to": "ISO or DD/MM/YYYY upper bound",
        "home_away": "'home', 'away' or 'any' (applies to `team`)",
        "stage": "Cup stage, e.g. 'final', 'semifinals', 'group stage'",
        "round": "League round number",
        "limit": "Maximum matches to return (default 20)",
    },
)
def _search_matches(graph: KnowledgeGraph, *, team: str | None = None,
                    opponent: str | None = None, competition: str | None = None,
                    season: object = None, date_from: object = None,
                    date_to: object = None, home_away: str = "any",
                    stage: str | None = None, round: str | None = None,
                    limit: int = 20) -> ToolResult:
    matches = q.search_matches(
        graph, team=team, opponent=opponent, competition=competition, season=season,
        date_from=date_from, date_to=date_to, home_away=home_away, stage=stage,
        round=round, limit=None,
    )
    shown = matches[: int(limit or 20)]
    title_bits = []
    if team:
        title_bits.append(q.resolve_team(graph, team).display_name)
    if opponent:
        title_bits.append(f"vs {q.resolve_team(graph, opponent).display_name}")
    if competition:
        competition_obj = q.resolve_competition(competition)
        if competition_obj:
            title_bits.append(f"in {competition_obj.name}" if title_bits
                              else competition_obj.name)
    if season:
        title_bits.append(str(season))
    if stage:
        title_bits.append(f"({stage})")
    title = " ".join(bit for bit in title_bits if bit) or "Matches"
    text = fmt.format_matches(graph, shown, title=title, limit=len(shown),
                              total=len(matches))
    return ToolResult(text, {"count": len(matches), "returned": len(shown),
                             "matches": _matches_payload(graph, shown)})


@tool(
    "head_to_head",
    "Full head-to-head record between two clubs: every meeting in the data plus "
    "wins, draws and goals for each side.",
    {
        "team_a": "First club",
        "team_b": "Second club",
        "competition": "Restrict to one competition (optional)",
        "season": "Restrict to one season (optional)",
        "limit": "How many matches to list (default 15)",
    },
)
def _head_to_head(graph: KnowledgeGraph, *, team_a: str, team_b: str,
                  competition: str | None = None, season: object = None,
                  limit: int = 15) -> ToolResult:
    record = q.head_to_head(graph, team_a, team_b, competition=competition,
                            season=season, limit=None)
    total = len(record.matches)
    record.matches = record.matches[: int(limit or 15)]
    text = fmt.format_head_to_head(graph, record, limit=len(record.matches),
                                   all_matches=total)
    return ToolResult(text, record.to_dict(graph.team_names()) | {"total_matches": total})


@tool(
    "find_derbies",
    "Matches between traditional rivals (Fla-Flu, Grenal, Derby Paulista, "
    "Clássico Mineiro, ...). Answers 'show me all derbies in 2023'.",
    {
        "season": "Season year (optional)",
        "competition": "Competition filter (optional)",
        "derby": "Name of a specific rivalry, e.g. 'Grenal' (optional)",
        "limit": "Matches to list per rivalry (default 5)",
    },
)
def _find_derbies(graph: KnowledgeGraph, *, season: object = None,
                  competition: str | None = None, derby: str | None = None,
                  limit: int = 5) -> ToolResult:
    entries = q.find_derbies(graph, season=season, competition=competition, derby=derby)
    text = fmt.format_derbies(graph, entries, limit=int(limit or 5))
    payload = [
        {
            "derby": entry["derby"],
            "team_a": entry["team_a"],
            "team_b": entry["team_b"],
            "match_count": len(entry["matches"]),
            "matches": _matches_payload(graph, entry["matches"][: int(limit or 5)]),
        }
        for entry in entries
    ]
    return ToolResult(text, {"derbies": payload, "count": len(payload)})


# ---------------------------------------------------------------------------
# Team tools
# ---------------------------------------------------------------------------


@tool(
    "team_stats",
    "Win/draw/loss record and goals for a club, optionally limited to one "
    "competition, one season, and home-only or away-only matches. Answers "
    "'what is Corinthians home record in 2022'.",
    {
        "team": "Club name",
        "competition": "Competition filter (optional)",
        "season": "Season year (optional)",
        "scope": "'all', 'home' or 'away' (default 'all')",
    },
)
def _team_stats(graph: KnowledgeGraph, *, team: str, competition: str | None = None,
                season: object = None, scope: str = "all") -> ToolResult:
    record = q.team_record(graph, team, competition=competition, season=season, scope=scope)
    label_bits = [record.team_name]
    if scope in ("home", "away"):
        label_bits.append(f"{scope} record")
    else:
        label_bits.append("record")
    context = []
    if season:
        context.append(str(season))
    competition_obj = q.resolve_competition(competition) if competition else None
    if competition_obj:
        context.append(competition_obj.short_name)
    title = " ".join(label_bits) + (f" ({' '.join(context)})" if context else "")
    return ToolResult(fmt.format_team_record(record, title=title), record.to_dict())


@tool(
    "team_profile",
    "Everything the graph knows about a club: overall/home/away records, the "
    "competitions and seasons it appears in, recent matches and squad size.",
    {"team": "Club name", "season": "Restrict to one season (optional)"},
)
def _team_profile(graph: KnowledgeGraph, *, team: str, season: object = None) -> ToolResult:
    profile = q.team_profile(graph, team, season=season)
    data = {
        "team": profile["team"].to_dict(),
        "season": profile["season"],
        "overall": profile["overall"].to_dict(),
        "home": profile["home"].to_dict(),
        "away": profile["away"].to_dict(),
        "by_competition": {k: v.to_dict() for k, v in profile["by_competition"].items()},
        "competitions": profile["competitions"],
        "seasons": profile["seasons"],
        "first_match": profile["first_match"].isoformat() if profile["first_match"] else None,
        "last_match": profile["last_match"].isoformat() if profile["last_match"] else None,
        "recent_matches": _matches_payload(graph, profile["recent_matches"]),
        "squad_size": profile["squad_size"],
    }
    return ToolResult(fmt.format_team_profile(graph, profile), data)


@tool(
    "compare_teams",
    "Side-by-side records for two clubs plus their head-to-head. Answers "
    "'compare Palmeiras and Santos'.",
    {
        "team_a": "First club",
        "team_b": "Second club",
        "competition": "Competition filter (optional)",
        "season": "Season filter (optional)",
    },
)
def _compare_teams(graph: KnowledgeGraph, *, team_a: str, team_b: str,
                   competition: str | None = None, season: object = None) -> ToolResult:
    comparison = q.compare_teams(graph, team_a, team_b, competition=competition, season=season)
    data = {
        "team_a": comparison["team_a"].to_dict(),
        "team_b": comparison["team_b"].to_dict(),
        "record_a": comparison["record_a"].to_dict(),
        "record_b": comparison["record_b"].to_dict(),
        "head_to_head": comparison["head_to_head"].to_dict(graph.team_names()),
    }
    return ToolResult(fmt.format_compare_teams(graph, comparison), data)


@tool(
    "best_records",
    "Rank clubs by points per game, win rate, wins, goals for/against or goal "
    "difference -- overall, home-only or away-only. Answers 'which team has the "
    "best away record'.",
    {
        "competition": "Competition filter (optional)",
        "season": "Season filter (optional)",
        "scope": "'all', 'home' or 'away' (default 'all')",
        "metric": "points_per_game | points | win_rate | wins | goals_for | "
                  "goals_against | goal_difference",
        "min_matches": "Minimum matches to qualify (default 10)",
        "limit": "How many clubs to return (default 10)",
    },
)
def _best_records(graph: KnowledgeGraph, *, competition: str | None = None,
                  season: object = None, scope: str = "all",
                  metric: str = "points_per_game", min_matches: int = 10,
                  limit: int = 10) -> ToolResult:
    records = q.best_records(graph, competition=competition, season=season, scope=scope,
                             metric=metric, min_matches=int(min_matches or 0),
                             limit=int(limit or 10))
    scope_label = {"home": "home", "away": "away"}.get(scope, "overall")
    context = []
    competition_obj = q.resolve_competition(competition) if competition else None
    if competition_obj:
        context.append(competition_obj.short_name)
    if season:
        context.append(str(season))
    title = f"Best {scope_label} records by {metric.replace('_', ' ')}"
    if context:
        title += f" ({' '.join(context)})"
    lines = [f"{title}:"]
    for index, record in enumerate(records, start=1):
        lines.append(
            f"{index}. {record.team_name} - {record.points} pts from {record.played} "
            f"matches ({record.points_per_game:.2f}/game), {record.wins}W {record.draws}D "
            f"{record.losses}L, {record.goals_for}-{record.goals_against} goals, "
            f"win rate {record.win_rate:.1f}%"
        )
    if not records:
        lines.append("No clubs matched the filter.")
    return ToolResult("\n".join(lines), {"records": [r.to_dict() for r in records]})


@tool(
    "top_scoring_teams",
    "Clubs ranked by goals scored. Answers 'which team scored the most goals in "
    "Serie A 2023'.",
    {"competition": "Competition filter", "season": "Season filter",
     "limit": "How many clubs (default 10)"},
)
def _top_scoring_teams(graph: KnowledgeGraph, *, competition: str | None = None,
                       season: object = None, limit: int = 10) -> ToolResult:
    records = q.top_scoring_teams(graph, competition=competition, season=season,
                                  limit=int(limit or 10))
    context = " ".join(str(bit) for bit in (competition, season) if bit)
    lines = [f"Top scoring teams{f' ({context})' if context else ''}:"]
    for index, record in enumerate(records, start=1):
        lines.append(f"{index}. {record.team_name} - {record.goals_for} goals in "
                     f"{record.played} matches "
                     f"({record.goals_for_per_game:.2f} per match)")
    if not records:
        lines.append("No clubs matched the filter.")
    return ToolResult("\n".join(lines), {"records": [r.to_dict() for r in records]})


# ---------------------------------------------------------------------------
# Competition tools
# ---------------------------------------------------------------------------


@tool(
    "competition_standings",
    "League table calculated from match results (3 points per win, tie-break on "
    "wins then goal difference). Answers 'who won the 2019 Brasileirão' and "
    "'which teams were relegated in 2020'.",
    {
        "competition": "brasileirao | serie-b | serie-c",
        "season": "Season year, required",
        "scope": "'all', 'home' or 'away' (default 'all')",
        "limit": "How many rows to show (default all)",
    },
)
def _competition_standings(graph: KnowledgeGraph, *, competition: str = "brasileirao",
                           season: object, scope: str = "all",
                           limit: int | None = None) -> ToolResult:
    rows = q.standings(graph, competition, season, scope=scope)
    competition_obj = q.resolve_competition(competition)
    scope_label = {"home": " home table", "away": " away table"}.get(scope, " final standings")
    title = (f"{season} {competition_obj.short_name if competition_obj else competition}"
             f"{scope_label} (calculated from matches)")
    text = fmt.format_standings(graph, rows, title=title,
                                limit=int(limit) if limit else None)
    return ToolResult(text, {"standings": [row.to_dict() for row in rows],
                             "season": q.as_season(season),
                             "competition": competition_obj.id if competition_obj else None})


@tool(
    "competition_champion",
    "Who won a season: the table winner for leagues, the winner of the final for "
    "the Copa do Brasil and Copa Libertadores.",
    {"competition": "Competition name", "season": "Season year"},
)
def _competition_champion(graph: KnowledgeGraph, *, competition: str,
                          season: object) -> ToolResult:
    result = q.competition_champion(graph, competition, season)
    competition_obj = result["competition"]
    champion = result["champion"]
    lines = [f"{result['season']} {competition_obj.name}:"]
    if champion is not None:
        lines.append(f"Champion: {champion.display_name}")
        if result.get("points") is not None:
            record = result["record"]
            lines.append(f"{record.points} points ({record.wins}W, {record.draws}D, "
                         f"{record.losses}L), goals {record.goals_for}-{record.goals_against}")
        if result.get("runner_up") is not None:
            lines.append(f"Runner-up: {result['runner_up'].display_name}")
    elif not result["final"]:
        lines.append("Champion could not be determined: the dataset records no final "
                     "for this season.")
    else:
        lines.append("Champion could not be determined from the data.")
    lines.append(f"Method: {result['method']}")
    if result["final"]:
        lines.append("")
        lines.append(fmt.format_matches(graph, result["final"], title="Final",
                                        limit=len(result["final"])))
    data = {
        "season": result["season"],
        "competition": competition_obj.id,
        "champion": champion.to_dict() if champion else None,
        "method": result["method"],
        "final": _matches_payload(graph, result["final"]),
    }
    if "aggregate" in result:
        data["aggregate"] = result["aggregate"]
    return ToolResult("\n".join(lines), data)


@tool(
    "relegated_teams",
    "The bottom placings of a calculated league table for a season.",
    {"competition": "Competition (default brasileirao)", "season": "Season year",
     "slots": "How many relegation places (default 4)"},
)
def _relegated_teams(graph: KnowledgeGraph, *, season: object,
                     competition: str = "brasileirao", slots: int = 4) -> ToolResult:
    rows = q.relegated_teams(graph, competition, season, slots=int(slots or 4))
    competition_obj = q.resolve_competition(competition)
    title = (f"{season} {competition_obj.short_name if competition_obj else competition} "
             f"relegation places (calculated from matches)")
    text = fmt.format_standings(graph, rows, title=title)
    return ToolResult(text, {"relegated": [row.to_dict() for row in rows]})


@tool(
    "competition_stats",
    "Aggregate statistics for a competition or season: goals per match, home "
    "advantage, draw rate, biggest win.",
    {"competition": "Competition filter (optional)", "season": "Season filter (optional)"},
)
def _competition_stats(graph: KnowledgeGraph, *, competition: str | None = None,
                       season: object = None) -> ToolResult:
    stats = q.competition_stats(graph, competition=competition, season=season)
    top = q.biggest_wins(graph, competition=competition, season=season, limit=5)
    text = fmt.format_competition_stats(graph, stats, biggest=top)
    payload = dict(stats)
    payload["biggest_win"] = (stats["biggest_win"].to_dict(graph.team_names())
                              if stats["biggest_win"] else None)
    payload["highest_scoring"] = (stats["highest_scoring"].to_dict(graph.team_names())
                                  if stats["highest_scoring"] else None)
    payload["biggest_wins"] = _matches_payload(graph, top)
    return ToolResult(text, payload)


@tool(
    "biggest_wins",
    "Matches ordered by margin of victory. Answers 'show me the biggest wins in "
    "the dataset'.",
    {"competition": "Competition filter (optional)", "season": "Season filter (optional)",
     "team": "Restrict to one club (optional)", "limit": "How many (default 10)"},
)
def _biggest_wins(graph: KnowledgeGraph, *, competition: str | None = None,
                  season: object = None, team: str | None = None,
                  limit: int = 10) -> ToolResult:
    matches = q.biggest_wins(graph, competition=competition, season=season, team=team,
                             limit=int(limit or 10))
    context = " ".join(str(bit) for bit in (team, competition, season) if bit)
    title = f"Biggest victories{f' ({context})' if context else ''}"
    text = fmt.format_matches(graph, matches, title=title, limit=len(matches))
    return ToolResult(text, {"matches": _matches_payload(graph, matches)})


@tool(
    "compare_seasons",
    "Aggregate several seasons of a competition side by side. Answers 'compare "
    "the 2018 and 2019 seasons'.",
    {"seasons": "List of season years, e.g. [2018, 2019]",
     "competition": "Competition (default brasileirao)"},
)
def _compare_seasons(graph: KnowledgeGraph, *, seasons: list,
                     competition: str | None = "brasileirao") -> ToolResult:
    if isinstance(seasons, (str, int)):
        seasons = [seasons]
    rows = q.compare_seasons(graph, seasons, competition=competition)
    lines = []
    for stats in rows:
        lines.append(f"{stats['competition']} {stats['season']}:")
        lines.append(f"- Matches: {stats['matches']}   Teams: {stats['teams']}   "
                     f"Goals: {stats['goals']}")
        lines.append(f"- Goals per match: {stats['goals_per_match']}   "
                     f"Home wins: {stats['home_win_rate']}%   "
                     f"Draws: {stats['draw_rate']}%   "
                     f"Away wins: {stats['away_win_rate']}%")
        if stats["champion"]:
            lines.append(f"- Champion: {stats['champion']} ({stats['champion_points']} pts)")
        lines.append("")
    payload = []
    for stats in rows:
        entry = dict(stats)
        entry["biggest_win"] = (stats["biggest_win"].to_dict(graph.team_names())
                                if stats["biggest_win"] else None)
        entry["highest_scoring"] = (stats["highest_scoring"].to_dict(graph.team_names())
                                    if stats["highest_scoring"] else None)
        payload.append(entry)
    return ToolResult("\n".join(lines).strip(), {"seasons": payload})


# ---------------------------------------------------------------------------
# Player tools
# ---------------------------------------------------------------------------


@tool(
    "search_players",
    "Search the FIFA player database by name, nationality, club, position and "
    "rating. Answers 'find all Brazilian players', 'who are the highest-rated "
    "players at Grêmio', 'show me all forwards from São Paulo'.",
    {
        "name": "Full or partial player name",
        "nationality": "e.g. 'Brazil'",
        "club": "Club name (FIFA club string or canonical club)",
        "position": "FIFA code ('LW') or group ('forward', 'goalkeeper', ...)",
        "min_overall": "Minimum FIFA overall rating",
        "max_age": "Maximum age",
        "brazilian_clubs_only": "Only players whose club exists in the match graph",
        "sort_by": "overall | potential | age | name",
        "limit": "How many players (default 20)",
    },
)
def _search_players(graph: KnowledgeGraph, *, name: str | None = None,
                    nationality: str | None = None, club: str | None = None,
                    position: str | None = None, min_overall: object = None,
                    max_overall: object = None, min_age: object = None,
                    max_age: object = None, brazilian_clubs_only: bool = False,
                    sort_by: str = "overall", limit: int = 20) -> ToolResult:
    players = q.search_players(
        graph, name=name, nationality=nationality, club=club, position=position,
        min_overall=min_overall, max_overall=max_overall, min_age=min_age,
        max_age=max_age, brazilian_clubs_only=brazilian_clubs_only,
        sort_by=sort_by, limit=0,
    )
    total = len(players)
    shown = players[: int(limit or 20)]
    criteria = ", ".join(
        f"{key}={value}" for key, value in (
            ("name", name), ("nationality", nationality), ("club", club),
            ("position", position), ("min_overall", min_overall), ("max_age", max_age),
        ) if value
    )
    title = f"Players matching {criteria}" if criteria else "Players"
    note = None
    if not shown and club:
        note = ("Note: the FIFA 19 dataset does not include every Brazilian club -- "
                "Flamengo, Palmeiras, Corinthians, São Paulo and Vasco were unlicensed "
                "and have no player rows.")
    text = fmt.format_players(shown, title=title, total=total, note=note)
    return ToolResult(text, {"count": total, "returned": len(shown),
                             "players": [p.to_dict() for p in shown]})


@tool(
    "player_profile",
    "Look up one player by name and return age, club, position, ratings and best "
    "attributes. Answers 'who is Neymar'.",
    {"name": "Player name (full or partial)"},
)
def _player_profile(graph: KnowledgeGraph, *, name: str) -> ToolResult:
    profile = q.player_profile(graph, name)
    data = {
        "query": profile["query"],
        "player": profile["player"].to_dict() if profile["player"] else None,
        "alternatives": [p.name for p in profile["alternatives"]],
        "suggestions": profile["suggestions"],
        "club_team": profile["club_team"].to_dict() if profile["club_team"] else None,
    }
    return ToolResult(fmt.format_player_profile(profile), data)


@tool(
    "club_squad",
    "Cross-file query: the FIFA squad of a club joined to that club's match "
    "record in the graph. Answers 'which players play for Grêmio'.",
    {"club": "Club name", "limit": "How many players to list (default 30)"},
)
def _club_squad(graph: KnowledgeGraph, *, club: str, limit: int = 30) -> ToolResult:
    squad = q.club_squad(graph, club, limit=int(limit or 30))
    data = {
        "team": squad["team"].to_dict(),
        "squad_size": squad["squad_size"],
        "average_overall": squad["average_overall"],
        "players": [p.to_dict() for p in squad["players"]],
        "record": squad["record"].to_dict(),
        "competitions": squad["competitions"],
    }
    return ToolResult(fmt.format_club_squad(graph, squad), data)


@tool(
    "brazilian_club_squads",
    "Squad size and average FIFA rating for every club that has both player rows "
    "and matches in the graph.",
    {"limit": "How many clubs (default 20)"},
)
def _brazilian_club_squads(graph: KnowledgeGraph, *, limit: int = 20) -> ToolResult:
    rows = q.brazilian_players_by_club(graph, limit=int(limit or 20))
    lines = ["Players at clubs that also appear in the match data:"]
    for row in rows:
        lines.append(f"- {row['team']}: {row['players']} players "
                     f"(avg rating: {row['average_overall']}, best: {row['best_player']})")
    return ToolResult("\n".join(lines), {"clubs": rows})


# ---------------------------------------------------------------------------
# Meta / graph tools
# ---------------------------------------------------------------------------


@tool(
    "resolve_team",
    "Resolve a club name to its canonical identity and list close alternatives. "
    "Useful when a name is ambiguous ('Botafogo', 'América', 'Atlético').",
    {"query": "Name to resolve", "limit": "How many candidates (default 8)"},
)
def _resolve_team(graph: KnowledgeGraph, *, query: str, limit: int = 8) -> ToolResult:
    candidates = graph.registry.search(query, limit=int(limit or 8))
    lines = [f"Clubs matching {query!r}:"]
    payload = []
    for team in candidates:
        played = len(graph.matches_by_team.get(team.id, []))
        lines.append(f"- {team.display_name} (id: {team.id}, {played} matches"
                     + (f", also known as {', '.join(team.nicknames)}" if team.nicknames else "")
                     + ")")
        entry = team.to_dict()
        entry["matches"] = played
        payload.append(entry)
    if not candidates:
        lines.append("No club matched.")
    return ToolResult("\n".join(lines), {"candidates": payload})


@tool(
    "list_teams",
    "List clubs in the graph, optionally filtered by state, country or "
    "competition, ordered by number of matches.",
    {"state": "Brazilian state code, e.g. 'SP'", "country": "e.g. 'BRA', 'ARG'",
     "competition": "Only clubs that played this competition",
     "search": "Substring to filter on", "limit": "How many (default 30)"},
)
def _list_teams(graph: KnowledgeGraph, *, state: str | None = None,
                country: str | None = None, competition: str | None = None,
                search: str | None = None, limit: int = 30) -> ToolResult:
    competition_id = q.competition_id_of(competition) if competition else None
    from .text import normalize_name

    needle = normalize_name(search) if search else None
    rows = []
    for team_id, matches in graph.matches_by_team.items():
        team = graph.teams.get(team_id)
        if team is None:
            continue
        if state and (team.state or "").upper() != state.upper():
            continue
        if country and (team.country or "").upper() != country.upper():
            continue
        if competition_id and competition_id not in graph.team_competitions.get(team_id, set()):
            continue
        if needle and needle not in normalize_name(team.name):
            continue
        rows.append((len(matches), team))
    rows.sort(key=lambda item: (-item[0], item[1].name))
    rows = rows[: int(limit or 30)]
    lines = [f"Clubs ({len(rows)} shown):"]
    for count, team in rows:
        lines.append(f"- {team.display_name} - {count} matches (id: {team.id})")
    return ToolResult("\n".join(lines),
                      {"teams": [team.to_dict() | {"matches": count} for count, team in rows]})


@tool(
    "list_competitions",
    "Competitions in the graph with their season coverage and match counts.",
    {},
)
def _list_competitions(graph: KnowledgeGraph) -> ToolResult:
    lines = ["Competitions in the knowledge graph:"]
    payload = []
    for competition in COMPETITIONS:
        seasons = graph.seasons_for(competition.id)
        count = len(graph.matches_by_competition.get(competition.id, []))
        span = f"{seasons[0]}-{seasons[-1]}" if seasons else "no data"
        lines.append(f"- {competition.name} ({competition.short_name}): {count} matches, "
                     f"seasons {span}")
        payload.append({"id": competition.id, "name": competition.name,
                        "kind": competition.kind, "matches": count, "seasons": seasons})
    return ToolResult("\n".join(lines), {"competitions": payload})


@tool(
    "dataset_summary",
    "Provenance and coverage: every CSV, its licence and row count, competitions, "
    "de-duplication results and the shape of the knowledge graph.",
    {},
)
def _dataset_summary(graph: KnowledgeGraph) -> ToolResult:
    summary = q.dataset_summary(graph)
    return ToolResult(fmt.format_dataset_summary(summary), summary)


@tool(
    "graph_neighbors",
    "Raw knowledge-graph traversal. Node ids look like 'team:flamengo-rj', "
    "'competition:serie-a', 'player:190871', 'match:brasileirao:12'.",
    {"node_id": "Node id to start from", "relation": "Edge type filter (optional)",
     "direction": "'out', 'in' or 'both' (default 'both')",
     "limit": "How many neighbours (default 25)"},
)
def _graph_neighbors(graph: KnowledgeGraph, *, node_id: str, relation: str | None = None,
                     direction: str = "both", limit: int = 25) -> ToolResult:
    node = graph.node(node_id)
    if node is None:
        return ToolResult(
            f"No node {node_id!r} in the graph. Node types: "
            + ", ".join(graph.graph_schema()["nodes"]),
            {"error": "unknown_node", "node_id": node_id},
        )
    edges = graph.neighbors(node_id, relation, direction)[: int(limit or 25)]
    lines = [f"{node['label']} ({node['type']}) -- {len(edges)} neighbours shown:"]
    payload = []
    for edge_relation, target in edges:
        target_node = graph.node(target)
        label = target_node["label"] if target_node else target
        lines.append(f"- {edge_relation}: {label} [{target}]")
        payload.append({"relation": edge_relation, "node_id": target, "label": label})
    return ToolResult("\n".join(lines), {"node": node, "neighbors": payload})


@tool(
    "position_groups",
    "The FIFA position codes behind each position group word (forward, "
    "midfielder, defender, goalkeeper).",
    {},
)
def _position_groups(graph: KnowledgeGraph) -> ToolResult:
    lines = ["Position groups:"]
    for group, codes in POSITION_GROUPS.items():
        lines.append(f"- {group}: {', '.join(codes)}")
    return ToolResult("\n".join(lines), {"groups": {k: list(v) for k, v in POSITION_GROUPS.items()}})


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def tool_names() -> list[str]:
    return sorted(TOOLS)


def list_tools() -> list[dict[str, Any]]:
    """Tool catalogue for MCP ``tools/list`` and the CLI."""

    return [
        {"name": spec.name, "description": spec.description, "parameters": spec.parameters}
        for spec in sorted(TOOLS.values(), key=lambda spec: spec.name)
    ]


def call_tool(name: str, arguments: dict[str, Any] | None = None, *,
              graph: KnowledgeGraph | None = None) -> ToolResult:
    """Invoke a tool by name with keyword arguments.

    Lookup failures (unknown club, unknown competition) are turned into a
    helpful message instead of an exception so an LLM can correct itself.
    """

    spec = TOOLS.get(name)
    if spec is None:
        raise KeyError(f"unknown tool {name!r}; available: {', '.join(tool_names())}")
    graph = graph or load_knowledge_graph()
    arguments = {key: value for key, value in (arguments or {}).items() if value is not None}
    try:
        return spec.handler(graph, **arguments)
    except (q.TeamNotFound, q.CompetitionNotFound) as error:
        return ToolResult(str(error), {"error": type(error).__name__,
                                       "query": getattr(error, "query", None),
                                       "suggestions": getattr(error, "suggestions", [])})
    except TypeError as error:
        expected = ", ".join(spec.parameters) or "no arguments"
        return ToolResult(f"Invalid arguments for {name}: {error}. Expected: {expected}.",
                          {"error": "InvalidArguments", "expected": list(spec.parameters)})
    except ValueError as error:
        return ToolResult(f"{name}: {error}", {"error": "ValueError", "message": str(error)})
