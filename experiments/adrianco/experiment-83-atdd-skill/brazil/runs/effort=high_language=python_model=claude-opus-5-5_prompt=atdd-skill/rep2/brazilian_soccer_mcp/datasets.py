"""
Loading the six provided Kaggle datasets into common records.

Each loader understands one file's own format - its columns, team-name style,
date format ("2012-05-19 18:30:00" vs "29/03/2003"), number format ("1.0" vs
"1") and missing-value markers ("NA", "-") - and produces RawMatch or Player
records with the original team names still attached. Team identity and
de-duplication across files happen later, in knowledge.py.

Files (all UTF-8, in the data directory, normally data/kaggle):
  Brasileirao_Matches.csv         Brasileirão Série A 2012-2022 (with rounds)
  Brazilian_Cup_Matches.csv       Copa do Brasil 2012-2021 (numbered rounds)
  Libertadores_Matches.csv        Copa Libertadores 2013-2022 (named stages)
  BR-Football-Dataset.csv         Série A/B/C + Copa do Brasil 2014-2023 with corners, shots, attacks
  novo_campeonato_brasileiro.csv  Brasileirão Série A 2003-2019 (with stadiums)
  fifa_data.csv                   FIFA 19 player database
"""
import csv
import dataclasses
import datetime
import pathlib

from . import competitions
from .text import parse_date, parse_int


@dataclasses.dataclass
class RawMatch:
    source: str
    competition: str
    season: int
    date: datetime.date | None
    home: str
    away: str
    home_goals: int
    away_goals: int
    round: int | None = None
    stage: str | None = None
    arena: str | None = None
    statistics: dict | None = None


@dataclasses.dataclass
class Player:
    id: int
    name: str
    age: int | None
    nationality: str
    overall: int
    potential: int | None
    club: str
    position: str
    jersey_number: int | None
    height: str
    weight: str
    value: str
    wage: str
    preferred_foot: str
    skills: dict

    def as_dict(self, club_display=None):
        data = dataclasses.asdict(self)
        if club_display:
            data["club"] = club_display
        return data


@dataclasses.dataclass
class DatasetInfo:
    name: str
    file: str
    description: str
    rows: int = 0
    loaded: bool = False
    problem: str | None = None


BRASILEIRAO = "Brasileirão matches"
COPA_DO_BRASIL = "Copa do Brasil matches"
LIBERTADORES = "Libertadores matches"
EXTENDED = "Extended match statistics"
HISTORICAL = "Historical Brasileirão"
FIFA = "FIFA players"

# Which dataset wins when several record the same match (lower is preferred)
PRIORITY = {BRASILEIRAO: 0, COPA_DO_BRASIL: 0, LIBERTADORES: 0, HISTORICAL: 1, EXTENDED: 2}

TOURNAMENTS = {"serie a": competitions.SERIE_A, "serie b": competitions.SERIE_B, "serie c": competitions.SERIE_C,
               "copa do brasil": competitions.COPA_DO_BRASIL}

FIFA_SKILLS = (
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling", "Curve", "FKAccuracy",
    "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance", "ShotPower",
    "Jumping", "Stamina", "Strength", "LongShots", "Aggression", "Interceptions", "Positioning", "Vision",
    "Penalties", "Composure", "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling", "GKKicking",
    "GKPositioning", "GKReflexes",
)


def load_all(data_dir):
    """Returns (matches, players, dataset infos). Missing or broken files are reported, not fatal."""
    data_dir = pathlib.Path(data_dir)
    loaders = [
        (BRASILEIRAO, "Brasileirao_Matches.csv", "Brasileirão Série A matches 2012-2022", _brasileirao),
        (COPA_DO_BRASIL, "Brazilian_Cup_Matches.csv", "Copa do Brasil matches 2012-2021", _copa_do_brasil),
        (LIBERTADORES, "Libertadores_Matches.csv", "Copa Libertadores matches 2013-2022", _libertadores),
        (EXTENDED, "BR-Football-Dataset.csv", "Série A/B/C and Copa do Brasil with match statistics", _extended),
        (HISTORICAL, "novo_campeonato_brasileiro.csv", "Brasileirão Série A matches 2003-2019", _historical),
        (FIFA, "fifa_data.csv", "FIFA 19 player ratings and attributes", _fifa),
    ]
    matches, players, infos = [], [], []
    for name, file_name, description, loader in loaders:
        info = DatasetInfo(name, file_name, description)
        infos.append(info)
        path = data_dir / file_name
        if not path.exists():
            info.problem = "file not found"
            continue
        try:
            with open(path, encoding="utf-8-sig", newline="") as source:
                rows = list(csv.DictReader(source))
        except (OSError, UnicodeDecodeError, csv.Error) as error:
            info.problem = str(error)
            continue
        info.rows, info.loaded = len(rows), True
        records = [record for record in (loader(row) for row in rows) if record is not None]
        (players if loader is _fifa else matches).extend(records)
    return matches, players, infos


