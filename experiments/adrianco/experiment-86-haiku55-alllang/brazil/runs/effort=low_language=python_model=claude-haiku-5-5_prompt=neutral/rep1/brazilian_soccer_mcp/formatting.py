# Context: Turns query results into the plain-text answer layout described in the spec
# (match lines, head-to-head summaries, standings tables, player lists). The LLM receives these
# strings through MCP tool results, so they are kept compact and self-describing.

from __future__ import annotations

from .data import Match, Player
from .queries import HeadToHead, SeasonStats, StandingRow, TeamRecord


def match_line(match: Match) -> str:
    stage = f" ({match.competition}{', ' + match.stage if match.stage else ''})"
    return (
        f"- {match.played_on.isoformat()}: {match.home.label} {match.home_goals}-"
        f"{match.away_goals} {match.away.label}{stage}"
    )


def format_matches(title: str, matches: list[Match], total: int | None = None) -> str:
    if not matches:
        return f"{title}\nNo matches found in the dataset."
    lines = [title] + [match_line(m) for m in matches]
    if total is not None and total > len(matches):
        lines.append(f"- ... ({total - len(matches)} more matches in dataset)")
    return "\n".join(lines)


def format_record(record: TeamRecord, label: str) -> str:
    if record.played == 0:
        return f"{record.team} {label}\nNo matches found in the dataset."
    return "\n".join([
        f"{record.team} {label}:",
        f"- Matches: {record.played}",
        f"- Wins: {record.wins}, Draws: {record.draws}, Losses: {record.losses}",
        f"- Goals For: {record.goals_for}, Goals Against: {record.goals_against}",
        f"- Goal difference: {record.goal_difference:+d}",
        f"- Win rate: {record.win_rate:.1%}",
    ])


def format_head_to_head(h2h: HeadToHead, recent: int = 5) -> str:
    if not h2h.matches:
        return f"{h2h.team_a} vs {h2h.team_b}: no head-to-head matches in the dataset."
    lines = [
        f"{h2h.team_a} vs {h2h.team_b} head-to-head in dataset:",
        f"{h2h.team_a} {h2h.a_wins} wins, {h2h.team_b} {h2h.b_wins} wins, {h2h.draws} draws "
        f"({len(h2h.matches)} matches)",
        "Most recent:",
    ]
    lines += [match_line(m) for m in h2h.matches[:recent]]
    return "\n".join(lines)


def format_standings(title: str, rows: list[StandingRow], relegation_places: int = 0) -> str:
    if not rows:
        return f"{title}\nNo matches found in the dataset."
    lines = [title]
    for position, row in enumerate(rows, start=1):
        tag = ""
        if position == 1:
            tag = " - Champion"
        elif relegation_places and position > len(rows) - relegation_places:
            tag = " - Relegated"
        lines.append(
            f"{position}. {row.team} - {row.points} pts ({row.wins}W, {row.draws}D, {row.losses}L, "
            f"GD {row.goal_difference:+d}){tag}"
        )
    return "\n".join(lines)


def format_season_stats(title: str, stats: SeasonStats) -> str:
    if stats.matches == 0:
        return f"{title}\nNo matches found in the dataset."
    return "\n".join([
        title,
        f"Matches: {stats.matches}, total goals: {stats.goals}",
        f"Average goals per match: {stats.goals_per_match:.2f}",
        f"Home win rate: {stats.home_win_rate:.1%}, draw rate: {stats.draw_rate:.1%}, "
        f"away win rate: {stats.away_win_rate:.1%}",
    ])


def format_venue_ranking(title: str, records: list[TeamRecord]) -> str:
    if not records:
        return f"{title}\nNo teams meet the minimum match count."
    lines = [title]
    for position, record in enumerate(records, start=1):
        lines.append(
            f"{position}. {record.team} - {record.win_rate:.1%} "
            f"({record.wins}W, {record.draws}D, {record.losses}L in {record.played} matches)"
        )
    return "\n".join(lines)


def player_line(player: Player) -> str:
    return (
        f"{player.name} - Overall: {player.overall}, Position: {player.position}, "
        f"Club: {player.club}, Nationality: {player.nationality}"
    )


def format_players(title: str, players: list[Player]) -> str:
    if not players:
        return f"{title}\nNo players found in the dataset."
    return "\n".join([title] + [f"{i}. {player_line(p)}" for i, p in enumerate(players, start=1)])


def format_club_profile(club: str, squad: list[Player]) -> str:
    if not squad:
        return f"{club}: no players found in the player dataset."
    average = sum(p.overall for p in squad) / len(squad)
    return "\n".join([
        f"{club} squad in player dataset:",
        f"- Players: {len(squad)} (avg overall: {average:.1f})",
        "- Top rated:",
    ] + [f"  {i}. {player_line(p)}" for i, p in enumerate(squad[:5], start=1)])
