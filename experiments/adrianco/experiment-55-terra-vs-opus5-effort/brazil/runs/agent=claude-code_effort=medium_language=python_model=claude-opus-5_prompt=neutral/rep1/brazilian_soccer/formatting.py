"""Human-readable rendering of query results.

Context
-------
The MCP tools return text, because that is what an LLM consumes best and it is
what the "Example answer format" blocks in ``TASK.md`` show.  Every renderer
here takes the plain data produced by :mod:`brazilian_soccer.queries` and emits
the corresponding layout, e.g.::

    Corinthians home record (2022, Brasileirão Série A):
    - Matches: 19
    - Wins: 12, Draws: 4, Losses: 3
    ...

Rendering is deliberately separate from querying so the analytics stay testable
as data and the presentation stays testable as strings.
"""

from __future__ import annotations

from .models import HeadToHead, Match, Player, TeamRecord


def format_score(match: Match) -> str:
    if not match.has_score:
        return "no score recorded"
    return f"{match.home_goals}-{match.away_goals}"


def format_match(match: Match, show_competition: bool = True) -> str:
    """``2019-11-23: Flamengo-RJ 2-1 River Plate (Copa Libertadores, final)``."""
    when = match.match_date.isoformat() if match.match_date else f"{match.season or '?'}"
    line = f"{when}: {match.home_name} {format_score(match)} {match.away_name}"
    if show_competition:
        context = [match.competition]
        if match.season is not None and (
            not match.match_date or match.match_date.year != match.season
        ):
            context.append(f"season {match.season}")
        if match.stage:
            context.append(match.stage)
        elif match.round:
            context.append(f"round {match.round}")
        line += " (" + ", ".join(context) + ")"
    if match.venue:
        line += f" @ {match.venue}"
    return line


def format_matches(
    matches: list[Match], title: str, limit: int = 25, total: int | None = None
) -> str:
    if not matches:
        return f"{title}\nNo matches found in the dataset."
    lines = [title]
    for match in matches[:limit]:
        lines.append(f"- {format_match(match)}")
    total = total if total is not None else len(matches)
    if total > limit:
        lines.append(f"- ... ({total - limit} more matches in dataset)")
    return "\n".join(lines)


def format_record(record: TeamRecord, title: str | None = None) -> str:
    """The team-statistics block from the spec."""
    heading = (title or f"{record.team_name} record").rstrip(":")
    if record.played == 0:
        return f"{heading}:\n- No matches with recorded scores in the dataset."
    return "\n".join(
        [
            f"{heading}:",
            f"- Matches: {record.played}",
            f"- Wins: {record.wins}, Draws: {record.draws}, Losses: {record.losses}",
            f"- Goals For: {record.goals_for}, Goals Against: {record.goals_against}"
            f" (GD {record.goal_difference:+d})",
            f"- Points: {record.points} ({record.points_per_game:.2f} per game)",
            f"- Win rate: {record.win_rate:.1f}%",
        ]
    )


def format_head_to_head(h2h: HeadToHead, limit: int = 15) -> str:
    if not h2h.matches:
        return (
            f"{h2h.team_a} vs {h2h.team_b}:\n"
            "No meetings between these teams in the dataset."
        )
    lines = [f"{h2h.team_a} vs {h2h.team_b}:"]
    for match in h2h.matches[:limit]:
        lines.append(f"- {format_match(match)}")
    if h2h.total > limit:
        lines.append(f"- ... ({h2h.total - limit} more matches in dataset)")
    lines.append("")
    lines.append(
        f"Head-to-head in dataset: {h2h.team_a} {h2h.a_wins} wins, "
        f"{h2h.team_b} {h2h.b_wins} wins, {h2h.draws} draws "
        f"(goals {h2h.a_goals}-{h2h.b_goals})"
    )
    return "\n".join(lines)


def format_standings(
    table: list[TeamRecord],
    competition: str,
    season: int,
    limit: int = 30,
    relegation_places: int = 4,
) -> str:
    if not table:
        return f"No {competition} matches for season {season} in the dataset."
    lines = [f"{season} {competition} standings (calculated from match results):"]
    relegation_zone = len(table) - relegation_places
    for position, record in enumerate(table[:limit], start=1):
        tag = ""
        if position == 1:
            tag = " - Champion"
        elif position > relegation_zone:
            tag = " - Relegation zone"
        lines.append(
            f"{position:2d}. {record.team_name} - {record.points} pts "
            f"({record.wins}W, {record.draws}D, {record.losses}L) "
            f"GF {record.goals_for} GA {record.goals_against} "
            f"GD {record.goal_difference:+d}{tag}"
        )
    if len(table) > limit:
        lines.append(f"... ({len(table) - limit} more teams)")
    return "\n".join(lines)