def _goals(row, home_column, away_column):
    home, away = parse_int(row.get(home_column)), parse_int(row.get(away_column))
    return (home, away) if home is not None and away is not None else None


def _brasileirao(row):
    goals = _goals(row, "home_goal", "away_goal")
    date = parse_date(row.get("datetime"))
    if not goals or not row.get("home_team") or not row.get("away_team"):
        return None
    return RawMatch(BRASILEIRAO, competitions.SERIE_A, parse_int(row.get("season")) or date.year, date,
                    row["home_team"], row["away_team"], *goals, round=parse_int(row.get("round")))


def _copa_do_brasil(row):
    goals = _goals(row, "home_goal", "away_goal")
    date = parse_date(row.get("datetime"))
    if not goals or not row.get("home_team") or not row.get("away_team"):
        return None
    return RawMatch(COPA_DO_BRASIL, competitions.COPA_DO_BRASIL, parse_int(row.get("season")) or date.year, date,
                    row["home_team"], row["away_team"], *goals, round=parse_int(row.get("round")))


def _libertadores(row):
    goals = _goals(row, "home_goal", "away_goal")
    date = parse_date(row.get("datetime"))
    season = parse_int(row.get("season")) or (date.year if date else None)
    if not goals or not season or not row.get("home_team") or not row.get("away_team"):
        return None
    return RawMatch(LIBERTADORES, competitions.LIBERTADORES, season, date, row["home_team"].strip(),
                    row["away_team"].strip(), *goals,
                    stage=competitions.stage_name(row["stage"]) if row.get("stage") else None)


def _extended(row):
    goals = _goals(row, "home_goal", "away_goal")
    date = parse_date(row.get("date"))
    competition = TOURNAMENTS.get((row.get("tournament") or "").strip().lower())
    if not goals or not date or not competition or not row.get("home") or not row.get("away"):
        return None
    season = date.year
    if competition in competitions.LEAGUES and date.month <= 3:
        season -= 1  # league seasons that overran into the new year (e.g. 2020 ended in February 2021)
    statistics = {}
    for name, home_column, away_column in (("corners", "home_corner", "away_corner"),
                                           ("shots", "home_shots", "away_shots"),
                                           ("attacks", "home_attack", "away_attack")):
        pair = _goals(row, home_column, away_column)
        if pair:
            statistics[name] = list(pair)
    return RawMatch(EXTENDED, competition, season, date, row["home"].strip(), row["away"].strip(), *goals,
                    statistics=statistics or None)


def _historical(row):
    goals = _goals(row, "Gols_mandante", "Gols_visitante")
    date = parse_date(row.get("Data"))
    if not goals or not row.get("Equipe_mandante") or not row.get("Equipe_visitante"):
        return None
    # The state columns (Mandante_UF/Visitante_UF) are unreliable - e.g. Bahia is "BH", Vitória "ES" - and
    # every club whose name needs a state already carries it ("América-RN", "Atlético-GO"), so they are ignored.
    return RawMatch(HISTORICAL, competitions.SERIE_A, parse_int(row.get("Ano")) or date.year, date,
                    row["Equipe_mandante"].strip(), row["Equipe_visitante"].strip(), *goals,
                    round=parse_int(row.get("Rodada")), arena=(row.get("Arena") or "").strip() or None)


def _fifa(row):
    name = (row.get("Name") or "").strip()
    overall = parse_int(row.get("Overall"))
    if not name or overall is None:
        return None
    return Player(
        id=parse_int(row.get("ID")), name=name, age=parse_int(row.get("Age")),
        nationality=(row.get("Nationality") or "").strip(), overall=overall,
        potential=parse_int(row.get("Potential")), club=(row.get("Club") or "").strip(),
        position=(row.get("Position") or "").strip(), jersey_number=parse_int(row.get("Jersey Number")),
        height=row.get("Height") or "", weight=row.get("Weight") or "", value=row.get("Value") or "",
        wage=row.get("Wage") or "", preferred_foot=row.get("Preferred Foot") or "",
        skills={skill: parse_int(row.get(skill)) for skill in FIFA_SKILLS if parse_int(row.get(skill)) is not None},
    )
