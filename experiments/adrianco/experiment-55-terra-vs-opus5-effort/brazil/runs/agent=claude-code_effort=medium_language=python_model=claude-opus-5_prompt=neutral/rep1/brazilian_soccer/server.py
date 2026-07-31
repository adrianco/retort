"""MCP server exposing the Brazilian soccer knowledge graph.

Context
-------
Publishes 18 tools covering the five capability groups in ``TASK.md``.  Every
tool returns pre-formatted text (see :mod:`brazilian_soccer.formatting`) so that
an LLM can quote the answer directly, and every tool catches
:class:`~brazilian_soccer.queries.TeamNotFound` to return a "did you mean"
message instead of an error.

The MCP Python SDK renamed ``FastMCP`` to ``MCPServer`` in 2.0; ``_build_server``
supports both so the module works against either SDK generation.  The graph is
loaded once at import time (~0.4 s for 42k rows), after which every tool is an
index lookup -- comfortably inside the spec's 2 s / 5 s response budgets.

Run with::

    python -m brazilian_soccer.server          # stdio transport
"""

from __future__ import annotations

import functools
import os
from pathlib import Path

from .formatting import (
    format_bullet_table,
    format_head_to_head,
    format_match,
    format_matches,
    format_player,
    format_players,
    format_ranking,
    format_record,
    format_standings,
    format_stats,
    format_team_profile,
)
from .loader import DEFAULT_DATA_DIR
from .queries import SoccerQueries, TeamNotFound

SERVER_NAME = "brazilian-soccer"
SERVER_INSTRUCTIONS = """\
Knowledge graph over six Brazilian football datasets: 17k de-duplicated matches
(Brasileirão Série A/B/C 2003-2023, Copa do Brasil 2012-2023, Copa Libertadores
2013-2022) and 18k FIFA players.

Team names are normalised, so "Palmeiras", "Palmeiras-SP" and "Palmeiras - SP"
all resolve to the same club. Standings, champions and every statistic are
CALCULATED FROM MATCH RESULTS in the datasets -- say so when reporting them.
Goal scorers are not in the data; there is no way to answer "top scorer"
questions about individual players.
"""

DATA_DIR = Path(os.environ.get("BRAZILIAN_SOCCER_DATA_DIR", DEFAULT_DATA_DIR))

queries = SoccerQueries.from_data_dir(DATA_DIR)


def _build_server():
    """Instantiate an MCP server against whichever SDK generation is installed."""
    kwargs = {"name": SERVER_NAME, "instructions": SERVER_INSTRUCTIONS}
    try:  # MCP Python SDK >= 2.0
        from mcp.server.mcpserver import MCPServer

        return MCPServer(**kwargs)
    except ImportError:  # MCP Python SDK 1.x
        from mcp.server.fastmcp import FastMCP

        return FastMCP(**kwargs)


mcp = _build_server()


def _team_error(exc: TeamNotFound) -> str:
    suggestions = [team.display for team in queries.suggest_teams(exc.query)]
    if suggestions:
        return f"No exact match for '{exc.query}'. Closest teams: " + ", ".join(
            suggestions
        )
    return f"No team matching '{exc.query}' in the dataset."


def _guard(function):
    """Turn lookup failures into readable text instead of tool errors.

    ``functools.wraps`` keeps ``__wrapped__``/``__annotations__`` intact so the
    MCP SDK still derives the correct JSON schema from the real signature.
    """

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except TeamNotFound as exc:
            return _team_error(exc)
        except ValueError as exc:
            return str(exc)

    return wrapper


# --------------------------------------------------------------------------
# 1. match queries
# --------------------------------------------------------------------------


@mcp.tool()
@_guard
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    season_from: int | None = None,
    season_to: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    venue: str = "any",
    stage: str | None = None,
    limit: int = 25,
) -> str:
    """Find matches by team, opponent, competition, season, date range or stage.

    Args:
        team: club name, any spelling ("Flamengo", "Palmeiras-SP").
        opponent: restrict to matches against this club.
        competition: "Brasileirao", "Copa do Brasil", "Libertadores", "Serie B"...
        season: a single year, e.g. 2023.
        season_from/season_to: inclusive season range.
        date_from/date_to: ISO dates ("2023-01-01") or "DD/MM/YYYY".
        venue: "home", "away" or "any" (relative to `team`).
        stage: cup stage or round, e.g. "final", "group stage".
        limit: maximum matches to list.
    """
    matches = queries.search_matches(
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        season_from=season_from,
        season_to=season_to,
        date_from=date_from,
        date_to=date_to,
        venue=venue,
        stage=stage,
        limit=None,
    )
    descriptor = " / ".join(
        part
        for part in [
            team,
            f"vs {opponent}" if opponent else None,
            competition,
            str(season) if season else None,
            stage,
            venue if venue != "any" else None,
        ]
        if part
    )
    title = f"Matches ({descriptor or 'all filters empty'}) - {len(matches)} found:"
    return format_matches(matches, title, limit=limit)


