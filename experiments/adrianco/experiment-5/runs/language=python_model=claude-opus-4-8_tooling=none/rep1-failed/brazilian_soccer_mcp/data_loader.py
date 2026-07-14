"""
================================================================================
Brazilian Soccer MCP Server - Data Loader
================================================================================

CONTEXT
-------
Reads the six pre-downloaded Kaggle CSV files from ``data/kaggle/`` and
normalises them into ``Match`` / ``Player`` records that feed the knowledge
graph. Only the Python standard library (``csv``) is used so that loading works
with no third-party packages installed.

The loader is *schema-tolerant*: each source file is mapped through an explicit
adapter that looks up columns by name (case-insensitively) and falls back
gracefully when optional columns are missing. Team names are cleaned and dates
are normalised to ISO format at load time (see ``normalize``).

SOURCE FILES (verified headers - see brazilian-soccer-mcp-guide.md)
  1. Brasileirao_Matches.csv        datetime,home_team,home_team_state,
                                    away_team,away_team_state,home_goal,
                                    away_goal,season,round
  2. Brazilian_Cup_Matches.csv      round,datetime,home_team,away_team,
                                    home_goal,away_goal,season
  3. Libertadores_Matches.csv       datetime,home_team,away_team,home_goal,
                                    away_goal,season,stage
  4. BR-Football-Dataset.csv        tournament,home,home_goal,away_goal,away,
                                    ...,date,...,total_corners
  5. novo_campeonato_brasileiro.csv ID,Data,Ano,Rodada,Equipe_mandante,
                                    Equipe_visitante,Gols_mandante,
                                    Gols_visitante,Mandante_UF,Visitante_UF,
                                    Vencedor,Arena,OBS
  6. fifa_data.csv                  <BOM>,ID,Name,Age,...,Nationality,...,
                                    Overall,Potential,Club,...,Position,...
================================================================================
"""

from __future__ import annotations

import csv
import os
from typing import Dict, List, Optional

from .models import Match, Player
from .normalize import (
    clean_team_name,
    iso_date,
    parse_date,
    to_int,
    COMP_BRASILEIRAO,
    COMP_COPA_BRASIL,
    COMP_LIBERTADORES,
)

# Default location of the bundled datasets, resolved relative to repo root.
DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "kaggle",
)


def _open_rows(path: str) -> List[Dict[str, str]]:
    """Read a CSV file (UTF-8, BOM tolerant) into a list of dict rows.

    Returns an empty list if the file is missing so that a partial dataset
    still loads the files that are present.
    """
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = []
        for raw in reader:
            rows.append({(k.strip() if k else k): v for k, v in raw.items()})
        return rows


def _get(row: Dict[str, str], *names: str) -> Optional[str]:
    """Case-insensitive lookup of the first present column among *names*."""
    lower = {k.lower(): v for k, v in row.items() if k}
    for name in names:
        if name in row:
            return row[name]
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def _season_from(row: Dict[str, str], *date_names: str) -> Optional[int]:
    """Resolve a season year from an explicit column or a date column."""
    for col in ("season", "Season", "Ano", "year", "Year"):
        val = _get(row, col)
        if val:
            yr = to_int(val)
            if yr:
                return yr
    for dn in date_names:
        dt = parse_date(_get(row, dn) or "")
        if dt:
            return dt.year
    return None


# --- Per-file adapters -----------------------------------------------------

def _load_brasileirao(path: str) -> List[Match]:
    matches: List[Match] = []
    for row in _open_rows(path):
        matches.append(
            Match(
                competition=COMP_BRASILEIRAO,
                season=_season_from(row, "datetime", "date"),
                date=iso_date(_get(row, "datetime", "date") or ""),
                home_team=clean_team_name(_get(row, "home_team", "home") or ""),
                away_team=clean_team_name(_get(row, "away_team", "away") or ""),
                home_goal=to_int(_get(row, "home_goal")),
                away_goal=to_int(_get(row, "away_goal")),
                round=_get(row, "round"),
                home_state=_get(row, "home_team_state"),
                away_state=_get(row, "away_team_state"),
                source="brasileirao_serie_a",
            )
        )
    return matches


def _load_cup(path: str) -> List[Match]:
    matches: List[Match] = []
    for row in _open_rows(path):
        matches.append(
            Match(
                competition=COMP_COPA_BRASIL,
                season=_season_from(row, "datetime", "date"),
                date=iso_date(_get(row, "datetime", "date") or ""),
                home_team=clean_team_name(_get(row, "home_team", "home") or ""),
                away_team=clean_team_name(_get(row, "away_team", "away") or ""),
                home_goal=to_int(_get(row, "home_goal")),
                away_goal=to_int(_get(row, "away_goal")),
                round=_get(row, "round"),
                source="copa_do_brasil",
            )
        )
    return matches


