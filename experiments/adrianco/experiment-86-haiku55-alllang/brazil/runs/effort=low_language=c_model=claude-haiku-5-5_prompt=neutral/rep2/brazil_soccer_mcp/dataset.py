"""Query layer over the loaded matches and players.

`Dataset` is the single place where filtering and aggregation happen. The MCP
server and the tests both call these methods, so the rules live in one spot.
"""

from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .loaders import SERIES_A, load_matches, load_players
from .models import Match, Player
from .normalize import Team, contains_text, parse_team_query, team_matches

VENUES = ("any", "home", "away")
RANKABLE_METRICS = ("win_rate", "home_win_rate", "away_win_rate", "goals_for", "goal_difference")


class Dataset:
    def __init__(self, matches: List[Match], players: List[Player]):
        self.matches = sorted(matches, key=lambda m: m.played_on)
        self.players = players

    @classmethod
    def load(cls, data_dir: Path) -> "Dataset":
        data_dir = Path(data_dir)
        return cls(load_matches(data_dir), load_players(data_dir / "fifa_data.csv"))

    # ------------------------------------------------------------------ filters

    def filter_matches(
        self,
        *,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        matches: Optional[Iterable[Match]] = None,
    ) -> List[Match]:
        """Filter by competition text ("brasileirao", "copa do brasil"), season and dates."""
        source = self.matches if matches is None else matches
        result = []
        for match in source:
            if competition and not contains_text(match.competition, competition):
                continue
            if season is not None and match.season != season:
                continue
            if start and match.played_on < start:
                continue
            if end and match.played_on > end:
                continue
            result.append(match)
        return result

    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        venue: str = "any",
        limit: int = 20,
        **filters,
    ) -> Dict:
        """Matches involving `team` (optionally against `opponent`), newest first."""
        if venue not in VENUES:
            raise ValueError(f"venue must be one of {VENUES}")
        candidates = self.filter_matches(**filters)
        if team or opponent:
            candidates = [m for m in candidates if self._involves(m, team, opponent, venue)]
        candidates = sorted(candidates, key=lambda m: m.played_on, reverse=True)
        return {"total": len(candidates), "matches": candidates[:limit]}

    # ------------------------------------------------------------- team stats

    def team_record(self, team: str, venue: str = "any", **filters) -> Dict:
        """Wins/draws/losses and goals for a team, from its own point of view."""
        if venue not in VENUES:
            raise ValueError(f"venue must be one of {VENUES}")
        query = parse_team_query(team)
        record = _Tally()
        for match in self.filter_matches(**filters):
            side = self._side(match, query, venue)
            if side is not None:
                record.add(*side)
        return record.summary()

    def head_to_head(self, team_a: str, team_b: str, **filters) -> Dict:
        qa, qb = parse_team_query(team_a), parse_team_query(team_b)
        tally = {"a": _Tally(), "b": _Tally()}
        games = []
        for match in self.filter_matches(**filters):
            a_side = self._side(match, qa, "any", opponent=qb)
            if a_side is None:
                continue
            tally["a"].add(*a_side)
            tally["b"].add(a_side[1], a_side[0])
            games.append(match)
        games.sort(key=lambda m: m.played_on, reverse=True)
        return {
            "total": len(games),
            "matches": games,
            "a": tally["a"].summary(),
            "b": tally["b"].summary(),
            "a_name": qa.base,
            "b_name": qb.base,
        }

    def standings(self, season: int, competition: str = SERIES_A) -> List[Dict]:
        table: Dict[str, _Tally] = defaultdict(_Tally)
        for match in self.filter_matches(season=season, competition=competition):
            table[match.home.base].add(match.home_goals, match.away_goals)
            table[match.away.base].add(match.away_goals, match.home_goals)
        rows = []
        for name, tally in table.items():
            summary = tally.summary()
            summary["team"] = name
            rows.append(summary)
        rows.sort(key=lambda r: (-r["points"], -r["wins"], -r["goal_difference"], -r["goals_for"]))
        for position, row in enumerate(rows, start=1):
            row["position"] = position
        return rows

    def league_stats(self, **filters) -> Dict:
        matches = self.filter_matches(**filters)
        total = len(matches)
        if not total:
            return {"matches": 0}
        goals = sum(m.home_goals + m.away_goals for m in matches)
        results = defaultdict(int)
        for m in matches:
            results[m.result] += 1
        return {
            "matches": total,
            "total_goals": goals,
            "goals_per_match": round(goals / total, 2),
            "home_win_rate": _pct(results["home"], total),
            "draw_rate": _pct(results["draw"], total),
            "away_win_rate": _pct(results["away"], total),
        }

    def rank_teams(self, metric: str, min_matches: int = 1, limit: int = 10, **filters) -> List[Dict]:
        """Rank every team on one metric, e.g. the best home record."""
        if metric not in RANKABLE_METRICS:
            raise ValueError(f"metric must be one of {RANKABLE_METRICS}")
        home_t: Dict[str, _Tally] = defaultdict(_Tally)
        away_t: Dict[str, _Tally] = defaultdict(_Tally)
        all_t: Dict[str, _Tally] = defaultdict(_Tally)
        for m in self.filter_matches(**filters):
            home_t[m.home.base].add(m.home_goals, m.away_goals)
            away_t[m.away.base].add(m.away_goals, m.home_goals)
            all_t[m.home.base].add(m.home_goals, m.away_goals)
            all_t[m.away.base].add(m.away_goals, m.home_goals)
        rows = []
        for name in all_t:
            if metric == "home_win_rate":
                source, key = home_t, "win_rate"
            elif metric == "away_win_rate":
                source, key = away_t, "win_rate"
            else:
                source, key = all_t, metric
            tally = source.get(name)
            if tally is None or tally.played < min_matches:
                continue
            summary = tally.summary()
            summary["team"] = name
            summary["ranked_by"] = metric
            summary["value"] = summary[key]
            rows.append(summary)
        rows.sort(key=lambda r: (-r["value"], -r["played"]))
        return rows[:limit]

    def biggest_wins(self, limit: int = 10, **filters) -> List[Match]:
        decided = [m for m in self.filter_matches(**filters) if m.home_goals != m.away_goals]
        decided.sort(key=lambda m: (-abs(m.home_goals - m.away_goals), -(m.home_goals + m.away_goals)))
        return decided[:limit]

    # ------------------------------------------------------------- players

    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        sort: str = "overall",
        limit: int = 20,
    ) -> Dict:
        results = []
        for p in self.players:
            if name and not contains_text(p.name, name):
                continue
            if nationality and not contains_text(p.nationality, nationality):
                continue
            if club and not contains_text(p.club, club):
                continue
            if position and not contains_text(p.position, position):
                continue
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            results.append(p)
        if sort == "overall":
            results.sort(key=lambda p: -(p.overall or 0))
        elif sort == "name":
            results.sort(key=lambda p: p.name)
        else:
            raise ValueError("sort must be 'overall' or 'name'")
        return {"total": len(results), "players": results[:limit]}

    def club_summary(self, nationality: Optional[str] = None) -> List[Dict]:
        """Average overall per club, optionally restricted to a nationality."""
        groups: Dict[str, List[int]] = defaultdict(list)
        for p in self.players:
            if nationality and not contains_text(p.nationality, nationality):
                continue
            if p.overall is not None:
                groups[p.club].append(p.overall)
        rows = [
            {"club": club, "players": len(vals), "avg_overall": round(sum(vals) / len(vals), 1)}
            for club, vals in groups.items()
        ]
        rows.sort(key=lambda r: (-r["avg_overall"], r["club"]))
        return rows

    # ------------------------------------------------------------- helpers

    @staticmethod
    def _side(match: Match, query: Team, venue: str, opponent: Optional[Team] = None):
        """Return (goals_for, goals_against) when `query` played in `match`, else None."""
        candidates = []
        if venue in ("any", "home") and team_matches(match.home, query):
            candidates.append(("home", match.home_goals, match.away_goals, match.away))
        if venue in ("any", "away") and team_matches(match.away, query):
            candidates.append(("away", match.away_goals, match.home_goals, match.home))
        for side, gf, ga, opp in candidates:
            if opponent is None or team_matches(opp, opponent):
                return gf, ga, side
        return None

    @classmethod
    def _involves(cls, match: Match, team, opponent, venue) -> bool:
        if team and opponent:
            return cls._side(match, parse_team_query(team), venue, opponent=parse_team_query(opponent)) is not None
        query = parse_team_query(team or opponent)
        return cls._side(match, query, venue if team else "any") is not None