@mcp.tool()
@_guard
def head_to_head(
    team_a: str, team_b: str, competition: str | None = None, season: int | None = None
) -> str:
    """Full meeting history and win/draw record between two clubs."""
    return format_head_to_head(queries.head_to_head(team_a, team_b, competition, season))


@mcp.tool()
@_guard
def last_meeting(team_a: str, team_b: str) -> str:
    """When did these two clubs last play, and what was the score?"""
    match = queries.last_meeting(team_a, team_b)
    if match is None:
        return f"No match between {team_a} and {team_b} in the dataset."
    return "Most recent meeting:\n- " + format_match(match)


@mcp.tool()
@_guard
def find_derbies(season: int | None = None, limit: int = 25) -> str:
    """List matches between traditional rivals (Fla-Flu, Derby Paulista, Gre-Nal...)."""
    rows = queries.derbies(season=season, limit=limit)
    if not rows:
        return "No derby matches found for those filters."
    scope = f" in {season}" if season else ""
    lines = [f"Derby matches{scope} ({len(rows)} shown):"]
    for row in rows:
        lines.append(f"- [{row['derby']}] {format_match(row['match'])}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 2. team queries
# --------------------------------------------------------------------------


@mcp.tool()
@_guard
def team_statistics(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str = "any",
) -> str:
    """Wins, draws, losses, goals and win rate for a club.

    Args:
        team: club name in any spelling.
        season: restrict to one year.
        competition: restrict to one competition.
        venue: "home", "away" or "any".
    """
    record = queries.team_record(team, season=season, competition=competition, venue=venue)
    scope = ", ".join(
        part
        for part in [
            str(season) if season else None,
            competition,
            f"{venue} matches" if venue != "any" else None,
        ]
        if part
    )
    title = f"{record.team_name} record" + (f" ({scope})" if scope else "")
    return format_record(record, title)


@mcp.tool()
@_guard
def team_profile(team: str) -> str:
    """Everything known about a club: competitions, seasons, home/away splits."""
    return format_team_profile(queries.team_profile(team))


@mcp.tool()
@_guard
def compare_teams(team_a: str, team_b: str, competition: str | None = None) -> str:
    """Side-by-side records for two clubs plus their head-to-head."""
    record_a = queries.team_record(team_a, competition=competition)
    record_b = queries.team_record(team_b, competition=competition)
    h2h = queries.head_to_head(team_a, team_b, competition=competition)
    return "\n\n".join(
        [
            f"Comparison ({competition or 'all competitions'}):",
            format_record(record_a),
            format_record(record_b),
            format_head_to_head(h2h, limit=5),
        ]
    )


@mcp.tool()
@_guard
def team_season_trend(team: str, competition: str | None = None) -> str:
    """Season-by-season record for a club, to show performance trends."""
    rows = queries.team_season_trend(team, competition=competition)
    if not rows:
        return f"No seasons found for {team}."
    lines = [f"{rows[0]['team']} season-by-season ({competition or 'all competitions'}):"]
    for row in rows:
        lines.append(
            f"- {row['season']}: {row['played']} matches, {row['wins']}W "
            f"{row['draws']}D {row['losses']}L, {row['points']} pts, "
            f"GF {row['goals_for']} GA {row['goals_against']}"
        )
    return "\n".join(lines)


@mcp.tool()
def search_teams(query: str, limit: int = 10) -> str:
    """Find clubs whose name matches a query; useful for resolving spellings."""
    teams = queries.search_teams(query, limit=limit)
    if not teams:
        return f"No teams matching '{query}'."
    lines = [f"Teams matching '{query}':"]
    for team in teams:
        lines.append(
            f"- {team.display} (key: {team.key}, {len(team.match_indexes)} matches, "
            f"spellings: {', '.join(sorted(team.aliases)[:4])})"
        )
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 3. player queries
# --------------------------------------------------------------------------


@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    sort_by: str = "overall",
    limit: int = 20,
) -> str:
    """Search the FIFA player database.

    Args:
        name: full or partial player name (accent-insensitive).
        nationality: e.g. "Brazil".
        club: club name, e.g. "Flamengo", "Gremio".
        position: FIFA position code, e.g. "GK", "LW", "CDM".
        min_overall: minimum FIFA overall rating.
        min_age/max_age: age bounds.
        sort_by: "overall", "potential", "age" or "name".
        limit: maximum players to list.
    """
    players = queries.search_players(
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
        min_age=min_age,
        max_age=max_age,
        sort_by=sort_by,
        limit=limit,
    )
    descriptor = ", ".join(
        part
        for part in [
            f"name~{name}" if name else None,
            nationality,
            club,
            position,
            f"overall>={min_overall}" if min_overall else None,
        ]
        if part
    )
    return format_players(players, f"Players ({descriptor or 'all'}):", limit=limit)


