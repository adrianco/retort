"""
Context
=======
Turns KnowledgeBase query results into the human-readable answer strings the
specification illustrates (see the "Example answer format" blocks). Each
public method maps to one MCP tool; the MCP server in ``server.py`` is a thin
wrapper that registers these and forwards arguments.

Keeping formatting here (rather than inside the MCP server) means the answer
text is unit-testable without standing up a protocol session.
"""

from __future__ import annotations

import datetime as dt
from typing import List, Optional

from .data_loader import Match
from .queries import KnowledgeBase


def _parse_date(value: Optional[str]) -> Optional[dt.date]:
    if not value:
        return None
    from .data_loader import parse_date
    return parse_date(value)


def _match_line(mt: Match) -> str:
    date = mt.date.isoformat() if mt.date else "????-??-??"
    if mt.home_goal is None or mt.away_goal is None:
        score = "vs"
    else:
        score = f"{mt.home_goal}-{mt.away_goal}"
    parts = [f"{date}: {mt.home_team} {score} {mt.away_team}"]
    tags = [mt.competition]
    if mt.round:
        tags.append(f"Round {mt.round}")
    elif mt.stage:
        tags.append(mt.stage)
    if mt.season:
        tags.append(str(mt.season))
    return f"- {parts[0]} ({', '.join(tags)})"


