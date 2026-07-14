"""Load the six Kaggle CSV files into an in-memory SoccerDatabase.

Handles the data-quality issues called out in the spec:
- multiple date formats (ISO, ISO with time, Brazilian DD/MM/YYYY)
- team name variations (delegated to :mod:`team_names`)
- UTF-8 / UTF-8-with-BOM encodings
- float-formatted goals ("1.0") and missing scores
"""

from __future__ import annotations

import csv
from collections import Counter
from datetime import date as Date
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from models import (
    COPA_DO_BRASIL,
    LIBERTADORES,
    SERIE_A,
    SERIE_B,
    SERIE_C,
    Match,
    Player,
)
from team_names import TeamKey, parse_team

DATA_DIR = Path(__file__).resolve().parent / "data" / "kaggle"

# When the same real-world match appears in several files, prefer the source
# earlier in this list (richer / cleaner data first).
SOURCE_PRIORITY = [
    "brasileirao",      # Brasileirao_Matches.csv
    "historico",        # novo_campeonato_brasileiro.csv
    "copa_do_brasil",   # Brazilian_Cup_Matches.csv
    "libertadores",     # Libertadores_Matches.csv
    "br_football",      # BR-Football-Dataset.csv
]

_SKILL_COLUMNS = [
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
    "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
    "GKKicking", "GKPositioning", "GKReflexes",
]


