"""Brazilian Soccer MCP Server.

Exposes the Kaggle Brazilian soccer datasets (Brasileirão, Copa do Brasil,
Copa Libertadores, extended match stats and FIFA player data) as MCP tools so
an LLM can answer natural language questions about players, teams, matches
and competitions.

Run over stdio:

    python server.py
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from mcp.server.fastmcp import FastMCP

import queries
from data_loader import SoccerDatabase, load_database

mcp = FastMCP(
    "brazilian-soccer",
    instructions=(
        "Knowledge graph over Brazilian soccer data: Brasileirão Série A/B/C "
        "(2003-2023), Copa do Brasil, Copa Libertadores and FIFA player "
        "ratings. Team names are normalized, so 'Flamengo', 'Flamengo-RJ' "
        "and 'flamengo' all work. Use data_summary to see coverage."
    ),
)


@lru_cache(maxsize=1)
def get_db() -> SoccerDatabase:
    return load_database()


def _format_match(match: dict) -> str:
    date = match["date"] or "unknown date"
    context = match["competition"]
    if match.get("stage"):
        context += f", {match['stage']}"
    elif match.get("round"):
        context += f" Round {match['round']}"
    return f"- {date}: {match['score']} ({context})"


def _format_record(entry: dict) -> str:
    return (f"{entry['played']} played — {entry['wins']}W {entry['draws']}D "
            f"{entry['losses']}L, GF {entry['goals_for']}, "
            f"GA {entry['goals_against']}")


@mcp.tool()
def search_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Find matches by team, opponent, competition, season and/or date range.

    Args:
        team: Team name in any common form ("Flamengo", "Atlético-MG").
        opponent: Restrict to matches against this second team.
        competition: "Brasileirão"/"Série A", "Série B", "Série C",
            "Copa do Brasil" or "Libertadores".
        season: Season year, e.g. 2019.
        date_from: Earliest date, ISO format (YYYY-MM-DD).
        date_to: Latest date, ISO format (YYYY-MM-DD).
        limit: Maximum number of matches to list (newest first).
    """
    matches = queries.filter_matches(
        get_db(), team=team, opponent=opponent, competition=competition,
        season=season, date_from=date_from, date_to=date_to)
    if not matches:
        return "No matches found for those criteria."
    shown = [queries.match_to_dict(m) for m in matches[:max(0, limit)]]
    lines = [f"Found {len(matches)} matches (showing {len(shown)}, newest first):"]
    lines += [_format_match(m) for m in shown]
    if len(matches) > len(shown):
        lines.append(f"... ({len(matches) - len(shown)} more in dataset)")
    return "\n".join(lines)


@mcp.tool()
def head_to_head(team1: str, team2: str,
                 competition: Optional[str] = None) -> str:
    """Head-to-head record between two teams: wins, draws, goals and the
    most recent meetings.

    Args:
        team1: First team name.
        team2: Second team name.
        competition: Optional competition filter.
    """
    result = queries.head_to_head(get_db(), team1, team2,
                                  competition=competition)
    if not result["matches"]:
        return f"No matches found between {team1} and {team2}."
    lines = [
        f"{result['team1']} vs {result['team2']} — "
        f"{result['matches']} matches in dataset:",
        f"Head-to-head: {result['team1']} {result['team1_wins']} wins, "
        f"{result['team2']} {result['team2_wins']} wins, "
        f"{result['draws']} draws",
        f"Goals: {result['team1']} {result['team1_goals']} — "
        f"{result['team2']} {result['team2_goals']}",
        "",
        "Most recent meetings:",
    ]
    lines += [_format_match(m) for m in result["recent_matches"][:10]]
    return "\n".join(lines)


