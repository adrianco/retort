"""
SoccerKB - the query and analytics layer.

Context
-------
Holds the in-memory match and player collections produced by
:mod:`brazilian_soccer.data_loader` and answers the capability categories from
TASK.md: match search, team records, head-to-head, league standings computed
from results, player search, and aggregate statistics.

All team/competition matching is accent- and suffix-insensitive (see
:mod:`brazilian_soccer.normalize`) so the many naming variants in the source
data resolve to the same logical team/competition.
"""
from __future__ import annotations

from typing import List, Optional

from . import normalize as nz
from .data_loader import Match, Player, load_all_matches, load_all_players


def _comp_match(query: Optional[str], competition: str) -> bool:
    """Accent-insensitive substring match of a competition query."""
    if not query:
        return True
    return nz.strip_accents(query).lower().strip() in \
        nz.strip_accents(competition).lower()


class SoccerKB:
    def __init__(self, matches: List[Match], players: List[Player]):
        self.matches = matches
        self.players = players

    @classmethod
    def from_data_dir(cls, data_dir: str) -> "SoccerKB":
        return cls(load_all_matches(data_dir), load_all_players(data_dir))

    # --- match queries -----------------------------------------------------

    def find_matches(self, team: Optional[str] = None,
                     opponent: Optional[str] = None,
                     competition: Optional[str] = None,
                     season: Optional[int] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     venue: str = "any",
                     limit: Optional[int] = None) -> List[Match]:
        """Return matches matching the given filters, newest first.

        ``venue`` (relative to ``team``) is one of ``"home"``, ``"away"``,
        ``"any"``.
        """
        start = nz.parse_date(start_date) if start_date else None
        end = nz.parse_date(end_date) if end_date else None
        results = []
        for m in self.matches:
            if competition and not _comp_match(competition, m.competition):
                continue
            if season is not None and m.season != season:
                continue
            if start and (m.date is None or m.date < start):
                continue
            if end and (m.date is None or m.date > end):
                continue
            if team and not self._team_plays(m, team, venue):
                continue
            if opponent and not (nz.key_matches(opponent, m.home_key)
                                 or nz.key_matches(opponent, m.away_key)):
                continue
            results.append(m)
        results.sort(key=lambda m: (m.date or "", m.season or 0), reverse=True)
        if limit is not None:
            results = results[:limit]
        return results

    @staticmethod
    def _team_plays(match: Match, team: str, venue: str) -> bool:
        home = nz.key_matches(team, match.home_key)
        away = nz.key_matches(team, match.away_key)
        if venue == "home":
            return home
        if venue == "away":
            return away
        return home or away

    def head_to_head(self, team1: str, team2: str,
                     competition: Optional[str] = None,
                     season: Optional[int] = None) -> dict:
        """Win/draw tally between two teams from ``team1``'s perspective."""
        matches = self.find_matches(team=team1, opponent=team2,
                                    competition=competition, season=season)
        t1_wins = t2_wins = draws = 0
        t1_goals = t2_goals = 0
        for m in matches:
            if m.home_score is None or m.away_score is None:
                continue
            if nz.key_matches(team1, m.home_key):
                t1, t2 = m.home_score, m.away_score
            else:
                t1, t2 = m.away_score, m.home_score
            t1_goals += t1
            t2_goals += t2
            if t1 > t2:
                t1_wins += 1
            elif t2 > t1:
                t2_wins += 1
            else:
                draws += 1
        return {
            "team1": nz.normalize_team_name(team1),
            "team2": nz.normalize_team_name(team2),
            "team1_wins": t1_wins,
            "team2_wins": t2_wins,
            "draws": draws,
            "team1_goals": t1_goals,
            "team2_goals": t2_goals,
            "total": len(matches),
            "matches": matches,
        }

    def team_record(self, team: str, competition: Optional[str] = None,
                    season: Optional[int] = None, venue: str = "any") -> dict:
        """Aggregate W/D/L, goals and win rate for a team."""
        matches = self.find_matches(team=team, competition=competition,
                                    season=season, venue=venue)
        wins = draws = losses = gf = ga = 0
        counted = 0
        for m in matches:
            if m.home_score is None or m.away_score is None:
                continue
            counted += 1
            if nz.key_matches(team, m.home_key):
                scored, conceded = m.home_score, m.away_score
            else:
                scored, conceded = m.away_score, m.home_score
            gf += scored
            ga += conceded
            if scored > conceded:
                wins += 1
            elif scored < conceded:
                losses += 1
            else:
                draws += 1
        win_rate = round(100.0 * wins / counted, 1) if counted else 0.0
        return {
            "team": nz.normalize_team_name(team),
            "competition": competition,
            "season": season,
            "venue": venue,
            "matches": counted,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": gf,
            "goals_against": ga,
            "goal_difference": gf - ga,
            "points": wins * 3 + draws,
            "win_rate": win_rate,
        }

    # --- competition queries ----------------------------------------------

    def standings(self, competition: str, season: int) -> List[dict]:
        """Compute a league table from match results for a competition/season."""
        table: dict = {}

        def row(key: str, team_display: str) -> dict:
            if key not in table:
                table[key] = {"key": key, "team": team_display, "played": 0,
                              "wins": 0, "draws": 0, "losses": 0,
                              "goals_for": 0, "goals_against": 0}
            return table[key]

        for m in self.matches:
            if not _comp_match(competition, m.competition):
                continue
            if m.season != season:
                continue
            if m.home_score is None or m.away_score is None:
                continue
            h = row(m.home_key, m.home_team)
            a = row(m.away_key, m.away_team)
            h["played"] += 1
            a["played"] += 1
            h["goals_for"] += m.home_score
            h["goals_against"] += m.away_score
            a["goals_for"] += m.away_score
            a["goals_against"] += m.home_score
            if m.home_score > m.away_score:
                h["wins"] += 1
                a["losses"] += 1
            elif m.home_score < m.away_score:
                a["wins"] += 1
                h["losses"] += 1
            else:
                h["draws"] += 1
                a["draws"] += 1

        # Disambiguate display names that collide because the state suffix was
        # stripped (e.g. Atlético-MG vs Atlético-PR both display "Atletico").
        from collections import Counter
        name_counts = Counter(r["team"] for r in table.values())
        rows = []
        for r in table.values():
            if name_counts[r["team"]] > 1:
                suffix = nz.state_suffix(r["key"])
                if suffix:
                    r["team"] = f"{r['team']}-{suffix}"
            r.pop("key", None)
            r["goal_difference"] = r["goals_for"] - r["goals_against"]
            r["points"] = r["wins"] * 3 + r["draws"]
            rows.append(r)
        rows.sort(key=lambda r: (r["points"], r["goal_difference"],
                                 r["goals_for"], r["wins"]), reverse=True)
        for i, r in enumerate(rows, start=1):
            r["position"] = i
        return rows

    def list_competitions(self) -> List[str]:
        return sorted({m.competition for m in self.matches})

    def list_seasons(self, competition: Optional[str] = None) -> List[int]:
        seasons = {m.season for m in self.matches
                   if m.season is not None
                   and (competition is None or _comp_match(competition, m.competition))}
        return sorted(seasons)

    # --- player queries ----------------------------------------------------

    def search_players(self, name: Optional[str] = None,
                       nationality: Optional[str] = None,
                       club: Optional[str] = None,
                       position: Optional[str] = None,
                       min_overall: Optional[int] = None,
                       limit: Optional[int] = None) -> List[Player]:
        """Search players, returned highest-overall first."""
        name_key = nz.strip_accents(name).lower().strip() if name else None
        nat_key = nz.strip_accents(nationality).lower().strip() if nationality else None
        results = []
        for p in self.players:
            if name_key and name_key not in p.name_key:
                continue
            if nat_key and nat_key not in nz.strip_accents(p.nationality).lower():
                continue
            if club and not nz.names_match(club, p.club):
                continue
            if position and position.strip().lower() != p.position.lower():
                continue
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            results.append(p)
        results.sort(key=lambda p: (p.overall or 0), reverse=True)
        if limit is not None:
            results = results[:limit]
        return results

    # --- statistics --------------------------------------------------------

    def competition_stats(self, competition: Optional[str] = None,
                          season: Optional[int] = None) -> dict:
        """Goals-per-match and home/away/draw rates over a slice of matches."""
        matches = self.find_matches(competition=competition, season=season)
        scored = [m for m in matches
                  if m.home_score is not None and m.away_score is not None]
        n = len(scored)
        total_goals = sum(m.home_score + m.away_score for m in scored)
        home_wins = sum(1 for m in scored if m.home_score > m.away_score)
        away_wins = sum(1 for m in scored if m.away_score > m.home_score)
        draws = n - home_wins - away_wins
        return {
            "competition": competition,
            "season": season,
            "matches": n,
            "total_goals": total_goals,
            "avg_goals_per_match": round(total_goals / n, 2) if n else 0.0,
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": round(100.0 * home_wins / n, 1) if n else 0.0,
            "away_win_rate": round(100.0 * away_wins / n, 1) if n else 0.0,
            "draw_rate": round(100.0 * draws / n, 1) if n else 0.0,
        }

    def biggest_wins(self, competition: Optional[str] = None,
                     season: Optional[int] = None,
                     limit: int = 10) -> List[Match]:
        """Matches with the largest goal margin, biggest first."""
        matches = self.find_matches(competition=competition, season=season)
        scored = [m for m in matches
                  if m.home_score is not None and m.away_score is not None]
        scored.sort(key=lambda m: (abs(m.home_score - m.away_score),
                                   m.total_goals), reverse=True)
        return scored[:limit]
