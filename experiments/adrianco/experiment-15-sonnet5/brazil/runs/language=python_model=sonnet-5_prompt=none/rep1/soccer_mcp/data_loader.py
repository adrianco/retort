"""Loads the six provided CSV datasets into unified Match/Player records."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas as pd

from .models import Match, Player
from .team_names import normalize_team

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

COMPETITION_BRASILEIRAO = "Brasileirao Serie A"
COMPETITION_COPA_DO_BRASIL = "Copa do Brasil"
COMPETITION_LIBERTADORES = "Copa Libertadores"
COMPETITION_SERIE_B = "Serie B"
COMPETITION_SERIE_C = "Serie C"


def _to_date(series: pd.Series, dayfirst: bool = False) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", dayfirst=dayfirst).dt.date


def _clean_int(value) -> int | None:
    if pd.isna(value):
        return None
    return int(value)


def load_brasileirao_matches(path: Path) -> list[Match]:
    df = pd.read_csv(path, encoding="utf-8")
    df = df.dropna(subset=["home_goal", "away_goal"])
    dates = _to_date(df["datetime"])
    matches = []
    for row, match_date in zip(df.itertuples(index=False), dates):
        home_key, home_name = normalize_team(row.home_team)
        away_key, away_name = normalize_team(row.away_team)
        matches.append(
            Match(
                source="brasileirao",
                competition=COMPETITION_BRASILEIRAO,
                season=_clean_int(row.season),
                match_date=match_date,
                home_team_key=home_key,
                home_team=home_name,
                away_team_key=away_key,
                away_team=away_name,
                home_goal=int(row.home_goal),
                away_goal=int(row.away_goal),
                round=str(row.round),
                home_team_raw=row.home_team,
                away_team_raw=row.away_team,
            )
        )
    return matches


def load_copa_do_brasil_matches(path: Path) -> list[Match]:
    df = pd.read_csv(path, encoding="utf-8")
    df = df.dropna(subset=["home_goal", "away_goal"])
    dates = _to_date(df["datetime"])
    matches = []
    for row, match_date in zip(df.itertuples(index=False), dates):
        home_key, home_name = normalize_team(row.home_team)
        away_key, away_name = normalize_team(row.away_team)
        matches.append(
            Match(
                source="copa_do_brasil",
                competition=COMPETITION_COPA_DO_BRASIL,
                season=_clean_int(row.season),
                match_date=match_date,
                home_team_key=home_key,
                home_team=home_name,
                away_team_key=away_key,
                away_team=away_name,
                home_goal=int(row.home_goal),
                away_goal=int(row.away_goal),
                round=str(row.round),
                home_team_raw=row.home_team,
                away_team_raw=row.away_team,
            )
        )
    return matches


def load_libertadores_matches(path: Path) -> list[Match]:
    df = pd.read_csv(path, encoding="utf-8")
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df = df.dropna(subset=["home_goal", "away_goal", "datetime", "season"])
    dates = _to_date(df["datetime"])
    matches = []
    for row, match_date in zip(df.itertuples(index=False), dates):
        home_key, home_name = normalize_team(row.home_team)
        away_key, away_name = normalize_team(row.away_team)
        matches.append(
            Match(
                source="libertadores",
                competition=COMPETITION_LIBERTADORES,
                season=_clean_int(row.season),
                match_date=match_date,
                home_team_key=home_key,
                home_team=home_name,
                away_team_key=away_key,
                away_team=away_name,
                home_goal=int(row.home_goal),
                away_goal=int(row.away_goal),
                stage=row.stage,
                home_team_raw=row.home_team,
                away_team_raw=row.away_team,
            )
        )
    return matches


_TOURNAMENT_TO_COMPETITION = {
    "Serie A": COMPETITION_BRASILEIRAO,
    "Serie B": COMPETITION_SERIE_B,
    "Serie C": COMPETITION_SERIE_C,
    "Copa do Brasil": COMPETITION_COPA_DO_BRASIL,
}


def load_br_football_dataset(path: Path) -> list[Match]:
    df = pd.read_csv(path, encoding="utf-8")
    df = df.dropna(subset=["home_goal", "away_goal", "date"])
    dates = _to_date(df["date"])
    matches = []
    for row, match_date in zip(df.itertuples(index=False), dates):
        home_key, home_name = normalize_team(row.home)
        away_key, away_name = normalize_team(row.away)
        competition = _TOURNAMENT_TO_COMPETITION.get(row.tournament, row.tournament)
        season = match_date.year if match_date else None
        matches.append(
            Match(
                source="br_football_dataset",
                competition=competition,
                season=season,
                match_date=match_date,
                home_team_key=home_key,
                home_team=home_name,
                away_team_key=away_key,
                away_team=away_name,
                home_goal=int(row.home_goal),
                away_goal=int(row.away_goal),
                home_team_raw=row.home,
                away_team_raw=row.away,
                extra={
                    "home_corner": _clean_int(row.home_corner),
                    "away_corner": _clean_int(row.away_corner),
                    "home_shots": _clean_int(row.home_shots),
                    "away_shots": _clean_int(row.away_shots),
                    "total_corners": _clean_int(row.total_corners),
                    "ht_result": row.ht_result,
                    "at_result": row.at_result,
                },
            )
        )
    return matches


def load_historical_brasileirao(path: Path) -> list[Match]:
    df = pd.read_csv(path, encoding="utf-8")
    df = df.dropna(subset=["Gols_mandante", "Gols_visitante"])
    dates = _to_date(df["Data"], dayfirst=True)
    matches = []
    for row, match_date in zip(df.itertuples(index=False), dates):
        home_key, home_name = normalize_team(row.Equipe_mandante)
        away_key, away_name = normalize_team(row.Equipe_visitante)
        matches.append(
            Match(
                source="historical_brasileirao",
                competition=COMPETITION_BRASILEIRAO,
                season=_clean_int(row.Ano),
                match_date=match_date,
                home_team_key=home_key,
                home_team=home_name,
                away_team_key=away_key,
                away_team=away_name,
                home_goal=int(row.Gols_mandante),
                away_goal=int(row.Gols_visitante),
                round=str(row.Rodada),
                venue=row.Arena,
                home_team_raw=row.Equipe_mandante,
                away_team_raw=row.Equipe_visitante,
            )
        )
    return matches


_FIFA_ATTRIBUTE_COLUMNS = [
    "Crossing",
    "Finishing",
    "HeadingAccuracy",
    "ShortPassing",
    "Dribbling",
    "LongPassing",
    "BallControl",
    "Acceleration",
    "SprintSpeed",
    "ShotPower",
    "Stamina",
    "Strength",
    "LongShots",
    "Vision",
    "Penalties",
    "Marking",
    "StandingTackle",
    "SlidingTackle",
    "GKDiving",
    "GKReflexes",
]


def load_fifa_players(path: Path) -> list[Player]:
    df = pd.read_csv(path, encoding="utf-8")
    df.columns = [c.strip().lstrip("﻿") for c in df.columns]
    players = []
    for row_dict in df.to_dict(orient="records"):
        attributes = {
            col: _clean_int(row_dict[col])
            for col in _FIFA_ATTRIBUTE_COLUMNS
            if col in row_dict
        }
        players.append(
            Player(
                player_id=_clean_int(row_dict.get("ID")),
                name=str(row_dict.get("Name", "")).strip(),
                age=_clean_int(row_dict.get("Age")),
                nationality=str(row_dict.get("Nationality", "")).strip(),
                overall=_clean_int(row_dict.get("Overall")),
                potential=_clean_int(row_dict.get("Potential")),
                club=str(row_dict.get("Club", "")).strip() if not pd.isna(row_dict.get("Club")) else "",
                position=(str(row_dict.get("Position", "")).strip() or None)
                if not pd.isna(row_dict.get("Position"))
                else None,
                jersey_number=_clean_int(row_dict.get("Jersey Number")),
                height=str(row_dict.get("Height")) if not pd.isna(row_dict.get("Height")) else None,
                weight=str(row_dict.get("Weight")) if not pd.isna(row_dict.get("Weight")) else None,
                attributes=attributes,
            )
        )
    return players


class SoccerData:
    """Container for every loaded match and player record."""

    def __init__(self, matches: list[Match], players: list[Player]):
        self.matches = matches
        self.players = players


# Brasileirao_Matches.csv, novo_campeonato_brasileiro.csv and the "Serie A"
# rows of BR-Football-Dataset.csv all describe the same real-world
# Brasileirao matches for overlapping seasons (likewise Brazilian_Cup_Matches
# .csv and the "Copa do Brasil" rows of BR-Football-Dataset.csv). Loading
# every source verbatim would count the same match 2-3x in any aggregate
# query. For seasons covered by more than one source, keep only the
# highest-priority source instead of merging every row.
_SOURCE_PRIORITY = {
    COMPETITION_BRASILEIRAO: ["brasileirao", "historical_brasileirao", "br_football_dataset"],
    COMPETITION_COPA_DO_BRASIL: ["copa_do_brasil", "br_football_dataset"],
}


def _dedupe_overlapping_sources(matches: list[Match]) -> list[Match]:
    seasons_by_competition_source: dict[tuple[str, str], set[int]] = defaultdict(set)
    for m in matches:
        if m.season is not None:
            seasons_by_competition_source[(m.competition, m.source)].add(m.season)

    chosen_source: dict[tuple[str, int], str] = {}
    for competition, priority in _SOURCE_PRIORITY.items():
        all_seasons = {
            season
            for source in priority
            for season in seasons_by_competition_source.get((competition, source), set())
        }
        for season in all_seasons:
            for source in priority:
                if season in seasons_by_competition_source.get((competition, source), set()):
                    chosen_source[(competition, season)] = source
                    break

    def _keep(m: Match) -> bool:
        if m.competition not in _SOURCE_PRIORITY or m.season is None:
            return True
        return chosen_source.get((m.competition, m.season)) == m.source

    return [m for m in matches if _keep(m)]


def load_all(data_dir: Path | str | None = None) -> SoccerData:
    data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    matches: list[Match] = []
    matches += load_brasileirao_matches(data_dir / "Brasileirao_Matches.csv")
    matches += load_copa_do_brasil_matches(data_dir / "Brazilian_Cup_Matches.csv")
    matches += load_libertadores_matches(data_dir / "Libertadores_Matches.csv")
    matches += load_br_football_dataset(data_dir / "BR-Football-Dataset.csv")
    matches += load_historical_brasileirao(data_dir / "novo_campeonato_brasileiro.csv")
    matches = _dedupe_overlapping_sources(matches)
    players = load_fifa_players(data_dir / "fifa_data.csv")
    return SoccerData(matches=matches, players=players)
