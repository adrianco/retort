"""KnowledgeGraph query engine over the loaded match and player records.

Implements the capabilities required by the specification: match searches,
head-to-head, team records, player searches, computed standings and a handful
of aggregate statistics.  All team matching is done via accent/case-insensitive
keys (see :mod:`brazilian_soccer.normalize`).
"""
from __future__ import annotations

import datetime
from typing import List, Optional

from . import normalize
from .data_loader import Match, Player

# Competition aliases -> canonical label used for comparison.
_COMP_CANON = {
    "brasileirao": "brasileirao",
    "brasileirão": "brasileirao",
    "serie a": "brasileirao",
    "série a": "brasileirao",
    "campeonato brasileiro": "brasileirao",
    "copa do brasil": "copa do brasil",
    "brazilian cup": "copa do brasil",
    "libertadores": "libertadores",
    "copa libertadores": "libertadores",
}


def canonical_competition(name: str) -> str:
    """Return a canonical competition key for loose matching."""
    if not name:
        return ""
    key = normalize.strip_accents(name).lower().strip()
    return _COMP_CANON.get(key, key)


# Canonical key -> preferred display label.
_COMP_DISPLAY = {
    "brasileirao": "Brasileirão",
    "copa do brasil": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
}


def display_competition(name: str) -> str:
    """Return a consistent display label for a competition name."""
    return _COMP_DISPLAY.get(canonical_competition(name), name)


def _match_dedup_key(m: Match):
    # Canonicalize the competition so the same fixture appearing in two source
    # files under different labels (e.g. "Brasileirão" vs "Serie A") collapses.
    return (
        m.date,
        m.home_key,
        m.away_key,
        m.home_goal,
        m.away_goal,
        canonical_competition(m.competition),
    )


def _prefer_match(a: Match, b: Match) -> Match:
    """Pick the better of two near-duplicate matches.

    Prefer a played match over an unplayed one; otherwise prefer the one with a
    known date, then keep the existing one.
    """
    if a.played != b.played:
        return a if a.played else b
    if (a.date is None) != (b.date is None):
        return a if a.date is not None else b
    return a


