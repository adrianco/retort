"""
================================================================================
Context: Brazilian Soccer MCP Server
Module:   brazilian_soccer.data_loader
--------------------------------------------------------------------------------
Purpose:
    Read the six raw CSV files in data/kaggle/ and turn each row into a unified
    ``Match`` or ``Player`` value object. Every file has a different schema,
    column order, encoding quirk and naming convention, so there is one small
    reader per file. All readers funnel team names through normalize.* so the
    downstream knowledge graph sees a single team identity.

    Files handled:
        Brasileirao_Matches.csv         -> Brasileirao matches (state suffixes)
        Brazilian_Cup_Matches.csv       -> Copa do Brasil matches
        Libertadores_Matches.csv        -> Copa Libertadores matches (stages)
        BR-Football-Dataset.csv         -> extended stats (corners/shots/...)
        novo_campeonato_brasileiro.csv  -> historical Brasileirao (PT columns)
        fifa_data.csv                   -> FIFA player database

Dependencies: standard library only (csv, os).
================================================================================
"""

from __future__ import annotations

import csv
import os
from typing import Iterator

from .models import Match, Player
from .normalize import normalize_team, parse_date, team_key, to_int

# Default location of the bundled datasets, resolved relative to this file so
# the loader works regardless of the process working directory.
_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(_PACKAGE_DIR), "data", "kaggle")


def _open_csv(path: str) -> Iterator[dict]:
    """Yield rows of a CSV as dicts, tolerant of a UTF-8 BOM."""
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        yield from csv.DictReader(fh)


def _make_match(home_raw, away_raw, hg, ag, **kw) -> Match:
    """Build a Match, applying team normalisation and int coercion once."""
    return Match(
        home_team=normalize_team(home_raw),
        away_team=normalize_team(away_raw),
        home_key=team_key(home_raw),
        away_key=team_key(away_raw),
        home_goal=to_int(hg),
        away_goal=to_int(ag),
        **kw,
    )


def load_brasileirao(path: str) -> list[Match]:
    out = []
    for row in _open_csv(path):
        out.append(_make_match(
            row["home_team"], row["away_team"], row["home_goal"], row["away_goal"],
            competition="Brasileirao",
            season=to_int(row.get("season")),
            match_date=parse_date(row.get("datetime")),
            round=row.get("round") or None,
            source="Brasileirao_Matches.csv",
        ))
    return out


def load_cup(path: str) -> list[Match]:
    out = []
    for row in _open_csv(path):
        out.append(_make_match(
            row["home_team"], row["away_team"], row["home_goal"], row["away_goal"],
            competition="Copa do Brasil",
            season=to_int(row.get("season")),
            match_date=parse_date(row.get("datetime")),
            round=row.get("round") or None,
            source="Brazilian_Cup_Matches.csv",
        ))
    return out


def load_libertadores(path: str) -> list[Match]:
    out = []
    for row in _open_csv(path):
        out.append(_make_match(
            row["home_team"], row["away_team"], row["home_goal"], row["away_goal"],
            competition="Copa Libertadores",
            season=to_int(row.get("season")),
            match_date=parse_date(row.get("datetime")),
            round=row.get("stage") or None,
            source="Libertadores_Matches.csv",
        ))
    return out


def load_br_football(path: str) -> list[Match]:
    """Extended-stats dataset. ``tournament`` becomes the competition name."""
    out = []
    for row in _open_csv(path):
        stats = {}
        for key in (
            "home_corner", "away_corner", "home_attack", "away_attack",
            "home_shots", "away_shots", "total_corners",
        ):
            val = to_int(row.get(key))
            if val is not None:
                stats[key] = val
        if row.get("ht_result"):
            stats["ht_result"] = row["ht_result"]
        if row.get("at_result"):
            stats["at_result"] = row["at_result"]
        out.append(_make_match(
            row["home"], row["away"], row["home_goal"], row["away_goal"],
            competition=(row.get("tournament") or "").strip() or "Unknown",
            season=(parse_date(row.get("date")).year if parse_date(row.get("date")) else None),
            match_date=parse_date(row.get("date")),
            round=None,
            source="BR-Football-Dataset.csv",
            stats=stats,
        ))
    return out


def load_novo(path: str) -> list[Match]:
    """Historical Brasileirao with Portuguese column names and DD/MM/YYYY."""
    out = []
    for row in _open_csv(path):
        out.append(_make_match(
            row["Equipe_mandante"], row["Equipe_visitante"],
            row["Gols_mandante"], row["Gols_visitante"],
            competition="Brasileirao",
            season=to_int(row.get("Ano")),
            match_date=parse_date(row.get("Data")),
            round=row.get("Rodada") or None,
            venue=(row.get("Arena") or "").strip() or None,
            source="novo_campeonato_brasileiro.csv",
        ))
    return out


# Skill columns copied verbatim into Player.skills for richer player answers.
_SKILL_COLUMNS = (
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
)


def load_players(path: str) -> list[Player]:
    out = []
    for row in _open_csv(path):
        skills = {}
        for col in _SKILL_COLUMNS:
            val = to_int(row.get(col))
            if val is not None:
                skills[col] = val
        out.append(Player(
            player_id=(row.get("ID") or "").strip(),
            name=(row.get("Name") or "").strip(),
            age=to_int(row.get("Age")),
            nationality=(row.get("Nationality") or "").strip(),
            overall=to_int(row.get("Overall")),
            potential=to_int(row.get("Potential")),
            club=(row.get("Club") or "").strip() or None,
            position=(row.get("Position") or "").strip() or None,
            jersey_number=(row.get("Jersey Number") or "").strip() or None,
            height=(row.get("Height") or "").strip() or None,
            weight=(row.get("Weight") or "").strip() or None,
            value=(row.get("Value") or "").strip() or None,
            skills=skills,
        ))
    return out


# Map of filename -> reader, used by load_all_matches.
_MATCH_READERS = {
    "Brasileirao_Matches.csv": load_brasileirao,
    "Brazilian_Cup_Matches.csv": load_cup,
    "Libertadores_Matches.csv": load_libertadores,
    "BR-Football-Dataset.csv": load_br_football,
    "novo_campeonato_brasileiro.csv": load_novo,
}


def load_all_matches(data_dir: str = DEFAULT_DATA_DIR) -> list[Match]:
    matches: list[Match] = []
    for filename, reader in _MATCH_READERS.items():
        path = os.path.join(data_dir, filename)
        if os.path.exists(path):
            matches.extend(reader(path))
    return matches


def load_all_players(data_dir: str = DEFAULT_DATA_DIR) -> list[Player]:
    path = os.path.join(data_dir, "fifa_data.csv")
    return load_players(path) if os.path.exists(path) else []
