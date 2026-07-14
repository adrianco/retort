"""
Context
=======
Module: brazilian_soccer_mcp.knowledge_graph
Purpose: The in-memory knowledge graph and the query API used by both the MCP
server and the BDD test-suite.

The graph stores every :class:`Match` and :class:`Player` and builds indexes
(team -> matches, team-key -> canonical name, club -> players, nationality ->
players) so the success-criteria response times (<2s simple, <5s aggregate) are
met without a database.  The class is the single source of truth for queries -
``server.py`` is a thin MCP wrapper over these methods.

Design notes
------------
* Teams are matched by accent/case-insensitive *team keys* (see
  :mod:`brazilian_soccer_mcp.normalize`), so "Palmeiras-SP" and "Palmeiras"
  resolve to the same node.
* Competitions are matched with a fuzzy normaliser so "brasileirao",
  "Serie A" and "Brasileirão Série A" all work.
* Standings/champions are *calculated* from match results using the standard
  3-1-0 points system.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List, Optional

from .data_loader import load_dataset
from .models import Match, Player
from .normalize import clean_team_name, extract_state, normalize_text, team_key


class KnowledgeGraph:
    """In-memory graph of Brazilian soccer matches and players."""

    # Lower number = more authoritative source for a (competition, season).
    _SOURCE_PRIORITY = {
        "Brasileirao_Matches.csv": 0,
        "Brazilian_Cup_Matches.csv": 0,
        "Libertadores_Matches.csv": 0,
        "novo_campeonato_brasileiro.csv": 1,
        "BR-Football-Dataset.csv": 2,
    }

    def __init__(self, matches: List[Match], players: List[Player]):
        self.raw_match_count = len(matches)
        self.matches = self._select_canonical(matches)
        self.players = players
        self._build_indexes()

    @staticmethod
    def _competition_family(competition: str) -> str:
        """Group differently-labelled-but-equivalent competitions.

        The same competition is spelled differently across files - e.g.
        ``"Brasileirão Série A"`` (Brasileirao_Matches / novo) and ``"Serie A"``
        (BR-Football).  Both map to the family ``"serie_a"`` so they can be
        recognised as overlapping.
        """
        c = normalize_text(competition)
        if "serie a" in c or "brasileirao" in c or "brasileiro" in c:
            return "serie_a"
        if "serie b" in c:
            return "serie_b"
        if "serie c" in c:
            return "serie_c"
        if "copa do brasil" in c or c == "cup":
            return "copa_do_brasil"
        if "libertadores" in c:
            return "libertadores"
        return c or "unknown"

    @classmethod
    def _select_canonical(cls, matches: List[Match]) -> List[Match]:
        """Keep exactly one source file per (competition-family, season).

        The Série A and Copa do Brasil fixtures appear in several CSVs.  They
        cannot be merged row-by-row because ``BR-Football-Dataset.csv`` shifts
        many kickoff dates by a day (timezone), so date-based dedup misses them
        and standings/head-to-head get inflated 2-3x.

        Instead, for each competition-family + season we pick the single most
        authoritative source that covers it (see ``_SOURCE_PRIORITY``) and drop
        the duplicate copies from the other files.  Different seasons and
        competitions still draw from whichever file covers them, so all six
        files contribute data overall - just never double-counted for the same
        slice.
        """
        # Which sources cover each (family, season)?
        present: Dict[tuple, set] = defaultdict(set)
        for m in matches:
            present[(cls._competition_family(m.competition), m.season)].add(m.source)
        chosen: Dict[tuple, int] = {
            slice_key: min(cls._SOURCE_PRIORITY.get(s, 99) for s in srcs)
            for slice_key, srcs in present.items()
        }
        out: List[Match] = []
        for m in matches:
            slice_key = (cls._competition_family(m.competition), m.season)
            if cls._SOURCE_PRIORITY.get(m.source, 99) == chosen[slice_key]:
                out.append(m)
        return out

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #
    @classmethod
    def load(cls, data_dir: Optional[str] = None) -> "KnowledgeGraph":
        if data_dir is None:
            matches, players = load_dataset()
        else:
            matches, players = load_dataset(data_dir)
        return cls(matches, players)

    def _build_indexes(self) -> None:
        # Step 1: find ambiguous base names - a base shared by two or more
        # distinct non-empty states (Atletico-MG vs Atletico-PR).  Only those
        # keep the state in their canonical id; everything else collapses to the
        # base so "Palmeiras-SP" and "Palmeiras" unify.
        base_states: Dict[str, set] = defaultdict(set)
        for m in self.matches:
            base_states[m.home_base].add(m.home_state)
            base_states[m.away_base].add(m.away_state)
        self._ambiguous_bases = {
            base for base, states in base_states.items()
            if len([s for s in states if s]) >= 2
        }

        # Step 2: assign each match home/away a canonical team id.
        self.matches_by_team: Dict[str, List[Match]] = defaultdict(list)
        name_votes: Dict[str, Counter] = defaultdict(Counter)
        # Record which states are seen for each base, for query resolution.
        self._base_ids: Dict[str, set] = defaultdict(set)
        # Ids that carry a state qualifier (so display keeps the suffix).
        stateful_ids: set = set()

        for m in self.matches:
            m.home_id = self._canonical_id(m.home_base, m.home_state)
            m.away_id = self._canonical_id(m.away_base, m.away_state)
            self.matches_by_team[m.home_id].append(m)
            self.matches_by_team[m.away_id].append(m)
            self._base_ids[m.home_base].add(m.home_id)
            self._base_ids[m.away_base].add(m.away_id)
            if m.home_id != m.home_base:
                stateful_ids.add(m.home_id)
            if m.away_id != m.away_base:
                stateful_ids.add(m.away_id)
            if m.home_team:
                name_votes[m.home_id][m.home_team.strip()] += 1
            if m.away_team:
                name_votes[m.away_id][m.away_team.strip()] += 1

        self.canonical_name: Dict[str, str] = {}
        for team_id, votes in name_votes.items():
            # Prefer the most common spelling; ties broken by shortest name.
            best = sorted(votes.items(), key=lambda kv: (-kv[1], len(kv[0])))
            raw = best[0][0] if best else team_id
            # Drop the state suffix for unambiguous teams (Flamengo-RJ ->
            # Flamengo); keep it where it is the only distinguisher.
            self.canonical_name[team_id] = raw if team_id in stateful_ids else clean_team_name(raw)

        # Player indexes.
        self.players_by_club: Dict[str, List[Player]] = defaultdict(list)
        self.players_by_nationality: Dict[str, List[Player]] = defaultdict(list)
        for p in self.players:
            self.players_by_club[team_key(p.club)].append(p)
            self.players_by_nationality[normalize_text(p.nationality)].append(p)

    def _canonical_id(self, base: str, state: str) -> str:
        """Canonical team id: base, plus state only when the base is ambiguous."""
        if base in self._ambiguous_bases and state:
            return f"{base} {state}"
        return base

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def display_name(self, team_id: str) -> str:
        return self.canonical_name.get(team_id, team_id)

    def resolve_team(self, name: str) -> Optional[str]:
        """Resolve a user supplied name to a known canonical team id, or ``None``.

        Handles state suffixes ("Atletico-MG"), bare names ("Flamengo") and
        partial names ("Sao Paulo"), preferring the most-played team on ties.
        """
        if not name:
            return None
        base = team_key(name)
        state = extract_state(name)

        # Exact canonical id (handles both ambiguous and unambiguous bases).
        candidate = self._canonical_id(base, state)
        if candidate in self.matches_by_team:
            return candidate
        # A bare ambiguous base ("Atletico"): pick its most-played variant.
        if base in self._base_ids and self._base_ids[base]:
            return max(self._base_ids[base], key=lambda i: len(self.matches_by_team[i]))
        # Fall back to a partial match where the query is part of a team name
        # ("Inter" -> "internacional").  Require a non-trivial query so short or
        # nonsense inputs do not match arbitrary teams.
        if len(base) >= 3:
            candidates = [k for k in self.matches_by_team if base in k]
            if candidates:
                return max(candidates, key=lambda k: len(self.matches_by_team[k]))
        return None

    @staticmethod
    def _competition_matches(target: str, competition: str) -> bool:
        """Fuzzy competition matcher."""
        t = normalize_text(target)
        c = normalize_text(competition)
        if not t:
            return True
        aliases = {
            "brasileirao": ["brasileirao serie a", "serie a"],
            "brasileiro": ["brasileirao serie a", "serie a"],
            "serie a": ["serie a", "brasileirao serie a"],
            "libertadores": ["copa libertadores"],
            "copa do brasil": ["copa do brasil"],
            "cup": ["copa do brasil"],
        }
        if t in c or c in t:
            return True
        for alias_key, targets in aliases.items():
            if alias_key in t:
                if any(normalize_text(x) in c or c in normalize_text(x) for x in targets):
                    return True
        return False

    # ------------------------------------------------------------------ #
    # 1. Match queries
    # ------------------------------------------------------------------ #
    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "either",  # 'home', 'away' or 'either'
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Match]:
        """Return matches filtered by the supplied criteria, newest first."""
        from .normalize import parse_date

        team_k = self.resolve_team(team) if team else None
        opp_k = self.resolve_team(opponent) if opponent else None
        d_from = parse_date(date_from) if date_from else None
        d_to = parse_date(date_to) if date_to else None

        if team_k is not None:
            pool = self.matches_by_team[team_k]
        else:
            pool = self.matches

        results = []
        for m in pool:
            if team_k is not None:
                if venue == "home" and m.home_id != team_k:
                    continue
                if venue == "away" and m.away_id != team_k:
                    continue
                if venue == "either" and not m.involves(team_k):
                    continue
            if opp_k is not None and not m.involves(opp_k):
                continue
            if season is not None and m.season != season:
                continue
            if competition and not self._competition_matches(competition, m.competition):
                continue
            if d_from and (m.match_date is None or m.match_date < d_from):
                continue
            if d_to and (m.match_date is None or m.match_date > d_to):
                continue
            results.append(m)

        results.sort(
            key=lambda m: (m.match_date is not None, m.match_date or _MIN_DATE),
            reverse=True,
        )
        if limit is not None:
            results = results[:limit]
        return results

    # ------------------------------------------------------------------ #
    # 2. Team queries / statistics
    # ------------------------------------------------------------------ #
    def team_stats(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "all",  # 'all', 'home', 'away'
    ) -> Optional[dict]:
        """Win/draw/loss + goals record for a team, optionally filtered."""
        team_k = self.resolve_team(team)
        if team_k is None:
            return None

        wins = draws = losses = gf = ga = played = 0
        for m in self.matches_by_team[team_k]:
            if season is not None and m.season != season:
                continue
            if competition and not self._competition_matches(competition, m.competition):
                continue
            if not m.has_score:
                continue
            is_home = m.home_id == team_k
            if venue == "home" and not is_home:
                continue
            if venue == "away" and is_home:
                continue
            played += 1
            if is_home:
                scored, conceded = m.home_goal, m.away_goal
            else:
                scored, conceded = m.away_goal, m.home_goal
            gf += scored
            ga += conceded
            if scored > conceded:
                wins += 1
            elif scored < conceded:
                losses += 1
            else:
                draws += 1

        win_rate = round(100.0 * wins / played, 1) if played else 0.0
        return {
            "team": self.display_name(team_k),
            "season": season,
            "competition": competition,
            "venue": venue,
            "played": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": gf,
            "goals_against": ga,
            "goal_difference": gf - ga,
            "points": wins * 3 + draws,
            "win_rate": win_rate,
        }

    def head_to_head(self, team1: str, team2: str) -> Optional[dict]:
        """Aggregate head-to-head record between two teams across all data."""
        k1 = self.resolve_team(team1)
        k2 = self.resolve_team(team2)
        if k1 is None or k2 is None:
            return None

        t1_wins = t2_wins = draws = 0
        t1_goals = t2_goals = 0
        matches = []
        for m in self.matches_by_team[k1]:
            if not m.involves(k2):
                continue
            matches.append(m)
            if not m.has_score:
                continue
            if m.home_id == k1:
                g1, g2 = m.home_goal, m.away_goal
            else:
                g1, g2 = m.away_goal, m.home_goal
            t1_goals += g1
            t2_goals += g2
            if g1 > g2:
                t1_wins += 1
            elif g2 > g1:
                t2_wins += 1
            else:
                draws += 1

        matches.sort(
            key=lambda m: (m.match_date is not None, m.match_date or _MIN_DATE),
            reverse=True,
        )
        return {
            "team1": self.display_name(k1),
            "team2": self.display_name(k2),
            "total_matches": len(matches),
            "team1_wins": t1_wins,
            "team2_wins": t2_wins,
            "draws": draws,
            "team1_goals": t1_goals,
            "team2_goals": t2_goals,
            "matches": matches,
        }

    # ------------------------------------------------------------------ #
    # 3. Player queries
    # ------------------------------------------------------------------ #
    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        sort_by: str = "overall",  # 'overall', 'potential', 'age', 'name'
        limit: Optional[int] = 25,
    ) -> List[Player]:
        """Filter the FIFA player database and return sorted matches."""
        name_n = normalize_text(name) if name else None
        nat_n = normalize_text(nationality) if nationality else None
        club_k = team_key(club) if club else None
        pos_n = normalize_text(position) if position else None

        # Narrow the search pool using indexes when possible.
        if nat_n and nat_n in self.players_by_nationality:
            pool = self.players_by_nationality[nat_n]
        elif club_k and club_k in self.players_by_club:
            pool = self.players_by_club[club_k]
        else:
            pool = self.players

        results = []
        for p in pool:
            if name_n and name_n not in normalize_text(p.name):
                continue
            if nat_n and nat_n not in normalize_text(p.nationality):
                continue
            if club_k:
                p_club = team_key(p.club)
                # Match when the query is a substring of the club key (or vice
                # versa), so "Flamengo" matches "Flamengo" and "Sao Paulo"
                # matches "Sao Paulo FC".
                if club_k not in p_club and p_club not in club_k:
                    continue
            if pos_n and pos_n not in normalize_text(p.position):
                continue
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            results.append(p)

        reverse = sort_by in ("overall", "potential")
        keymap = {
            "overall": lambda p: p.overall or 0,
            "potential": lambda p: p.potential or 0,
            "age": lambda p: p.age or 0,
            "name": lambda p: normalize_text(p.name),
        }
        results.sort(key=keymap.get(sort_by, keymap["overall"]), reverse=reverse)
        if limit is not None:
            results = results[:limit]
        return results

    def find_player(self, name: str) -> Optional[Player]:
        """Return the best single match for a player name (highest rated)."""
        matches = self.search_players(name=name, sort_by="overall", limit=None)
        if not matches:
            return None
        # Prefer an exact (accent-insensitive) name match if present.
        target = normalize_text(name)
        exact = [p for p in matches if normalize_text(p.name) == target]
        pool = exact or matches
        return max(pool, key=lambda p: p.overall or 0)

    def players_by_brazilian_clubs(self, min_overall: Optional[int] = None) -> Dict[str, List[Player]]:
        """Group Brazilian-national players by the (Brazilian) clubs they play for."""
        brazilians = self.players_by_nationality.get("brazil", [])
        grouped: Dict[str, List[Player]] = defaultdict(list)
        for p in brazilians:
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            if p.club:
                grouped[p.club].append(p)
        return grouped

    # ------------------------------------------------------------------ #
    # 4. Competition queries (calculated standings)
    # ------------------------------------------------------------------ #
    def standings(
        self,
        season: int,
        competition: str = "Brasileirão",
    ) -> List[dict]:
        """Compute a league table from match results (3-1-0 points)."""
        table: Dict[str, dict] = {}

        def row(k: str) -> dict:
            if k not in table:
                table[k] = {
                    "team": self.display_name(k),
                    "played": 0, "wins": 0, "draws": 0, "losses": 0,
                    "goals_for": 0, "goals_against": 0, "points": 0,
                }
            return table[k]

        for m in self.matches:
            if m.season != season:
                continue
            if not self._competition_matches(competition, m.competition):
                continue
            if not m.has_score:
                continue
            h, a = row(m.home_id), row(m.away_id)
            h["played"] += 1
            a["played"] += 1
            h["goals_for"] += m.home_goal
            h["goals_against"] += m.away_goal
            a["goals_for"] += m.away_goal
            a["goals_against"] += m.home_goal
            if m.home_goal > m.away_goal:
                h["wins"] += 1; a["losses"] += 1; h["points"] += 3
            elif m.home_goal < m.away_goal:
                a["wins"] += 1; h["losses"] += 1; a["points"] += 3
            else:
                h["draws"] += 1; a["draws"] += 1
                h["points"] += 1; a["points"] += 1

        rows = list(table.values())
        for r in rows:
            r["goal_difference"] = r["goals_for"] - r["goals_against"]
        rows.sort(
            key=lambda r: (r["points"], r["goal_difference"], r["goals_for"]),
            reverse=True,
        )
        for i, r in enumerate(rows, start=1):
            r["position"] = i
        return rows

    def champion(self, season: int, competition: str = "Brasileirão") -> Optional[dict]:
        table = self.standings(season, competition)
        return table[0] if table else None

    # ------------------------------------------------------------------ #
    # 5. Statistical analysis
    # ------------------------------------------------------------------ #
    def competition_stats(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> dict:
        """Aggregate statistics over a slice of matches."""
        scored = []
        home_wins = away_wins = draws = 0
        for m in self.matches:
            if competition and not self._competition_matches(competition, m.competition):
                continue
            if season is not None and m.season != season:
                continue
            if not m.has_score:
                continue
            scored.append(m)
            if m.home_goal > m.away_goal:
                home_wins += 1
            elif m.away_goal > m.home_goal:
                away_wins += 1
            else:
                draws += 1

        n = len(scored)
        total_goals = sum(m.total_goals for m in scored)
        return {
            "competition": competition,
            "season": season,
            "matches_with_score": n,
            "total_goals": total_goals,
            "avg_goals_per_match": round(total_goals / n, 2) if n else 0.0,
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": round(100.0 * home_wins / n, 1) if n else 0.0,
            "away_win_rate": round(100.0 * away_wins / n, 1) if n else 0.0,
            "draw_rate": round(100.0 * draws / n, 1) if n else 0.0,
        }

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> List[Match]:
        """Matches with the largest goal margin, biggest first."""
        pool = []
        for m in self.matches:
            if competition and not self._competition_matches(competition, m.competition):
                continue
            if season is not None and m.season != season:
                continue
            if m.has_score:
                pool.append(m)
        pool.sort(
            key=lambda m: (abs(m.home_goal - m.away_goal), m.total_goals),
            reverse=True,
        )
        return pool[:limit]

    def best_records(
        self,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "all",
        metric: str = "win_rate",  # 'win_rate' or 'points'
        min_played: int = 5,
        limit: int = 10,
    ) -> List[dict]:
        """Rank teams by win rate / points (e.g. best home record)."""
        keys = set()
        for m in self.matches:
            if season is not None and m.season != season:
                continue
            if competition and not self._competition_matches(competition, m.competition):
                continue
            keys.add(m.home_id)
            keys.add(m.away_id)

        rows = []
        for k in keys:
            stats = self.team_stats(
                self.display_name(k), season=season,
                competition=competition, venue=venue,
            )
            if stats and stats["played"] >= min_played:
                rows.append(stats)
        rows.sort(key=lambda s: (s.get(metric, 0), s["played"]), reverse=True)
        return rows[:limit]

    # ------------------------------------------------------------------ #
    # Meta
    # ------------------------------------------------------------------ #
    def dataset_summary(self) -> dict:
        by_source = Counter(m.source for m in self.matches)
        by_competition = Counter(m.competition for m in self.matches)
        seasons = [m.season for m in self.matches if m.season]
        return {
            "total_matches": len(self.matches),
            "raw_match_rows": self.raw_match_count,
            "total_players": len(self.players),
            "distinct_teams": len(self.matches_by_team),
            "matches_by_source": dict(by_source),
            "matches_by_competition": dict(by_competition),
            "season_range": [min(seasons), max(seasons)] if seasons else None,
            "brazilian_players": len(self.players_by_nationality.get("brazil", [])),
        }


# A sentinel "minimum" date used purely for sorting matches that have no date.
from datetime import date as _date  # noqa: E402

_MIN_DATE = _date.min