def format_player(player: Player, detailed: bool = False) -> str:
    parts = [player.name]
    if player.overall is not None:
        parts.append(f"Overall: {player.overall}")
    if player.potential is not None:
        parts.append(f"Potential: {player.potential}")
    if player.position:
        parts.append(f"Position: {player.position}")
    if player.club_raw:
        parts.append(f"Club: {player.club_raw}")
    parts.append(f"Nationality: {player.nationality}")
    if player.age is not None:
        parts.append(f"Age: {player.age}")
    line = ", ".join(parts)
    if not detailed:
        return line
    extra = []
    if player.value:
        extra.append(f"Value: {player.value}")
    if player.wage:
        extra.append(f"Wage: {player.wage}")
    if player.height:
        extra.append(f"Height: {player.height}")
    if player.weight:
        extra.append(f"Weight: {player.weight}")
    if player.preferred_foot:
        extra.append(f"Preferred foot: {player.preferred_foot}")
    if player.jersey_number is not None:
        extra.append(f"Shirt: {player.jersey_number}")
    lines = [line]
    if extra:
        lines.append("  " + ", ".join(extra))
    if player.skills:
        top = sorted(player.skills.items(), key=lambda item: -item[1])[:8]
        lines.append("  Top attributes: " + ", ".join(f"{k} {v}" for k, v in top))
    return "\n".join(lines)


def format_players(players: list[Player], title: str, limit: int = 25) -> str:
    if not players:
        return f"{title}\nNo players found in the FIFA dataset."
    lines = [title]
    for position, player in enumerate(players[:limit], start=1):
        lines.append(f"{position}. {format_player(player)}")
    if len(players) > limit:
        lines.append(f"... ({len(players) - limit} more players)")
    return "\n".join(lines)


def format_stats(stats: dict) -> str:
    season = f" {stats['season']}" if stats.get("season") else ""
    lines = [f"{stats['competition']}{season} statistics:"]
    covered = stats.get("seasons_covered")
    if covered and not stats.get("season"):
        lines.append(f"- Seasons covered: {covered[0]}-{covered[1]}")
    lines.extend(
        [
            f"- Matches: {stats['matches']} ({stats['matches_with_scores']} with scores)",
            f"- Total goals: {stats['total_goals']}",
            f"- Average goals per match: {stats['goals_per_match']}",
            f"- Home wins: {stats['home_wins']} ({stats['home_win_rate']}%)",
            f"- Draws: {stats['draws']} ({stats['draw_rate']}%)",
            f"- Away wins: {stats['away_wins']} ({stats['away_win_rate']}%)",
        ]
    )
    return "\n".join(lines)


def format_ranking(
    records: list[TeamRecord], title: str, metric: str = "points_per_game"
) -> str:
    if not records:
        return f"{title}\nNo teams matched the filters."
    labels = {
        "points_per_game": lambda r: f"{r.points_per_game:.2f} pts/game",
        "points": lambda r: f"{r.points} pts",
        "win_rate": lambda r: f"{r.win_rate:.1f}% win rate",
        "wins": lambda r: f"{r.wins} wins",
        "goals_for": lambda r: f"{r.goals_for} goals",
        "goals_per_game": lambda r: f"{r.goals_per_game:.2f} goals/game",
        "goal_difference": lambda r: f"{r.goal_difference:+d} GD",
    }
    label = labels.get(metric, labels["points_per_game"])
    lines = [title]
    for position, record in enumerate(records, start=1):
        lines.append(
            f"{position}. {record.team_name} - {label(record)} "
            f"({record.played} matches: {record.wins}W {record.draws}D {record.losses}L,"
            f" GF {record.goals_for} GA {record.goals_against})"
        )
    return "\n".join(lines)


def format_team_profile(profile: dict) -> str:
    lines = [f"{profile['team']} ({profile['team_key']})"]
    if profile.get("region"):
        lines.append(f"State/country: {profile['region']}")
    overall = profile["overall"]
    lines.append(
        f"All competitions: {overall['played']} matches, {overall['wins']}W "
        f"{overall['draws']}D {overall['losses']}L, GF {overall['goals_for']} "
        f"GA {overall['goals_against']}, win rate {overall['win_rate']}%"
    )
    home, away = profile["home"], profile["away"]
    lines.append(
        f"Home: {home['played']} matches, {home['wins']}W {home['draws']}D "
        f"{home['losses']}L ({home['win_rate']}%)"
    )
    lines.append(
        f"Away: {away['played']} matches, {away['wins']}W {away['draws']}D "
        f"{away['losses']}L ({away['win_rate']}%)"
    )
    if profile["seasons"]:
        lines.append(
            f"Seasons in dataset: {profile['seasons'][0]}-{profile['seasons'][-1]} "
            f"({len(profile['seasons'])} seasons)"
        )
    lines.append("Competitions played:")
    for name, record in profile["competitions"].items():
        lines.append(
            f"- {name}: {record['played']} matches, {record['wins']}W "
            f"{record['draws']}D {record['losses']}L"
        )
    if profile.get("fifa_players"):
        lines.append(f"Players in the FIFA dataset: {profile['fifa_players']}")
    if profile.get("known_as"):
        lines.append("Also spelled: " + ", ".join(profile["known_as"][:8]))
    return "\n".join(lines)


def format_bullet_table(rows: list[dict], title: str, columns: list[str]) -> str:
    if not rows:
        return f"{title}\nNothing found."
    lines = [title]
    for row in rows:
        lines.append(
            "- " + ", ".join(f"{column}: {row.get(column)}" for column in columns)
        )
    return "\n".join(lines)