class KnowledgeGraph:
    """In-memory query engine over matches and players."""

    def __init__(self, matches: List[Match], players: List[Player]):
        self.matches = self._dedup(matches)
        self.players = players

    @classmethod
    def _dedup(cls, matches: List[Match]) -> List[Match]:
        # Pass 1: drop exact duplicates (same date/teams/score/competition).
        seen = set()
        unique = []
        for m in matches:
            k = _match_dedup_key(m)
            if k not in seen:
                seen.add(k)
                unique.append(m)
        # Pass 2: collapse near-duplicate fixtures from overlapping source
        # files.  Two complementary keys are used:
        #   (a) same competition/season/date/home team -- a team plays at most
        #       once per day, so this merges team-name variants of the same
        #       game (e.g. "Atletico" / "Athletico Paranaense").
        #   (b) same competition/season and ordered (home, away) pair -- in a
        #       round-robin / two-leg tie an ordered pair meets once, so this
        #       merges copies that disagree only on the date (timezone offset).
        # When merging, the played copy (with goals) is preferred.
        unique = cls._collapse(
            unique,
            lambda m: (canonical_competition(m.competition), m.season, m.date, m.home_key)
            if (m.season is not None and m.date is not None)
            else None,
        )
        unique = cls._collapse(
            unique,
            lambda m: (canonical_competition(m.competition), m.season, m.home_key, m.away_key)
            if m.season is not None
            else None,
        )
        return unique

    @staticmethod
    def _collapse(matches: List[Match], key_fn) -> List[Match]:
        """Merge matches sharing a non-None ``key_fn`` value, preferring played."""
        groups: dict = {}
        order: List = []
        result: List[Match] = []
        for m in matches:
            key = key_fn(m)
            if key is None:
                result.append(m)
                continue
            if key not in groups:
                groups[key] = len(result)
                order.append(key)
                result.append(m)
            else:
                idx = groups[key]
                result[idx] = _prefer_match(result[idx], m)
        return result

    # --- match queries ---------------------------------------------------

    def find_matches(
        self,
        team: Optional[str] = None,
        team2: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[datetime.date] = None,
        date_to: Optional[datetime.date] = None,
        venue: str = "either",
    ) -> List[Match]:
        """Return matches filtered by the given criteria, sorted by date."""
        team_k = normalize.team_key(team) if team else None
        team2_k = normalize.team_key(team2) if team2 else None
        comp_k = canonical_competition(competition) if competition else None

        results = []
        for m in self.matches:
            if comp_k and canonical_competition(m.competition) != comp_k:
                continue
            if season is not None and m.season != season:
                continue
            if team_k:
                if venue == "home" and m.home_key != team_k:
                    continue
                if venue == "away" and m.away_key != team_k:
                    continue
                if venue == "either" and team_k not in (m.home_key, m.away_key):
                    continue
            if team2_k and team2_k not in (m.home_key, m.away_key):
                continue
            if date_from and (m.date is None or m.date < date_from):
                continue
            if date_to and (m.date is None or m.date > date_to):
                continue
            results.append(m)

        results.sort(key=lambda x: (x.date is None, x.date or datetime.date.min))
        return results

    def head_to_head(
        self, team_a: str, team_b: str, competition: Optional[str] = None
    ) -> dict:
        """Return the head-to-head record between two teams."""
        key_a = normalize.team_key(team_a)
        key_b = normalize.team_key(team_b)
        matches = self.find_matches(team=team_a, team2=team_b, competition=competition)
        wins_a = wins_b = draws = 0
        for m in matches:
            if not m.played:
                continue
            if m.winner_key == key_a:
                wins_a += 1
            elif m.winner_key == key_b:
                wins_b += 1
            else:
                draws += 1
        return {
            "team_a": normalize.normalize_team_name(team_a),
            "team_b": normalize.normalize_team_name(team_b),
            "wins_a": wins_a,
            "wins_b": wins_b,
            "draws": draws,
            "total": len([m for m in matches if m.played]),
            "matches": matches,
        }

    # --- team queries ----------------------------------------------------

    def team_record(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "either",
    ) -> dict:
        """Compute win/loss/draw and goal record for a team."""
        key = normalize.team_key(team)
        matches = self.find_matches(
            team=team, season=season, competition=competition, venue=venue
        )
        wins = draws = losses = gf = ga = played = 0
        for m in matches:
            if not m.played:
                continue
            played += 1
            if m.home_key == key:
                gf += m.home_goal
                ga += m.away_goal
            else:
                gf += m.away_goal
                ga += m.home_goal
            if m.winner_key == key:
                wins += 1
            elif m.winner_key is None:
                draws += 1
            else:
                losses += 1
        win_rate = round(100 * wins / played, 1) if played else 0.0
        return {
            "team": normalize.normalize_team_name(team),
            "matches": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": gf,
            "goals_against": ga,
            "win_rate": win_rate,
        }

    # --- player queries --------------------------------------------------

    def find_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Player]:
        """Search players, sorted by Overall rating (descending)."""
        name_k = normalize.strip_accents(name).lower() if name else None
        nat_k = normalize.strip_accents(nationality).lower() if nationality else None
        club_k = normalize.team_key(club) if club else None
        pos_k = position.strip().upper() if position else None

        results = []
        for p in self.players:
            if name_k and name_k not in p.name_key:
                continue
            if nat_k and normalize.strip_accents(p.nationality).lower() != nat_k:
                continue
            if club_k and p.club_key != club_k:
                continue
            if pos_k and p.position.upper() != pos_k:
                continue
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            results.append(p)

        results.sort(key=lambda x: (x.overall is None, -(x.overall or 0)))
        return results[:limit] if limit else results

    # --- competition queries ---------------------------------------------

    def standings(self, competition: str, season: int) -> List[dict]:
        """Compute a league table from match results (3pts win, 1pt draw)."""
        table: dict[str, dict] = {}
        matches = self.find_matches(competition=competition, season=season)
        for m in matches:
            if not m.played:
                continue
            for key, name, gf, ga in (
                (m.home_key, m.home_team, m.home_goal, m.away_goal),
                (m.away_key, m.away_team, m.away_goal, m.home_goal),
            ):
                row = table.setdefault(
                    key,
                    {
                        "team": name,
                        "played": 0,
                        "wins": 0,
                        "draws": 0,
                        "losses": 0,
                        "goals_for": 0,
                        "goals_against": 0,
                        "points": 0,
                    },
                )
                row["played"] += 1
                row["goals_for"] += gf
                row["goals_against"] += ga
                if gf > ga:
                    row["wins"] += 1
                    row["points"] += 3
                elif gf == ga:
                    row["draws"] += 1
                    row["points"] += 1
                else:
                    row["losses"] += 1

        rows = list(table.values())
        for row in rows:
            row["goal_diff"] = row["goals_for"] - row["goals_against"]
        rows.sort(
            key=lambda r: (-r["points"], -r["goal_diff"], -r["goals_for"], r["team"])
        )
        return rows

    def champion(self, competition: str, season: int) -> Optional[str]:
        """Return the season champion (top of the computed standings)."""
        table = self.standings(competition, season)
        return table[0]["team"] if table else None

    # --- statistics ------------------------------------------------------

    def average_goals_per_match(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> float:
        matches = [
            m
            for m in self.find_matches(competition=competition, season=season)
            if m.played
        ]
        if not matches:
            return 0.0
        total = sum(m.home_goal + m.away_goal for m in matches)
        return round(total / len(matches), 2)

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> List[Match]:
        matches = [
            m
            for m in self.find_matches(competition=competition, season=season)
            if m.played and m.home_goal != m.away_goal
        ]
        matches.sort(key=lambda m: abs(m.home_goal - m.away_goal), reverse=True)
        return matches[:limit]

    def home_win_rate(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> float:
        matches = [
            m
            for m in self.find_matches(competition=competition, season=season)
            if m.played
        ]
        if not matches:
            return 0.0
        home_wins = sum(1 for m in matches if m.home_goal > m.away_goal)
        return round(100 * home_wins / len(matches), 1)
