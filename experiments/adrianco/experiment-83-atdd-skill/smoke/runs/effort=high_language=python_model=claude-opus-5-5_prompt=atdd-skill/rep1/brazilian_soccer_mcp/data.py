"""
Loading the provided Kaggle datasets into one consistent model.

Reads all six CSV files (UTF-8, with or without BOM), parses their
different date formats ("2023-09-24", "29/03/2003", "2012-05-19 18:30:00"),
maps every team name to a stable identity via `teams.TeamRegistry`, and
merges the match files. The Brasileirão and Copa do Brasil are covered by
more than one file, so a match already loaded from a higher-priority file
is not loaded twice; the later copy only contributes its extra statistics
(corners, shots, attacks).
"""

import csv
import datetime
import os
from dataclasses import dataclass, field
from pathlib import Path

from .teams import TeamRegistry, fold, identify

SERIE_A = "Brasileirão Série A"
SERIE_B = "Brasileirão Série B"
SERIE_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"
COMPETITIONS = [SERIE_A, SERIE_B, SERIE_C, COPA_DO_BRASIL, LIBERTADORES]
LEAGUES = {SERIE_A, SERIE_B, SERIE_C}
DOMESTIC = {SERIE_A, SERIE_B, SERIE_C, COPA_DO_BRASIL}

BRASILEIRAO_FILE = "Brasileirao_Matches.csv"
HISTORICAL_FILE = "novo_campeonato_brasileiro.csv"
CUP_FILE = "Brazilian_Cup_Matches.csv"
LIBERTADORES_FILE = "Libertadores_Matches.csv"
EXTENDED_FILE = "BR-Football-Dataset.csv"
FIFA_FILE = "fifa_data.csv"
ALL_FILES = [BRASILEIRAO_FILE, CUP_FILE, LIBERTADORES_FILE, EXTENDED_FILE, HISTORICAL_FILE, FIFA_FILE]

EXTENDED_TOURNAMENTS = {"serie a": SERIE_A, "serie b": SERIE_B, "serie c": SERIE_C,
                        "copa do brasil": COPA_DO_BRASIL}

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"


@dataclass
class Match:
    date: datetime.date
    home: str
    away: str
    home_goals: int
    away_goals: int
    competition: str
    season: int
    source: str
    round: str = None
    stage: str = None
    kickoff: str = None
    arena: str = None
    stats: dict = None

    @property
    def total_goals(self):
        return self.home_goals + self.away_goals

    @property
    def winner(self):
        if self.home_goals > self.away_goals:
            return self.home
        if self.away_goals > self.home_goals:
            return self.away
        return None

    def involves(self, team):
        return team in (self.home, self.away)


@dataclass
class Player:
    id: str
    name: str
    age: int
    nationality: str
    overall: int
    potential: int
    club: str
    club_key: str
    position: str
    jersey_number: str
    height: str
    weight: str
    preferred_foot: str
    value: str
    wage: str
    skills: dict = field(default_factory=dict)


@dataclass
class FileReport:
    file: str
    rows: int = 0
    loaded: bool = False
    skipped: int = 0
    duplicates: int = 0
    error: str = None


PLAYER_SKILLS = ["Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling", "Curve",
                 "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Agility",
                 "Reactions", "Balance", "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
                 "Aggression", "Interceptions", "Positioning", "Vision", "Penalties", "Composure", "Marking",
                 "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling", "GKKicking", "GKPositioning",
                 "GKReflexes"]


def parse_date(text):
    """Parse ISO, ISO-with-time or Brazilian DD/MM/YYYY dates; None if absent or unparseable."""
    text = (text or "").strip()
    if not text or text.upper() == "NA":
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M"):
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _goals(text):
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _number(text):
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


