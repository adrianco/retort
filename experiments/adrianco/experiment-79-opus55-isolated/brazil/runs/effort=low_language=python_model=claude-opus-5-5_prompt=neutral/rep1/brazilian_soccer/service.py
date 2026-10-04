"""Query layer: everything the MCP tools can ask of the data."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from pathlib import Path

from .data import DEFAULT_DATA_DIR, Match, load_matches, load_players
from .normalize import (
    CLUB_STATE, LEAGUES,
    TeamRegistry, fold, known_club, normalize_competition, parse_date,
)


class QueryError(ValueError):
    """A query could not be answered (unknown team, bad date, ...)."""


# Traditional rivalries (clássicos), by canonical team name.
DERBIES = {
    frozenset(pair): name
    for name, pair in [
        ("Fla-Flu", ("Flamengo", "Fluminense")),
        ("Clássico dos Milhões", ("Flamengo", "Vasco da Gama")),
        ("Clássico da Rivalidade", ("Flamengo", "Botafogo")),
        ("Clássico dos Gigantes", ("Fluminense", "Vasco da Gama")),
        ("Clássico Vovô", ("Fluminense", "Botafogo")),
        ("Clássico da Amizade", ("Botafogo", "Vasco da Gama")),
        ("Derby Paulista", ("Corinthians", "Palmeiras")),
        ("Majestoso", ("Corinthians", "São Paulo")),
        ("Clássico Alvinegro", ("Corinthians", "Santos")),
        ("Choque-Rei", ("Palmeiras", "São Paulo")),
        ("Clássico da Saudade", ("Palmeiras", "Santos")),
        ("San-São", ("Santos", "São Paulo")),
        ("Gre-Nal", ("Grêmio", "Internacional")),
        ("Clássico Mineiro", ("Atlético Mineiro", "Cruzeiro")),
        ("Ba-Vi", ("Bahia", "Vitória")),
        ("Atletiba", ("Athletico Paranaense", "Coritiba")),
        ("Clássico dos Clássicos", ("Sport Recife", "Náutico")),
        ("Clássico das Multidões", ("Sport Recife", "Santa Cruz")),
        ("Clássico das Emoções", ("Náutico", "Santa Cruz")),
        ("Clássico-Rei", ("Ceará", "Fortaleza")),
        ("Clássico de Florianópolis", ("Avaí", "Figueirense")),
        ("Re-Pa", ("Remo", "Paysandu")),
        ("Derby Campineiro", ("Ponte Preta", "Guarani")),
        ("Clássico das Multidões (AL)", ("CRB", "CSA")),
    ]
}

POSITION_GROUPS = {
    "goalkeeper": {"GK"},
    "defender": {"CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"},
    "midfielder": {"CM", "LCM", "RCM", "CDM", "LDM", "RDM", "CAM", "LAM", "RAM", "LM", "RM"},
    "forward": {"ST", "LS", "RS", "CF", "LF", "RF", "LW", "RW"},
}
_POSITION_WORDS = {
    "goalkeeper": "goalkeeper", "keeper": "goalkeeper", "goleiro": "goalkeeper",
    "defender": "defender", "defence": "defender", "defense": "defender", "zagueiro": "defender",
    "midfielder": "midfielder", "midfield": "midfielder", "meia": "midfielder",
    "forward": "forward", "attacker": "forward", "striker": "forward", "atacante": "forward",
}


def _new_record() -> dict:
    return {"matches": 0, "wins": 0, "draws": 0, "losses": 0,
            "goals_for": 0, "goals_against": 0}


def _add_result(record: dict, goals_for: int, goals_against: int) -> None:
    record["matches"] += 1
    record["goals_for"] += goals_for
    record["goals_against"] += goals_against
    if goals_for > goals_against:
        record["wins"] += 1
    elif goals_for == goals_against:
        record["draws"] += 1
    else:
        record["losses"] += 1


def _finish_record(record: dict) -> dict:
    played = record["matches"]
    record["goal_difference"] = record["goals_for"] - record["goals_against"]
    record["points"] = 3 * record["wins"] + record["draws"]
    record["win_rate"] = round(100 * record["wins"] / played, 1) if played else 0.0
    record["points_per_match"] = round(record["points"] / played, 2) if played else 0.0
    return record


def _date_key(match: Match):
    return (match.date is not None, match.date or parse_date("1900-01-01"))


class SoccerData:
    """In-memory knowledge base over the match and player datasets."""

    def __init__(self, matches: list[Match], registry: TeamRegistry, players: list[dict],
                 load_report: dict | None = None) -> None:
        self.matches = matches
        self.registry = registry
        self.players = players
        self.load_report = load_report or {}
        self._inferred_finals: set[tuple[str, int]] = set()
        self._tag_unlabelled_finals()

    def _tag_unlabelled_finals(self) -> None:
        """Label the final of knockout seasons whose rows carry no stage.

        The Copa do Brasil files only number the rounds, so the final is taken
        to be the last fixture of the season plus its reverse leg.
        """
        seasons = defaultdict(list)
        for m in self.matches:
            if m.competition not in LEAGUES:
                seasons[(m.competition, m.season)].append(m)
        for key, matches in seasons.items():
            dated = [m for m in matches if m.date]
            if any(m.stage for m in matches) or not dated:
                continue
            last = max(dated, key=lambda m: m.date)
            pair = {last.home, last.away}
            for m in dated:
                if {m.home, m.away} == pair and last.date - m.date <= timedelta(days=45):
                    m.stage = "final"
            self._inferred_finals.add(key)

    @classmethod
    def load(cls, data_dir: str | Path = DEFAULT_DATA_DIR) -> "SoccerData":
        data_dir = Path(data_dir)
        if not data_dir.is_dir():
            raise FileNotFoundError(f"Data directory not found: {data_dir}")
        matches, registry, report = load_matches(data_dir)
        return cls(matches, registry, load_players(data_dir), report)

    # ------------------------------------------------------------------ #
    # Argument resolution
    # ------------------------------------------------------------------ #

    def find_teams(self, query: str) -> list[str]:
        return self.registry.find(query)

    def resolve_team(self, query: str) -> str:
        """Resolve a query to exactly one team or raise a helpful error."""
        if not query or not str(query).strip():
            raise QueryError("A team name is required.")
        found = self.find_teams(str(query))
        if not found:
            raise QueryError(f"No team matching {query!r} was found in the match data.")
        if len(found) > 1:
            shown = ", ".join(found[:10]) + (", ..." if len(found) > 10 else "")
            raise QueryError(f"Team {query!r} is ambiguous. Did you mean one of: {shown}?")
        return found[0]

    @staticmethod
    def _competition(query) -> str | None:
        try:
            return normalize_competition(query)
        except ValueError as exc:
            raise QueryError(str(exc)) from None

    @staticmethod
    def _season(value) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(str(value).strip())
        except ValueError:
            raise QueryError(f"Season must be a year, got {value!r}.") from None

    @staticmethod
    def _date(value, label: str):
        if value is None or value == "":
            return None
        parsed = parse_date(value)
        if parsed is None:
            raise QueryError(f"Could not parse {label} {value!r}; use YYYY-MM-DD or DD/MM/YYYY.")
        return parsed

    @staticmethod
    def _venue(value) -> str:
        venue = fold(str(value or "either"))
        if venue in ("either", "all", "any", "both", ""):
            return "either"
        if venue in ("home", "away"):
            return venue
        raise QueryError(f"venue must be 'home', 'away' or 'either', got {value!r}.")

    # ------------------------------------------------------------------ #
    # Matches
    # ------------------------------------------------------------------ #

    def find_matches(self, team=None, opponent=None, competition=None, season=None,
                     date_from=None, date_to=None, venue="either", stage=None) -> list[Match]:
        """Matches filtered by any combination of criteria, newest first.

        ``venue`` is relative to ``team``.  ``team``/``opponent`` may match
        several clubs (e.g. "Atlético"); an unknown name raises ``QueryError``.
        """
        competition = self._competition(competition)
        season = self._season(season)
        start, end = self._date(date_from, "date_from"), self._date(date_to, "date_to")
        if start and end and start > end:
            raise QueryError("date_from must not be after date_to.")
        venue = self._venue(venue)
        teams = others = None
        if team:
            teams = set(self.find_teams(team))
            if not teams:
                raise QueryError(f"No team matching {team!r} was found in the match data.")
        if opponent:
            others = set(self.find_teams(opponent))
            if not others:
                raise QueryError(f"No team matching {opponent!r} was found in the match data.")
        if others and not teams:
            teams, others = others, None
        stage_query = fold(str(stage)) if stage not in (None, "") else None

        result = []
        for m in self.matches:
            if competition and m.competition != competition:
                continue
            if season is not None and m.season != season:
                continue
            if (start or end) and (m.date is None or (start and m.date < start)
                                   or (end and m.date > end)):
                continue
            if stage_query is not None and stage_query not in (
                    fold(m.stage or ""), fold(m.round or "")):
                continue
            if teams is not None:
                home_ok = m.home in teams and venue != "away"
                away_ok = m.away in teams and venue != "home"
                if others is not None:
                    home_ok = home_ok and m.away in others
                    away_ok = away_ok and m.home in others
                if not (home_ok or away_ok):
                    continue
            result.append(m)
        result.sort(key=_date_key, reverse=True)
        return result

    def head_to_head(self, team_a, team_b, competition=None, season=None) -> dict:
        a, b = self.resolve_team(team_a), self.resolve_team(team_b)
        if a == b:
            raise QueryError("Head-to-head needs two different teams.")
        matches = [m for m in self.find_matches(competition=competition, season=season)
                   if m.involves(a) and m.involves(b)]
        record = _new_record()
        for m in matches:
            mine, theirs = (m.home_goals, m.away_goals) if m.home == a else (m.away_goals, m.home_goals)
            _add_result(record, mine, theirs)
        return {
            "team_a": a, "team_b": b, "derby": DERBIES.get(frozenset((a, b))),
            "matches": matches, "total": len(matches),
            "wins_a": record["wins"], "wins_b": record["losses"], "draws": record["draws"],
            "goals_a": record["goals_for"], "goals_b": record["goals_against"],
        }

    def team_stats(self, team, season=None, competition=None, venue="either") -> dict:
        """Win/draw/loss record and goals for a team, with a per-competition split."""
        name = self.resolve_team(team)
        venue = self._venue(venue)
        matches = [m for m in self.find_matches(competition=competition, season=season)
                   if (m.home == name and venue != "away") or (m.away == name and venue != "home")]
        total, by_competition = _new_record(), defaultdict(_new_record)
        for m in matches:
            mine, theirs = (m.home_goals, m.away_goals) if m.home == name else (m.away_goals, m.home_goals)
            _add_result(total, mine, theirs)
            _add_result(by_competition[m.competition], mine, theirs)
        return {
            "team": name, "season": self._season(season),
            "competition": self._competition(competition), "venue": venue,
            **_finish_record(total),
            "by_competition": {c: _finish_record(r) for c, r in sorted(by_competition.items())},
        }

    def team_competitions(self, team) -> dict:
        """Competitions (and seasons) a team appears in."""
        name = self.resolve_team(team)
        seasons = defaultdict(set)
        counts = defaultdict(int)
        for m in self.matches:
            if m.involves(name):
                seasons[m.competition].add(m.season)
                counts[m.competition] += 1
        return {"team": name,
                "competitions": {c: {"matches": counts[c], "seasons": sorted(s)}
                                 for c, s in sorted(seasons.items())}}

    def derbies(self, season=None, competition=None) -> list[tuple[str, Match]]:
        """Matches between traditional rivals, newest first."""
        found = []
        for m in self.find_matches(season=season, competition=competition):
            name = DERBIES.get(frozenset((m.home, m.away)))
            if name:
                found.append((name, m))
        return found

    def biggest_wins(self, competition=None, season=None, team=None, limit=10) -> list[Match]:
        matches = [m for m in self.find_matches(team=team, competition=competition, season=season)
                   if m.margin > 0]
        matches.sort(key=lambda m: (-m.margin, -m.total_goals, m.date.toordinal() if m.date else 0))
        return matches[:max(0, int(limit))]

    # ------------------------------------------------------------------ #
    # Competitions
    # ------------------------------------------------------------------ #

    def seasons(self, competition=None) -> dict[str, list[int]]:
        competition = self._competition(competition)
        found = defaultdict(set)
        for m in self.matches:
            if competition is None or m.competition == competition:
                found[m.competition].add(m.season)
        return {c: sorted(s) for c, s in sorted(found.items())}

    def table(self, competition=None, season=None, venue="either") -> list[dict]:
        """Per-team records, ranked by points, wins, goal difference, goals for."""
        venue = self._venue(venue)
        records = defaultdict(_new_record)
        for m in self.find_matches(competition=competition, season=season):
            if venue != "away":
                _add_result(records[m.home], m.home_goals, m.away_goals)
            if venue != "home":
                _add_result(records[m.away], m.away_goals, m.home_goals)
        rows = [{"team": team, **_finish_record(r)} for team, r in records.items()]
        rows.sort(key=lambda r: (-r["points"], -r["wins"], -r["goal_difference"],
                                 -r["goals_for"], r["team"]))
        for position, row in enumerate(rows, 1):
            row["position"] = position
        return rows

    def standings(self, season, competition="Brasileirão") -> list[dict]:
        competition = self._competition(competition) or "Brasileirão"
        season = self._season(season)
        if season is None:
            raise QueryError("A season (year) is required for standings.")
        rows = self.table(competition, season)
        if not rows:
            available = self.seasons(competition).get(competition, [])
            raise QueryError(f"No {competition} matches for season {season}. "
                             f"Available seasons: {', '.join(map(str, available)) or 'none'}.")
        return rows

    def final(self, season, competition) -> dict | None:
        """The final tie of a knockout competition and its winner (if decidable)."""
        competition = self._competition(competition)
        matches = self.find_matches(competition=competition, season=season)
        if not matches:
            return None
        legs = [m for m in matches if m.stage and fold(m.stage) == "final"]
        if not legs:
            return None  # the final itself is missing from the data
        inferred = (competition, self._season(season)) in self._inferred_finals
        legs.sort(key=_date_key)
        a, b = sorted({legs[0].home, legs[0].away})
        goals = {a: 0, b: 0}
        for m in legs:
            goals[m.home] += m.home_goals
            goals[m.away] += m.away_goals
        winner = None if goals[a] == goals[b] else max(goals, key=goals.get)
        return {"competition": competition, "season": self._season(season), "legs": legs,
                "aggregate": goals, "winner": winner, "inferred": inferred}

    def season_summary(self, season, competition="Brasileirão") -> dict:
        """Champion (and relegation zone for Serie A) of a competition season."""
        competition = self._competition(competition) or "Brasileirão"
        season = self._season(season)
        summary = {"competition": competition, "season": season}
        if competition in LEAGUES:
            rows = self.standings(season, competition)
            summary["standings"] = rows
            summary["champion"] = rows[0]["team"] if competition == "Brasileirão" else None
            summary["relegated"] = ([r["team"] for r in rows[-4:]]
                                    if competition == "Brasileirão" and len(rows) >= 20 else [])
            expected = len(rows) * (len(rows) - 1)
            summary["complete"] = sum(r["matches"] for r in rows) == 2 * expected
        else:
            final = self.final(season, competition)
            if not self.find_matches(competition=competition, season=season):
                raise QueryError(f"No {competition} matches for season {season}.")
            summary["final"] = final
            summary["champion"] = final["winner"] if final else None
        summary.update(self.competition_stats(competition, season))
        return summary

    def competition_stats(self, competition=None, season=None) -> dict:
        """Aggregate goal and result statistics."""
        matches = self.find_matches(competition=competition, season=season)
        n = len(matches)
        goals = sum(m.total_goals for m in matches)
        home_wins = sum(1 for m in matches if m.home_goals > m.away_goals)
        draws = sum(1 for m in matches if m.home_goals == m.away_goals)
        pct = lambda x: round(100 * x / n, 1) if n else 0.0  # noqa: E731
        return {
            "competition": self._competition(competition), "season": self._season(season),
            "matches": n, "goals": goals,
            "goals_per_match": round(goals / n, 2) if n else 0.0,
            "home_goals": sum(m.home_goals for m in matches),
            "away_goals": sum(m.away_goals for m in matches),
            "home_wins": home_wins, "draws": draws, "away_wins": n - home_wins - draws,
            "home_win_rate": pct(home_wins), "draw_rate": pct(draws),
            "away_win_rate": pct(n - home_wins - draws),
        }

    def compare_seasons(self, season_a, season_b, competition="Brasileirão") -> dict:
        competition = self._competition(competition) or "Brasileirão"
        result = {"competition": competition, "seasons": {}}
        for season in (self._season(season_a), self._season(season_b)):
            if season is None:
                raise QueryError("Two seasons are required.")
            stats = self.competition_stats(competition, season)
            if not stats["matches"]:
                raise QueryError(f"No {competition} matches for season {season}.")
            rows = self.table(competition, season)
            stats["leader"] = rows[0]["team"]
            stats["leader_points"] = rows[0]["points"]
            stats["top_attack"] = max(rows, key=lambda r: r["goals_for"])["team"]
            stats["top_attack_goals"] = max(r["goals_for"] for r in rows)
            stats["biggest_win"] = self.biggest_wins(competition, season, limit=1)[0]
            result["seasons"][season] = stats
        return result

    def rank_teams(self, metric="win_rate", competition=None, season=None, venue="either",
                   min_matches=10, limit=10) -> list[dict]:
        """Rank teams by a record metric (win_rate, points, goals_for, ...)."""
        rows = self.table(competition, season, venue)
        if metric not in ("win_rate", "points", "points_per_match", "wins", "goals_for",
                          "goals_against", "goal_difference", "matches", "draws", "losses"):
            raise QueryError(f"Unknown metric {metric!r}.")
        rows = [r for r in rows if r["matches"] >= int(min_matches)]
        reverse = metric != "goals_against"
        rows.sort(key=lambda r: (r[metric], r["points"], r["goal_difference"]), reverse=reverse)
        return rows[:max(0, int(limit))]

    # ------------------------------------------------------------------ #
    # Players
    # ------------------------------------------------------------------ #

    def _club_filter(self, club: str):
        """Predicate matching FIFA club names against a club query."""
        canonical = known_club(club)
        if canonical and any(p["club"] and known_club(p["club"]) == canonical for p in self.players):
            return lambda name: known_club(name) == canonical
        needle = fold(club)
        return lambda name: needle in fold(name)

    def search_players(self, name=None, nationality=None, club=None, position=None,
                       min_overall=None, max_age=None, brazilian_clubs_only=False,
                       sort_by="overall", limit=20) -> dict:
        """Filter the FIFA database; returns {'total': n, 'players': [...]}."""
        players = self.players
        if name:
            words = fold(name).split()
            players = [p for p in players if all(w in fold(p["name"]) for w in words)]
        if nationality:
            wanted = fold(nationality)
            wanted = {"brasil": "brazil", "brazilian": "brazil", "brasileiro": "brazil"}.get(wanted, wanted)
            players = [p for p in players if fold(p["nationality"]) == wanted]
        if club:
            matches_club = self._club_filter(club)
            players = [p for p in players if p["club"] and matches_club(p["club"])]
        if brazilian_clubs_only:
            players = [p for p in players if p["club"] and known_club(p["club"]) in CLUB_STATE]
        if position:
            wanted = fold(position).rstrip("s")
            group = _POSITION_WORDS.get(wanted)
            codes = POSITION_GROUPS[group] if group else {position.strip().upper()}
            players = [p for p in players if p["position"] in codes]
        if min_overall not in (None, ""):
            players = [p for p in players if (p["overall"] or 0) >= int(min_overall)]
        if max_age not in (None, ""):
            players = [p for p in players if p["age"] is not None and p["age"] <= int(max_age)]
        if sort_by not in ("overall", "potential", "age", "name"):
            raise QueryError("sort_by must be one of: overall, potential, age, name.")
        if sort_by in ("name", "age"):
            players = sorted(players, key=lambda p: (p[sort_by] is None, p[sort_by], p["name"]))
        else:
            players = sorted(players, key=lambda p: (-(p[sort_by] or 0), p["name"]))
        return {"total": len(players), "players": players[:max(0, int(limit))]}

    def players_by_club(self, nationality=None, brazilian_clubs_only=True, limit=20) -> list[dict]:
        """Squad size and average rating per club."""
        found = self.search_players(nationality=nationality, limit=len(self.players),
                                    brazilian_clubs_only=brazilian_clubs_only)["players"]
        clubs = defaultdict(list)
        for p in found:
            if p["club"]:
                clubs[p["club"]].append(p)
        rows = [{"club": club, "players": len(ps),
                 "average_overall": round(sum(p["overall"] or 0 for p in ps) / len(ps), 1),
                 "best_player": max(ps, key=lambda p: p["overall"] or 0)["name"]}
                for club, ps in clubs.items()]
        rows.sort(key=lambda r: (-r["players"], -r["average_overall"], r["club"]))
        return rows[:max(0, int(limit))]

    def team_profile(self, team, season=None) -> dict:
        """Cross-file view: match record plus the club's FIFA squad."""
        stats = self.team_stats(team, season=season)
        squad = self.search_players(club=stats["team"], limit=50)
        if squad["players"] and known_club(squad["players"][0]["club"]) != stats["team"]:
            squad = {"total": 0, "players": []}  # substring hit on a different club
        return {"team": stats["team"], "state": CLUB_STATE.get(stats["team"]), "stats": stats,
                "competitions": self.team_competitions(team)["competitions"], "squad": squad}

    def summary(self) -> dict:
        per_competition = defaultdict(int)
        for m in self.matches:
            per_competition[m.competition] += 1
        dates = [m.date for m in self.matches if m.date]
        return {"matches": len(self.matches), "teams": len(self.registry.names),
                "players": len(self.players), "by_competition": dict(sorted(per_competition.items())),
                "seasons": self.seasons(), "first_date": min(dates), "last_date": max(dates),
                "files": self.load_report}


_default: SoccerData | None = None


def load_default() -> SoccerData:
    """Process-wide cached instance over the bundled data."""
    global _default
    if _default is None:
        _default = SoccerData.load()
    return _default