class _Tally:
    """Accumulates wins, draws, losses and goals for one team."""

    def __init__(self):
        self.played = self.wins = self.draws = self.losses = 0
        self.goals_for = self.goals_against = 0
        self.home_played = self.home_wins = 0
        self.away_played = self.away_wins = 0

    def add(self, goals_for: int, goals_against: int, side: Optional[str] = None):
        self.played += 1
        self.goals_for += goals_for
        self.goals_against += goals_against
        if goals_for > goals_against:
            self.wins += 1
        elif goals_for == goals_against:
            self.draws += 1
        else:
            self.losses += 1
        if side == "home":
            self.home_played += 1
            self.home_wins += goals_for > goals_against
        elif side == "away":
            self.away_played += 1
            self.away_wins += goals_for > goals_against

    def summary(self) -> Dict:
        return {
            "played": self.played,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goals_for - self.goals_against,
            "points": self.wins * 3 + self.draws,
            "win_rate": _pct(self.wins, self.played),
            "home_win_rate": _pct(self.home_wins, self.home_played),
            "away_win_rate": _pct(self.away_wins, self.away_played),
            "goals_per_match": round(self.goals_for / self.played, 2) if self.played else 0.0,
        }


def _pct(part: int, whole: int) -> float:
    return round(100.0 * part / whole, 1) if whole else 0.0