@mcp.tool()
def get_player(name: str) -> str:
    """Full profile for one player: ratings, club, physicals, top attributes."""
    result = queries.lookup_player(name)
    if result["player"] is None:
        return f"No player matching '{name}' in the FIFA dataset."
    lines = []
    if not result["exact"]:
        lines.append(
            f"No exact match for '{name}' in the FIFA dataset (a FIFA 19 / 2018-19"
            " snapshot). Closest match:"
        )
    lines.append(format_player(result["player"], detailed=True))
    if not result["exact"] and result["alternatives"]:
        lines.append(
            "Other candidates: "
            + ", ".join(player.name for player in result["alternatives"])
        )
    return "\n".join(lines)


@mcp.tool()
def club_squad(club: str, limit: int = 30) -> str:
    """FIFA squad for a club, best-rated first, with the squad average."""
    squad = queries.club_squad(club, limit=limit)
    if not squad["players"]:
        return f"No FIFA players found for club '{club}'."
    title = (
        f"{squad['club']} squad in the FIFA dataset "
        f"({squad['players_found']} players, average overall "
        f"{squad['average_overall']}):"
    )
    return format_players(squad["players"], title, limit=limit)


@mcp.tool()
def players_by_club(nationality: str = "Brazil", limit: int = 20) -> str:
    """Group players of one nationality by club, with squad sizes and averages."""
    rows = queries.players_by_nationality_at_clubs(nationality, limit=limit)
    return format_bullet_table(
        rows,
        f"{nationality} players grouped by club (FIFA dataset):",
        ["club", "players", "average_overall", "top_player"],
    )


# --------------------------------------------------------------------------
# 4. competition queries
# --------------------------------------------------------------------------


@mcp.tool()
@_guard
def standings(season: int, competition: str = "Brasileirão Série A", limit: int = 30) -> str:
    """League table for a season, calculated from match results (3-1-0)."""
    table = queries.standings(competition, season)
    resolved = queries._competition(competition) or competition
    return format_standings(table, resolved, season, limit=limit)


@mcp.tool()
@_guard
def season_champion(season: int, competition: str = "Brasileirão Série A") -> str:
    """Who won a competition in a given season (league leader / final winner)."""
    result = queries.champion(competition, season)
    if not result.get("champion"):
        message = (
            f"Could not determine the {result['competition']} {season} champion "
            f"from the dataset ({result.get('basis', 'insufficient data')})."
        )
        if result.get("finalists"):
            message += " Finalists: " + " and ".join(result["finalists"]) + "."
        for match in result.get("matches", []):
            message += (
                f"\n- {match['date']}: {match['home_team']} {match['home_goals']}-"
                f"{match['away_goals']} {match['away_team']}"
            )
        return message
    lines = [
        f"{season} {result['competition']} champion: {result['champion']}",
        f"Basis: {result['basis']}",
    ]
    if result.get("record"):
        record = result["record"]
        lines.append(
            f"Record: {record['points']} pts ({record['wins']}W, {record['draws']}D, "
            f"{record['losses']}L), GF {record['goals_for']} GA {record['goals_against']}"
        )
    if result.get("runner_up"):
        lines.append(f"Runner-up: {result['runner_up']}")
    for match in result.get("matches", []):
        lines.append(
            f"- {match['date']}: {match['home_team']} {match['home_goals']}-"
            f"{match['away_goals']} {match['away_team']}"
        )
    return "\n".join(lines)


