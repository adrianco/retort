"""
Data location and dataset catalogue.

Context
-------
Every loader in :mod:`brazilian_soccer.loaders` reads a CSV from a single data
directory.  That directory defaults to ``<repo>/data/kaggle`` but can be
overridden with the ``BRAZILIAN_SOCCER_DATA_DIR`` environment variable so the
MCP server can be pointed at a different copy of the datasets (or at a small
fixture directory in tests).

``DATASETS`` is the authoritative catalogue of the six required CSV files.  It
records the license/attribution required by TASK.md and the competition each
file describes, and it is surfaced verbatim by the ``dataset_summary`` tool.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "kaggle"

DATA_DIR_ENV_VAR = "BRAZILIAN_SOCCER_DATA_DIR"


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    """Metadata for one of the six required CSV files."""

    key: str
    filename: str
    kind: str  # "matches" or "players"
    description: str
    source_url: str
    license: str
    competitions: tuple[str, ...] = ()


DATASETS: tuple[DatasetSpec, ...] = (
    DatasetSpec(
        key="brasileirao",
        filename="Brasileirao_Matches.csv",
        kind="matches",
        description="Brasileirao Serie A matches, seasons 2012-2022",
        source_url="https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro",
        license="CC BY 4.0",
        competitions=("serie-a",),
    ),
    DatasetSpec(
        key="copa_do_brasil",
        filename="Brazilian_Cup_Matches.csv",
        kind="matches",
        description="Copa do Brasil matches, seasons 2012-2021",
        source_url="https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro",
        license="CC BY 4.0",
        competitions=("copa-do-brasil",),
    ),
    DatasetSpec(
        key="libertadores",
        filename="Libertadores_Matches.csv",
        kind="matches",
        description="Copa Libertadores matches, seasons 2013-2022",
        source_url="https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro",
        license="CC BY 4.0",
        competitions=("libertadores",),
    ),
    DatasetSpec(
        key="br_football",
        filename="BR-Football-Dataset.csv",
        kind="matches",
        description=(
            "Extended match statistics (corners, shots, attacks) for Serie A/B/C "
            "and Copa do Brasil, 2014-2023"
        ),
        source_url="https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches",
        license="CC0 Public Domain",
        competitions=("serie-a", "serie-b", "serie-c", "copa-do-brasil"),
    ),
    DatasetSpec(
        key="historical_brasileirao",
        filename="novo_campeonato_brasileiro.csv",
        kind="matches",
        description="Historical Brasileirao Serie A matches with stadiums, 2003-2019",
        source_url="https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019",
        license="CC BY 4.0",
        competitions=("serie-a",),
    ),
    DatasetSpec(
        key="fifa_players",
        filename="fifa_data.csv",
        kind="players",
        description="FIFA 19 player database (18,207 players, ratings and attributes)",
        source_url="https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data",
        license="Apache 2.0",
    ),
)

DATASETS_BY_KEY: dict[str, DatasetSpec] = {spec.key: spec for spec in DATASETS}


def data_dir() -> Path:
    """Return the directory holding the Kaggle CSV files."""

    override = os.environ.get(DATA_DIR_ENV_VAR)
    if override:
        return Path(override).expanduser().resolve()
    return DEFAULT_DATA_DIR


def dataset_path(key: str) -> Path:
    """Return the full path of the CSV registered under ``key``."""

    try:
        spec = DATASETS_BY_KEY[key]
    except KeyError:  # pragma: no cover - programming error
        raise KeyError(f"unknown dataset {key!r}; known: {sorted(DATASETS_BY_KEY)}") from None
    return data_dir() / spec.filename


def missing_datasets() -> list[str]:
    """Return the keys of datasets whose CSV file is not present on disk."""

    return [spec.key for spec in DATASETS if not dataset_path(spec.key).exists()]
