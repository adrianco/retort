"""Load the six Kaggle CSV files into a unified in-memory knowledge base.

Matches from the five match files become `Match` records with canonical team
ids (see team_names.py), parsed dates and a canonical competition name.  The
same Brasileirão / Copa do Brasil match often appears in two or three files;
duplicates are merged into a single record (the highest-priority source keeps
its score, the others contribute extra fields such as arena or shot/corner
statistics and are listed in `Match.sources`).

Players from fifa_data.csv become `Player` records.
"""

from __future__ import annotations

import csv
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from team_names import FIFA_CLUB_TO_TEAM, canonical_team_id, display_name, normalize_text

DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data" / "kaggle"

SERIE_A = "Brasileirão Série A"
SERIE_B = "Brasileirão Série B"
SERIE_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"
COMPETITIONS = (SERIE_A, SERIE_B, SERIE_C, COPA_DO_BRASIL, LIBERTADORES)
LEAGUES = frozenset({SERIE_A, SERIE_B, SERIE_C})

FILES = {
    "brasileirao": "Brasileirao_Matches.csv",
    "cup": "Brazilian_Cup_Matches.csv",
    "libertadores": "Libertadores_Matches.csv",
    "br_football": "BR-Football-Dataset.csv",
    "historical": "novo_campeonato_brasileiro.csv",
    "fifa": "fifa_data.csv",
}

_COMPETITION_ALIASES = {
    "brasileirao": SERIE_A,
    "brasileirao serie a": SERIE_A,
    "serie a": SERIE_A,
    "campeonato brasileiro": SERIE_A,
    "campeonato brasileiro serie a": SERIE_A,
    "brasileiro": SERIE_A,
    "brazilian league": SERIE_A,
    "brasileirao serie b": SERIE_B,
    "serie b": SERIE_B,
    "brasileirao serie c": SERIE_C,
    "serie c": SERIE_C,
    "copa do brasil": COPA_DO_BRASIL,
    "brazilian cup": COPA_DO_BRASIL,
    "brazil cup": COPA_DO_BRASIL,
    "cup": COPA_DO_BRASIL,
    "libertadores": LIBERTADORES,
    "copa libertadores": LIBERTADORES,
    "copa libertadores da america": LIBERTADORES,
    "conmebol libertadores": LIBERTADORES,
}


def resolve_competition(name: str | None) -> str | None:
    """Map free-text competition names to a canonical one (None = all)."""
    if name is None or not str(name).strip():
        return None
    key = normalize_text(str(name))
    if key in ("all", "any"):
        return None
    if key in _COMPETITION_ALIASES:
        return _COMPETITION_ALIASES[key]
    for alias, comp in _COMPETITION_ALIASES.items():
        if len(alias) > 4 and alias in key:
            return comp
    raise ValueError(f"Unknown competition '{name}'. Valid options: {', '.join(COMPETITIONS)}")


_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%d-%m-%Y")


def parse_date(value: str | None) -> date | None:
    """Parse ISO, ISO-with-time and Brazilian DD/MM/YYYY dates."""
    if value is None:
        return None
    value = str(value).strip()
    if not value or value.upper() in ("NA", "NAN", "NONE"):
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date '{value}'. Use YYYY-MM-DD or DD/MM/YYYY.")


def _parse_time(value: str | None) -> str | None:
    if not value:
        return None
    m = re.search(r"(\d{1,2}:\d{2})", value)
    return m.group(1) if m else None


def _parse_goals(value: str | None) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _parse_int(value: str | None) -> int | None:
    return _parse_goals(value)


@dataclass(slots=True)
class Match:
    competition: str
    season: int
    date: date | None
    home_id: str
    away_id: str
    home_goals: int
    away_goals: int
    source: str
    time: str | None = None
    round: str | None = None
    stage: str | None = None
    arena: str | None = None
    stats: dict | None = None
    sources: list[str] = field(default_factory=list)
    score_conflict: bool = False

    @property
    def total_goals(self) -> int:
        return self.home_goals + self.away_goals

    @property
    def margin(self) -> int:
        return abs(self.home_goals - self.away_goals)

    @property
    def winner_id(self) -> str | None:
        if self.home_goals > self.away_goals:
            return self.home_id
        if self.away_goals > self.home_goals:
            return self.away_id
        return None

    def involves(self, team_id: str) -> bool:
        return self.home_id == team_id or self.away_id == team_id

    def goals_for(self, team_id: str) -> int:
        return self.home_goals if self.home_id == team_id else self.away_goals

    def goals_against(self, team_id: str) -> int:
        return self.away_goals if self.home_id == team_id else self.home_goals


