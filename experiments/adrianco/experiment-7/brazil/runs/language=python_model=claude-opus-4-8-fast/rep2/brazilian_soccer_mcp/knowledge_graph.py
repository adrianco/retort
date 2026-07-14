"""
================================================================================
Module: brazilian_soccer_mcp.knowledge_graph
--------------------------------------------------------------------------------
Context:
    The heart of the server. Loads every dataset once, de-duplicates matches
    that appear in multiple source files (the historical and modern Brasileirão
    files overlap on 2012-2019), and builds in-memory indexes that model a
    lightweight knowledge graph:

        Nodes : Team, Player, Competition, Season, Match
        Edges : Team --played_in--> Match, Player --plays_for--> Club,
                Player --nationality--> Country, Match --part_of--> Competition

    Indexes (team_key -> matches, club_key -> players, nationality -> players,
    (competition, season) -> matches) make every query in TASK.md answerable in
    well under the 2s / 5s performance budget.

Responsibility:
    Expose a clean, framework-agnostic Python API for all five query categories
    (Match, Team, Player, Competition, Statistics). The MCP server is a thin
    adapter over these methods; the BDD tests exercise them directly.
================================================================================
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from . import data_loader
from .models import Match, Player
from .normalize import (
    base_key,
    contains_words,
    names_match,
    parse_date,
    strip_accents,
    team_key,
    team_suffix,
)


def _comp_key(text: str) -> str:
    return strip_accents(text or "").lower().strip()


# Per-competition source-file priority (best first). The overlapping CSVs each
# carry the same season's fixtures; to avoid double-counting in standings,
# records and averages we pick ONE authoritative source per (competition,
# season) — the highest-priority file that actually covers that season.
_SOURCE_PRIORITY = {
    "Brasileirão Série A": [
        "Brasileirao_Matches.csv",          # 2012-2022, rich (rounds + states)
        "novo_campeonato_brasileiro.csv",   # 2003-2019
        "BR-Football-Dataset.csv",          # 2014-2023 (fills 2023)
    ],
    "Copa do Brasil": [
        "Brazilian_Cup_Matches.csv",        # 2012-2021
        "BR-Football-Dataset.csv",          # 2014-2023 (fills 2022-2023)
    ],
    "Copa Libertadores": ["Libertadores_Matches.csv"],
}


class KnowledgeGraph:
    """In-memory knowledge graph over Brazilian soccer matches and players."""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir: Path = data_loader.find_data_dir(data_dir)
        self.matches: List[Match] = []
        self.players: List[Player] = []
        # Indexes (the "edges" of the graph).
        self._by_team: Dict[str, List[Match]] = defaultdict(list)
        self._team_display: Dict[str, str] = {}   # team_key -> a display spelling
        self._team_base: Dict[str, str] = {}       # team_key -> base_key
        self._team_suffix: Dict[str, Optional[str]] = {}  # team_key -> state/country code
        self._by_comp_season: Dict[tuple, List[Match]] = defaultdict(list)
        self._players_by_club: Dict[str, List[Player]] = defaultdict(list)
        self._players_by_nat: Dict[str, List[Player]] = defaultdict(list)
        self._loaded = False

    # ------------------------------------------------------------------ #
    # Loading / indexing                                                 #
    # ------------------------------------------------------------------ #
    def load(self) -> "KnowledgeGraph":
        """Load all CSVs, de-duplicate matches and build indexes (idempotent)."""
        if self._loaded:
            return self
        raw_matches = data_loader.load_all_matches(self.data_dir)
        self.matches = self._select_authoritative(raw_matches)
        self.players = data_loader.load_all_players(self.data_dir)
        self._build_indexes()
        self._loaded = True
        return self

    @staticmethod
    def _select_authoritative(matches: List[Match]) -> List[Match]:
        """Keep one authoritative source per (competition, season).

        The provided CSVs overlap heavily (e.g. the 2019 Brasileirão appears in
        three files). Merging them by fuzzy match is unreliable because of team
        name spelling variations across files, so instead — for each
        (competition, season) — we keep matches from a single source: the
        highest-priority file (see ``_SOURCE_PRIORITY``) that covers that
        season, falling back to whichever source has the most rows. Within the
        chosen source, exact duplicate rows are collapsed.
        """
        groups: Dict[tuple, Dict[str, List[Match]]] = defaultdict(lambda: defaultdict(list))
        for m in matches:
            groups[(m.competition, m.season)][m.source].append(m)

        selected: List[Match] = []
        for (competition, _season), by_source in groups.items():
            priority = _SOURCE_PRIORITY.get(competition, [])
            chosen_source = None
            for src in priority:
                if src in by_source:
                    chosen_source = src
                    break
            if chosen_source is None:
                # No priority listed/present -> richest (most rows) source.
                chosen_source = max(by_source, key=lambda s: len(by_source[s]))

            seen: set = set()
            for m in by_source[chosen_source]:
                key = m.dedup_key()
                if key in seen:
                    continue
                seen.add(key)
                selected.append(m)
        return selected

    def _build_indexes(self) -> None:
        for m in self.matches:
            hk, ak = team_key(m.home_team), team_key(m.away_team)
            self._by_team[hk].append(m)
            if hk not in self._team_display:
                self._team_display[hk] = m.home_team
                self._team_base[hk] = base_key(m.home_team)
                self._team_suffix[hk] = team_suffix(m.home_team)
            if ak != hk:
                self._by_team[ak].append(m)
            if ak not in self._team_display:
                self._team_display[ak] = m.away_team
                self._team_base[ak] = base_key(m.away_team)
                self._team_suffix[ak] = team_suffix(m.away_team)
            self._by_comp_season[(m.competition, m.season)].append(m)
        for p in self.players:
            self._players_by_club[team_key(p.club)].append(p)
            self._players_by_nat[strip_accents(p.nationality).lower()].append(p)

    def _resolve_team_keys(self, query: str) -> List[str]:
        """Map a (possibly suffix-less) team query to canonical team keys.

        "Flamengo" -> ["flamengo"]; "Palmeiras" -> ["palmeiras-sp"];
        "Atlético" -> every "atletico-*" key (ambiguous; caller may add suffix).
        Returns ``[]`` when nothing matches.
        """
        if not query:
            return []
        qk = team_key(query)
        q_base = base_key(query)
        q_suffix = team_suffix(query)
        matched = []
        for k, cand_base in self._team_base.items():
            if k == qk:
                matched.append(k)
                continue
            if q_suffix is not None:
                # Suffix given: require same base AND a compatible suffix
                # (candidate has no suffix, or the exact same one). This keeps
                # "Atlético-MG" from matching "Atlético-GO".
                cand_suffix = self._team_suffix.get(k)
                if cand_base == q_base and cand_suffix in (None, q_suffix):
                    matched.append(k)
            else:
                # No suffix: match the whole club family by base name, plus
                # long official names via whole-word containment.
                if cand_base == q_base or contains_words(cand_base, q_base) or contains_words(
                    q_base, cand_base
                ):
                    matched.append(k)
        return matched

    def _team_matches(self, query: str) -> List[Match]:
        """All matches involving any team resolved from *query* (de-duplicated)."""
        keys = self._resolve_team_keys(query)
        if len(keys) == 1:
            return self._by_team.get(keys[0], [])
        seen: set = set()
        out: List[Match] = []
        for k in keys:
            for m in self._by_team.get(k, []):
                if id(m) not in seen:
                    seen.add(id(m))
                    out.append(m)
        return out

    # ------------------------------------------------------------------ #
    # 1. Match queries                                                   #
    # ------------------------------------------------------------------ #
    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        venue: str = "either",
        limit: Optional[int] = None,
    ) -> List[Match]:
        """Find matches by any combination of criteria.

        venue: 'either' (default), 'home' or 'away' — interpreted relative to
        *team*. Results are sorted most-recent first.
        """
        # Start from the narrowest index available.
        team_keys = set(self._resolve_team_keys(team)) if team else set()
        if team:
            pool = self._team_matches(team)
        elif competition is not None and season is not None:
            pool = list(self._by_comp_season.get((self._resolve_competition(competition), season), []))
        else:
            pool = self.matches

        start = parse_date(start_date) if start_date else None
        end = parse_date(end_date) if end_date else None
        comp = self._resolve_competition(competition) if competition else None

        out = []
        for m in pool:
            if comp and m.competition != comp:
                continue
            if season is not None and m.season != season:
                continue
            if team_keys and venue == "home" and team_key(m.home_team) not in team_keys:
                continue
            if team_keys and venue == "away" and team_key(m.away_team) not in team_keys:
                continue
            if opponent and not (
                names_match(opponent, m.home_team) or names_match(opponent, m.away_team)
            ):
                continue
            if start and (m.match_date is None or m.match_date < start):
                continue
            if end and (m.match_date is None or m.match_date > end):
                continue
            out.append(m)

        out.sort(key=lambda x: (x.match_date or date.min), reverse=True)
        return out[:limit] if limit else out

    def head_to_head(
        self, team1: str, team2: str, competition: Optional[str] = None
    ) -> dict:
        """Return the head-to-head record between two teams."""
        matches = self.find_matches(team=team1, opponent=team2, competition=competition)
        keys1 = set(self._resolve_team_keys(team1))
        keys2 = set(self._resolve_team_keys(team2))
        t1_wins = t2_wins = draws = 0
        t1_goals = t2_goals = 0
        for m in matches:
            if not m.played:
                continue
            home_is_t1 = team_key(m.home_team) in keys1
            g1 = m.home_goal if home_is_t1 else m.away_goal
            g2 = m.away_goal if home_is_t1 else m.home_goal
            t1_goals += g1
            t2_goals += g2
            if g1 > g2:
                t1_wins += 1
            elif g2 > g1:
                t2_wins += 1
            else:
                draws += 1
        return {
            "team1": _display(team1, matches, keys1),
            "team2": _display(team2, matches, keys2),
            "matches": matches,
            "total": len([m for m in matches if m.played]),
            "team1_wins": t1_wins,
            "team2_wins": t2_wins,
            "draws": draws,
            "team1_goals": t1_goals,
            "team2_goals": t2_goals,
        }

    # ------------------------------------------------------------------ #
    # 2. Team queries                                                    #
    # ------------------------------------------------------------------ #
    def team_record(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "all",
    ) -> dict:
        """Compute W/D/L, goals for/against and win-rate for a team.

        venue: 'all', 'home' or 'away'.
        """
        team_keys = set(self._resolve_team_keys(team))
        comp = self._resolve_competition(competition) if competition else None
        wins = draws = losses = gf = ga = 0
        played = 0
        display = team
        for m in self._team_matches(team):
            if season is not None and m.season != season:
                continue
            if comp and m.competition != comp:
                continue
            if not m.played:
                continue
            is_home = team_key(m.home_team) in team_keys
            if venue == "home" and not is_home:
                continue
            if venue == "away" and is_home:
                continue
            display = m.home_team if is_home else m.away_team
            gffor = m.home_goal if is_home else m.away_goal
            gaag = m.away_goal if is_home else m.home_goal
            gf += gffor
            ga += gaag
            played += 1
            if gffor > gaag:
                wins += 1
            elif gffor < gaag:
                losses += 1
            else:
                draws += 1
        win_rate = (wins / played * 100) if played else 0.0
        return {
            "team": display,
            "season": season,
            "competition": comp,
            "venue": venue,
            "matches": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": gf,
            "goals_against": ga,
            "goal_difference": gf - ga,
            "points": wins * 3 + draws,
            "win_rate": round(win_rate, 1),
        }

    def team_competitions(self, team: str) -> List[str]:
        """List the competitions a team has appeared in (sorted)."""
        comps = {m.competition for m in self._team_matches(team)}
        return sorted(comps)

    # ------------------------------------------------------------------ #
    # 3. Player queries                                                  #
    # ------------------------------------------------------------------ #
    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        sort_by: str = "overall",
        limit: Optional[int] = 25,
    ) -> List[Player]:
        """Search the FIFA player database by any combination of filters."""
        # Use the narrowest index to seed the candidate pool.
        if club:
            pool = list(self._players_by_club.get(team_key(club), []))
            # Fall back to fuzzy contains if exact club key missed.
            if not pool:
                pool = [p for p in self.players if names_match(club, p.club)]
        elif nationality:
            pool = list(self._players_by_nat.get(strip_accents(nationality).lower(), []))
        else:
            pool = self.players

        nat_key = strip_accents(nationality).lower() if nationality else None
        pos_key = position.lower() if position else None
        name_key = strip_accents(name).lower() if name else None

        results = []
        for p in pool:
            if name_key and name_key not in strip_accents(p.name).lower():
                continue
            if nat_key and strip_accents(p.nationality).lower() != nat_key:
                continue
            if pos_key and pos_key not in p.position.lower():
                continue
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            results.append(p)

        reverse = sort_by in {"overall", "potential", "age"}
        results.sort(key=lambda p: (getattr(p, sort_by, 0) or 0), reverse=reverse)
        return results[:limit] if limit else results

    def get_player(self, name: str) -> Optional[Player]:
        """Return the best (highest-overall) player matching *name* exactly-ish."""
        matches = self.search_players(name=name, limit=None)
        return matches[0] if matches else None

    def players_by_club_summary(self, nationality: str = "Brazil") -> List[dict]:
        """Group players of a nationality by club with counts and average rating."""
        nat_key = strip_accents(nationality).lower()
        buckets: Dict[str, List[Player]] = defaultdict(list)
        for p in self._players_by_nat.get(nat_key, []):
            if p.club:
                buckets[p.club].append(p)
        out = []
        for club, plist in buckets.items():
            ratings = [p.overall for p in plist if p.overall is not None]
            avg = round(sum(ratings) / len(ratings), 1) if ratings else 0.0
            out.append({"club": club, "count": len(plist), "avg_overall": avg})
        out.sort(key=lambda x: (x["count"], x["avg_overall"]), reverse=True)
        return out

    # ------------------------------------------------------------------ #
    # 4. Competition queries                                             #
    # ------------------------------------------------------------------ #
    def standings(self, competition: str, season: int) -> List[dict]:
        """Compute a league table from match results (3pts win, 1pt draw).

        Sorted by points, then goal difference, then goals for. Works best for
        round-robin leagues (Brasileirão) but will tabulate any competition.
        """
        comp = self._resolve_competition(competition)
        matches = self._by_comp_season.get((comp, season), [])
        table: Dict[str, dict] = {}

        def row(name: str) -> dict:
            return table.setdefault(
                team_key(name),
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

        for m in matches:
            if not m.played:
                continue
            h, a = row(m.home_team), row(m.away_team)
            h["played"] += 1
            a["played"] += 1
            h["goals_for"] += m.home_goal
            h["goals_against"] += m.away_goal
            a["goals_for"] += m.away_goal
            a["goals_against"] += m.home_goal
            if m.home_goal > m.away_goal:
                h["wins"] += 1
                h["points"] += 3
                a["losses"] += 1
            elif m.away_goal > m.home_goal:
                a["wins"] += 1
                a["points"] += 3
                h["losses"] += 1
            else:
                h["draws"] += 1
                a["draws"] += 1
                h["points"] += 1
                a["points"] += 1

        rows = list(table.values())
        for r in rows:
            r["goal_difference"] = r["goals_for"] - r["goals_against"]
        rows.sort(
            key=lambda r: (r["points"], r["goal_difference"], r["goals_for"]),
            reverse=True,
        )
        for i, r in enumerate(rows, 1):
            r["position"] = i
        return rows

    def champion(self, competition: str, season: int) -> Optional[dict]:
        """Return the league winner (top of the computed standings)."""
        table = self.standings(competition, season)
        return table[0] if table else None

    def list_competitions(self) -> List[str]:
        return sorted({m.competition for m in self.matches})

    def list_seasons(self, competition: Optional[str] = None) -> List[int]:
        comp = self._resolve_competition(competition) if competition else None
        seasons = {
            m.season
            for m in self.matches
            if m.season is not None and (comp is None or m.competition == comp)
        }
        return sorted(seasons)

    # ------------------------------------------------------------------ #
    # 5. Statistical analysis                                            #
    # ------------------------------------------------------------------ #
    def average_goals(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> dict:
        """Average goals per match and home/away win rates over a slice."""
        comp = self._resolve_competition(competition) if competition else None
        total_goals = 0
        played = home_wins = away_wins = draws = 0
        for m in self.matches:
            if comp and m.competition != comp:
                continue
            if season is not None and m.season != season:
                continue
            if not m.played:
                continue
            played += 1
            total_goals += m.total_goals
            if m.home_goal > m.away_goal:
                home_wins += 1
            elif m.away_goal > m.home_goal:
                away_wins += 1
            else:
                draws += 1
        return {
            "competition": comp,
            "season": season,
            "matches": played,
            "total_goals": total_goals,
            "avg_goals_per_match": round(total_goals / played, 2) if played else 0.0,
            "home_win_rate": round(home_wins / played * 100, 1) if played else 0.0,
            "away_win_rate": round(away_wins / played * 100, 1) if played else 0.0,
            "draw_rate": round(draws / played * 100, 1) if played else 0.0,
        }

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> List[Match]:
        """Return the matches with the largest goal margin (most lopsided)."""
        comp = self._resolve_competition(competition) if competition else None
        pool = [
            m
            for m in self.matches
            if m.played
            and (comp is None or m.competition == comp)
            and (season is None or m.season == season)
        ]
        pool.sort(
            key=lambda m: (abs(m.home_goal - m.away_goal), m.total_goals),
            reverse=True,
        )
        return pool[:limit]

    def best_record(
        self,
        venue: str = "all",
        competition: Optional[str] = None,
        season: Optional[int] = None,
        min_matches: int = 5,
        metric: str = "win_rate",
        limit: int = 10,
    ) -> List[dict]:
        """Rank teams by record (e.g. best home/away win-rate) over a slice."""
        comp = self._resolve_competition(competition) if competition else None
        agg: Dict[str, dict] = {}
        for m in self.matches:
            if comp and m.competition != comp:
                continue
            if season is not None and m.season != season:
                continue
            if not m.played:
                continue
            pairs = []
            if venue in ("all", "home"):
                pairs.append((m.home_team, m.home_goal, m.away_goal))
            if venue in ("all", "away"):
                pairs.append((m.away_team, m.away_goal, m.home_goal))
            for name, gf, ga in pairs:
                r = agg.setdefault(
                    team_key(name),
                    {"team": name, "matches": 0, "wins": 0, "draws": 0,
                     "losses": 0, "goals_for": 0, "goals_against": 0},
                )
                r["matches"] += 1
                r["goals_for"] += gf
                r["goals_against"] += ga
                if gf > ga:
                    r["wins"] += 1
                elif gf < ga:
                    r["losses"] += 1
                else:
                    r["draws"] += 1
        rows = []
        for r in agg.values():
            if r["matches"] < min_matches:
                continue
            r["points"] = r["wins"] * 3 + r["draws"]
            r["win_rate"] = round(r["wins"] / r["matches"] * 100, 1)
            r["goal_difference"] = r["goals_for"] - r["goals_against"]
            rows.append(r)
        rows.sort(key=lambda r: (r.get(metric, 0), r["goal_difference"]), reverse=True)
        return rows[:limit]

    # ------------------------------------------------------------------ #
    # Helpers                                                            #
    # ------------------------------------------------------------------ #
    def _resolve_competition(self, query: Optional[str]) -> Optional[str]:
        """Map a loose competition query to its canonical label.

        Accepts aliases like "brasileirao", "serie a", "libertadores",
        "brazilian cup". Returns the original query if no canonical match (so
        exact labels still work).
        """
        if not query:
            return None
        q = _comp_key(query)
        known = self.list_competitions() if self._loaded else []
        # Exact (accent-insensitive) match first.
        for comp in known:
            if _comp_key(comp) == q:
                return comp
        # Alias table.
        aliases = {
            "brasileirao": "Brasileirão Série A",
            "brasileirao serie a": "Brasileirão Série A",
            "serie a": "Brasileirão Série A",
            "brasileiro": "Brasileirão Série A",
            "serie b": "Brasileirão Série B",
            "serie c": "Brasileirão Série C",
            "libertadores": "Copa Libertadores",
            "copa libertadores": "Copa Libertadores",
            "copa do brasil": "Copa do Brasil",
            "brazilian cup": "Copa do Brasil",
            "cup": "Copa do Brasil",
        }
        if q in aliases:
            return aliases[q]
        # Substring fallback against known labels.
        for comp in known:
            if q and q in _comp_key(comp):
                return comp
        return query


def _display(query: str, matches: List[Match], keys: set) -> str:
    """Pick the dataset's display spelling for a queried team, if available."""
    for m in matches:
        if team_key(m.home_team) in keys:
            return m.home_team
        if team_key(m.away_team) in keys:
            return m.away_team
    return query