@mcp.tool()
@_guard
def relegated_teams(season: int, competition: str = "Brasileirão Série A", count: int = 4) -> str:
    """Bottom placed clubs of a season's calculated table (relegation zone)."""
    result = queries.relegated(season, competition, count)
    if not result["relegated"]:
        return f"No {result['competition']} table available for {season}."
    lines = [
        f"{season} {result['competition']} relegation zone "
        f"(bottom {count} of {result['teams_in_table']}, {result['note']}):"
    ]
    for record in result["relegated"]:
        lines.append(
            f"- {record['team']}: {record['points']} pts ({record['wins']}W "
            f"{record['draws']}D {record['losses']}L), GD {record['goal_difference']:+d}"
        )
    return "\n".join(lines)


@mcp.tool()
@_guard
def competition_bracket(season: int, competition: str = "Copa Libertadores") -> str:
    """Knockout matches for a season, grouped by stage."""
    bracket = queries.season_bracket(competition, season)
    if not bracket["stages"]:
        return f"No {competition} matches for {season} in the dataset."
    lines = [f"{season} {bracket['competition']} by stage:"]
    for stage, matches in bracket["stages"].items():
        lines.append(f"\n{stage} ({len(matches)} matches):")
        for match in matches[:20]:
            lines.append(f"- {format_match(match, show_competition=False)}")
        if len(matches) > 20:
            lines.append(f"- ... ({len(matches) - 20} more)")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 5. statistics
# --------------------------------------------------------------------------


@mcp.tool()
@_guard
def competition_statistics(
    competition: str | None = None, season: int | None = None
) -> str:
    """Goals per match, home/draw/away split and volume for a competition slice."""
    return format_stats(queries.competition_stats(competition, season))


@mcp.tool()
@_guard
def biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    team: str | None = None,
    limit: int = 10,
) -> str:
    """Largest winning margins in the dataset, optionally filtered."""
    matches = queries.biggest_wins(competition, season, team, limit)
    scope = ", ".join(
        part for part in [team, competition, str(season) if season else None] if part
    )
    return format_matches(
        matches, f"Biggest victories ({scope or 'all data'}):", limit=limit
    )


@mcp.tool()
@_guard
def team_rankings(
    competition: str | None = None,
    season: int | None = None,
    venue: str = "any",
    metric: str = "points_per_game",
    min_matches: int = 10,
    limit: int = 10,
) -> str:
    """Rank clubs by a metric.

    Args:
        metric: "points_per_game", "points", "win_rate", "wins", "goals_for",
            "goals_per_game" or "goal_difference".
        venue: "home", "away" or "any" -- e.g. best away record.
        min_matches: ignore clubs with fewer matches than this.
    """
    records = queries.best_records(
        competition=competition,
        season=season,
        venue=venue,
        metric=metric,
        min_matches=min_matches,
        limit=limit,
    )
    scope = ", ".join(
        part
        for part in [
            competition,
            str(season) if season else None,
            f"{venue} matches" if venue != "any" else None,
        ]
        if part
    )
    return format_ranking(records, f"Top teams by {metric} ({scope or 'all data'}):", metric)


@mcp.tool()
@_guard
def compare_seasons(seasons: list[int], competition: str | None = None) -> str:
    """Compare aggregate statistics across several seasons."""
    blocks = [format_stats(stats) for stats in queries.compare_seasons(seasons, competition)]
    return "\n\n".join(blocks)


@mcp.tool()
def dataset_overview() -> str:
    """What data is loaded: files, matches, teams, players, season coverage."""
    overview = queries.dataset_overview()
    lines = [
        "Brazilian soccer knowledge graph:",
        f"- Matches (de-duplicated): {overview['matches']}",
        f"- Source rows read: {overview['rows_read']} "
        f"({overview['duplicate_rows_merged']} duplicates merged across files)",
        f"- Teams: {overview['teams']}",
        f"- Players (FIFA): {overview['players']}",
        f"- Load time: {overview['load_seconds']}s",
        "Competitions:",
    ]
    for competition, count in overview["competitions"].items():
        span = overview["seasons_by_competition"].get(competition) or []
        window = f" ({span[0]}-{span[1]})" if span else ""
        lines.append(f"- {competition}: {count} matches{window}")
    lines.append(
        "Note: the datasets contain no goal-scorer or lineup information, so "
        "individual scoring records cannot be derived."
    )
    return "\n".join(lines)


def main() -> None:
    """Entry point: serve over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