@dataclass(slots=True)
class Player:
    id: int
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    position: str
    jersey_number: int | None
    height: str
    weight: str
    preferred_foot: str
    value: str
    wage: str
    contract_until: str
    attributes: dict[str, int]
    name_norm: str = ""
    club_norm: str = ""
    nationality_norm: str = ""

    @property
    def team_id(self) -> str | None:
        """Canonical team id if the player is at a Brazilian club in the match data."""
        return FIFA_CLUB_TO_TEAM.get(self.club)


SKILL_COLUMNS = (
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling", "Curve", "FKAccuracy",
    "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance", "ShotPower",
    "Jumping", "Stamina", "Strength", "LongShots", "Aggression", "Interceptions", "Positioning", "Vision",
    "Penalties", "Composure", "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling", "GKKicking",
    "GKPositioning", "GKReflexes",
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    # utf-8-sig strips the BOM present in fifa_data.csv.
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


class SoccerData:
    """All datasets loaded, normalized and indexed."""

    def __init__(self, data_dir: str | os.PathLike | None = None):
        self.data_dir = Path(data_dir or os.environ.get("BR_SOCCER_DATA_DIR") or DEFAULT_DATA_DIR)
        self.matches: list[Match] = []
        self.players: list[Player] = []
        self.raw_counts: dict[str, int] = {}
        self.loaded_counts: dict[str, int] = {}
        self.skipped_counts: dict[str, int] = {}
        self.duplicates_merged = 0
        self._raw_names: dict[str, Counter] = defaultdict(Counter)
        self._dedup_index: dict[tuple, list[Match]] = defaultdict(list)
        self._load()

    # ------------------------------------------------------------------ loading
    def _load(self) -> None:
        # Order matters: earlier sources win when the same match appears twice.
        self._load_brasileirao()
        self._load_historical()
        # Seasons whose dedicated files are complete (20 teams -> 380 games,
        # more in 2003-2005); incomplete ones (2022 has unplayed 'NA' rows)
        # are topped up from BR-Football.
        per_season = Counter(m.season for m in self.matches if m.competition == SERIE_A)
        self._primary_serie_a_seasons = {s for s, n in per_season.items() if n >= 380}
        self._load_cup()
        self._load_libertadores()
        self._load_br_football()
        self._label_cup_stages()
        self._load_fifa()
        self.matches.sort(key=lambda m: (m.date or date.min, m.competition, m.home_id))
        self.team_names = {tid: self._pick_display(tid) for tid in self._raw_names}
        self.by_team: dict[str, list[Match]] = defaultdict(list)
        for m in self.matches:
            self.by_team[m.home_id].append(m)
            self.by_team[m.away_id].append(m)
        del self._dedup_index

    def _team(self, raw: str, state: str | None = None) -> str:
        tid = canonical_team_id(raw, state)
        self._raw_names[tid][raw.strip()] += 1
        return tid

    def _pick_display(self, tid: str) -> str:
        known = display_name(tid)
        if known:
            return known
        return self._raw_names[tid].most_common(1)[0][0]

    def _add(self, m: Match) -> None:
        m.sources = [m.source]
        key = (m.competition, m.home_id, m.away_id)
        for existing in self._dedup_index[key]:
            if existing.source != m.source and self._same_match(existing, m):
                self._merge(existing, m)
                return
        if m.source == FILES["br_football"] and m.competition == SERIE_A and m.season in self._primary_serie_a_seasons:
            # Série A seasons already fully covered by the dedicated files: an
            # unmatched BR-Football row is a mislabelled match (e.g. a
            # state-championship game tagged 'Serie A'), so it is dropped.
            self._skip(m.source)
            return
        self._dedup_index[key].append(m)
        self.matches.append(m)
        self.loaded_counts[m.source] = self.loaded_counts.get(m.source, 0) + 1

    @staticmethod
    def _same_match(a: Match, b: Match) -> bool:
        if a.competition in LEAGUES:
            # In a league each team hosts each opponent once per season.
            return a.season == b.season
        if a.date and b.date:
            return abs((a.date - b.date).days) <= 3
        return a.season == b.season

    def _merge(self, primary: Match, dup: Match) -> None:
        self.duplicates_merged += 1
        primary.sources.append(dup.source)
        if (primary.home_goals, primary.away_goals) != (dup.home_goals, dup.away_goals):
            primary.score_conflict = True
        if primary.arena is None and dup.arena:
            primary.arena = dup.arena
        if primary.stats is None and dup.stats:
            primary.stats = dup.stats
        if primary.time is None and dup.time:
            primary.time = dup.time
        if primary.date is None and dup.date:
            primary.date = dup.date

    def _skip(self, source: str) -> None:
        self.skipped_counts[source] = self.skipped_counts.get(source, 0) + 1

    def _load_brasileirao(self) -> None:
        src = FILES["brasileirao"]
        rows = _read_csv(self.data_dir / src)
        self.raw_counts[src] = len(rows)
        for r in rows:
            hg, ag = _parse_goals(r["home_goal"]), _parse_goals(r["away_goal"])
            if hg is None or ag is None:
                self._skip(src)
                continue
            self._add(Match(
                competition=SERIE_A,
                season=int(r["season"]),
                date=parse_date(r["datetime"]),
                time=_parse_time(r["datetime"]),
                home_id=self._team(r["home_team"], r.get("home_team_state")),
                away_id=self._team(r["away_team"], r.get("away_team_state")),
                home_goals=hg, away_goals=ag,
                round=r["round"] or None,
                source=src,
            ))

    def _load_historical(self) -> None:
        src = FILES["historical"]
        rows = _read_csv(self.data_dir / src)
        self.raw_counts[src] = len(rows)
        for r in rows:
            hg, ag = _parse_goals(r["Gols_mandante"]), _parse_goals(r["Gols_visitante"])
            if hg is None or ag is None:
                self._skip(src)
                continue
            self._add(Match(
                competition=SERIE_A,
                season=int(r["Ano"]),
                date=parse_date(r["Data"]),
                home_id=self._team(r["Equipe_mandante"], r.get("Mandante_UF")),
                away_id=self._team(r["Equipe_visitante"], r.get("Visitante_UF")),
                home_goals=hg, away_goals=ag,
                round=r["Rodada"] or None,
                arena=(r.get("Arena") or "").strip() or None,
                source=src,
            ))

    def _load_cup(self) -> None:
        src = FILES["cup"]
        rows = _read_csv(self.data_dir / src)
        self.raw_counts[src] = len(rows)
        for r in rows:
            hg, ag = _parse_goals(r["home_goal"]), _parse_goals(r["away_goal"])
            if hg is None or ag is None:
                self._skip(src)
                continue
            self._add(Match(
                competition=COPA_DO_BRASIL,
                season=int(r["season"]),
                date=parse_date(r["datetime"]),
                time=_parse_time(r["datetime"]),
                home_id=self._team(r["home_team"]),
                away_id=self._team(r["away_team"]),
                home_goals=hg, away_goals=ag,
                round=r["round"] or None,
                source=src,
            ))

    def _load_libertadores(self) -> None:
        src = FILES["libertadores"]
        rows = _read_csv(self.data_dir / src)
        self.raw_counts[src] = len(rows)
        for r in rows:
            hg, ag = _parse_goals(r["home_goal"]), _parse_goals(r["away_goal"])
            season = _parse_int(r["season"])
            if hg is None or ag is None or season is None:
                self._skip(src)
                continue
            self._add(Match(
                competition=LIBERTADORES,
                season=season,
                date=parse_date(r["datetime"]),
                time=_parse_time(r["datetime"]),
                home_id=self._team(r["home_team"]),
                away_id=self._team(r["away_team"]),
                home_goals=hg, away_goals=ag,
                stage=(r.get("stage") or "").strip() or None,
                source=src,
            ))

    @staticmethod
    def _br_football_season(tournament: str, d: date) -> int:
        # The 2020 seasons were pushed into early 2021 by COVID-19.
        if d.year == 2021:
            if tournament == COPA_DO_BRASIL and d <= date(2021, 3, 7):
                return 2020
            if tournament in LEAGUES and d < date(2021, 3, 1):
                return 2020
        return d.year

    def _load_br_football(self) -> None:
        src = FILES["br_football"]
        rows = _read_csv(self.data_dir / src)
        self.raw_counts[src] = len(rows)
        comp_map = {"Serie A": SERIE_A, "Serie B": SERIE_B, "Serie C": SERIE_C, "Copa do Brasil": COPA_DO_BRASIL}
        for r in rows:
            hg, ag = _parse_goals(r["home_goal"]), _parse_goals(r["away_goal"])
            d = parse_date(r["date"])
            comp = comp_map.get(r["tournament"].strip())
            if hg is None or ag is None or d is None or comp is None:
                self._skip(src)
                continue
            stats = {}
            for key in ("home_corner", "away_corner", "home_attack", "away_attack", "home_shots", "away_shots"):
                val = _parse_int(r.get(key))
                if val is not None:
                    stats[key] = val
            self._add(Match(
                competition=comp,
                season=self._br_football_season(comp, d),
                date=d,
                time=_parse_time(r.get("time")),
                home_id=self._team(r["home"]),
                away_id=self._team(r["away"]),
                home_goals=hg, away_goals=ag,
                stats=stats or None,
                source=src,
            ))

    def _label_cup_stages(self) -> None:
        """Name Copa do Brasil rounds (final, semifinals, ...) per season.

        The cup file numbers rounds 1..N; the last round with two matches is
        the final and earlier rounds are named counting backwards. Seasons
        only covered by BR-Football have no round numbers, so the final is
        inferred as the last two-legged tie of the season.
        """
        by_season: dict[int, list[Match]] = defaultdict(list)
        for m in self.matches:
            if m.competition == COPA_DO_BRASIL:
                by_season[m.season].append(m)
        names = ["final", "semifinals", "quarterfinals", "round of 16"]
        for season, ms in by_season.items():
            rounds = Counter(int(m.round) for m in ms if m.round and m.round.isdigit())
            stage_by_round: dict[int, str] = {}
            if rounds:
                finals = [r for r, n in rounds.items() if n == 2]
                last = max(rounds)
                if finals and max(finals) == last:
                    for i, name in enumerate(names):
                        if rounds.get(last - i) == 2 * (2 ** i):
                            stage_by_round[last - i] = name
                        else:
                            break
            for m in ms:
                if m.round and m.round.isdigit():
                    m.stage = stage_by_round.get(int(m.round), f"round {m.round}")
            if "final" not in stage_by_round.values():
                dated = sorted((m for m in ms if m.date), key=lambda m: m.date)
                if len(dated) >= 2:
                    last_m, prev = dated[-1], dated[-2]
                    if {last_m.home_id, last_m.away_id} == {prev.home_id, prev.away_id} and \
                            (last_m.date - prev.date).days <= 21:
                        last_m.stage = prev.stage = "final"

    def _load_fifa(self) -> None:
        src = FILES["fifa"]
        rows = _read_csv(self.data_dir / src)
        self.raw_counts[src] = len(rows)
        for r in rows:
            name = (r.get("Name") or "").strip()
            if not name:
                self._skip(src)
                continue
            attrs = {}
            for col in SKILL_COLUMNS:
                val = _parse_int(r.get(col))
                if val is not None:
                    attrs[col] = val
            p = Player(
                id=_parse_int(r.get("ID")) or 0,
                name=name,
                age=_parse_int(r.get("Age")),
                nationality=(r.get("Nationality") or "").strip(),
                overall=_parse_int(r.get("Overall")),
                potential=_parse_int(r.get("Potential")),
                club=(r.get("Club") or "").strip(),
                position=(r.get("Position") or "").strip(),
                jersey_number=_parse_int(r.get("Jersey Number")),
                height=(r.get("Height") or "").strip(),
                weight=(r.get("Weight") or "").strip(),
                preferred_foot=(r.get("Preferred Foot") or "").strip(),
                value=(r.get("Value") or "").strip(),
                wage=(r.get("Wage") or "").strip(),
                contract_until=(r.get("Contract Valid Until") or "").strip(),
                attributes=attrs,
            )
            p.name_norm = normalize_text(p.name)
            p.club_norm = normalize_text(p.club)
            p.nationality_norm = normalize_text(p.nationality)
            self.players.append(p)
        self.loaded_counts[src] = len(self.players)

    # ------------------------------------------------------------------ helpers
    def team_name(self, team_id: str) -> str:
        return self.team_names.get(team_id) or display_name(team_id) or team_id

    def seasons(self, competition: str | None = None) -> list[int]:
        return sorted({m.season for m in self.matches if competition is None or m.competition == competition})


_DEFAULT: SoccerData | None = None


def get_data() -> SoccerData:
    """Process-wide singleton (loading takes ~1s)."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = SoccerData()
    return _DEFAULT
