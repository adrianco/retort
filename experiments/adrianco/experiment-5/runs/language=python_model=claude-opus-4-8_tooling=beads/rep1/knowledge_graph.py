"""
================================================================================
Module: knowledge_graph.py
Project: Brazilian Soccer MCP Server
--------------------------------------------------------------------------------
Context
-------
The in-memory knowledge graph and query engine that sits between the raw loaded
data (``data_loader.Dataset``) and the MCP tool layer (``mcp_server.py``).

"Graph" model
-------------
Entities (nodes): Team, Player, Competition, Match.
Relationships (edges), all materialised as adjacency indexes for O(1) lookup:

    Team   --played-->        Match        (team_matches[key])
    Team   --in-->            Competition  (derivable from matches)
    Player --plays_for-->     Team/Club    (club_players[club_key])
    Player --from-->          Nation       (nation_players[nationality])
    Match  --part_of-->       Competition  (comp_matches[competition])

On top of the indexes the engine exposes the five query families required by the
spec: match, team, player, competition and statistical queries. Every team name
argument is resolved through ``normalize.normalize_key`` (+ a fuzzy fallback) so
the many naming conventions in the data all map to one entity.

Pure stdlib; no I/O beyond what ``data_loader`` already did, so it is fast and
fully unit-testable.
================================================================================
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from data_loader import Dataset, load_dataset
from models import Match, Player
from normalize import normalize_key, canonical_name

WIN_POINTS, DRAW_POINTS = 3, 1


class TeamResolutionError(ValueError):
    """Raised when a team name cannot be matched to any entity in the data."""


class SoccerGraph:
    """Knowledge graph + query engine over the Brazilian soccer datasets."""

    def __init__(self, dataset: Dataset):
        self.ds = dataset
        # ---- adjacency indexes (the "edges") ----
        self.team_matches: dict[str, list[Match]] = defaultdict(list)
        self.comp_matches: dict[str, list[Match]] = defaultdict(list)
        self.club_players: dict[str, list[Player]] = defaultdict(list)
        self.nation_players: dict[str, list[Player]] = defaultdict(list)
        # ---- display-name registry: key -> most frequent canonical label ----
        self._team_label_votes: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for m in dataset.matches:
            self.comp_matches[m.competition].append(m)
            if m.home_key:
                self.team_matches[m.home_key].append(m)
                self._team_label_votes[m.home_key][m.home_team] += 1
            if m.away_key:
                self.team_matches[m.away_key].append(m)
                self._team_label_votes[m.away_key][m.away_team] += 1

        for p in dataset.players:
            if p.club_key:
                self.club_players[p.club_key].append(p)
            if p.nationality:
                self.nation_players[p.nationality].append(p)

        self.team_label: dict[str, str] = {
            k: max(votes.items(), key=lambda kv: kv[1])[0]
            for k, votes in self._team_label_votes.items()
        }

    # ------------------------------------------------------------------ #
    # Construction helpers                                               #
    # ------------------------------------------------------------------ #
    @classmethod
    def from_data_dir(cls, data_dir: Optional[str] = None) -> "SoccerGraph":
        ds = load_dataset(data_dir) if data_dir else load_dataset()
        return cls(ds)

    # ------------------------------------------------------------------ #
    # Team-name resolution                                               #
    # ------------------------------------------------------------------ #
    def resolve_team(self, query: str) -> Optional[str]:
        """Resolve a free-text team name to its canonical key (or None).

        Strategy: exact normalized-key match first; then a fuzzy fallback that
        matches on key/label substring, preferring the team with the most data.
        """
        if not query:
            return None
        key = normalize_key(query)
        if key in self.team_matches:
            return key
        # fuzzy: substring on key or display label
        q = key or query.lower()
        candidates = [
            k for k in self.team_matches
            if q in k or k in q or q in self.team_label.get(k, "").lower()
        ]
        if not candidates:
            return None
        # prefer the candidate whose key the query best matches, then by volume
        candidates.sort(key=lambda k: (k != q, len(self.team_matches[k])),
                        reverse=False)
        candidates.sort(key=lambda k: len(self.team_matches[k]), reverse=True)
        # exact-substring of full query wins
        for k in candidates:
            if k == q:
                return k
        return candidates[0]

    def require_team(self, query: str) -> str:
        key = self.resolve_team(query)
        if key is None:
            raise TeamResolutionError(f"No team matching {query!r} found in the data")
        return key

    def label(self, key: str) -> str:
        return self.team_label.get(key, canonical_name(key))

    def list_teams(self, competition: Optional[str] = None) -> list[str]:
        """Return canonical display labels for all known teams (optionally
        restricted to a competition), sorted alphabetically."""
        if competition:
            keys = {m.home_key for m in self.comp_matches.get(competition, [])}
            keys |= {m.away_key for m in self.comp_matches.get(competition, [])}
        else:
            keys = set(self.team_matches)
        return sorted(self.label(k) for k in keys if k)

    def list_competitions(self) -> list[str]:
        return sorted(self.comp_matches)

    def list_seasons(self, competition: Optional[str] = None) -> list[int]:
        src = self.comp_matches.get(competition, []) if competition else self.ds.matches
        return sorted({m.season for m in src if m.season is not None})

    # ------------------------------------------------------------------ #
    # 1. Match queries                                                   #
    # ------------------------------------------------------------------ #
    def find_matches(self, *, team: Optional[str] = None, team2: Optional[str] = None,
                     competition: Optional[str] = None, season: Optional[int] = None,
                     date_from: Optional[str] = None, date_to: Optional[str] = None,
                     venue: str = "either", limit: Optional[int] = None) -> list[Match]:
        """Find matches by any combination of criteria.

        venue: 'either' | 'home' | 'away' — interpreted relative to ``team``.
        Results are sorted most-recent first.
        """
        team_key = self.resolve_team(team) if team else None
        team2_key = self.resolve_team(team2) if team2 else None

        if team_key is not None:
            pool = self.team_matches.get(team_key, [])
        elif competition:
            pool = self.comp_matches.get(competition, [])
        else:
            pool = self.ds.matches

        out = []
        for m in pool:
            if competition and m.competition != competition:
                continue
            if season is not None and m.season != season:
                continue
            if team_key is not None:
                if venue == "home" and m.home_key != team_key:
                    continue
                if venue == "away" and m.away_key != team_key:
                    continue
            if team2_key is not None:
                if team_key is not None:
                    if {m.home_key, m.away_key} != {team_key, team2_key}:
                        continue
                elif team2_key not in (m.home_key, m.away_key):
                    continue
            if date_from and (not m.date or m.date < date_from):
                continue
            if date_to and (not m.date or m.date > date_to):
                continue
            out.append(m)

        out.sort(key=lambda m: (m.date or "", m.season or 0), reverse=True)
        return out[:limit] if limit else out

    def head_to_head(self, team_a: str, team_b: str,
                     competition: Optional[str] = None) -> dict:
        """Full head-to-head record between two teams."""
        ka, kb = self.require_team(team_a), self.require_team(team_b)
        matches = [m for m in self.team_matches.get(ka, [])
                   if kb in (m.home_key, m.away_key)
                   and (competition is None or m.competition == competition)
                   and m.has_score]
        matches.sort(key=lambda m: (m.date or "", m.season or 0), reverse=True)
        a_wins = b_wins = draws = a_goals = b_goals = 0
        for m in matches:
            ag = m.home_goal if m.home_key == ka else m.away_goal
            bg = m.home_goal if m.home_key == kb else m.away_goal
            a_goals += ag
            b_goals += bg
            if ag > bg:
                a_wins += 1
            elif bg > ag:
                b_wins += 1
            else:
                draws += 1
        return {
            "team_a": self.label(ka), "team_b": self.label(kb),
            "total_matches": len(matches),
            "team_a_wins": a_wins, "team_b_wins": b_wins, "draws": draws,
            "team_a_goals": a_goals, "team_b_goals": b_goals,
            "matches": matches,
        }

    # ------------------------------------------------------------------ #
    # 2. Team queries                                                    #
    # ------------------------------------------------------------------ #
    def team_record(self, team: str, *, season: Optional[int] = None,
                    competition: Optional[str] = None,
                    venue: str = "all") -> dict:
        """Win/draw/loss + goals record for a team.

        venue: 'all' | 'home' | 'away'.
        """
        key = self.require_team(team)
        played = wins = draws = losses = gf = ga = 0
        for m in self.team_matches.get(key, []):
            if not m.has_score:
                continue
            if season is not None and m.season != season:
                continue
            if competition and m.competition != competition:
                continue
            is_home = m.home_key == key
            if venue == "home" and not is_home:
                continue
            if venue == "away" and is_home:
                continue
            played += 1
            for_, against = (m.home_goal, m.away_goal) if is_home else (m.away_goal, m.home_goal)
            gf += for_
            ga += against
            if for_ > against:
                wins += 1
            elif against > for_:
                losses += 1
            else:
                draws += 1
        points = wins * WIN_POINTS + draws * DRAW_POINTS
        return {
            "team": self.label(key),
            "season": season, "competition": competition, "venue": venue,
            "played": played, "wins": wins, "draws": draws, "losses": losses,
            "goals_for": gf, "goals_against": ga, "goal_difference": gf - ga,
            "points": points,
            "win_rate": round(wins / played * 100, 1) if played else 0.0,
        }

    def compare_teams(self, team_a: str, team_b: str,
                      season: Optional[int] = None,
                      competition: Optional[str] = None) -> dict:
        return {
            "head_to_head": self.head_to_head(team_a, team_b, competition),
            "team_a_record": self.team_record(team_a, season=season, competition=competition),
            "team_b_record": self.team_record(team_b, season=season, competition=competition),
        }

    # ------------------------------------------------------------------ #
    # 3. Player queries                                                  #
    # ------------------------------------------------------------------ #
    def find_players(self, *, name: Optional[str] = None,
                     nationality: Optional[str] = None,
                     club: Optional[str] = None, position: Optional[str] = None,
                     min_overall: Optional[int] = None,
                     sort_by: str = "overall", limit: Optional[int] = 25) -> list[Player]:
        name_l = name.lower() if name else None
        nat_l = nationality.lower() if nationality else None
        pos_l = position.lower() if position else None
        club_key = normalize_key(club) if club else None

        # Use the most selective index available as the candidate pool.
        if club_key and club_key in self.club_players:
            pool = self.club_players[club_key]
        elif nationality and nationality in self.nation_players:
            pool = self.nation_players[nationality]
        else:
            pool = self.ds.players

        out = []
        for p in pool:
            if name_l and name_l not in p.name.lower():
                continue
            if nat_l and nat_l not in p.nationality.lower():
                continue
            if club_key and p.club_key != club_key:
                continue
            if pos_l and pos_l != p.position.lower():
                continue
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            out.append(p)

        if sort_by == "name":
            out.sort(key=lambda p: p.name.lower())
        elif sort_by == "age":
            out.sort(key=lambda p: (p.age is None, p.age or 0))
        elif sort_by == "potential":
            out.sort(key=lambda p: (p.potential is None, -(p.potential or 0)))
        else:  # overall (default), highest first
            out.sort(key=lambda p: (p.overall is None, -(p.overall or 0)))
        return out[:limit] if limit else out

    def players_by_club(self, club: str, limit: Optional[int] = 25) -> list[Player]:
        return self.find_players(club=club, sort_by="overall", limit=limit)

    def top_brazilian_players(self, limit: int = 10) -> list[Player]:
        return self.find_players(nationality="Brazil", sort_by="overall", limit=limit)

    # ------------------------------------------------------------------ #
    # 4. Competition queries                                             #
    # ------------------------------------------------------------------ #
    def standings(self, competition: str, season: int) -> list[dict]:
        """Compute a league table from match results (3 pts win, 1 draw)."""
        rows: dict[str, dict] = {}
        for m in self.comp_matches.get(competition, []):
            if m.season != season or not m.has_score:
                continue
            for key, for_, against in (
                (m.home_key, m.home_goal, m.away_goal),
                (m.away_key, m.away_goal, m.home_goal),
            ):
                if not key:
                    continue
                r = rows.setdefault(key, {
                    "team": self.label(key), "played": 0, "wins": 0,
                    "draws": 0, "losses": 0, "goals_for": 0,
                    "goals_against": 0, "points": 0,
                })
                r["played"] += 1
                r["goals_for"] += for_
                r["goals_against"] += against
                if for_ > against:
                    r["wins"] += 1
                    r["points"] += WIN_POINTS
                elif against > for_:
                    r["losses"] += 1
                else:
                    r["draws"] += 1
                    r["points"] += DRAW_POINTS
        table = list(rows.values())
        for r in table:
            r["goal_difference"] = r["goals_for"] - r["goals_against"]
        table.sort(key=lambda r: (r["points"], r["goal_difference"],
                                  r["goals_for"], r["wins"]), reverse=True)
        for i, r in enumerate(table, 1):
            r["position"] = i
        return table

    def champion(self, competition: str, season: int) -> Optional[dict]:
        table = self.standings(competition, season)
        return table[0] if table else None

    # ------------------------------------------------------------------ #
    # 5. Statistical analysis                                            #
    # ------------------------------------------------------------------ #
    def _stat_pool(self, competition: Optional[str], season: Optional[int]) -> list[Match]:
        pool = self.comp_matches.get(competition, []) if competition else self.ds.matches
        return [m for m in pool
                if m.has_score
                and (season is None or m.season == season)]

    def average_goals(self, competition: Optional[str] = None,
                      season: Optional[int] = None) -> dict:
        pool = self._stat_pool(competition, season)
        n = len(pool)
        total = sum(m.total_goals for m in pool)
        home_wins = sum(1 for m in pool if m.winner == "home")
        away_wins = sum(1 for m in pool if m.winner == "away")
        draws = sum(1 for m in pool if m.winner == "draw")
        return {
            "competition": competition, "season": season,
            "matches": n,
            "total_goals": total,
            "avg_goals_per_match": round(total / n, 2) if n else 0.0,
            "home_win_rate": round(home_wins / n * 100, 1) if n else 0.0,
            "away_win_rate": round(away_wins / n * 100, 1) if n else 0.0,
            "draw_rate": round(draws / n * 100, 1) if n else 0.0,
        }

    def biggest_wins(self, competition: Optional[str] = None,
                     season: Optional[int] = None, limit: int = 10) -> list[Match]:
        pool = self._stat_pool(competition, season)
        pool = sorted(pool, key=lambda m: (abs(m.home_goal - m.away_goal),
                                           m.total_goals), reverse=True)
        return pool[:limit]

    def best_record(self, *, venue: str = "all", competition: Optional[str] = None,
                    season: Optional[int] = None, min_matches: int = 10,
                    by: str = "win_rate", limit: int = 10) -> list[dict]:
        """Rank teams by record (win_rate or points). venue: all/home/away."""
        if competition:
            keys = {m.home_key for m in self.comp_matches.get(competition, [])}
            keys |= {m.away_key for m in self.comp_matches.get(competition, [])}
        else:
            keys = set(self.team_matches)
        recs = []
        for k in keys:
            if not k:
                continue
            r = self.team_record(k, season=season, competition=competition, venue=venue)
            if r["played"] >= min_matches:
                recs.append(r)
        recs.sort(key=lambda r: (r.get(by, 0), r["points"], r["goal_difference"]),
                  reverse=True)
        return recs[:limit]
