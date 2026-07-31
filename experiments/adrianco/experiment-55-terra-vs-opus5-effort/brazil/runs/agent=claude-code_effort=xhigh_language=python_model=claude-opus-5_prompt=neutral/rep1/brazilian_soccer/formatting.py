"""
Human-readable rendering of query results.

Context
-------
TASK.md specifies literal "Example answer format" blocks -- match lists with a
head-to-head summary, a team record card, a ranked player list, a league table.
This module reproduces those layouts so an LLM connected to the MCP server can
quote the answer directly instead of re-deriving prose from JSON.

Every tool returns *both* the rendered text (from here) and the structured data
(from :mod:`brazilian_soccer.queries`), so downstream consumers can pick.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from .graph import KnowledgeGraph
from .models import HeadToHead, Match, Player, StandingRow, Team, TeamRecord

__all__ = [
    "format_match_line",
    "format_matches",
    "format_head_to_head",
    "format_team_record",
    "format_team_profile",
    "format_standings",
    "format_players",
    "format_player_profile",
    "format_club_squad",
    "format_competition_stats",
    "format_compare_teams",
    "format_derbies",
    "format_dataset_summary",
]

_BULLET = "- "


def _short_competition(graph: KnowledgeGraph, competition_id: str) -> str:
    competition = graph.competitions_by_id.get(competition_id)
    return competition.short_name if competition else competition_id


def _context(graph: KnowledgeGraph, match: Match) -> str:
    parts = [_short_competition(graph, match.competition_id)]
    if match.stage:
        # "round of 32" -> "Round of 32"; leave already-capitalised stages alone.
        parts.append(match.stage.capitalize() if match.stage.islower() else match.stage)
    elif match.round:
        parts.append(f"Round {match.round}")
    if match.season is not None:
        parts.append(str(match.season))
    return " ".join(parts)


def format_match_line(graph: KnowledgeGraph, match: Match) -> str:
    """``- 2019-11-23: Flamengo 4-1 Ceará (Brasileirão Round 35 2019)``"""

    date = match.date.isoformat() if match.date else "date unknown"
    home = graph.team_name(match.home_team_id)
    away = graph.team_name(match.away_team_id)
    if match.has_score:
        score = f"{home} {match.home_goals}-{match.away_goals} {away}"
    else:
        score = f"{home} vs {away} (no score recorded)"
    return f"{_BULLET}{date}: {score} ({_context(graph, match)})"


def format_matches(
    graph: KnowledgeGraph,
    matches: Sequence[Match],
    *,
    title: str = "Matches",
    limit: int = 20,
    total: int | None = None,
    empty_message: str | None = None,
) -> str:
    if not matches:
        return empty_message or f"{title}:\nNo matches found in the dataset."
    lines = [f"{title}:"]
    shown = list(matches[:limit])
    lines.extend(format_match_line(graph, match) for match in shown)
    remaining = (total if total is not None else len(matches)) - len(shown)
    if remaining > 0:
        lines.append(f"... ({remaining} more match{'es' if remaining != 1 else ''} in dataset)")
    return "\n".join(lines)


def format_head_to_head(graph: KnowledgeGraph, record: HeadToHead,
                        *, limit: int = 15, all_matches: int | None = None) -> str:
    header = f"{record.team_a} vs {record.team_b}"
    derby = _derby_name(graph, record.team_a_id, record.team_b_id)
    if derby:
        header += f" ({derby})"
    body = format_matches(
        graph, record.matches, title=header, limit=limit, total=all_matches,
        empty_message=f"{header}:\nNo meetings between these clubs in the dataset.",
    )
    if record.played == 0:
        return body
    summary = (
        f"\n\nHead-to-head in dataset: {record.team_a} {record.team_a_wins} wins, "
        f"{record.team_b} {record.team_b_wins} wins, {record.draws} draws "
        f"({record.played} matches with a recorded score)."
        f"\nGoals: {record.team_a} {record.team_a_goals} - {record.team_b_goals} {record.team_b}."
    )
    return body + summary


def _derby_name(graph: KnowledgeGraph, team_a: str, team_b: str) -> str | None:
    pair = {team_a, team_b}
    for derby in graph.derbies:
        if {derby.team_a, derby.team_b} == pair:
            return f"{derby.name} derby"
    return None


def format_team_record(record: TeamRecord, *, title: str | None = None) -> str:
    scope = {"home": "home record", "away": "away record"}.get(record.scope, record.scope)
    heading = title or f"{record.team_name} {scope}"
    return "\n".join([
        f"{heading}:",
        f"{_BULLET}Matches: {record.played}",
        f"{_BULLET}Wins: {record.wins}, Draws: {record.draws}, Losses: {record.losses}",
        f"{_BULLET}Goals For: {record.goals_for}, Goals Against: {record.goals_against} "
        f"(diff {record.goal_difference:+d})",
        f"{_BULLET}Points: {record.points} ({record.points_per_game:.2f} per game)",
        f"{_BULLET}Win rate: {record.win_rate:.1f}%",
    ])


def format_team_profile(graph: KnowledgeGraph, profile: dict[str, Any]) -> str:
    team: Team = profile["team"]
    season = profile["season"]
    scope = f" in {season}" if season else ""
    lines = [f"{team.display_name}{scope}"]
    if team.nicknames:
        lines.append(f"Nicknames: {', '.join(team.nicknames)}")
    seasons = profile["seasons"]
    if seasons:
        lines.append(f"Seasons in dataset: {seasons[0]}-{seasons[-1]} ({len(seasons)} seasons)")
    competitions = [graph.competition_name(c) for c in profile["competitions"]]
    if competitions:
        lines.append(f"Competitions: {', '.join(competitions)}")
    lines.append("")
    lines.append(format_team_record(profile["overall"], title="Overall record"))
    lines.append("")
    lines.append(format_team_record(profile["home"], title="Home record"))
    lines.append("")
    lines.append(format_team_record(profile["away"], title="Away record"))
    if profile["by_competition"]:
        lines.append("")
        lines.append("By competition:")
        for competition_id, record in profile["by_competition"].items():
            lines.append(
                f"{_BULLET}{graph.competition_name(competition_id)}: {record.played} matches, "
                f"{record.wins}W {record.draws}D {record.losses}L, "
                f"{record.goals_for}-{record.goals_against} goals"
            )
    if profile["recent_matches"]:
        lines.append("")
        lines.append(format_matches(graph, profile["recent_matches"],
                                    title="Most recent matches", limit=5))
    if profile["squad_size"]:
        lines.append("")
        lines.append(f"FIFA squad entries linked to this club: {profile['squad_size']}")
    return "\n".join(lines)


def format_standings(graph: KnowledgeGraph, rows: Sequence[StandingRow],
                     *, title: str, limit: int | None = None) -> str:
    if not rows:
        return f"{title}:\nNo results available for this season in the dataset."
    lines = [f"{title}:"]
    shown = rows[:limit] if limit else rows
    for row in shown:
        record = row.record
        note = f" - {row.note}" if row.note else ""
        lines.append(
            f"{row.position}. {record.team_name} - {record.points} pts "
            f"({record.wins}W, {record.draws}D, {record.losses}L) "
            f"GF {record.goals_for} GA {record.goals_against} "
            f"GD {record.goal_difference:+d}{note}"
        )
    if limit and len(rows) > limit:
        lines.append(f"... ({len(rows) - limit} more teams)")
    return "\n".join(lines)


def _player_line(index: int, player: Player) -> str:
    bits = [f"{index}. {player.name}"]
    if player.overall is not None:
        bits.append(f"Overall: {player.overall}")
    if player.position:
        bits.append(f"Position: {player.position}")
    if player.club_raw:
        bits.append(f"Club: {player.club_raw}")
    if player.nationality:
        bits.append(f"Nationality: {player.nationality}")
    return " - ".join(bits)


def format_players(players: Sequence[Player], *, title: str,
                   total: int | None = None, note: str | None = None) -> str:
    if not players:
        message = f"{title}:\nNo players in the FIFA dataset match this query."
        return f"{message}\n{note}" if note else message
    lines = [f"{title}:"]
    lines.extend(_player_line(index, player) for index, player in enumerate(players, start=1))
    if total is not None and total > len(players):
        lines.append(f"... ({total - len(players)} more players match)")
    if note:
        lines.append(note)
    return "\n".join(lines)


def format_player_profile(profile: dict[str, Any]) -> str:
    player: Player | None = profile["player"]
    if player is None:
        lines = [f"No player named {profile['query']!r} in the FIFA dataset."]
        if profile["suggestions"]:
            lines.append(f"Closest names: {', '.join(profile['suggestions'])}")
        lines.append(
            "Note: the bundled FIFA 19 database omits some Brazilian clubs "
            "(Flamengo, Palmeiras, Corinthians, São Paulo, Vasco were unlicensed), "
            "so players from those squads are not present."
        )
        return "\n".join(lines)
    lines = [
        f"{player.name}",
        f"{_BULLET}Age: {player.age}   Nationality: {player.nationality}",
        f"{_BULLET}Club: {player.club_raw or 'free agent'}   Position: {player.position}"
        f"   Shirt: {player.jersey_number}",
        f"{_BULLET}Overall: {player.overall}   Potential: {player.potential}",
        f"{_BULLET}Height: {player.height}   Weight: {player.weight}"
        f"   Preferred foot: {player.preferred_foot}",
        f"{_BULLET}Value: {player.value}   Wage: {player.wage}",
    ]
    top = player.top_skills(6)
    if top:
        lines.append(f"{_BULLET}Best attributes: "
                     + ", ".join(f"{name} {value}" for name, value in top))
    club_team: Team | None = profile["club_team"]
    if club_team is not None:
        lines.append(
            f"{_BULLET}Linked club in match graph: {club_team.display_name} "
            f"({profile['club_matches']} matches on record)"
        )
    if profile["alternatives"]:
        lines.append("Other players matching that name: "
                     + ", ".join(p.name for p in profile["alternatives"]))
    return "\n".join(lines)


def format_club_squad(graph: KnowledgeGraph, squad: dict[str, Any]) -> str:
    team: Team = squad["team"]
    if not squad["players"]:
        return "\n".join([
            f"{team.display_name}: no players in the FIFA 19 dataset.",
            f"The club does appear in the match graph "
            f"({squad['record'].played} matches with a recorded score).",
            "Note: FIFA 19 did not license every Brazilian club, so Flamengo, "
            "Palmeiras, Corinthians, São Paulo and Vasco have no player rows.",
        ])
    lines = [
        f"{team.display_name} squad in the FIFA dataset "
        f"({squad['squad_size']} players, average rating "
        f"{squad['average_overall']}):"
    ]
    for index, player in enumerate(squad["players"], start=1):
        lines.append(_player_line(index, player))
    lines.append("")
    lines.append(format_team_record(squad["record"], title="Club record in match data"))
    return "\n".join(lines)


def format_competition_stats(graph: KnowledgeGraph, stats: dict[str, Any],
                             *, biggest: Sequence[Match] = ()) -> str:
    scope = stats["competition"]
    if stats["season"]:
        scope += f" {stats['season']}"
    elif stats["seasons"]:
        scope += f" {stats['seasons'][0]}-{stats['seasons'][-1]}"
    lines = [
        f"{scope} statistics (calculated from the provided data):",
        f"{_BULLET}Matches: {stats['matches']} "
        f"({stats['matches_with_scores']} with a recorded score)",
        f"{_BULLET}Teams: {stats['teams']}",
        f"{_BULLET}Total goals: {stats['goals']}",
        f"{_BULLET}Average goals per match: {stats['goals_per_match']}",
        f"{_BULLET}Home win rate: {stats['home_win_rate']}%   "
        f"Away win rate: {stats['away_win_rate']}%   Draws: {stats['draw_rate']}%",
        f"{_BULLET}Home goals per match: {stats['home_goals_per_match']}   "
        f"Away goals per match: {stats['away_goals_per_match']}",
    ]
    if biggest:
        lines.append("")
        lines.append(format_matches(graph, biggest, title="Biggest victories", limit=len(biggest)))
    elif stats.get("biggest_win") is not None:
        lines.append("")
        lines.append("Biggest victory:")
        lines.append(format_match_line(graph, stats["biggest_win"]))
    return "\n".join(lines)


def format_compare_teams(graph: KnowledgeGraph, comparison: dict[str, Any]) -> str:
    a: Team = comparison["team_a"]
    b: Team = comparison["team_b"]
    scope = []
    if comparison["competition"]:
        scope.append(graph.competition_name(comparison["competition"]))
    if comparison["season"]:
        scope.append(str(comparison["season"]))
    suffix = f" ({', '.join(scope)})" if scope else ""
    lines = [f"{a.display_name} vs {b.display_name}{suffix}", ""]
    lines.append(format_team_record(comparison["record_a"], title=f"{a.display_name} record"))
    lines.append("")
    lines.append(format_team_record(comparison["record_b"], title=f"{b.display_name} record"))
    lines.append("")
    lines.append(format_head_to_head(graph, comparison["head_to_head"], limit=10))
    return "\n".join(lines)


def format_derbies(graph: KnowledgeGraph, derbies: Iterable[dict[str, Any]],
                   *, limit: int = 5) -> str:
    derbies = list(derbies)
    if not derbies:
        return "No derby matches found for that filter."
    lines = []
    for entry in derbies:
        lines.append(f"{entry['derby']} - {entry['team_a']} vs {entry['team_b']} "
                     f"({entry['description']})")
        for match in entry["matches"][:limit]:
            lines.append(format_match_line(graph, match))
        remaining = len(entry["matches"]) - limit
        if remaining > 0:
            lines.append(f"... ({remaining} more)")
        lines.append("")
    return "\n".join(lines).strip()


def format_dataset_summary(summary: dict[str, Any]) -> str:
    lines = ["Brazilian Soccer knowledge graph", ""]
    lines.append("Datasets:")
    for dataset in summary["datasets"]:
        lines.append(f"{_BULLET}{dataset['file']} ({dataset['license']}) - "
                     f"{dataset['rows']:,} rows - {dataset['description']}")
    lines.append("")
    lines.append("Competitions:")
    for competition in summary["competitions"]:
        lines.append(f"{_BULLET}{competition['name']}: {competition['matches']:,} matches, "
                     f"seasons {competition['seasons']}")
    report = summary["report"]
    graph_info = summary["graph"]
    lines.extend([
        "",
        f"Matches after cross-source de-duplication: {report['matches_after_merge']:,} "
        f"({report['merged_duplicates']:,} duplicate rows merged)",
        f"Teams: {report['teams']:,} ({summary['teams_with_matches']:,} with matches)   "
        f"Players: {report['players']:,} "
        f"({summary['players_linked_to_clubs']:,} linked to a club in the match graph)",
        f"Graph: {graph_info['node_count']:,} nodes, {graph_info['edge_count']:,} edges",
        f"Load time: {report['load_seconds']}s",
    ])
    return "\n".join(lines)