class SoccerData:
    """All matches and players from one data directory."""

    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir or os.environ.get("SOCCER_DATA_DIR") or DEFAULT_DATA_DIR)
        self.teams = TeamRegistry()
        self.matches = []
        self.players = []
        self.files = {name: FileReport(name) for name in ALL_FILES}
        self._league_index = {}
        self._cup_index = {}
        self._unplayed = {}
        self._latest_played = {}
        self._serie_a_teams = set()
        self._load()

    # -- loading -----------------------------------------------------------

    def _load(self):
        loaders = [
            (BRASILEIRAO_FILE, self._load_brasileirao),
            (HISTORICAL_FILE, self._load_historical),
            (CUP_FILE, self._load_cup),
            (LIBERTADORES_FILE, self._load_libertadores),
            (EXTENDED_FILE, self._load_extended),
            (FIFA_FILE, self._load_players),
        ]
        for name, loader in loaders:
            report = self.files[name]
            path = self.data_dir / name
            if not path.exists():
                report.error = "file not found"
                continue
            try:
                with open(path, encoding="utf-8-sig", newline="") as f:
                    for row in csv.DictReader(f):
                        report.rows += 1
                        loader(row, report)
                report.loaded = True
            except (OSError, csv.Error, UnicodeDecodeError) as error:
                report.error = str(error)
        self.matches.sort(key=lambda m: (m.date or datetime.date.min, m.kickoff or ""))
        self.brazilian_clubs = {key for m in self.matches if m.competition in DOMESTIC for key in (m.home, m.away)}

    def _add(self, report, home, away, home_goals, away_goals, competition, season, date, **extra):
        if not home or not away or season is None:
            report.skipped += 1
            return
        if home_goals is None or away_goals is None:
            report.skipped += 1
            if competition in LEAGUES:
                fixture = (competition, season, self.teams.register(home), self.teams.register(away))
                self._unplayed.setdefault(fixture, (report.file, date, extra.get("kickoff")))
            return
        match = Match(date=date, home=self.teams.register(home), away=self.teams.register(away),
                      home_goals=home_goals, away_goals=away_goals, competition=competition, season=season,
                      source=report.file, **extra)
        if self._recorded_as_unplayed(match) or self._mislabelled(match):
            report.skipped += 1
            return
        existing = self._find_existing(match)
        if existing is not None:
            report.duplicates += 1
            if match.stats and not existing.stats:
                existing.stats = match.stats
            return
        self._index(match)
        self.matches.append(match)

    def _candidate_seasons(self, match):
        """League seasons a match could belong to: the extended file only gives a date, and some
        seasons (e.g. 2020) finished in the first months of the following year."""
        if match.source == EXTENDED_FILE and match.date and match.date.month <= 3:
            return [match.season - 1, match.season]
        return [match.season]

    def _recorded_as_unplayed(self, match):
        """A fixture another file lists without a result even though that file has results from the
        same kick-off or later — so it was never played (Chapecoense v Atlético-MG, 2016), rather than
        simply not played yet when that file was compiled (the end of 2022)."""
        for season in self._candidate_seasons(match):
            unplayed = self._unplayed.get((match.competition, season, match.home, match.away))
            if unplayed is None or unplayed[0] == match.source or unplayed[1] is None:
                continue
            source, date, kickoff = unplayed
            latest = self._latest_played.get((source, match.competition, season))
            if latest is not None and latest >= (date, kickoff or ""):
                return True
        return False

    def _mislabelled(self, match):
        """An extended-file Série A match between two teams that never appear in the dedicated Série A
        files (e.g. the regional Brasília v CA Taguatinga tagged as Série A)."""
        if match.source != EXTENDED_FILE or match.competition != SERIE_A or not self._serie_a_teams:
            return False
        return match.home not in self._serie_a_teams and match.away not in self._serie_a_teams

    def _find_existing(self, match):
        if match.competition in LEAGUES:
            for season in self._candidate_seasons(match):
                existing = self._league_index.get((match.competition, season, match.home, match.away))
                if existing is not None and existing.source != match.source:
                    if season != match.season:
                        match.season = season
                    return existing
            return None
        for existing in self._cup_index.get((match.competition, match.home, match.away), []):
            if existing.source != match.source and existing.date and match.date \
                    and abs((existing.date - match.date).days) <= 3:
                return existing
        return None

    def _index(self, match):
        if match.competition in LEAGUES:
            self._league_index.setdefault((match.competition, match.season, match.home, match.away), match)
            if match.source != EXTENDED_FILE and match.competition == SERIE_A:
                self._serie_a_teams.update((match.home, match.away))
            if match.date:
                key = (match.source, match.competition, match.season)
                self._latest_played[key] = max(self._latest_played.get(key, (match.date, "")),
                                               (match.date, match.kickoff or ""))
        else:
            self._cup_index.setdefault((match.competition, match.home, match.away), []).append(match)

    def _load_brasileirao(self, row, report):
        date = parse_date(row["datetime"])
        self._add(report, row["home_team"], row["away_team"], _goals(row["home_goal"]), _goals(row["away_goal"]),
                  SERIE_A, _number(row["season"]), date, round=row.get("round") or None,
                  kickoff=_kickoff(row["datetime"]))

    def _load_historical(self, row, report):
        date = parse_date(row["Data"])
        self._add(report, row["Equipe_mandante"], row["Equipe_visitante"], _goals(row["Gols_mandante"]),
                  _goals(row["Gols_visitante"]), SERIE_A, _number(row["Ano"]), date,
                  round=row.get("Rodada") or None, arena=row.get("Arena") or None)

    def _load_cup(self, row, report):
        date = parse_date(row["datetime"])
        self._add(report, row["home_team"], row["away_team"], _goals(row["home_goal"]), _goals(row["away_goal"]),
                  COPA_DO_BRASIL, _number(row["season"]), date, round=row.get("round") or None,
                  kickoff=_kickoff(row["datetime"]))

    def _load_libertadores(self, row, report):
        date = parse_date(row["datetime"])
        self._add(report, row["home_team"], row["away_team"], _goals(row["home_goal"]), _goals(row["away_goal"]),
                  LIBERTADORES, _number(row["season"]), date, stage=(row.get("stage") or "").strip() or None,
                  kickoff=_kickoff(row["datetime"]))

    def _load_extended(self, row, report):
        competition = EXTENDED_TOURNAMENTS.get(fold(row["tournament"]))
        date = parse_date(row["date"])
        if competition is None or date is None:
            report.skipped += 1
            return
        stats = {}
        for name, column in [("corners", "corner"), ("attacks", "attack"), ("shots", "shots")]:
            home, away = _number(row.get(f"home_{column}")), _number(row.get(f"away_{column}"))
            if home is not None and away is not None:
                stats[f"home_{name}"], stats[f"away_{name}"] = home, away
        self._add(report, row["home"], row["away"], _goals(row["home_goal"]), _goals(row["away_goal"]),
                  competition, date.year, date, kickoff=row.get("time") or None, stats=stats or None)

    def _load_players(self, row, report):
        name = (row.get("Name") or "").strip()
        if not name:
            report.skipped += 1
            return
        club = (row.get("Club") or "").strip()
        self.players.append(Player(
            id=row.get("ID"), name=name, age=_number(row.get("Age")), nationality=(row.get("Nationality") or "").strip(),
            overall=_number(row.get("Overall")) or 0, potential=_number(row.get("Potential")),
            club=club, club_key=identify(club)[0] if club else "", position=(row.get("Position") or "").strip(),
            jersey_number=_text_number(row.get("Jersey Number")), height=row.get("Height") or None,
            weight=row.get("Weight") or None, preferred_foot=row.get("Preferred Foot") or None,
            value=row.get("Value") or None, wage=row.get("Wage") or None,
            skills={s: _number(row[s]) for s in PLAYER_SKILLS if _number(row.get(s)) is not None},
        ))


def _kickoff(text):
    text = (text or "").strip()
    return text[11:16] if len(text) >= 16 else None


def _text_number(text):
    number = _number(text)
    return str(number) if number is not None else None
