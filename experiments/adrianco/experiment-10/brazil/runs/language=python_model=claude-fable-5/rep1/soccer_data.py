"""Data loading and team-name normalization for the Brazilian Soccer MCP server.

Loads the six Kaggle CSV files in data/kaggle/ into in-memory match and
player records, normalizing team names (state suffixes, accents, club
aliases) and date formats so the different datasets can be queried and
cross-referenced consistently.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "data" / "kaggle"

# Brazilian state (UF) codes, used to recognize "Team-SP" / "Team - SP" /
# "Team SP" suffixes.
STATE_CODES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

# Clubs whose identity depends on their state: base name + state -> canonical base.
_STATEFUL_CANONICAL = {
    ("atletico", "MG"): "atletico mineiro",
    ("atletico", "PR"): "athletico paranaense",
    ("athletico", "PR"): "athletico paranaense",
    ("atletico", "GO"): "atletico goianiense",
    ("america", "MG"): "america mineiro",
    ("america", "RN"): "america rn",
}

# Exact aliases applied after accent stripping / lowercasing / suffix removal.
# Value is (canonical base, state or None to keep the detected state).
_ALIASES = {
    "atletico mineiro": ("atletico mineiro", "MG"),
    "atletico paranaense": ("athletico paranaense", "PR"),
    "athletico paranaense": ("athletico paranaense", "PR"),
    "athletico": ("athletico paranaense", "PR"),
    "atletico goianiense": ("atletico goianiense", "GO"),
    "america mineiro": ("america mineiro", "MG"),
    "america fc natal": ("america rn", "RN"),
    "vasco": ("vasco da gama", "RJ"),
    "vasco da gama": ("vasco da gama", "RJ"),
    "sport": ("sport recife", "PE"),
    "sport recife": ("sport recife", "PE"),
    "ec bahia": ("bahia", "BA"),
    "ec vitoria": ("vitoria", "BA"),
    "vitoria ec": ("vitoria", "BA"),
    "ec juventude": ("juventude", "RS"),
    "fortaleza ec": ("fortaleza", "CE"),
    "fortaleza fc": ("fortaleza", "CE"),
    "fortaleza esporte clube": ("fortaleza", "CE"),
    "nautico capibaribe": ("nautico", "PE"),
    "santa cruz fc": ("santa cruz", "PE"),
    "portuguesa desportos": ("portuguesa", "SP"),
    "red bull bragantino": ("bragantino", "SP"),
    "sport club corinthians paulista": ("corinthians", "SP"),
    "corinthians paulista": ("corinthians", "SP"),
    "sociedade esportiva palmeiras": ("palmeiras", "SP"),
    "clube de regatas do flamengo": ("flamengo", "RJ"),
    "sao paulo fc": ("sao paulo", "SP"),
    "sao paulo futebol clube": ("sao paulo", "SP"),
    "santos fc": ("santos", "SP"),
    "csa": ("csa", "AL"),
    "gremio": ("gremio", "RS"),
    "internacional": ("internacional", "RS"),
}

_PAREN_RE = re.compile(r"\s*\([^)]*\)")
_WS_RE = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def normalize_team(name: str) -> tuple[str, Optional[str]]:
    """Normalize a team name to (canonical base, state or None).

    Handles "Palmeiras-SP", "Corinthians - SP", "America MG", accented
    names, and known club aliases. The base is a lowercase accent-free
    key used for matching across datasets.
    """
    if not name:
        return "", None
    text = strip_accents(name).strip()
    text = _PAREN_RE.sub("", text)
    text = text.replace("-", " ")
    text = _WS_RE.sub(" ", text).strip().lower()

    state: Optional[str] = None
    tokens = text.split(" ")
    if len(tokens) > 1 and tokens[-1].upper() in STATE_CODES:
        state = tokens[-1].upper()
        tokens = tokens[:-1]
    # Drop club-form abbreviations ("EC Bahia", "4 de Julho EC", "Fortaleza FC")
    # so the same club keys identically across datasets.
    if len(tokens) > 1 and tokens[-1] in ("ec", "fc"):
        tokens = tokens[:-1]
    if len(tokens) > 1 and tokens[0] == "ec":
        tokens = tokens[1:]
    text = " ".join(tokens)

    canonical = _STATEFUL_CANONICAL.get((text, state))
    if canonical:
        return canonical, state

    alias = _ALIASES.get(text)
    if alias:
        base, alias_state = alias
        return base, (state or alias_state)

    return text, state


# Competition keys and display names.
COMPETITIONS = {
    "serie-a": "Brasileirão Série A",
    "serie-b": "Brasileirão Série B",
    "serie-c": "Brasileirão Série C",
    "copa-do-brasil": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
}

_COMPETITION_ALIASES = {
    "serie a": "serie-a",
    "serie-a": "serie-a",
    "brasileirao": "serie-a",
    "brasileirao serie a": "serie-a",
    "campeonato brasileiro": "serie-a",
    "serie b": "serie-b",
    "serie-b": "serie-b",
    "brasileirao serie b": "serie-b",
    "serie c": "serie-c",
    "serie-c": "serie-c",
    "brasileirao serie c": "serie-c",
    "copa do brasil": "copa-do-brasil",
    "copa-do-brasil": "copa-do-brasil",
    "brazilian cup": "copa-do-brasil",
    "libertadores": "libertadores",
    "copa libertadores": "libertadores",
}


def normalize_competition(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    key = _WS_RE.sub(" ", strip_accents(name).lower().strip())
    return _COMPETITION_ALIASES.get(key, key)


_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M")


def parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    value = value.strip()
    if not value or value.upper() == "NA":
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _parse_int(value) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() == "NA":
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


@dataclass
class Match:
    source: str
    competition: str  # competition key, e.g. "serie-a"
    season: Optional[int]
    date: Optional[datetime]
    home: str
    away: str
    home_base: str
    away_base: str
    home_state: Optional[str]
    away_state: Optional[str]
    home_goal: Optional[int]
    away_goal: Optional[int]
    stage: Optional[str] = None  # round number or tournament stage
    extras: dict = field(default_factory=dict)

    @property
    def competition_name(self) -> str:
        return COMPETITIONS.get(self.competition, self.competition)

    @property
    def has_score(self) -> bool:
        return self.home_goal is not None and self.away_goal is not None

    def winner_base(self) -> Optional[str]:
        """Base name of the winner, or None for a draw / unknown score."""
        if not self.has_score:
            return None
        if self.home_goal > self.away_goal:
            return self.home_base
        if self.away_goal > self.home_goal:
            return self.away_base
        return None

    def involves(self, base: str, state: Optional[str] = None) -> bool:
        return self._side_matches("home", base, state) or self._side_matches("away", base, state)

    def _side_matches(self, side: str, base: str, state: Optional[str]) -> bool:
        m_base = self.home_base if side == "home" else self.away_base
        m_state = self.home_state if side == "home" else self.away_state
        if m_base != base:
            return False
        if state and m_state and state != m_state:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "date": self.date.strftime("%Y-%m-%d") if self.date else None,
            "competition": self.competition_name,
            "season": self.season,
            "stage": self.stage,
            "home_team": self.home,
            "away_team": self.away,
            "score": f"{self.home_goal}-{self.away_goal}" if self.has_score else None,
            "home_goals": self.home_goal,
            "away_goals": self.away_goal,
            **({"extras": self.extras} if self.extras else {}),
        }


@dataclass
class Player:
    player_id: str
    name: str
    age: Optional[int]
    nationality: str
    overall: Optional[int]
    potential: Optional[int]
    club: str
    position: str
    jersey_number: Optional[int]
    height: str
    weight: str
    value: str
    wage: str
    preferred_foot: str
    skills: dict

    @property
    def name_key(self) -> str:
        return strip_accents(self.name).lower()

    def to_dict(self, include_skills: bool = False) -> dict:
        data = {
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "position": self.position,
            "jersey_number": self.jersey_number,
            "height": self.height,
            "weight": self.weight,
            "value": self.value,
            "wage": self.wage,
            "preferred_foot": self.preferred_foot,
        }
        if include_skills:
            data["skills"] = self.skills
        return data


# Position groups for player queries.
POSITION_GROUPS = {
    "goalkeeper": {"GK"},
    "defender": {"LB", "LCB", "CB", "RCB", "RB", "LWB", "RWB"},
    "midfielder": {"LDM", "CDM", "RDM", "LCM", "CM", "RCM", "LM", "RM", "LAM", "CAM", "RAM"},
    "forward": {"LS", "ST", "RS", "LW", "RW", "LF", "CF", "RF"},
}


def _read_csv(filename: str) -> list[dict]:
    path = DATA_DIR / filename
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _load_brasileirao() -> list[Match]:
    matches = []
    for row in _read_csv("Brasileirao_Matches.csv"):
        home_base, home_state = normalize_team(row["home_team"])
        away_base, away_state = normalize_team(row["away_team"])
        matches.append(Match(
            source="brasileirao",
            competition="serie-a",
            season=_parse_int(row["season"]),
            date=parse_date(row["datetime"]),
            home=row["home_team"], away=row["away_team"],
            home_base=home_base, away_base=away_base,
            home_state=home_state or row.get("home_team_state") or None,
            away_state=away_state or row.get("away_team_state") or None,
            home_goal=_parse_int(row["home_goal"]),
            away_goal=_parse_int(row["away_goal"]),
            stage=f"Round {row['round']}" if row.get("round") else None,
        ))
    return matches


def _load_cup() -> list[Match]:
    matches = []
    for row in _read_csv("Brazilian_Cup_Matches.csv"):
        home_base, home_state = normalize_team(row["home_team"])
        away_base, away_state = normalize_team(row["away_team"])
        matches.append(Match(
            source="cup",
            competition="copa-do-brasil",
            season=_parse_int(row["season"]),
            date=parse_date(row["datetime"]),
            home=row["home_team"], away=row["away_team"],
            home_base=home_base, away_base=away_base,
            home_state=home_state, away_state=away_state,
            home_goal=_parse_int(row["home_goal"]),
            away_goal=_parse_int(row["away_goal"]),
            stage=f"Round {row['round']}" if row.get("round") else None,
        ))
    return matches


def _load_libertadores() -> list[Match]:
    matches = []
    for row in _read_csv("Libertadores_Matches.csv"):
        home_base, home_state = normalize_team(row["home_team"])
        away_base, away_state = normalize_team(row["away_team"])
        matches.append(Match(
            source="libertadores",
            competition="libertadores",
            season=_parse_int(row["season"]),
            date=parse_date(row["datetime"]),
            home=row["home_team"], away=row["away_team"],
            home_base=home_base, away_base=away_base,
            home_state=home_state, away_state=away_state,
            home_goal=_parse_int(row["home_goal"]),
            away_goal=_parse_int(row["away_goal"]),
            stage=row.get("stage") or None,
        ))
    return matches


def _load_historical() -> list[Match]:
    matches = []
    for row in _read_csv("novo_campeonato_brasileiro.csv"):
        home_base, home_state = normalize_team(row["Equipe_mandante"])
        away_base, away_state = normalize_team(row["Equipe_visitante"])
        matches.append(Match(
            source="hist",
            competition="serie-a",
            season=_parse_int(row["Ano"]),
            date=parse_date(row["Data"]),
            home=row["Equipe_mandante"], away=row["Equipe_visitante"],
            home_base=home_base, away_base=away_base,
            home_state=home_state or row.get("Mandante_UF") or None,
            away_state=away_state or row.get("Visitante_UF") or None,
            home_goal=_parse_int(row["Gols_mandante"]),
            away_goal=_parse_int(row["Gols_visitante"]),
            stage=f"Round {row['Rodada']}" if row.get("Rodada") else None,
            extras={"stadium": row["Arena"]} if row.get("Arena") else {},
        ))
    return matches


_EXT_TOURNAMENTS = {
    "Serie A": "serie-a",
    "Serie B": "serie-b",
    "Serie C": "serie-c",
    "Copa do Brasil": "copa-do-brasil",
}


def _load_extended() -> list[Match]:
    matches = []
    for row in _read_csv("BR-Football-Dataset.csv"):
        home_base, home_state = normalize_team(row["home"])
        away_base, away_state = normalize_team(row["away"])
        match_date = parse_date(row.get("date"))
        extras = {}
        for key, col in [("home_corners", "home_corner"), ("away_corners", "away_corner"),
                         ("home_shots", "home_shots"), ("away_shots", "away_shots"),
                         ("home_attacks", "home_attack"), ("away_attacks", "away_attack")]:
            val = _parse_int(row.get(col))
            if val is not None:
                extras[key] = val
        matches.append(Match(
            source="ext",
            competition=_EXT_TOURNAMENTS.get(row["tournament"], row["tournament"].lower()),
            season=match_date.year if match_date else None,
            date=match_date,
            home=row["home"], away=row["away"],
            home_base=home_base, away_base=away_base,
            home_state=home_state, away_state=away_state,
            home_goal=_parse_int(row["home_goal"]),
            away_goal=_parse_int(row["away_goal"]),
            extras=extras,
        ))
    return matches


_SKILL_COLUMNS = [
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
    "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
    "GKKicking", "GKPositioning", "GKReflexes",
]


def _load_players() -> list[Player]:
    players = []
    for row in _read_csv("fifa_data.csv"):
        skills = {}
        for col in _SKILL_COLUMNS:
            val = _parse_int(row.get(col))
            if val is not None:
                skills[col] = val
        players.append(Player(
            player_id=row.get("ID", ""),
            name=row.get("Name", ""),
            age=_parse_int(row.get("Age")),
            nationality=row.get("Nationality", ""),
            overall=_parse_int(row.get("Overall")),
            potential=_parse_int(row.get("Potential")),
            club=row.get("Club") or "",
            position=row.get("Position") or "",
            jersey_number=_parse_int(row.get("Jersey Number")),
            height=row.get("Height") or "",
            weight=row.get("Weight") or "",
            value=row.get("Value") or "",
            wage=row.get("Wage") or "",
            preferred_foot=row.get("Preferred Foot") or "",
            skills=skills,
        ))
    return players


# Sources in priority order for de-duplicating the same real-world match
# appearing in multiple datasets (richer/dedicated files first).
_SOURCE_PRIORITY = ["brasileirao", "hist", "cup", "libertadores", "ext"]

# Preferred display names for clubs whose raw names vary the most.
_DISPLAY_OVERRIDES = {
    "athletico paranaense": "Athletico Paranaense",
    "atletico mineiro": "Atlético Mineiro",
    "atletico goianiense": "Atlético Goianiense",
    "america mineiro": "América Mineiro",
    "america rn": "América-RN",
    "vasco da gama": "Vasco da Gama",
    "sport recife": "Sport Recife",
    "sao paulo": "São Paulo",
    "gremio": "Grêmio",
    "goias": "Goiás",
    "avai": "Avaí",
    "ceara": "Ceará",
    "criciuma": "Criciúma",
    "nautico": "Náutico",
    "parana": "Paraná",
    "vitoria": "Vitória",
    "cuiaba": "Cuiabá",
    "sao caetano": "São Caetano",
    "santo andre": "Santo André",
    "csa": "CSA",
    "bragantino": "Red Bull Bragantino",
}

_STATE_SUFFIX_RE = re.compile(r"\s*-\s*[A-Z]{2}$| [A-Z]{2}$")


class SoccerDatabase:
    """In-memory database over all six CSV files."""

    def __init__(self):
        self.matches_by_source: dict[str, list[Match]] = {
            "brasileirao": _load_brasileirao(),
            "cup": _load_cup(),
            "libertadores": _load_libertadores(),
            "hist": _load_historical(),
            "ext": _load_extended(),
        }
        self.matches: list[Match] = self._deduplicate()
        self.players: list[Player] = _load_players()
        self.display_names: dict[str, str] = self._build_display_names()

    def _build_display_names(self) -> dict[str, str]:
        counts: dict[str, dict[str, int]] = {}
        for m in self.matches:
            for base, raw in ((m.home_base, m.home), (m.away_base, m.away)):
                cleaned = _STATE_SUFFIX_RE.sub("", raw).strip() or raw
                counts.setdefault(base, {})
                counts[base][cleaned] = counts[base].get(cleaned, 0) + 1
        names = {base: max(variants, key=variants.get)
                 for base, variants in counts.items()}
        names.update(_DISPLAY_OVERRIDES)
        return names

    def display_name(self, base: str) -> str:
        return self.display_names.get(base, base.title())

    def _deduplicate(self) -> list[Match]:
        # The same real-world match can appear in several datasets, and the
        # extended dataset records UTC dates (evening kick-offs roll over to
        # the next day), so duplicates are matched with a ±1 day tolerance.
        seen: set[tuple] = set()
        result: list[Match] = []
        one_day = timedelta(days=1)
        for source in _SOURCE_PRIORITY:
            for m in self.matches_by_source[source]:
                if m.date:
                    d = m.date.date()
                    fixture = (m.competition, m.home_base, m.away_base)
                    if any((dd, *fixture) in seen for dd in (d - one_day, d, d + one_day)):
                        continue
                    seen.add((d, *fixture))
                result.append(m)
        result.sort(key=lambda m: (m.date or datetime.min))
        return result


_db: Optional[SoccerDatabase] = None


def get_database() -> SoccerDatabase:
    global _db
    if _db is None:
        _db = SoccerDatabase()
    return _db
