"""Loading and unifying the six Kaggle CSV files.

All match files are merged into one list of ``Match`` objects:

* team names are normalised with :func:`brsoccer.teams.normalize_team`;
* dates in ISO (``2023-09-24``), ISO+time (``2012-05-19 18:30:00``) and
  Brazilian (``29/03/2003``) formats are parsed to ``datetime.date``;
* the same fixture appearing in several files (e.g. Brasileirão 2012-2019 is in
  three files) is merged into a single match that lists every source, so
  standings and statistics never double count.

Source priority (first wins for the score/date):
``Brasileirao_Matches.csv`` > ``novo_campeonato_brasileiro.csv`` >
``Brazilian_Cup_Matches.csv`` > ``Libertadores_Matches.csv`` > ``BR-Football-Dataset.csv``.
The extended statistics (shots, corners, attacks) of ``BR-Football-Dataset.csv``
are attached to the merged match.
"""

from __future__ import annotations

import csv
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from .teams import Team, fold, normalize_team

SERIE_A = "Brasileirão Série A"
SERIE_B = "Brasileirão Série B"
SERIE_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"
COMPETITIONS = [SERIE_A, SERIE_B, SERIE_C, COPA_DO_BRASIL, LIBERTADORES]

FILES = {
    "brasileirao": "Brasileirao_Matches.csv",
    "historical": "novo_campeonato_brasileiro.csv",
    "cup": "Brazilian_Cup_Matches.csv",
    "libertadores": "Libertadores_Matches.csv",
    "extended": "BR-Football-Dataset.csv",
    "fifa": "fifa_data.csv",
}

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"


def data_dir() -> Path:
    return Path(os.environ.get("BRSOCCER_DATA_DIR", DEFAULT_DATA_DIR))


# --------------------------------------------------------------------------- helpers

