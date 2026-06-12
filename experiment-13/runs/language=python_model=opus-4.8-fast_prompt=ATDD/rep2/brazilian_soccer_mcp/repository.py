"""Query layer over the loaded matches and players.

This is the domain logic the MCP tools delegate to. It deals purely in plain
Python values so it is straightforward to unit test and to serialize to JSON.
"""

from __future__ import annotations

from .data_loader import load_dataset
from .models import Match, Player
from .normalize import (
    canonical_competition,
    competition_key,
    parse_date,
    team_key,
    text_key,
)


class SoccerRepository:
    def __init__(self, matches: list[Match], players: list[Player]):
        self._matches = matches
        self._players = players

    @classmethod
    def from_dir(cls, data_dir: str) -> "SoccerRepository":
        matches, players = load_dataset(data_dir)
        return cls(matches, players)

    # ------------------------------------------------------------------ #
    # Matches
    # ------------------------------------------------------------------ #
    def _filter_matches(
        self,
        *,
        team=None,
        opponent=None,
        competition=None,
        season=None,
        date_from=None,
        date_to=None,
        venue=None,
    ) -> list[Match]:
        team_k = team_key(team) if team else None
        opp_k = team_key(opponent) if opponent else None
        comp_k = competition_key(competition) if competition else None
        d_from = parse_date(date_from) if date_from else None
        d_to = parse_date(date_to) if date_to else None
        venue = (venue or "").strip().lower() or None

        results = []
        for m in self._matches:
            if comp_k and competition_key(m.competition) != comp_k:
                continue
            if season is not None and m.season != int(season):
                continue
            if d_from and (m.date is None or m.date < d_from):
                continue
            if d_to and (m.date is None or m.date > d_to):
                continue
            if team_k:
                if venue == "home":
                    if m.home_key != team_k:
                        continue
                elif venue == "away":
                    if m.away_key != team_k:
                        continue
                elif team_k not in (m.home_key, m.away_key):
                    continue
            if opp_k and opp_k not in (m.home_key, m.away_key):
                continue
            if team_k and opp_k and {team_k, opp_k} != {m.home_key, m.away_key}:
                continue
            results.append(m)

        results.sort(key=lambda x: (x.date or _MIN_DATE, x.competition))
        return results

    def find_matches(self, *, limit=50, **kwargs) -> list[Match]:
        matches = self._filter_matches(**kwargs)
        if limit:
            return matches[:limit]
        return matches

    def head_to_head(self, team_a: str, team_b: str, competition=None) -> dict:
        a_k = team_key(team_a)
        b_k = team_key(team_b)
        matches = self._filter_matches(
            team=team_a, opponent=team_b, competition=competition
        )
        a_wins = b_wins = draws = 0
        a_goals = b_goals = 0
        for m in matches:
            if not m.has_score:
                continue
            home_is_a = m.home_key == a_k
            a_for = m.home_goal if home_is_a else m.away_goal
            b_for = m.away_goal if home_is_a else m.home_goal
            a_goals += a_for
            b_goals += b_for
            if a_for > b_for:
                a_wins += 1
            elif b_for > a_for:
                b_wins += 1
            else:
                draws += 1
        return {
            "team_a": _display(matches, a_k, team_a),
            "team_b": _display(matches, b_k, team_b),
            "total_matches": len(matches),
            "team_a_wins": a_wins,
            "team_b_wins": b_wins,
            "draws": draws,
            "team_a_goals": a_goals,
            "team_b_goals": b_goals,
            "matches": [m.to_dict() for m in matches],
        }

    def team_record(
        self, team: str, *, season=None, competition=None, venue=None
    ) -> dict:
        t_k = team_key(team)
        matches = self._filter_matches(
            team=team, season=season, competition=competition, venue=venue
        )
        wins = draws = losses = gf = ga = 0
        counted = 0
        for m in matches:
            if not m.has_score:
                continue
            counted += 1
            home_is_team = m.home_key == t_k
            for_ = m.home_goal if home_is_team else m.away_goal
            against = m.away_goal if home_is_team else m.home_goal
            gf += for_
            ga += against
            if for_ > against:
                wins += 1
            elif against > for_:
                losses += 1
            else:
                draws += 1
        win_rate = round(100.0 * wins / counted, 1) if counted else 0.0
        return {
            "team": _display(matches, t_k, team),
            "season": int(season) if season is not None else None,
            "competition": canonical_competition(competition)
            if competition
            else None,
            "venue": (venue or "all"),
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

    # ------------------------------------------------------------------ #
    # Competitions
    # ------------------------------------------------------------------ #
    def standings(self, competition: str, season: int, limit=None) -> list[dict]:
        matches = self._filter_matches(competition=competition, season=season)
        matches = _dominant_source_only(matches)
        table: dict[str, dict] = {}

        def row(key, name):
            if key not in table:
                table[key] = {
                    "team": name,
                    "_key": key,
                    "played": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "points": 0,
                }
            return table[key]

        for m in matches:
            if not m.has_score:
                continue
            home = row(m.home_key, m.home_team)
            away = row(m.away_key, m.away_team)
            home["played"] += 1
            away["played"] += 1
            home["goals_for"] += m.home_goal
            home["goals_against"] += m.away_goal
            away["goals_for"] += m.away_goal
            away["goals_against"] += m.home_goal
            if m.home_goal > m.away_goal:
                home["wins"] += 1
                away["losses"] += 1
                home["points"] += 3
            elif m.away_goal > m.home_goal:
                away["wins"] += 1
                home["losses"] += 1
                away["points"] += 3
            else:
                home["draws"] += 1
                away["draws"] += 1
                home["points"] += 1
                away["points"] += 1

        rows = list(table.values())
        for r in rows:
            r["goal_difference"] = r["goals_for"] - r["goals_against"]
        rows.sort(
            key=lambda r: (
                -r["points"],
                -r["goal_difference"],
                -r["goals_for"],
                r["team"],
            )
        )
        for i, r in enumerate(rows, start=1):
            r["position"] = i
            r.pop("_key", None)
        if limit:
            return rows[:limit]
        return rows

    def competition_winner(self, competition: str, season: int) -> dict | None:
        table = self.standings(competition, season, limit=1)
        if not table:
            return None
        champ = dict(table[0])
        champ["competition"] = canonical_competition(competition)
        champ["season"] = int(season)
        return champ

    def list_competitions(self) -> list[str]:
        return sorted({m.competition for m in self._matches})

    # ------------------------------------------------------------------ #
    # Statistics
    # ------------------------------------------------------------------ #
    def statistics(self, *, competition=None, season=None) -> dict:
        matches = [m for m in self._filter_matches(
            competition=competition, season=season) if m.has_score]
        total = len(matches)
        if total == 0:
            return {
                "competition": canonical_competition(competition)
                if competition else None,
                "season": int(season) if season is not None else None,
                "total_matches": 0,
                "total_goals": 0,
                "average_goals_per_match": 0.0,
                "home_wins": 0,
                "away_wins": 0,
                "draws": 0,
                "home_win_rate": 0.0,
            }
        total_goals = sum(m.home_goal + m.away_goal for m in matches)
        home_wins = sum(1 for m in matches if m.home_goal > m.away_goal)
        away_wins = sum(1 for m in matches if m.away_goal > m.home_goal)
        draws = total - home_wins - away_wins
        return {
            "competition": canonical_competition(competition)
            if competition else None,
            "season": int(season) if season is not None else None,
            "total_matches": total,
            "total_goals": total_goals,
            "average_goals_per_match": round(total_goals / total, 2),
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": round(100.0 * home_wins / total, 1),
        }

    def biggest_wins(self, *, competition=None, season=None, limit=10) -> list[dict]:
        matches = [m for m in self._filter_matches(
            competition=competition, season=season) if m.has_score]
        matches.sort(
            key=lambda m: (
                -abs(m.home_goal - m.away_goal),
                -(m.home_goal + m.away_goal),
                m.date or _MIN_DATE,
            )
        )
        out = []
        for m in matches[:limit]:
            d = m.to_dict()
            d["margin"] = abs(m.home_goal - m.away_goal)
            out.append(d)
        return out

    # ------------------------------------------------------------------ #
    # Players
    # ------------------------------------------------------------------ #
    def search_players(
        self,
        *,
        name=None,
        nationality=None,
        club=None,
        position=None,
        min_overall=None,
        limit=50,
    ) -> list[Player]:
        name_k = text_key(name) if name else None
        nat_k = text_key(nationality) if nationality else None
        club_k = text_key(club) if club else None
        pos_k = text_key(position) if position else None
        min_ovr = int(min_overall) if min_overall is not None else None

        results = []
        for p in self._players:
            if name_k and name_k not in p.name_key:
                continue
            if nat_k and p.nationality_key != nat_k:
                continue
            if club_k and club_k not in p.club_key:
                continue
            if pos_k and p.position_key != pos_k:
                continue
            if min_ovr is not None and (p.overall is None or p.overall < min_ovr):
                continue
            results.append(p)

        results.sort(key=lambda p: (-(p.overall or 0), p.name))
        if limit:
            return results[:limit]
        return results


_MIN_DATE = parse_date("0001-01-01")


def _dominant_source_only(matches: list[Match]) -> list[Match]:
    """Keep only matches from the source file with the most rows in this set.

    The provided datasets overlap for several seasons but use slightly
    different team-name spellings, so naively merging them double-counts games
    in a league table. Computing a season's standings from its single most
    complete source keeps the table internally consistent.
    """
    if not matches:
        return matches
    counts: dict[str, int] = {}
    for m in matches:
        counts[m.source] = counts.get(m.source, 0) + 1
    best = max(counts, key=lambda s: counts[s])
    return [m for m in matches if m.source == best]


def _display(matches: list[Match], key: str, fallback: str) -> str:
    """Best display name for a team key, taken from matched rows."""
    for m in matches:
        if m.home_key == key:
            return m.home_team
        if m.away_key == key:
            return m.away_team
    return fallback