def parse_date(value: str) -> Optional[Date]:
    """Parse ISO ('2023-09-24'), ISO datetime and Brazilian ('29/03/2003')."""
    value = (value or "").strip()
    if not value:
        return None
    head = value[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(head, fmt).date()
        except ValueError:
            continue
    return None


def _parse_int(value) -> Optional[int]:
    """Parse '2', '2.0' or 2.0 to int; anything unparseable becomes None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _read_csv(path: Path) -> Iterator[dict]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


class SoccerDatabase:
    """In-memory knowledge graph over the Kaggle CSVs."""

    def __init__(self, matches: list[Match], players: list[Player]):
        self.matches = matches
        self.players = players
        # Most common display spelling for each team key string.
        spellings: dict[str, Counter] = {}
        for match in matches:
            for key, name in ((match.home_key, match.home_name),
                              (match.away_key, match.away_name)):
                spellings.setdefault(str(key), Counter())[name] += 1
        self._display = {
            key: counter.most_common(1)[0][0] for key, counter in spellings.items()
        }

    def display_name(self, key: TeamKey) -> str:
        """Best display spelling for a team key (falls back to title-case)."""
        name = self._display.get(str(key))
        if name:
            return name
        # A query key without a region may still match a single stored team.
        candidates = {
            stored: display for stored, display in self._display.items()
            if stored == key.base or stored.startswith(key.base + "/")
        }
        if len(candidates) == 1:
            return next(iter(candidates.values()))
        return key.base.title()

    def sources(self) -> dict[str, int]:
        counts: Counter = Counter(m.source for m in self.matches)
        return dict(counts)


# ---------------------------------------------------------------------------
# Per-file loaders
# ---------------------------------------------------------------------------

def _load_brasileirao(path: Path) -> list[Match]:
    """Brasileirao_Matches.csv — Série A with state suffixes and datetimes."""
    matches = []
    for row in _read_csv(path):
        home, away = row["home_team"], row["away_team"]
        if not home or not away:
            continue
        when = row.get("datetime", "")
        matches.append(Match(
            competition=SERIE_A,
            source="brasileirao",
            date=parse_date(when),
            time=when[11:16] or None if len(when) > 11 else None,
            season=_parse_int(row.get("season")),
            home_name=home, away_name=away,
            home_key=parse_team(home), away_key=parse_team(away),
            home_goals=_parse_int(row.get("home_goal")),
            away_goals=_parse_int(row.get("away_goal")),
            round=(row.get("round") or "").strip() or None,
        ))
    return matches


def _load_historico(path: Path) -> list[Match]:
    """novo_campeonato_brasileiro.csv — Série A 2003-2019, Brazilian dates."""
    matches = []
    for row in _read_csv(path):
        home, away = row["Equipe_mandante"], row["Equipe_visitante"]
        if not home or not away:
            continue
        matches.append(Match(
            competition=SERIE_A,
            source="historico",
            date=parse_date(row.get("Data", "")),
            season=_parse_int(row.get("Ano")),
            home_name=home, away_name=away,
            home_key=parse_team(home), away_key=parse_team(away),
            home_goals=_parse_int(row.get("Gols_mandante")),
            away_goals=_parse_int(row.get("Gols_visitante")),
            round=(row.get("Rodada") or "").strip() or None,
            extras={"stadium": (row.get("Arena") or "").strip() or None},
        ))
    return matches


_CUP_FINAL_ROUND = 8
_CUP_STAGES = {0: "Final", 1: "Semi-final", 2: "Quarter-final",
               3: "Round of 16"}


def _label_cup_stages(matches: list[Match]) -> None:
    """Name the late knockout rounds of the Copa do Brasil.

    Cup rounds are plain numbers 1-8.  For seasons whose data reaches the
    final (round 8) we can safely name the last rounds; incomplete seasons
    are left unlabeled rather than guessed at.
    """
    max_round: dict[int, int] = {}
    for match in matches:
        if match.season is not None and (match.round or "").isdigit():
            max_round[match.season] = max(max_round.get(match.season, 0),
                                          int(match.round))
    for match in matches:
        if (match.season is None or not (match.round or "").isdigit()
                or max_round.get(match.season) != _CUP_FINAL_ROUND):
            continue
        stage = _CUP_STAGES.get(_CUP_FINAL_ROUND - int(match.round))
        if stage:
            match.stage = stage


def _load_copa_do_brasil(path: Path) -> list[Match]:
    """Brazilian_Cup_Matches.csv — cup rounds, verbose team names."""
    matches = []
    for row in _read_csv(path):
        home, away = row["home_team"], row["away_team"]
        if not home or not away:
            continue
        when = row.get("datetime", "")
        matches.append(Match(
            competition=COPA_DO_BRASIL,
            source="copa_do_brasil",
            date=parse_date(when),
            time=when[11:16] or None if len(when) > 11 else None,
            season=_parse_int(row.get("season")),
            home_name=home, away_name=away,
            home_key=parse_team(home), away_key=parse_team(away),
            home_goals=_parse_int(row.get("home_goal")),
            away_goals=_parse_int(row.get("away_goal")),
            round=(row.get("round") or "").strip() or None,
        ))
    _label_cup_stages(matches)
    return matches


def _load_libertadores(path: Path) -> list[Match]:
    """Libertadores_Matches.csv — includes non-Brazilian clubs and stages."""
    matches = []
    for row in _read_csv(path):
        home, away = row["home_team"], row["away_team"]
        if not home or not away:
            continue
        when = row.get("datetime", "")
        matches.append(Match(
            competition=LIBERTADORES,
            source="libertadores",
            date=parse_date(when),
            time=when[11:16] or None if len(when) > 11 else None,
            season=_parse_int(row.get("season")),
            home_name=home, away_name=away,
            home_key=parse_team(home), away_key=parse_team(away),
            home_goals=_parse_int(row.get("home_goal")),
            away_goals=_parse_int(row.get("away_goal")),
            stage=(row.get("stage") or "").strip() or None,
        ))
    return matches


_BR_FOOTBALL_COMPETITIONS = {
    "Serie A": SERIE_A,
    "Serie B": SERIE_B,
    "Serie C": SERIE_C,
    "Copa do Brasil": COPA_DO_BRASIL,
}


def _load_br_football(path: Path) -> list[Match]:
    """BR-Football-Dataset.csv — extended stats (corners, shots, attacks)."""
    matches = []
    for row in _read_csv(path):
        home, away = row["home"], row["away"]
        if not home or not away:
            continue
        when = parse_date(row.get("date", ""))
        extras = {
            field: _parse_int(row.get(field))
            for field in ("home_corner", "away_corner", "home_attack",
                          "away_attack", "home_shots", "away_shots",
                          "total_corners")
        }
        matches.append(Match(
            competition=_BR_FOOTBALL_COMPETITIONS.get(
                row.get("tournament", "").strip(), row.get("tournament", "")),
            source="br_football",
            date=when,
            time=(row.get("time") or "")[:5] or None,
            season=when.year if when else None,
            home_name=home, away_name=away,
            home_key=parse_team(home), away_key=parse_team(away),
            home_goals=_parse_int(row.get("home_goal")),
            away_goals=_parse_int(row.get("away_goal")),
            extras=extras,
        ))
    return matches


def _load_players(path: Path) -> list[Player]:
    """fifa_data.csv — 18k players with ratings and skill attributes."""
    players = []
    for row in _read_csv(path):
        name = (row.get("Name") or "").strip()
        if not name:
            continue
        skills = {}
        for column in _SKILL_COLUMNS:
            rating = _parse_int(row.get(column))
            if rating is not None:
                skills[column] = rating
        players.append(Player(
            player_id=(row.get("ID") or "").strip(),
            name=name,
            age=_parse_int(row.get("Age")),
            nationality=(row.get("Nationality") or "").strip(),
            overall=_parse_int(row.get("Overall")),
            potential=_parse_int(row.get("Potential")),
            club=(row.get("Club") or "").strip(),
            position=(row.get("Position") or "").strip(),
            jersey_number=_parse_int(row.get("Jersey Number")),
            value=(row.get("Value") or "").strip(),
            wage=(row.get("Wage") or "").strip(),
            height=(row.get("Height") or "").strip(),
            weight=(row.get("Weight") or "").strip(),
            preferred_foot=(row.get("Preferred Foot") or "").strip(),
            skills=skills,
        ))
    return players


def load_database(data_dir: Path = DATA_DIR) -> SoccerDatabase:
    """Load all six CSV files and return the populated database."""
    matches: list[Match] = []
    matches += _load_brasileirao(data_dir / "Brasileirao_Matches.csv")
    matches += _load_historico(data_dir / "novo_campeonato_brasileiro.csv")
    matches += _load_copa_do_brasil(data_dir / "Brazilian_Cup_Matches.csv")
    matches += _load_libertadores(data_dir / "Libertadores_Matches.csv")
    matches += _load_br_football(data_dir / "BR-Football-Dataset.csv")
    players = _load_players(data_dir / "fifa_data.csv")
    return SoccerDatabase(matches, players)