@mcp.tool()
def team_statistics(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "all",
) -> str:
    """Win/draw/loss record, goals and win rate for a team.

    Args:
        team: Team name.
        season: Optional season year filter.
        competition: Optional competition filter.
        venue: "home", "away" or "all".
    """
    stats = queries.team_statistics(get_db(), team, season=season,
                                    competition=competition, venue=venue)
    if not stats["played"]:
        return f"No scored matches found for {team} with those filters."
    scope = []
    if stats["season"]:
        scope.append(str(stats["season"]))
    if stats["competition"]:
        scope.append(stats["competition"])
    if venue != "all":
        scope.append(f"{venue} games")
    title = f"{stats['team']} record" + (f" ({', '.join(scope)})" if scope else "")
    lines = [
        title + ":",
        f"- Matches: {stats['played']}",
        f"- Wins: {stats['wins']}, Draws: {stats['draws']}, "
        f"Losses: {stats['losses']}",
        f"- Goals For: {stats['goals_for']}, "
        f"Goals Against: {stats['goals_against']}",
        f"- Win rate: {stats['win_rate']}%",
    ]
    if len(stats["by_competition"]) > 1:
        lines.append("By competition:")
        for comp, c in sorted(stats["by_competition"].items()):
            lines.append(
                f"- {comp}: {c.get('played', 0)} played, {c.get('wins', 0)}W "
                f"{c.get('draws', 0)}D {c.get('losses', 0)}L")
    return "\n".join(lines)


@mcp.tool()
def competition_standings(season: int, competition: str = "serie a",
                          limit: int = 25) -> str:
    """League standings for a season, calculated from match results
    (3 points per win, 1 per draw).

    Args:
        season: Season year, e.g. 2019.
        competition: Competition name (default Brasileirão Série A).
        limit: Maximum table rows to show.
    """
    table = queries.competition_standings(get_db(), season,
                                          competition=competition)
    rows = table["standings"]
    if not rows:
        return (f"No match data for {table['competition']} {season}. "
                "Use data_summary to see available seasons.")
    lines = [f"{table['competition']} {season} standings "
             f"(calculated from {table['matches_counted']} matches):"]
    for entry in rows[:max(0, limit)]:
        marker = " - Champion" if entry["position"] == 1 else ""
        lines.append(
            f"{entry['position']}. {entry['team']} - {entry['points']} pts "
            f"({entry['wins']}W, {entry['draws']}D, {entry['losses']}L, "
            f"GD {entry['goal_difference']:+d}){marker}")
    return "\n".join(lines)


@mcp.tool()
def goal_statistics(competition: Optional[str] = None,
                    season: Optional[int] = None) -> str:
    """Average goals per match and home/draw/away outcome rates.

    Args:
        competition: Optional competition filter.
        season: Optional season year filter.
    """
    stats = queries.goal_statistics(get_db(), competition=competition,
                                    season=season)
    if not stats["matches"]:
        return "No scored matches found for those filters."
    scope = stats["competition"] or "all competitions"
    if stats["season"]:
        scope += f", {stats['season']}"
    return "\n".join([
        f"Goal statistics ({scope}):",
        f"- Matches: {stats['matches']}",
        f"- Total goals: {stats['total_goals']}",
        f"- Average goals per match: {stats['avg_goals_per_match']}",
        f"- Home wins: {stats['home_win_rate']}% ({stats['home_wins']})",
        f"- Draws: {stats['draw_rate']}% ({stats['draws']})",
        f"- Away wins: {stats['away_win_rate']}% ({stats['away_wins']})",
    ])


@mcp.tool()
def biggest_wins(competition: Optional[str] = None,
                 season: Optional[int] = None, limit: int = 10) -> str:
    """Matches with the largest margins of victory.

    Args:
        competition: Optional competition filter.
        season: Optional season year filter.
        limit: Number of matches to return.
    """
    wins = queries.biggest_wins(get_db(), competition=competition,
                                season=season, limit=limit)
    if not wins:
        return "No scored matches found for those filters."
    lines = ["Biggest victories in dataset:"]
    for index, match in enumerate(wins, start=1):
        lines.append(f"{index}. {match['date']}: {match['score']} "
                     f"({match['competition']})")
    return "\n".join(lines)