class SoccerTools:
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    # ---- matches ----------------------------------------------------------

    def search_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        home: Optional[str] = None,
        away: Optional[str] = None,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 25,
    ) -> str:
        results = self.kb.find_matches(
            team=team, opponent=opponent, home=home, away=away,
            season=season, competition=competition,
            start_date=_parse_date(start_date), end_date=_parse_date(end_date),
        )
        if not results:
            return "No matches found for the given criteria."

        header = f"Found {len(results)} match(es):"
        shown = results[:limit]
        lines = [_match_line(mt) for mt in shown]
        if len(results) > limit:
            lines.append(f"- ... ({len(results) - limit} more not shown)")
        return "\n".join([header, *lines])

    # ---- head to head -----------------------------------------------------

    def head_to_head(
        self,
        team_a: str,
        team_b: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        h = self.kb.head_to_head(team_a, team_b, season=season, competition=competition)
        if h["matches"] == 0:
            return f"No matches found between {team_a} and {team_b}."
        lines = [
            f"{team_a} vs {team_b} head-to-head ({h['matches']} matches):",
            f"- {team_a}: {h['team_a_wins']} wins",
            f"- {team_b}: {h['team_b_wins']} wins",
            f"- Draws: {h['draws']}",
            f"- Goals: {team_a} {h['team_a_goals']} - {h['team_b_goals']} {team_b}",
            "",
            "Recent meetings:",
        ]
        for mt in h["match_list"][-limit:]:
            lines.append(_match_line(mt))
        return "\n".join(lines)

    # ---- team record ------------------------------------------------------

    def team_record(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: Optional[str] = None,
    ) -> str:
        rec = self.kb.team_record(team, season=season, competition=competition, venue=venue)
        if rec["matches"] == 0:
            return f"No match data found for {team}."
        scope = []
        if venue:
            scope.append(f"{venue} ")
        scope_str = "".join(scope)
        label = f"{team} {scope_str}record"
        qualifiers = []
        if season:
            qualifiers.append(str(season))
        if competition:
            qualifiers.append(competition)
        if qualifiers:
            label += f" ({', '.join(qualifiers)})"
        return "\n".join([
            f"{label}:",
            f"- Matches: {rec['played']}",
            f"- Wins: {rec['wins']}, Draws: {rec['draws']}, Losses: {rec['losses']}",
            f"- Goals For: {rec['goals_for']}, Goals Against: {rec['goals_against']}",
            f"- Points: {rec['points']}",
            f"- Win rate: {rec['win_rate']}%",
        ])

    # ---- standings --------------------------------------------------------

    def standings(
        self, season: int, competition: str = "Brasileirão", limit: int = 20
    ) -> str:
        table = self.kb.standings(season=season, competition=competition)
        if not table:
            return f"No standings could be computed for {competition} {season}."
        lines = [f"{season} {competition} standings (calculated from matches):"]
        for r in table[:limit]:
            tag = " - Champion" if r["position"] == 1 else ""
            lines.append(
                f"{r['position']}. {r['team']} - {r['points']} pts "
                f"({r['wins']}W, {r['draws']}D, {r['losses']}L, "
                f"GF {r['goals_for']}, GA {r['goals_against']}){tag}"
            )
        return "\n".join(lines)

    # ---- players ----------------------------------------------------------

    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: int = 15,
    ) -> str:
        players = self.kb.search_players(
            name=name, nationality=nationality, club=club,
            position=position, min_overall=min_overall, limit=limit,
        )
        if not players:
            return "No players found for the given criteria."
        lines = [f"Found {len(players)} player(s):"]
        for i, p in enumerate(players, start=1):
            lines.append(
                f"{i}. {p.name} - Overall: {p.overall}, Position: {p.position}, "
                f"Club: {p.club}, Nationality: {p.nationality}"
            )
        return "\n".join(lines)

    def players_by_club(self, nationality: Optional[str] = None, limit: int = 15) -> str:
        rows = self.kb.players_by_club_summary(nationality=nationality)
        if not rows:
            return "No club data found."
        title = "Players by club"
        if nationality:
            title += f" ({nationality})"
        lines = [title + ":"]
        for r in rows[:limit]:
            avg = r["avg_overall"] if r["avg_overall"] is not None else "n/a"
            lines.append(f"- {r['club']}: {r['count']} players (avg rating: {avg})")
        return "\n".join(lines)

    # ---- statistics -------------------------------------------------------

    def statistics(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> str:
        games = self.kb.find_matches(competition=competition, season=season)
        scored = [g for g in games if g.total_goals is not None]
        avg = self.kb.average_goals_per_match(competition=competition, season=season)
        home_wins = sum(1 for g in scored if g.winner == "home")
        scope = " ".join(filter(None, [str(season) if season else "", competition or "all competitions"]))
        lines = [f"Statistics for {scope.strip()}:",
                 f"- Matches with scores: {len(scored)}",
                 f"- Average goals per match: {avg}"]
        if scored:
            lines.append(f"- Home win rate: {round(100.0 * home_wins / len(scored), 1)}%")
        return "\n".join(lines)

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> str:
        wins = self.kb.biggest_wins(competition=competition, season=season, limit=limit)
        if not wins:
            return "No matches found for the given criteria."
        lines = ["Biggest victories:"]
        for i, mt in enumerate(wins, start=1):
            margin = abs(mt.home_goal - mt.away_goal)
            lines.append(f"{i}. {_match_line(mt)[2:]} [margin {margin}]")
        return "\n".join(lines)

    def best_record(
        self,
        venue: str = "home",
        competition: Optional[str] = None,
        season: Optional[int] = None,
        min_matches: int = 10,
        limit: int = 10,
    ) -> str:
        ranking = self.kb.best_record(
            venue=venue, competition=competition, season=season,
            min_matches=min_matches, limit=limit,
        )
        if not ranking:
            return "No teams met the minimum-matches threshold."
        lines = [f"Best {venue} records:"]
        for i, r in enumerate(ranking, start=1):
            lines.append(
                f"{i}. {r['team']} - {r['win_rate']}% "
                f"({r['wins']}W, {r['draws']}D, {r['losses']}L in {r['played']} games)"
            )
        return "\n".join(lines)

    def data_summary(self) -> str:
        s = self.kb.summary()
        lines = [
            f"Loaded {s['total_matches']} matches and {s['total_players']} players.",
            "Matches by competition:",
        ]
        for comp, n in sorted(s["competitions"].items(), key=lambda kv: kv[1], reverse=True):
            lines.append(f"- {comp}: {n}")
        return "\n".join(lines)
