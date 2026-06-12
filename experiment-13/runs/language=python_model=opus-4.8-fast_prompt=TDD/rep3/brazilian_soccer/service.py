"""
Service layer: turn :class:`SoccerKB` results into human-readable answers.

Context
-------
The MCP tools in :mod:`brazilian_soccer.server` are thin wrappers around these
``answer_*`` functions. Keeping the formatting here (free of any MCP imports)
lets the response shaping be unit-tested directly and mirrors the answer
formats described in TASK.md.
"""
from __future__ import annotations

from typing import Optional

from .knowledge_base import SoccerKB

# Default number of rows to show in list-style answers.
DEFAULT_LIMIT = 15


def _match_line(m) -> str:
    score = f"{m.home_score}-{m.away_score}"
    context = m.competition
    if m.round:
        context += f", Round {m.round}"
    elif m.stage:
        context += f", {m.stage}"
    return f"- {m.date}: {m.home_team} {score} {m.away_team} ({context})"


def answer_find_matches(kb: SoccerKB, team: Optional[str] = None,
                        opponent: Optional[str] = None,
                        competition: Optional[str] = None,
                        season: Optional[int] = None,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        venue: str = "any",
                        limit: int = DEFAULT_LIMIT) -> str:
    matches = kb.find_matches(team=team, opponent=opponent,
                              competition=competition, season=season,
                              start_date=start_date, end_date=end_date,
                              venue=venue)
    if not matches:
        return "No matches found for the given criteria."

    if team and opponent:
        header = f"{team} vs {opponent}:"
    elif team:
        header = f"Matches for {team}:"
    else:
        header = "Matches found:"

    lines = [header]
    shown = matches[:limit]
    lines.extend(_match_line(m) for m in shown)
    if len(matches) > len(shown):
        lines.append(f"... ({len(matches) - len(shown)} more of "
                     f"{len(matches)} total)")

    if team and opponent:
        h2h = kb.head_to_head(team, opponent, competition=competition,
                              season=season)
        lines.append("")
        lines.append(
            f"Head-to-head: {h2h['team1']} {h2h['team1_wins']} wins, "
            f"{h2h['team2']} {h2h['team2_wins']} wins, {h2h['draws']} draws "
            f"(goals {h2h['team1_goals']}-{h2h['team2_goals']})"
        )
    return "\n".join(lines)


def answer_head_to_head(kb: SoccerKB, team1: str, team2: str,
                        competition: Optional[str] = None,
                        season: Optional[int] = None) -> str:
    h2h = kb.head_to_head(team1, team2, competition=competition, season=season)
    if h2h["total"] == 0:
        return f"No matches found between {team1} and {team2}."
    lines = [
        f"Head-to-head: {h2h['team1']} vs {h2h['team2']}"
        + (f" ({competition})" if competition else "")
        + (f" {season}" if season else ""),
        f"{h2h['team1']} wins: {h2h['team1_wins']}, "
        f"{h2h['team2']} wins: {h2h['team2_wins']}, Draws: {h2h['draws']} "
        f"(Total: {h2h['total']})",
        f"Goals: {h2h['team1']} {h2h['team1_goals']} - "
        f"{h2h['team2_goals']} {h2h['team2']}",
        "Recent meetings:",
    ]
    lines.extend(_match_line(m) for m in h2h["matches"][:5])
    return "\n".join(lines)


def answer_team_record(kb: SoccerKB, team: str,
                       competition: Optional[str] = None,
                       season: Optional[int] = None, venue: str = "any") -> str:
    r = kb.team_record(team, competition=competition, season=season,
                       venue=venue)
    if r["matches"] == 0:
        return f"No matches found for {team} with the given criteria."
    scope = []
    if competition:
        scope.append(competition)
    if season:
        scope.append(str(season))
    if venue != "any":
        scope.append(venue)
    scope_text = f" ({', '.join(scope)})" if scope else ""
    return "\n".join([
        f"{r['team']} record{scope_text}:",
        f"- Matches: {r['matches']}",
        f"- Wins: {r['wins']}, Draws: {r['draws']}, Losses: {r['losses']}",
        f"- Goals For: {r['goals_for']}, Goals Against: {r['goals_against']} "
        f"(GD: {r['goal_difference']:+d})",
        f"- Points: {r['points']}, Win rate: {r['win_rate']}%",
    ])