@mcp.tool()
def best_records(
    venue: str = "home",
    competition: Optional[str] = None,
    season: Optional[int] = None,
    min_matches: int = 10,
    limit: int = 10,
) -> str:
    """Teams ranked by win rate, e.g. best home or away record.

    Args:
        venue: "home", "away" or "all".
        competition: Optional competition filter.
        season: Optional season year filter.
        min_matches: Minimum matches played to qualify.
        limit: Number of teams to return.
    """
    ranked = queries.best_records(get_db(), venue=venue,
                                  competition=competition, season=season,
                                  min_matches=min_matches, limit=limit)
    if not ranked:
        return "No teams matched those filters (try lowering min_matches)."
    scope = venue if venue != "all" else "overall"
    lines = [f"Best {scope} records (min {min_matches} matches):"]
    for index, entry in enumerate(ranked, start=1):
        lines.append(f"{index}. {entry['team']} - {entry['win_rate']}% win "
                     f"rate ({_format_record(entry)})")
    return "\n".join(lines)


@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 20,
) -> str:
    """Search FIFA player data by name, nationality, club and/or position.

    Args:
        name: Partial player name (accent-insensitive).
        nationality: e.g. "Brazil".
        club: Partial club name, e.g. "Cruzeiro".
        position: A position code ("ST", "GK", "CAM", comma-separated list)
            or a group: "forward", "midfielder", "defender", "goalkeeper".
        min_overall: Minimum FIFA overall rating.
        limit: Maximum players to return (sorted by overall rating).
    """
    result = queries.search_players(
        get_db(), name=name, nationality=nationality, club=club,
        position=position, min_overall=min_overall, limit=limit)
    if not result["total_matches"]:
        return "No players found for those criteria."
    lines = [f"Found {result['total_matches']} players "
             f"(showing top {len(result['players'])} by rating):"]
    for index, player in enumerate(result["players"], start=1):
        club_name = player["club"] or "no club"
        lines.append(
            f"{index}. {player['name']} - Overall: {player['overall']}, "
            f"Position: {player['position'] or '?'}, Club: {club_name}, "
            f"Nationality: {player['nationality']}")
    return "\n".join(lines)


@mcp.tool()
def get_player(name: str) -> str:
    """Detailed profile (ratings, club, physicals, top skills) for one player.

    Args:
        name: Player name, full or partial, e.g. "Gabriel Barbosa".
    """
    profile = queries.get_player(get_db(), name)
    if profile is None:
        return f"No player matching {name!r} found in the FIFA dataset."
    top_skills = sorted(profile["skills"].items(), key=lambda kv: kv[1],
                        reverse=True)[:8]
    lines = [
        f"{profile['name']}",
        f"- Overall: {profile['overall']} (Potential: {profile['potential']})",
        f"- Position: {profile['position'] or '?'}, "
        f"Jersey: {profile['jersey_number'] or '?'}",
        f"- Club: {profile['club'] or 'no club'}",
        f"- Nationality: {profile['nationality']}, Age: {profile['age']}",
        f"- Height: {profile['height']}, Weight: {profile['weight']}, "
        f"Preferred foot: {profile['preferred_foot']}",
        f"- Value: {profile['value']}, Wage: {profile['wage']}",
        "Top skills: " + ", ".join(f"{k} {v}" for k, v in top_skills),
    ]
    if profile["other_matches"]:
        lines.append("Other players matching that name: "
                     + ", ".join(profile["other_matches"]))
    return "\n".join(lines)


@mcp.tool()
def data_summary() -> str:
    """Summary of dataset coverage: competitions, seasons, match and player
    counts. Useful to know what questions can be answered."""
    summary = queries.data_summary(get_db())
    lines = [
        "Brazilian soccer dataset coverage:",
        f"- Total matches: {summary['total_matches']} "
        f"({summary['total_teams']} distinct teams)",
        f"- Players (FIFA data): {summary['total_players']} "
        f"({summary['brazilian_players']} Brazilian)",
        "Competitions:",
    ]
    for comp, info in sorted(summary["competitions"].items()):
        lines.append(f"- {comp}: {info['matches']} matches, seasons "
                     f"{info['first_season']}-{info['last_season']}")
    lines.append("Source files: " + ", ".join(
        f"{name} ({count})" for name, count in
        sorted(summary["source_files"].items())))
    return "\n".join(lines)


def main() -> None:
    get_db()          # load data up front so the first query is fast
    mcp.run()         # stdio transport


if __name__ == "__main__":
    main()