def _load_libertadores(path: str) -> List[Match]:
    matches: List[Match] = []
    for row in _open_rows(path):
        matches.append(
            Match(
                competition=COMP_LIBERTADORES,
                season=_season_from(row, "datetime", "date"),
                date=iso_date(_get(row, "datetime", "date") or ""),
                home_team=clean_team_name(_get(row, "home_team", "home") or ""),
                away_team=clean_team_name(_get(row, "away_team", "away") or ""),
                home_goal=to_int(_get(row, "home_goal")),
                away_goal=to_int(_get(row, "away_goal")),
                stage=_get(row, "stage"),
                round=_get(row, "round"),
                source="libertadores",
            )
        )
    return matches


def _load_br_football(path: str) -> List[Match]:
    """Extended-statistics dataset. Competition comes from the ``tournament``
    column; extra per-match stats are retained in ``Match.extra``."""
    matches: List[Match] = []
    for row in _open_rows(path):
        tournament = (_get(row, "tournament") or "Brazilian Football").strip()
        extra = {}
        for key in (
            "home_corner", "away_corner", "home_attack", "away_attack",
            "home_shots", "away_shots", "ht_result", "at_result",
            "total_corners",
        ):
            val = _get(row, key)
            if val not in (None, ""):
                extra[key] = val
        matches.append(
            Match(
                competition=tournament or "Brazilian Football",
                season=_season_from(row, "date"),
                date=iso_date(_get(row, "date") or ""),
                home_team=clean_team_name(_get(row, "home", "home_team") or ""),
                away_team=clean_team_name(_get(row, "away", "away_team") or ""),
                home_goal=to_int(_get(row, "home_goal")),
                away_goal=to_int(_get(row, "away_goal")),
                source="br_football_extended",
                extra=extra,
            )
        )
    return matches


def _load_novo(path: str) -> List[Match]:
    """Historic Brasileirão (2003-2019) with Portuguese column names."""
    matches: List[Match] = []
    for row in _open_rows(path):
        matches.append(
            Match(
                competition=COMP_BRASILEIRAO,
                season=_season_from(row, "Data"),
                date=iso_date(_get(row, "Data", "data") or ""),
                home_team=clean_team_name(_get(row, "Equipe_mandante") or ""),
                away_team=clean_team_name(_get(row, "Equipe_visitante") or ""),
                home_goal=to_int(_get(row, "Gols_mandante")),
                away_goal=to_int(_get(row, "Gols_visitante")),
                round=_get(row, "Rodada"),
                home_state=_get(row, "Mandante_UF"),
                away_state=_get(row, "Visitante_UF"),
                stadium=_get(row, "Arena"),
                source="brasileirao_historic",
            )
        )
    return matches


def _load_players(path: str) -> List[Player]:
    players: List[Player] = []
    for row in _open_rows(path):
        name = _get(row, "Name", "name")
        if not name:
            continue
        players.append(
            Player(
                name=name.strip(),
                age=to_int(_get(row, "Age")),
                nationality=(_get(row, "Nationality") or "").strip() or None,
                overall=to_int(_get(row, "Overall")),
                potential=to_int(_get(row, "Potential")),
                club=(_get(row, "Club") or "").strip() or None,
                position=(_get(row, "Position") or "").strip() or None,
                jersey_number=to_int(_get(row, "Jersey Number", "Jersey_Number")),
                height=(_get(row, "Height") or "").strip() or None,
                weight=(_get(row, "Weight") or "").strip() or None,
                player_id=to_int(_get(row, "ID", "Id")),
            )
        )
    return players


# Map of dataset filename -> match adapter.
_MATCH_FILES = {
    "Brasileirao_Matches.csv": _load_brasileirao,
    "Brazilian_Cup_Matches.csv": _load_cup,
    "Libertadores_Matches.csv": _load_libertadores,
    "BR-Football-Dataset.csv": _load_br_football,
    "novo_campeonato_brasileiro.csv": _load_novo,
}

_PLAYER_FILE = "fifa_data.csv"


def load_matches(data_dir: str = DEFAULT_DATA_DIR) -> List[Match]:
    """Load and normalise every match across all match datasets."""
    matches: List[Match] = []
    for filename, adapter in _MATCH_FILES.items():
        matches.extend(adapter(os.path.join(data_dir, filename)))
    return matches


def load_players(data_dir: str = DEFAULT_DATA_DIR) -> List[Player]:
    """Load and normalise every FIFA player record."""
    return _load_players(os.path.join(data_dir, _PLAYER_FILE))


def load_knowledge_graph(data_dir: str = DEFAULT_DATA_DIR):
    """Convenience constructor returning a populated ``KnowledgeGraph``."""
    from .knowledge_graph import KnowledgeGraph

    return KnowledgeGraph(
        matches=load_matches(data_dir),
        players=load_players(data_dir),
    )