def parse_date(text: str | None) -> date | None:
    """Parse ISO, ISO with time, or Brazilian DD/MM/YYYY dates. Returns None if unparseable."""
    if not text:
        return None
    text = text.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _int(text: str | None) -> int | None:
    if text is None:
        return None
    text = text.strip()
    if not text or text in {"-", "NA", "nan"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _read(name: str) -> list[dict[str, str]]:
    # utf-8-sig strips the BOM present in fifa_data.csv
    with open(data_dir() / name, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _team_with_state(name: str, state: str) -> Team:
    """Prefer the club list over a state column (novo_campeonato_brasileiro.csv tags Vitória as ES)."""
    team = normalize_team(name)
    return team if team.known else normalize_team(name, state)


def _similar(a: Team, b: Team) -> bool:
    """Loose name similarity for minor clubs: share a significant word."""
    stop = {"de", "da", "do", "das", "dos", "e", "ec", "fc", "sc", "ac", "ce", "ad", "ae", "se", "clube",
            "esporte", "atletico", "sport", "real", "uniao", "fr"}
    wa = set(fold(a.name).split()) - stop
    wb = set(fold(b.name).split()) - stop
    return bool(wa & wb) and (a.state is None or b.state is None or a.state == b.state)


# --------------------------------------------------------------------------- models

@dataclass
class Match:
    competition: str
    season: int
    date: date | None
    home: Team
    away: Team
    home_goals: int
    away_goals: int
    round: str | None = None        # league round number or cup round
    stage: str | None = None        # "Final", "group stage", "Round of 16", ...
    time: str | None = None
    arena: str | None = None
    stats: dict[str, int] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def total_goals(self) -> int:
        return self.home_goals + self.away_goals

    @property
    def margin(self) -> int:
        return abs(self.home_goals - self.away_goals)

    @property
    def winner(self) -> Team | None:
        if self.home_goals > self.away_goals:
            return self.home
        if self.away_goals > self.home_goals:
            return self.away
        return None

    def involves(self, team_id: str) -> bool:
        return self.home.id == team_id or self.away.id == team_id

    def label(self) -> str:
        bits = [self.competition]
        if self.stage:
            bits.append(self.stage)
        elif self.round and self.competition in (SERIE_A, SERIE_B, SERIE_C):
            bits.append(f"Round {self.round}")
        elif self.round:
            bits.append(f"Round {self.round}")
        return " ".join(bits)

    def line(self) -> str:
        d = self.date.isoformat() if self.date else "date unknown"
        return (f"{d}: {self.home.name} {self.home_goals}-{self.away_goals} {self.away.name} "
                f"({self.label()}, {self.season})")

    def to_dict(self) -> dict:
        return {
            "competition": self.competition,
            "season": self.season,
            "date": self.date.isoformat() if self.date else None,
            "home_team": self.home.name,
            "away_team": self.away.name,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "round": self.round,
            "stage": self.stage,
            "arena": self.arena,
            "stats": dict(self.stats),
            "sources": list(self.sources),
        }


@dataclass
class Player:
    id: int
    name: str
    age: int | None
    nationality: str
    overall: int
    potential: int
    club: str
    club_team: Team | None
    position: str
    jersey_number: int | None
    height_cm: int | None
    weight_kg: int | None
    preferred_foot: str
    value_eur: float | None
    wage_eur: float | None
    contract_until: str
    attributes: dict[str, int]

    @property
    def at_brazilian_club(self) -> bool:
        return bool(self.club_team and self.club_team.known)

    def line(self) -> str:
        club = self.club or "Free agent"
        return f"{self.name} - Overall: {self.overall}, Position: {self.position or '?'}, Club: {club}"

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "age": self.age, "nationality": self.nationality,
            "overall": self.overall, "potential": self.potential, "club": self.club,
            "position": self.position, "jersey_number": self.jersey_number,
            "height_cm": self.height_cm, "weight_kg": self.weight_kg,
            "preferred_foot": self.preferred_foot, "value_eur": self.value_eur,
            "wage_eur": self.wage_eur, "contract_until": self.contract_until,
            "attributes": dict(self.attributes),
        }


SKILL_COLUMNS = [
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling", "Curve",
    "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Agility", "Reactions",
    "Balance", "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure", "Marking", "StandingTackle",
    "SlidingTackle", "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
]


def _money(text: str) -> float | None:
    m = re.match(r"^\D*([\d.]+)\s*([KM]?)", (text or "").strip())
    if not m:
        return None
    value = float(m.group(1))
    return value * {"K": 1e3, "M": 1e6, "": 1}[m.group(2)]


def _height_cm(text: str) -> int | None:
    m = re.match(r"^(\d+)'(\d+)", (text or "").strip())
    return round((int(m.group(1)) * 12 + int(m.group(2))) * 2.54) if m else None


def _weight_kg(text: str) -> int | None:
    m = re.match(r"^(\d+)", (text or "").strip())
    return round(int(m.group(1)) * 0.4536) if m else None


# --------------------------------------------------------------------------- database

class SoccerDB:
    """In-memory, indexed view over all the provided datasets."""

    def __init__(self) -> None:
        self.matches: list[Match] = []
        self.players: list[Player] = []
        self.teams: dict[str, Team] = {}
        self.source_rows: dict[str, int] = {}
        self.skipped_rows: dict[str, int] = Counter()
        self.merged_rows: dict[str, int] = Counter()
        self.score_conflicts = 0
        self._index: dict[tuple, list[Match]] = defaultdict(list)
        self._team_alias: dict[str, str] = {}
        self.matches_by_team: dict[str, list[Match]] = defaultdict(list)

    # ---- construction

    @classmethod
    def load(cls) -> "SoccerDB":
        db = cls()
        db._load_brasileirao()
        db._load_historical()
        db._load_cup()
        db._load_libertadores()
        db._load_extended()
        db._finalise_matches()
        db._load_fifa()
        return db

    def _add(self, m: Match, source: str) -> None:
        """Add a match, merging it with an equivalent match from another file if present."""
        m.home, m.away = self._canon(m.home), self._canon(m.away)
        key = (m.competition, m.season, m.home.id, m.away.id)
        candidates = [c for c in self._index[key] if source not in c.sources]
        if candidates:
            target = min(candidates, key=lambda c: abs((c.date - m.date).days) if c.date and m.date else 0)
            self._merge(target, m, source)
            return
        m.sources = [source]
        self._index[key].append(m)
        self.matches.append(m)

    def _enrich(self, m: Match, source: str) -> bool:
        """Merge ``m`` into an existing equivalent match; never adds a new match."""
        m.home, m.away = self._canon(m.home), self._canon(m.away)
        key = (m.competition, m.season, m.home.id, m.away.id)
        candidates = [c for c in self._index[key] if source not in c.sources]
        if not candidates:
            return False
        self._merge(candidates[0], m, source)
        return True

    def _merge(self, target: Match, other: Match, source: str) -> None:
        target.sources.append(source)
        self.merged_rows[source] += 1
        if (target.home_goals, target.away_goals) != (other.home_goals, other.away_goals):
            self.score_conflicts += 1
            target.notes.append(f"{source} reports {other.home_goals}-{other.away_goals}")
        for k, v in other.stats.items():
            target.stats.setdefault(k, v)
        target.arena = target.arena or other.arena
        target.round = target.round or other.round
        target.stage = target.stage or other.stage
        target.date = target.date or other.date

    def _canon(self, team: Team) -> Team:
        team = self.teams.get(self._team_alias.get(team.id, team.id), team)
        self.teams.setdefault(team.id, team)
        return team

    def _load_brasileirao(self) -> None:
        rows = _read(FILES["brasileirao"])
        self.source_rows[FILES["brasileirao"]] = len(rows)
        for r in rows:
            hg, ag, season = _int(r["home_goal"]), _int(r["away_goal"]), _int(r["season"])
            if hg is None or ag is None or season is None:
                self.skipped_rows[FILES["brasileirao"]] += 1
                continue
            self._add(Match(
                competition=SERIE_A, season=season, date=parse_date(r["datetime"]),
                home=normalize_team(r["home_team"], r["home_team_state"]),
                away=normalize_team(r["away_team"], r["away_team_state"]),
                home_goals=hg, away_goals=ag, round=r["round"] or None,
                time=r["datetime"][11:16] or None,
            ), FILES["brasileirao"])

    def _load_historical(self) -> None:
        rows = _read(FILES["historical"])
        self.source_rows[FILES["historical"]] = len(rows)
        for r in rows:
            hg, ag, season = _int(r["Gols_mandante"]), _int(r["Gols_visitante"]), _int(r["Ano"])
            if hg is None or ag is None or season is None:
                self.skipped_rows[FILES["historical"]] += 1
                continue
            self._add(Match(
                competition=SERIE_A, season=season, date=parse_date(r["Data"]),
                home=_team_with_state(r["Equipe_mandante"], r["Mandante_UF"]),
                away=_team_with_state(r["Equipe_visitante"], r["Visitante_UF"]),
                home_goals=hg, away_goals=ag, round=r["Rodada"] or None,
                arena=(r.get("Arena") or "").strip() or None,
            ), FILES["historical"])

    def _load_cup(self) -> None:
        rows = _read(FILES["cup"])
        self.source_rows[FILES["cup"]] = len(rows)
        # Name the last cup rounds from their number of matches, counting back from the final:
        # the highest round must have 2 matches (final), the one before 4 (semis), then 8, then 16.
        per_round = Counter((r["season"], r["round"]) for r in rows)
        stage_of: dict[tuple[str, str], str] = {}
        for season in {s for s, _ in per_round}:
            rounds = sorted((rd for s, rd in per_round if s == season), key=lambda x: _int(x) or 0, reverse=True)
            for rd, (size, name) in zip(rounds, [(2, "Final"), (4, "Semi-finals"), (8, "Quarter-finals"),
                                                 (16, "Round of 16")]):
                if per_round[(season, rd)] != size:
                    break
                stage_of[(season, rd)] = name
        for r in rows:
            hg, ag, season = _int(r["home_goal"]), _int(r["away_goal"]), _int(r["season"])
            if hg is None or ag is None or season is None:
                self.skipped_rows[FILES["cup"]] += 1
                continue
            self._add(Match(
                competition=COPA_DO_BRASIL, season=season, date=parse_date(r["datetime"]),
                home=normalize_team(r["home_team"]), away=normalize_team(r["away_team"]),
                home_goals=hg, away_goals=ag, round=r["round"] or None,
                stage=stage_of.get((r["season"], r["round"])),
                time=r["datetime"][11:16] or None,
            ), FILES["cup"])

    def _load_libertadores(self) -> None:
        rows = _read(FILES["libertadores"])
        self.source_rows[FILES["libertadores"]] = len(rows)
        raw_teams = {normalize_team(r[c]) for r in rows for c in ("home_team", "away_team")}
        # "Delfín" and "Delfín-EQU" are the same club: map country-less names onto the tagged one.
        tagged = {t.id.rsplit("-", 1)[0]: t.id for t in raw_teams if t.country not in ("BRA", None)}
        tagged.pop("river-plate", None)  # River Plate (ARG) and River Plate (URU) are different clubs
        for t in raw_teams:
            if t.country is None and t.id in tagged:
                self._team_alias[t.id] = tagged[t.id]
        stage_names = {"group stage": "Group stage", "round of 16": "Round of 16",
                       "quarterfinals": "Quarter-finals", "semifinals": "Semi-finals", "final": "Final"}
        for r in rows:
            hg, ag, season = _int(r["home_goal"]), _int(r["away_goal"]), _int(r["season"])
            if hg is None or ag is None or season is None:
                self.skipped_rows[FILES["libertadores"]] += 1
                continue
            self._add(Match(
                competition=LIBERTADORES, season=season, date=parse_date(r["datetime"]),
                home=normalize_team(r["home_team"]), away=normalize_team(r["away_team"]),
                home_goals=hg, away_goals=ag,
                stage=stage_names.get(r["stage"].strip().lower(), r["stage"].strip() or None),
                time=r["datetime"][11:16] or None,
            ), FILES["libertadores"])

    def _load_extended(self) -> None:
        rows = _read(FILES["extended"])
        source = FILES["extended"]
        self.source_rows[source] = len(rows)
        comp = {"Serie A": SERIE_A, "Serie B": SERIE_B, "Serie C": SERIE_C, "Copa do Brasil": COPA_DO_BRASIL}
        # Resolve state-less names ("Treze") to the single state-qualified club seen elsewhere ("Treze - PB").
        by_base: dict[str, set[str]] = defaultdict(set)
        for tid, t in self.teams.items():
            if t.state and not t.known and tid.endswith("-" + t.state.lower()):
                by_base[tid[: -3]].add(tid)

        parsed: list[Match] = []
        for r in rows:
            hg, ag = _int(r["home_goal"]), _int(r["away_goal"])
            competition = comp.get(r["tournament"].strip())
            raw_date = parse_date(r["date"])
            if hg is None or ag is None or competition is None or raw_date is None:
                self.skipped_rows[source] += 1
                continue
            # Kick-off times are UTC (~4h ahead of the other files); convert to Brazilian local time.
            kickoff = datetime.combine(raw_date, datetime.strptime(r["time"] or "00:00:00", "%H:%M:%S").time())
            local = kickoff - timedelta(hours=4)
            season = local.year
            if local.date() <= date(2021, 3, 7):
                season = min(season, 2020)  # the COVID-delayed 2020 season finished in Feb/Mar 2021
            stats = {col: v for col in ("home_corner", "away_corner", "home_attack", "away_attack",
                                        "home_shots", "away_shots") if (v := _int(r.get(col))) is not None}
            teams = []
            for col in ("home", "away"):
                t = normalize_team(r[col])
                if t.state is None and len(by_base.get(t.id, ())) == 1:
                    t = self.teams[next(iter(by_base[t.id]))]
                teams.append(self._canon(t))
            parsed.append(Match(competition=competition, season=season, date=local.date(), home=teams[0],
                                away=teams[1], home_goals=hg, away_goals=ag, time=local.strftime("%H:%M"),
                                stats=stats))

        # Pass 1: learn spellings of minor clubs by pairing fixtures that match on date, competition
        # and one team (e.g. "Brasil de Pelotas" == "Brasil - RS").
        votes: dict[str, Counter] = defaultdict(Counter)
        for m in parsed:
            if self._index.get((m.competition, m.season, m.home.id, m.away.id)):
                continue
            other = self._fuzzy_candidate(m)
            if other is None:
                continue
            for mine, theirs in ((m.home, other.home), (m.away, other.away)):
                if mine.id != theirs.id and not mine.known and (
                        mine.state is None or theirs.state is None or mine.state == theirs.state):
                    votes[mine.id][theirs.id] += 1
        for mine, counter in votes.items():
            target, n = counter.most_common(1)[0]
            if n > sum(counter.values()) / 2:
                self._team_alias[mine] = target

        # Pass 2: merge or add.
        per_season = Counter(m.season for m in self.matches if m.competition == SERIE_A)
        complete_seasons = {s for s, n in per_season.items() if n >= 380}
        for m in parsed:
            m.home, m.away = self._canon(m.home), self._canon(m.away)
            if self._enrich(m, source):
                continue
            other = self._fuzzy_candidate(m)
            if other is not None:
                self._merge(other, m, source)
                continue
            if m.competition == SERIE_A and m.season in complete_seasons:
                # The season is complete in the primary files, so this row is spurious
                # (BR-Football mislabels a handful of cup/regional games as "Serie A").
                self.skipped_rows[source] += 1
                continue
            self._add(m, source)

    def _fuzzy_candidate(self, m: Match) -> Match | None:
        """Find an existing match from another file that is the same fixture under different spellings."""
        if m.date is None:
            return None
        if not hasattr(self, "_by_day"):
            self._by_day: dict[tuple, list[Match]] = defaultdict(list)
            for x in self.matches:
                if x.date:
                    self._by_day[(x.competition, x.date)].append(x)
        for delta in (0, -1, 1, -2, 2):
            for x in self._by_day.get((m.competition, m.date + timedelta(days=delta)), ()):
                if len(x.sources) > 1:
                    continue
                same_home, same_away = x.home.id == m.home.id, x.away.id == m.away.id
                if same_home and same_away:
                    return x
                if (same_home or same_away) and (
                        (x.home_goals, x.away_goals) == (m.home_goals, m.away_goals)
                        or _similar(x.away if same_home else x.home, m.away if same_home else m.home)):
                    return x
        return None

    def _finalise_matches(self) -> None:
        # Copa do Brasil seasons only covered by BR-Football have no round info: infer the final
        # as the season's last match plus its reverse fixture.
        cup_seasons = defaultdict(list)
        for m in self.matches:
            if m.competition == COPA_DO_BRASIL:
                cup_seasons[m.season].append(m)
        for season, ms in cup_seasons.items():
            if any(m.stage == "Final" for m in ms) or not all(m.date for m in ms):
                continue
            ms.sort(key=lambda m: m.date)
            last = ms[-1]
            legs = [m for m in ms if {m.home.id, m.away.id} == {last.home.id, last.away.id}
                    and (last.date - m.date).days <= 21]
            if len(legs) <= 2 and len(ms) > 20:
                for m in legs:
                    m.stage = "Final"
                    m.notes.append("final inferred from date order")
        self.matches.sort(key=lambda m: (m.date or date.min, m.competition))
        for m in self.matches:
            self.matches_by_team[m.home.id].append(m)
            self.matches_by_team[m.away.id].append(m)

    def _load_fifa(self) -> None:
        rows = _read(FILES["fifa"])
        self.source_rows[FILES["fifa"]] = len(rows)
        for r in rows:
            overall = _int(r.get("Overall"))
            if overall is None or not r.get("Name"):
                self.skipped_rows[FILES["fifa"]] += 1
                continue
            club = (r.get("Club") or "").strip()
            club_team = normalize_team(club) if club else None
            self.players.append(Player(
                id=_int(r.get("ID")) or 0, name=r["Name"].strip(), age=_int(r.get("Age")),
                nationality=(r.get("Nationality") or "").strip(), overall=overall,
                potential=_int(r.get("Potential")) or overall, club=club,
                club_team=club_team if club_team and club_team.known else None,
                position=(r.get("Position") or "").strip(), jersey_number=_int(r.get("Jersey Number")),
                height_cm=_height_cm(r.get("Height", "")), weight_kg=_weight_kg(r.get("Weight", "")),
                preferred_foot=(r.get("Preferred Foot") or "").strip(),
                value_eur=_money(r.get("Value", "")), wage_eur=_money(r.get("Wage", "")),
                contract_until=(r.get("Contract Valid Until") or "").strip(),
                attributes={c: v for c in SKILL_COLUMNS if (v := _int(r.get(c))) is not None},
            ))
        self.players.sort(key=lambda p: (-p.overall, p.name))

    # ---- lookups

    def find_team(self, query: str) -> Team | None:
        """Resolve free-text team input ("fla", "Sao Paulo FC", "Palmeiras-SP") to a known team."""
        candidates = self.find_teams(query)
        return candidates[0] if candidates else None

    def find_teams(self, query: str, limit: int = 5) -> list[Team]:
        """Rank teams for free text: exact canonical club first, then name matches (big clubs first)."""
        if not query or not query.strip():
            return []
        t = normalize_team(query)
        tid = self._team_alias.get(t.id, t.id)
        if t.known and self.matches_by_team.get(tid):
            return [self.teams[tid]]
        q = fold(query)
        scored = []
        for team_id, team in self.teams.items():
            n = len(self.matches_by_team.get(team_id, ()))
            if not n:
                continue
            name = fold(team.name)
            if team_id == tid and t.state:
                score = 0  # explicit state given, e.g. "Treze-PB"
            elif team_id == tid or name == q or name.startswith(q) or team_id.startswith(q.replace(" ", "-")):
                score = 1
            elif q in name:
                score = 2
            elif all(word in name.split() for word in q.split()):
                score = 3
            else:
                continue
            scored.append((score, -int(team.known), -n, team.name, team))
        scored.sort(key=lambda s: s[:4])
        return [s[-1] for s in scored[:limit]]

    def competitions_for(self, team_id: str) -> Counter:
        return Counter(m.competition for m in self.matches_by_team.get(team_id, ()))


_DB: SoccerDB | None = None


def get_db() -> SoccerDB:
    """Process-wide lazily loaded database."""
    global _DB
    if _DB is None:
        _DB = SoccerDB.load()
    return _DB
