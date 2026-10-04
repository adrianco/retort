"""Loading of the Kaggle CSV files into unified ``Match`` and player records."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .normalize import (
    BRASILEIRAO, COPA_DO_BRASIL, LIBERTADORES, SERIE_B, SERIE_C,
    TeamRegistry, parse_datetime,
)

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

MATCH_FILES = (
    "Brasileirao_Matches.csv",
    "novo_campeonato_brasileiro.csv",
    "Brazilian_Cup_Matches.csv",
    "Libertadores_Matches.csv",
    "BR-Football-Dataset.csv",
)
PLAYER_FILE = "fifa_data.csv"

_BR_FOOTBALL_TOURNAMENTS = {
    "Serie A": BRASILEIRAO, "Serie B": SERIE_B, "Serie C": SERIE_C,
    "Copa do Brasil": COPA_DO_BRASIL,
}


@dataclass
class Match:
    competition: str
    season: int
    date: date | None
    home: str
    away: str
    home_goals: int
    away_goals: int
    time: str | None = None
    round: str | None = None
    stage: str | None = None
    arena: str | None = None
    stats: dict = field(default_factory=dict)
    sources: list = field(default_factory=list)

    @property
    def winner(self) -> str | None:
        if self.home_goals == self.away_goals:
            return None
        return self.home if self.home_goals > self.away_goals else self.away

    @property
    def margin(self) -> int:
        return abs(self.home_goals - self.away_goals)

    @property
    def total_goals(self) -> int:
        return self.home_goals + self.away_goals

    def involves(self, team: str) -> bool:
        return team == self.home or team == self.away

    def to_dict(self) -> dict:
        return {
            "competition": self.competition, "season": self.season,
            "date": self.date.isoformat() if self.date else None, "time": self.time,
            "home_team": self.home, "away_team": self.away,
            "home_goals": self.home_goals, "away_goals": self.away_goals,
            "round": self.round, "stage": self.stage, "arena": self.arena,
            "stats": dict(self.stats), "sources": list(self.sources),
        }


def _read_csv(path: Path) -> list[dict]:
    # utf-8-sig: fifa_data.csv starts with a BOM; harmless for the others.
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _to_int(value) -> int | None:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _clean(value) -> str | None:
    text = (value or "").strip()
    return text if text and text.upper() != "NA" else None


def _raw_rows(data_dir: Path):
    """Yield one uniform dict per CSV row of every match file."""
    for row in _read_csv(data_dir / "Brasileirao_Matches.csv"):
        yield dict(source="Brasileirao_Matches.csv", competition=BRASILEIRAO,
                   when=row["datetime"], home=row["home_team"], away=row["away_team"],
                   hg=row["home_goal"], ag=row["away_goal"], season=row["season"],
                   round=_clean(row["round"]))
    for row in _read_csv(data_dir / "novo_campeonato_brasileiro.csv"):
        yield dict(source="novo_campeonato_brasileiro.csv", competition=BRASILEIRAO,
                   when=row["Data"], home=row["Equipe_mandante"], away=row["Equipe_visitante"],
                   hg=row["Gols_mandante"], ag=row["Gols_visitante"], season=row["Ano"],
                   round=_clean(row["Rodada"]), arena=_clean(row["Arena"]))
    for row in _read_csv(data_dir / "Brazilian_Cup_Matches.csv"):
        yield dict(source="Brazilian_Cup_Matches.csv", competition=COPA_DO_BRASIL,
                   when=row["datetime"], home=row["home_team"], away=row["away_team"],
                   hg=row["home_goal"], ag=row["away_goal"], season=row["season"],
                   round=_clean(row["round"]))
    for row in _read_csv(data_dir / "Libertadores_Matches.csv"):
        yield dict(source="Libertadores_Matches.csv", competition=LIBERTADORES,
                   when=row["datetime"], home=row["home_team"], away=row["away_team"],
                   hg=row["home_goal"], ag=row["away_goal"], season=row["season"],
                   stage=_clean(row["stage"]))
    stat_columns = ("home_corner", "away_corner", "home_attack", "away_attack",
                    "home_shots", "away_shots", "total_corners")
    for row in _read_csv(data_dir / "BR-Football-Dataset.csv"):
        competition = _BR_FOOTBALL_TOURNAMENTS.get(row["tournament"].strip(), row["tournament"].strip())
        stats = {c: _to_int(row[c]) for c in stat_columns if _to_int(row.get(c)) is not None}
        for key in ("ht_result", "at_result"):
            if _clean(row.get(key)):
                stats[key] = row[key].strip()
        yield dict(source="BR-Football-Dataset.csv", competition=competition,
                   when=f"{row['date']} {row['time']}".strip(), home=row["home"], away=row["away"],
                   hg=row["home_goal"], ag=row["away_goal"], season=None, stats=stats)


def _infer_season(day: date, competition: str) -> int:
    # The pandemic-delayed 2020 season finished in early 2021: the leagues in
    # January/February, the Copa do Brasil with its final on 7 March.
    end = date(2021, 3, 7) if competition == COPA_DO_BRASIL else date(2021, 3, 15)
    if date(2021, 1, 1) <= day <= end:
        return 2020
    return day.year


def load_matches(data_dir: Path = DEFAULT_DATA_DIR) -> tuple[list[Match], TeamRegistry, dict]:
    """Load, normalise and de-duplicate every match file.

    The same fixture often appears in several files (e.g. Brasileirão 2012-2019
    is in three of them).  Duplicates are merged into one ``Match`` that lists
    all its ``sources`` so statistics are not double counted.
    """
    rows = list(_raw_rows(Path(data_dir)))
    registry = TeamRegistry()
    for row in rows:
        registry.observe(row["home"])
        registry.observe(row["away"])

    matches: list[Match] = []
    index: dict[tuple, list[Match]] = {}
    report = {name: {"rows": 0, "skipped": 0, "merged": 0} for name in MATCH_FILES}

    for row in rows:
        counts = report[row["source"]]
        counts["rows"] += 1
        when = parse_datetime(row["when"])
        home_goals, away_goals = _to_int(row["hg"]), _to_int(row["ag"])
        season = _to_int(row["season"]) or (_infer_season(when.date(), row["competition"]) if when else None)
        if home_goals is None or away_goals is None or season is None:
            counts["skipped"] += 1  # unplayed fixture or unusable row
            continue
        day = when.date() if when else None
        if (row["season"] is None and row["competition"] == BRASILEIRAO and day
                and day.month <= 3 and season == day.year):
            counts["skipped"] += 1  # Serie A is never played Jan-Mar: mislabelled row
            continue
        has_time = when is not None and (when.hour or when.minute)
        home, away = registry.add(row["home"]), registry.add(row["away"])
        key = (row["competition"], home, away)

        duplicate, repeated = None, False
        for other in index.get(key, ()):
            if row["source"] in other.sources:
                # Some files repeat a row with the date shifted by a day.
                if (day and other.date and abs((day - other.date).days) <= 1
                        and (home_goals, away_goals) == (other.home_goals, other.away_goals)):
                    repeated = True
                    break
                continue
            close = day and other.date and abs((day - other.date).days) <= 2
            # A Serie A pairing is played once per season at each ground, so a
            # rescheduled fixture still matches even when the dates disagree.
            same_season = row["competition"] == BRASILEIRAO and other.season == season
            if close or same_season:
                duplicate = other
                break
        if repeated:
            counts["skipped"] += 1
            continue
        if duplicate is not None:
            counts["merged"] += 1
            duplicate.sources.append(row["source"])
            duplicate.round = duplicate.round or row.get("round")
            duplicate.stage = duplicate.stage or row.get("stage")
            duplicate.arena = duplicate.arena or row.get("arena")
            duplicate.date = duplicate.date or day
            if not duplicate.stats and row.get("stats"):
                duplicate.stats = row["stats"]
            continue

        match = Match(
            competition=row["competition"], season=season, date=day,
            home=home, away=away, home_goals=home_goals, away_goals=away_goals,
            time=when.strftime("%H:%M") if has_time else None,
            round=row.get("round"), stage=row.get("stage"), arena=row.get("arena"),
            stats=row.get("stats") or {}, sources=[row["source"]],
        )
        matches.append(match)
        index.setdefault(key, []).append(match)

    return matches, registry, report


_PLAYER_INT_FIELDS = ("Age", "Overall", "Potential", "Jersey Number", "Skill Moves", "Weak Foot",
                      "International Reputation")
_SKILLS = ("Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling",
           "Curve", "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed",
           "Agility", "Reactions", "Balance", "ShotPower", "Jumping", "Stamina", "Strength",
           "LongShots", "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
           "Composure", "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
           "GKKicking", "GKPositioning", "GKReflexes")


def load_players(data_dir: Path = DEFAULT_DATA_DIR) -> list[dict]:
    """Load the FIFA player database as a list of tidy dicts."""
    players = []
    for row in _read_csv(Path(data_dir) / PLAYER_FILE):
        player = {
            "id": _to_int(row["ID"]),
            "name": row["Name"].strip(),
            "nationality": row["Nationality"].strip(),
            "club": _clean(row["Club"]),
            "position": _clean(row["Position"]),
            "height": _clean(row["Height"]),
            "weight": _clean(row["Weight"]),
            "preferred_foot": _clean(row["Preferred Foot"]),
            "value": _clean(row["Value"]),
            "wage": _clean(row["Wage"]),
            "skills": {s: _to_int(row[s]) for s in _SKILLS if _to_int(row.get(s)) is not None},
        }
        for column in _PLAYER_INT_FIELDS:
            player[column.lower().replace(" ", "_")] = _to_int(row[column])
        players.append(player)
    return players
