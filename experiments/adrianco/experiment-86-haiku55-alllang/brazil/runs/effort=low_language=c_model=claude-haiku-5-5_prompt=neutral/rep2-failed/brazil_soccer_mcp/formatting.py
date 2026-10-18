"""Turn query results into the plain-text answer format the spec asks for."""

from typing import Dict, Iterable, List

from .models import Match


def team_label(base: str) -> str:
    return base.title()


def format_match_line(match: Match) -> str:
    score = f"{match.home_goals}-{match.away_goals}"
    detail = match.competition
    if match.round_or_stage:
        detail = f"{detail}, {match.round_or_stage}"
    return (
        f"- {match.played_on.isoformat()}: {team_label(match.home.base)} {score} "
        f"{team_label(match.away.base)} ({detail})"
    )


def format_matches(result: Dict, title: str) -> str:
    lines = [title]
    if not result["matches"]:
        lines.append("- No matches found in the dataset.")
        return "\n".join(lines)
    lines += [format_match_line(m) for m in result["matches"]]
    remaining = result["total"] - len(result["matches"])
    if remaining > 0:
        lines.append(f"- ... ({remaining} more matches in dataset)")
    lines.append(f"Total matches in dataset: {result['total']}")
    return "\n".join(lines)


def format_record(name: str, record: Dict, context: str) -> str:
    if not record["played"]:
        return f"{name} ({context}): no matches found in dataset."
    return "\n".join(
        [
            f"{name} ({context}):",
            f"- Matches: {record['played']}",
            f"- Wins: {record['wins']}, Draws: {record['draws']}, Losses: {record['losses']}",
            f"- Goals For: {record['goals_for']}, Goals Against: {record['goals_against']}",
            f"- Win rate: {record['win_rate']}%",
        ]
    )


def format_head_to_head(result: Dict) -> str:
    a, b = team_label(result["a_name"]), team_label(result["b_name"])
    lines = [f"{a} vs {b}:", f"- Matches in dataset: {result['total']}"]
    lines.append(
        f"- {a} wins: {result['a']['wins']}, {b} wins: {result['b']['wins']}, "
        f"Draws: {result['a']['draws']}"
    )
    lines.append(f"- Goals: {a} {result['a']['goals_for']}, {b} {result['b']['goals_for']}")
    for m in result["matches"][:10]:
        lines.append(format_match_line(m))
    if result["total"] > 10:
        lines.append(f"- ... ({result['total'] - 10} more matches in dataset)")
    return "\n".join(lines)


def format_standings(rows: Iterable[Dict], season: int, competition: str) -> str:
    rows = list(rows)
    if not rows:
        return f"No standings available for {competition} {season}."
    lines = [f"{season} {competition} standings (calculated from matches):"]
    for row in rows:
        lines.append(
            f"{row['position']}. {team_label(row['team'])} - {row['points']} pts "
            f"({row['wins']}W, {row['draws']}D, {row['losses']}L, GD {row['goal_difference']:+d})"
        )
    return "\n".join(lines)


def format_league_stats(stats: Dict, label: str) -> str:
    if not stats.get("matches"):
        return f"No matches found for {label}."
    return "\n".join(
        [
            f"{label}:",
            f"- Matches: {stats['matches']}",
            f"- Average goals per match: {stats['goals_per_match']}",
            f"- Home win rate: {stats['home_win_rate']}%",
            f"- Draw rate: {stats['draw_rate']}%",
            f"- Away win rate: {stats['away_win_rate']}%",
        ]
    )


def format_rankings(rows: List[Dict], metric: str) -> str:
    if not rows:
        return f"No teams qualify for ranking by {metric}."
    lines = [f"Teams ranked by {metric}:"]
    for i, row in enumerate(rows, start=1):
        lines.append(
            f"{i}. {team_label(row['team'])} - {row['value']} "
            f"(played {row['played']}, {row['wins']}W {row['draws']}D {row['losses']}L)"
        )
    return "\n".join(lines)


def format_biggest_wins(matches: Iterable[Match]) -> str:
    lines = ["Biggest wins in dataset:"]
    lines += [format_match_line(m) for m in matches]
    return "\n".join(lines) if len(lines) > 1 else "No decided matches found."


def format_players(result: Dict, title: str) -> str:
    lines = [title]
    if not result["players"]:
        lines.append("- No players found in dataset.")
        return "\n".join(lines)
    for i, p in enumerate(result["players"], start=1):
        lines.append(
            f"{i}. {p.name} - Overall: {p.overall}, Position: {p.position or '-'}, "
            f"Club: {p.club or '-'}, Nationality: {p.nationality or '-'}, Age: {p.age}"
        )
    if result["total"] > len(result["players"]):
        lines.append(f"... ({result['total'] - len(result['players'])} more players in dataset)")
    lines.append(f"Total players matched: {result['total']}")
    return "\n".join(lines)


def format_club_summary(rows: List[Dict], label: str) -> str:
    if not rows:
        return f"No players found for {label}."
    lines = [f"Average overall rating by club ({label}):"]
    for row in rows[:20]:
        lines.append(f"- {row['club']}: {row['players']} players (avg overall {row['avg_overall']})")
    return "\n".join(lines)
