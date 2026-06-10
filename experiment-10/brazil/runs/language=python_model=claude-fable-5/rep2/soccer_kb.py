"""In-memory knowledge base over the Brazilian soccer datasets.

Provides the query layer used by the MCP server: match search, head-to-head
records, team statistics, standings calculated from results, player search,
and aggregate statistics.  All team-name inputs are normalized, so
"Flamengo", "Flamengo-RJ" and "CR Flamengo" refer to the same club.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from typing import Dict, List, Optional

from data_loader import (
    COPA_DO_BRASIL, LIBERTADORES, SERIE_A, SERIE_B, SERIE_C,
    Match, Player, load_matches, load_players, parse_date,
)
from team_normalizer import strip_accents, team_matches

_COMPETITION_ALIASES = {
    "brasileirao": SERIE_A,
    "brasileirão": SERIE_A,
    "serie a": SERIE_A,
    "série a": SERIE_A,
    "brasileirao serie a": SERIE_A,
    "campeonato brasileiro": SERIE_A,
    "serie b": SERIE_B,
    "série b": SERIE_B,
    "serie c": SERIE_C,
    "série c": SERIE_C,
    "copa do brasil": COPA_DO_BRASIL,
    "brazilian cup": COPA_DO_BRASIL,
    "libertadores": LIBERTADORES,
    "copa libertadores": LIBERTADORES,
}


def resolve_competition(name: Optional[str]) -> Optional[str]:
    """Map a user-supplied competition name to its canonical form."""
    if not name:
        return None
    cleaned = strip_accents(name).lower().strip()
    for alias, canonical in _COMPETITION_ALIASES.items():
        if cleaned == strip_accents(alias).lower():
            return canonical
    for alias, canonical in _COMPETITION_ALIASES.items():
        if cleaned in strip_accents(alias).lower() or strip_accents(alias).lower() in cleaned:
            return canonical
    return name


class SoccerKB:
    """Loads every dataset once and answers structured queries."""

    def __init__(self) -> None:
        self.matches: List[Match] = load_matches()
        self.players: List[Player] = load_players()

    # ------------------------------------------------------------------ #
    # Match queries
    # ------------------------------------------------------------------ #

    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50,
    ) -> List[Match]:
        comp = resolve_competition(competition)
        start = parse_date(date_from) if date_from else None
        end = parse_date(date_to) if date_to else None
        results = []
        for m in self.matches:
            if comp and m.competition != comp:
                continue
            if season is not None and m.season != int(season):
                continue
            if start and (m.date is None or m.date < start):
                continue
            if end and (m.date is None or m.date > end):
                continue
            if team:
                home = team_matches(team, m.home_team)
                away = team_matches(team, m.away_team)
                if not (home or away):
                    continue
                if opponent:
                    other = m.away_team if home else m.home_team
                    if not team_matches(opponent, other):
                        continue
            elif opponent:
                if not (team_matches(opponent, m.home_team)
                        or team_matches(opponent, m.away_team)):
                    continue
            results.append(m)
        results.sort(key=lambda m: m.date or date.min, reverse=True)
        return results[:limit] if limit else results

    def head_to_head(self, team1: str, team2: str) -> dict:
        matches = self.find_matches(team=team1, opponent=team2, limit=0)
        record = {"team1_wins": 0, "team2_wins": 0, "draws": 0}
        goals = {"team1": 0, "team2": 0}
        for m in matches:
            t1_home = team_matches(team1, m.home_team)
            t1_goals = m.home_goal if t1_home else m.away_goal
            t2_goals = m.away_goal if t1_home else m.home_goal
            goals["team1"] += t1_goals
            goals["team2"] += t2_goals
            if t1_goals > t2_goals:
                record["team1_wins"] += 1
            elif t2_goals > t1_goals:
                record["team2_wins"] += 1
            else:
                record["draws"] += 1
        return {
            "team1": team1,
            "team2": team2,
            "total_matches": len(matches),
            "record": record,
            "goals": goals,
            "matches": [m.to_dict() for m in matches],
        }

    # ------------------------------------------------------------------ #
    # Team queries
    # ------------------------------------------------------------------ #

    def team_statistics(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "all",
    ) -> dict:
        comp = resolve_competition(competition)
        stats = {
            "matches": 0, "wins": 0, "draws": 0, "losses": 0,
            "goals_for": 0, "goals_against": 0,
        }
        by_competition: Dict[str, Counter] = defaultdict(Counter)
        for m in self.matches:
            if comp and m.competition != comp:
                continue
            if season is not None and m.season != int(season):
                continue
            is_home = team_matches(team, m.home_team)
            is_away = team_matches(team, m.away_team)
            if not (is_home or is_away):
                continue
            if venue == "home" and not is_home:
                continue
            if venue == "away" and not is_away:
                continue
            gf = m.home_goal if is_home else m.away_goal
            ga = m.away_goal if is_home else m.home_goal
            stats["matches"] += 1
            stats["goals_for"] += gf
            stats["goals_against"] += ga
            outcome = "wins" if gf > ga else ("losses" if ga > gf else "draws")
            stats[outcome] += 1
            comp_counter = by_competition[m.competition]
            comp_counter["matches"] += 1
            comp_counter[outcome] += 1
        played = stats["matches"]
        return {
            "team": team,
            "season": season,
            "competition": comp or "all competitions",
            "venue": venue,
            **stats,
            "points": stats["wins"] * 3 + stats["draws"],
            "win_rate": round(stats["wins"] / played * 100, 1) if played else 0.0,
            "by_competition": {k: dict(v) for k, v in by_competition.items()},
        }

    def list_team_competitions(self, team: str) -> dict:
        """Competitions and seasons in which a team appears in the data."""
        comps: Dict[str, set] = defaultdict(set)
        for m in self.matches:
            if team_matches(team, m.home_team) or team_matches(team, m.away_team):
                if m.season is not None:
                    comps[m.competition].add(m.season)
        return {
            "team": team,
            "competitions": {
                comp: sorted(seasons) for comp, seasons in sorted(comps.items())
            },
        }

    # ------------------------------------------------------------------ #
    # Competition queries
    # ------------------------------------------------------------------ #

    def _season_matches(self, competition: str, season: int) -> List[Match]:
        """League matches for one season, restricted to the dominant source.

        Several sources overlap for Serie A; mixing them would inflate the
        table, so standings use whichever single source covers the season
        most completely.
        """
        pool = [
            m for m in self.matches
            if m.competition == competition and m.season == int(season)
        ]
        if not pool:
            return []
        by_source = Counter(m.source for m in pool)
        dominant = by_source.most_common(1)[0][0]
        return [m for m in pool if m.source == dominant]

    def standings(self, season: int, competition: str = "Serie A") -> dict:
        comp = resolve_competition(competition) or SERIE_A
        pool = self._season_matches(comp, season)
        table: Dict[str, dict] = {}
        names: Dict[str, str] = {}
        for m in pool:
            for key, raw, gf, ga in (
                (m.home_key, m.home_team, m.home_goal, m.away_goal),
                (m.away_key, m.away_team, m.away_goal, m.home_goal),
            ):
                row = table.setdefault(key, {
                    "played": 0, "wins": 0, "draws": 0, "losses": 0,
                    "goals_for": 0, "goals_against": 0,
                })
                names.setdefault(key, raw)
                row["played"] += 1
                row["goals_for"] += gf
                row["goals_against"] += ga
                if gf > ga:
                    row["wins"] += 1
                elif gf < ga:
                    row["losses"] += 1
                else:
                    row["draws"] += 1
        rows = []
        for key, row in table.items():
            rows.append({
                "team": names[key],
                "points": row["wins"] * 3 + row["draws"],
                **row,
                "goal_difference": row["goals_for"] - row["goals_against"],
            })
        rows.sort(
            key=lambda r: (r["points"], r["wins"], r["goal_difference"],
                           r["goals_for"]),
            reverse=True,
        )
        for pos, row in enumerate(rows, start=1):
            row["position"] = pos
        return {
            "competition": comp,
            "season": int(season),
            "standings": rows,
            "champion": rows[0]["team"] if rows else None,
            "relegated": [r["team"] for r in rows[-4:]] if comp == SERIE_A and len(rows) >= 16 else [],
        }

    def cup_finals(self, competition: str = COPA_DO_BRASIL) -> dict:
        """Final-round matches per season for a knockout cup.

        Copa do Brasil rounds are numbered, so the final is the highest
        round of each season; Libertadores has an explicit "final" stage.
        """
        comp = resolve_competition(competition) or COPA_DO_BRASIL
        if comp == LIBERTADORES:
            finals = [
                m for m in self.matches
                if m.competition == comp and (m.stage or "").lower() == "final"
            ]
        else:
            by_round: Dict[tuple, List[Match]] = defaultdict(list)
            for m in self.matches:
                if m.competition != comp or m.season is None:
                    continue
                if m.round and m.round.strip().isdigit():
                    by_round[(m.season, int(m.round))].append(m)
            finals = []
            for season in {s for s, _ in by_round}:
                last = max(r for s, r in by_round if s == season)
                legs = by_round[(season, last)]
                # A real final has one or two legs; more matches means the
                # dataset stops before the final of that season.
                if len(legs) <= 2:
                    finals.extend(legs)
        finals.sort(key=lambda m: m.date or date.min)
        return {
            "competition": comp,
            "finals_by_season": {
                str(season): [
                    m.to_dict() for m in finals if m.season == season
                ]
                for season in sorted({m.season for m in finals})
            },
        }

    def libertadores_stage_results(self, season: int, stage: Optional[str] = None) -> dict:
        matches = [
            m for m in self.matches
            if m.competition == LIBERTADORES and m.season == int(season)
            and (stage is None or (m.stage or "").lower() == stage.lower())
        ]
        by_stage: Dict[str, list] = defaultdict(list)
        for m in sorted(matches, key=lambda m: m.date or date.min):
            by_stage[m.stage or "unknown"].append(m.to_dict())
        return {"season": int(season), "stages": dict(by_stage)}

    # ------------------------------------------------------------------ #
    # Player queries
    # ------------------------------------------------------------------ #

    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: int = 20,
    ) -> List[Player]:
        name_q = strip_accents(name).lower() if name else None
        nat_q = strip_accents(nationality).lower() if nationality else None
        results = []
        for p in self.players:
            if name_q and name_q not in strip_accents(p.name).lower():
                continue
            if nat_q and strip_accents(p.nationality).lower() != nat_q:
                continue
            if club and not team_matches(club, p.club):
                continue
            if position and p.position.upper() != position.upper():
                continue
            if min_overall is not None and (p.overall or 0) < int(min_overall):
                continue
            results.append(p)
        results.sort(key=lambda p: p.overall or 0, reverse=True)
        return results[:limit] if limit else results

    def players_by_club_summary(self, nationality: str = "Brazil",
                                clubs: Optional[List[str]] = None,
                                limit: int = 10) -> dict:
        """Average rating and player count per club for one nationality."""
        groups: Dict[str, list] = defaultdict(list)
        for p in self.search_players(nationality=nationality, limit=0):
            if not p.club:
                continue
            if clubs and not any(team_matches(c, p.club) for c in clubs):
                continue
            groups[p.club].append(p.overall or 0)
        summary = [
            {
                "club": club,
                "players": len(ratings),
                "avg_rating": round(sum(ratings) / len(ratings), 1),
            }
            for club, ratings in groups.items()
        ]
        summary.sort(key=lambda r: (r["players"], r["avg_rating"]), reverse=True)
        return {"nationality": nationality, "clubs": summary[:limit] if limit else summary}

    # ------------------------------------------------------------------ #
    # Statistical analysis
    # ------------------------------------------------------------------ #

    def average_goals(self, competition: Optional[str] = None,
                      season: Optional[int] = None) -> dict:
        comp = resolve_competition(competition)
        total_goals = 0
        count = 0
        home_wins = away_wins = draws = 0
        for m in self.matches:
            if comp and m.competition != comp:
                continue
            if season is not None and m.season != int(season):
                continue
            count += 1
            total_goals += m.home_goal + m.away_goal
            if m.home_goal > m.away_goal:
                home_wins += 1
            elif m.away_goal > m.home_goal:
                away_wins += 1
            else:
                draws += 1
        return {
            "competition": comp or "all competitions",
            "season": season,
            "matches": count,
            "total_goals": total_goals,
            "avg_goals_per_match": round(total_goals / count, 2) if count else 0.0,
            "home_win_rate": round(home_wins / count * 100, 1) if count else 0.0,
            "away_win_rate": round(away_wins / count * 100, 1) if count else 0.0,
            "draw_rate": round(draws / count * 100, 1) if count else 0.0,
        }

    def biggest_wins(self, competition: Optional[str] = None,
                     limit: int = 10) -> List[dict]:
        comp = resolve_competition(competition)
        pool = [
            m for m in self.matches
            if (not comp or m.competition == comp)
        ]
        pool.sort(
            key=lambda m: (abs(m.home_goal - m.away_goal),
                           m.home_goal + m.away_goal),
            reverse=True,
        )
        out = []
        for m in pool[:limit]:
            d = m.to_dict()
            d["margin"] = abs(m.home_goal - m.away_goal)
            out.append(d)
        return out

    def best_record(self, venue: str = "home",
                    competition: Optional[str] = None,
                    season: Optional[int] = None,
                    min_matches: int = 10, limit: int = 10) -> dict:
        comp = resolve_competition(competition)
        table: Dict[str, Counter] = defaultdict(Counter)
        names: Dict[str, str] = {}
        for m in self.matches:
            if comp and m.competition != comp:
                continue
            if season is not None and m.season != int(season):
                continue
            sides = []
            if venue in ("home", "all"):
                sides.append((m.home_key, m.home_team, m.home_goal, m.away_goal))
            if venue in ("away", "all"):
                sides.append((m.away_key, m.away_team, m.away_goal, m.home_goal))
            for key, raw, gf, ga in sides:
                names.setdefault(key, raw)
                c = table[key]
                c["matches"] += 1
                c["goals_for"] += gf
                c["goals_against"] += ga
                if gf > ga:
                    c["wins"] += 1
                elif gf < ga:
                    c["losses"] += 1
                else:
                    c["draws"] += 1
        rows = []
        for key, c in table.items():
            if c["matches"] < min_matches:
                continue
            rows.append({
                "team": names[key],
                "matches": c["matches"],
                "wins": c["wins"],
                "draws": c["draws"],
                "losses": c["losses"],
                "goals_for": c["goals_for"],
                "goals_against": c["goals_against"],
                "win_rate": round(c["wins"] / c["matches"] * 100, 1),
            })
        rows.sort(key=lambda r: (r["win_rate"], r["wins"]), reverse=True)
        return {
            "venue": venue,
            "competition": comp or "all competitions",
            "season": season,
            "min_matches": min_matches,
            "teams": rows[:limit] if limit else rows,
        }

    # ------------------------------------------------------------------ #
    # Meta
    # ------------------------------------------------------------------ #

    def data_summary(self) -> dict:
        by_comp = Counter(m.competition for m in self.matches)
        seasons = [m.season for m in self.matches if m.season is not None]
        return {
            "total_matches": len(self.matches),
            "matches_by_competition": dict(by_comp),
            "season_range": [min(seasons), max(seasons)] if seasons else None,
            "total_players": len(self.players),
            "brazilian_players": sum(
                1 for p in self.players if p.nationality == "Brazil"
            ),
            "sources": sorted({m.source for m in self.matches}),
        }


_kb: Optional[SoccerKB] = None


def get_kb() -> SoccerKB:
    """Singleton knowledge base (datasets load once per process)."""
    global _kb
    if _kb is None:
        _kb = SoccerKB()
    return _kb