def answer_standings(kb: SoccerKB, competition: str, season: int) -> str:
    table = kb.standings(competition, season)
    if not table:
        return f"No standings available for {competition} {season}."
    lines = [f"{season} {competition} Standings (calculated from matches):"]
    for r in table:
        lines.append(
            f"{r['position']:>2}. {r['team']} - {r['points']} pts "
            f"({r['wins']}W {r['draws']}D {r['losses']}L) "
            f"GF:{r['goals_for']} GA:{r['goals_against']} "
            f"GD:{r['goal_difference']:+d}"
        )
    return "\n".join(lines)


def answer_search_players(kb: SoccerKB, name: Optional[str] = None,
                          nationality: Optional[str] = None,
                          club: Optional[str] = None,
                          position: Optional[str] = None,
                          min_overall: Optional[int] = None,
                          limit: int = DEFAULT_LIMIT) -> str:
    players = kb.search_players(name=name, nationality=nationality, club=club,
                                position=position, min_overall=min_overall)
    if not players:
        return "No players found for the given criteria."
    lines = [f"Players found: {len(players)}"
             + (f" (showing {min(limit, len(players))})"
                if len(players) > limit else "")]
    for i, p in enumerate(players[:limit], start=1):
        lines.append(
            f"{i}. {p.name} - Overall: {p.overall}, Position: {p.position}, "
            f"Club: {p.club}, Age: {p.age}, Nationality: {p.nationality}"
        )
    return "\n".join(lines)


def answer_competition_stats(kb: SoccerKB, competition: Optional[str] = None,
                             season: Optional[int] = None) -> str:
    s = kb.competition_stats(competition=competition, season=season)
    if s["matches"] == 0:
        return "No matches found for the given criteria."
    scope = []
    if competition:
        scope.append(competition)
    if season:
        scope.append(str(season))
    scope_text = f" ({', '.join(scope)})" if scope else ""
    return "\n".join([
        f"Statistics{scope_text}:",
        f"- Matches: {s['matches']}",
        f"- Total goals: {s['total_goals']}",
        f"- Average goals per match: {s['avg_goals_per_match']}",
        f"- Home wins: {s['home_wins']} ({s['home_win_rate']}%)",
        f"- Away wins: {s['away_wins']} ({s['away_win_rate']}%)",
        f"- Draws: {s['draws']} ({s['draw_rate']}%)",
    ])


def answer_biggest_wins(kb: SoccerKB, competition: Optional[str] = None,
                        season: Optional[int] = None, limit: int = 10) -> str:
    matches = kb.biggest_wins(competition=competition, season=season,
                              limit=limit)
    if not matches:
        return "No matches found for the given criteria."
    lines = ["Biggest victories:"]
    for i, m in enumerate(matches, start=1):
        margin = abs(m.home_score - m.away_score)
        lines.append(
            f"{i}. {m.date}: {m.home_team} {m.home_score}-{m.away_score} "
            f"{m.away_team} ({m.competition}, margin {margin})"
        )
    return "\n".join(lines)


def answer_list_competitions(kb: SoccerKB) -> str:
    comps = kb.list_competitions()
    return "Competitions available:\n" + "\n".join(f"- {c}" for c in comps)


def answer_list_seasons(kb: SoccerKB, competition: Optional[str] = None) -> str:
    seasons = kb.list_seasons(competition=competition)
    if not seasons:
        return "No seasons found for the given competition."
    label = f" for {competition}" if competition else ""
    return (f"Seasons{label}: "
            + ", ".join(str(s) for s in seasons))
