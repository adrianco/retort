"""Turn query results into the plain-text answer format used by the MCP tools."""

from __future__ import annotations

from typing import Optional

from .loader import Match, Player
from .normalize import COMPETITION_NAMES
from .queries import TeamRecord, label


def _score(match: Match) -> str:
    return f"{match.home_goals}-{match.away_goals}"


def _match_line(match: Match) -> str:
    where = COMPETITION_NAMES[match.competition]
    if match.stage:
        where = f"{where}, {match.stage}"
    return (f"- {match.date.isoformat()}: {label(match.home)} {_score(match)} "
            f"{label(match.away)} ({where})")


def format_matches(matches: list[Match], title: str, limit: int = 20) -> str:
    if not matches:
        return f"{title}:\nNo matches found in the dataset."
    lines = [f"{title}:"] + [_match_line(m) for m in matches[:limit]]
    if len(matches) > limit:
        lines.append(f"- ... ({len(matches) - limit} more matches in dataset)")
    lines.append(f"\nTotal matches: {len(matches)}")
    return "\n".join(lines)


def format_head_to_head(h: dict) -> str:
    lines = [f"{h['team_a']} vs {h['team_b']} head-to-head in dataset:"]
    if not h["matches"]:
        lines.append("No meetings found.")
        return "\n".join(lines)
    lines.append(f"Matches: {len(h['matches'])}")
    lines.append(f"{h['team_a']} wins: {h['wins_a']}, {h['team_b']} wins: {h['wins_b']}, "
                 f"draws: {h['draws']}")
    lines.append(f"Goals: {h['team_a']} {h['goals_a']} - {h['goals_b']} {h['team_b']}")
    lines.append("")
    lines.append(_match_line(h["last_meeting"]).replace("- ", "Most recent: ", 1))
    lines.append("")
    lines.append("Recent meetings:")
    lines.extend(_match_line(m) for m in h["matches"][:10])
    return "\n".join(lines)


def format_team_record(result: dict) -> str:
    rec: TeamRecord = result["record"]
    scope = result["season"] or "all seasons"
    venue = {"either": "all matches", "home": "home matches", "away": "away matches"}[result["venue"]]
    lines = [
        f"{result['team']} record ({scope}, {result['competition']}, {venue}):",
        f"- Matches: {rec.played}",
        f"- Wins: {rec.wins}, Draws: {rec.draws}, Losses: {rec.losses}",
        f"- Goals For: {rec.goals_for}, Goals Against: {rec.goals_against}",
        f"- Win rate: {rec.win_rate}%",
    ]
    if rec.played == 0:
        lines.append("No matches found in the dataset for these filters.")
    return "\n".join(lines)


def format_standings(rows: list[dict], season: int, competition: str) -> str:
    if not rows:
        return f"No standings found for {competition} {season}."
    lines = [f"{season} {competition} standings (calculated from matches):"]
    for row in rows:
        lines.append(
            f"{row['position']}. {row['team']} - {row['points']} pts "
            f"({row['won']}W, {row['drawn']}D, {row['lost']}L) "
            f"GF {row['goals_for']} GA {row['goals_against']} GD {row['goal_difference']:+d}"
        )
    return "\n".join(lines)


def format_league_stats(stats: dict) -> str:
    scope = stats["season"] or "all seasons"
    if not stats["matches"]:
        return f"No matches found for {stats['competition']} ({scope})."
    return "\n".join([
        f"{stats['competition']} statistics ({scope}, {stats['matches']} matches):",
        f"- Goals per match: {stats['goals_per_match']}",
        f"- Total goals: {stats['total_goals']}",
        f"- Home win rate: {stats['home_win_pct']}%",
        f"- Draw rate: {stats['draw_pct']}%",
        f"- Away win rate: {stats['away_win_pct']}%",
    ])


def format_biggest_wins(matches: list[Match]) -> str:
    if not matches:
        return "No matches found for these filters."
    lines = ["Biggest wins in dataset:"]
    for i, m in enumerate(matches, start=1):
        winner_home = m.home_goals > m.away_goals
        winner = m.home if winner_home else m.away
        loser = m.away if winner_home else m.home
        win_goals = max(m.home_goals, m.away_goals)
        lose_goals = min(m.home_goals, m.away_goals)
        lines.append(f"{i}. {m.date.isoformat()}: {label(winner)} {win_goals}-{lose_goals} "
                     f"{label(loser)} ({COMPETITION_NAMES[m.competition]})")
    return "\n".join(lines)


def format_leaderboard(rows: list[dict], venue: str, min_matches: int) -> str:
    if not rows:
        return f"No teams with at least {min_matches} {venue} matches found."
    lines = [f"Best {venue} win rates (minimum {min_matches} matches):"]
    for i, row in enumerate(rows, start=1):
        rec: TeamRecord = row["record"]
        lines.append(f"{i}. {row['team']} - {row['win_rate']}% "
                     f"({rec.wins}W, {rec.draws}D, {rec.losses}L in {rec.played} {venue} matches)")
    return "\n".join(lines)


def format_players(players: list[Player], title: str) -> str:
    if not players:
        return f"{title}:\nNo players found in the dataset."
    lines = [f"{title}:"]
    for i, p in enumerate(players, start=1):
        lines.append(f"{i}. {p.name} - Overall: {p.overall}, Potential: {p.potential}, "
                     f"Age: {p.age}, Position: {p.position or 'n/a'}, Club: {p.club or 'n/a'}, "
                     f"Nationality: {p.nationality}")
    return "\n".join(lines)


def format_brazilian_clubs(rows: list[dict]) -> str:
    if not rows:
        return "No Brazilian players found at Brazilian clubs."
    lines = ["Brazilian players at Brazilian clubs (FIFA dataset):"]
    lines.extend(f"- {r['club']}: {r['players']} players (avg overall: {r['avg_overall']})"
                 for r in rows)
    return "\n".join(lines)


def format_teams(rows: list[dict], query: str) -> str:
    if not rows:
        return f"No clubs matching {query!r} in the dataset."
    lines = [f"Clubs matching {query!r} (by number of match rows):"]
    lines.extend(f"- {r['team']} ({r['matches']} matches)" for r in rows)
    return "\n".join(lines)


def describe_filters(*pairs: tuple[str, Optional[object]]) -> str:
    """Render the non-empty filters, for titles such as 'Matches for Flamengo, 2023'."""
    parts = [str(value) for _, value in pairs if value not in (None, "")]
    return ", ".join(parts) if parts else "all"
