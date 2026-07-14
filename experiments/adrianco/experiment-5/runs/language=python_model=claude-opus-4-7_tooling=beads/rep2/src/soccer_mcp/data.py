"""Dataset loader and normalization helpers.

Loads the six Kaggle CSVs under ``data/kaggle`` into pandas DataFrames in a
single canonical shape so the query modules don't have to know per-file
quirks. Every match table is normalised to the same columns::

    competition  date  season  round  stage
    home_team    away_team    home_goal    away_goal
    home_team_norm    away_team_norm
    home_state   away_state
    arena

The FIFA player table is loaded mostly as-is but with normalised club and
nationality columns added so it can be joined to the match data.

Team-name normalisation is the crux of cross-dataset queries — the same club
appears as ``"Palmeiras-SP"`` in one file, ``"Palmeiras"`` in another, and the
historical Portuguese name in a third. ``normalize_team_name`` strips state
suffixes, accents, punctuation, and a small set of common aliases so a search
for "São Paulo" finds rows tagged "Sao Paulo-SP", "Sao Paulo FC", or
"São Paulo".
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import pandas as pd

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "kaggle"

BRASILEIRAO_FILE = "Brasileirao_Matches.csv"
CUP_FILE = "Brazilian_Cup_Matches.csv"
LIBERTADORES_FILE = "Libertadores_Matches.csv"
EXTENDED_FILE = "BR-Football-Dataset.csv"
HISTORICAL_FILE = "novo_campeonato_brasileiro.csv"
FIFA_FILE = "fifa_data.csv"

COMPETITION_BRASILEIRAO = "Brasileirão"
COMPETITION_CUP = "Copa do Brasil"
COMPETITION_LIBERTADORES = "Copa Libertadores"
COMPETITION_HISTORICAL = "Brasileirão (historical)"
COMPETITION_EXTENDED = "Extended"


_ALIASES: dict[str, str] = {
    "atletico mineiro": "atletico mg",
    "atletico paranaense": "athletico pr",
    "athletico paranaense": "athletico pr",
    "atletico pr": "athletico pr",
    "sport recife": "sport",
    "sport club do recife": "sport",
    "sao paulo fc": "sao paulo",
    "sport club corinthians paulista": "corinthians",
    "clube de regatas do flamengo": "flamengo",
    "fluminense football club": "fluminense",
    "sociedade esportiva palmeiras": "palmeiras",
    "santos fc": "santos",
    "santos futebol clube": "santos",
    "gremio foot-ball porto alegrense": "gremio",
    "vasco da gama": "vasco",
    "club de regatas vasco da gama": "vasco",
}


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


_STATE_SUFFIX_RE = re.compile(r"\s*[-/]\s*[A-Z]{2,3}\s*$")
_PUNCT_RE = re.compile(r"[^a-z0-9\s]")
_WS_RE = re.compile(r"\s+")


@lru_cache(maxsize=8192)
def normalize_team_name(name: str | None) -> str:
    """Collapse a team name to a comparable key.

    Strips a trailing state code (``-SP``, ``- RJ``, ``/MG``), Portuguese
    accents, and punctuation; lower-cases; collapses whitespace; then applies a
    small alias table for the worst offenders.
    """
    if name is None:
        return ""
    raw = str(name).strip()
    if not raw:
        return ""
    raw = _STATE_SUFFIX_RE.sub("", raw)
    raw = raw.replace("(URU)", "").replace("(ARG)", "").replace("(EQU)", "")
    raw = raw.replace("(BOL)", "").replace("(COL)", "").replace("(PAR)", "")
    raw = raw.replace("(CHI)", "").replace("(VEN)", "").replace("(PER)", "")
    raw = _strip_accents(raw).lower()
    raw = _PUNCT_RE.sub(" ", raw)
    raw = _WS_RE.sub(" ", raw).strip()
    return _ALIASES.get(raw, raw)


def _split_state(name: str | None) -> tuple[str, str | None]:
    if name is None:
        return "", None
    raw = str(name).strip()
    match = re.search(r"[-/]\s*([A-Z]{2,3})\s*$", raw)
    state = match.group(1) if match else None
    cleaned = _STATE_SUFFIX_RE.sub("", raw).strip()
    return cleaned, state


def _coerce_date(value) -> pd.Timestamp | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return pd.to_datetime(value, errors="coerce", dayfirst=False)
    except (ValueError, TypeError):
        return None


def _to_int(value) -> int | None:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


_MATCH_COLUMNS = [
    "competition",
    "date",
    "season",
    "round",
    "stage",
    "home_team",
    "away_team",
    "home_team_norm",
    "away_team_norm",
    "home_state",
    "away_state",
    "home_goal",
    "away_goal",
    "arena",
]


def _empty_matches() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="object") for c in _MATCH_COLUMNS})


def _finalize_matches(df: pd.DataFrame) -> pd.DataFrame:
    for col in _MATCH_COLUMNS:
        if col not in df.columns:
            df[col] = None
    df = df[_MATCH_COLUMNS].copy()
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce").astype("Int64")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce").astype("Int64")
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["home_team_norm"] = df["home_team"].map(normalize_team_name)
    df["away_team_norm"] = df["away_team"].map(normalize_team_name)
    return df


def _load_brasileirao(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, encoding="utf-8")
    home_split = raw["home_team"].astype(str).map(_split_state)
    away_split = raw["away_team"].astype(str).map(_split_state)
    out = pd.DataFrame(
        {
            "competition": COMPETITION_BRASILEIRAO,
            "date": raw["datetime"],
            "season": raw["season"],
            "round": raw["round"],
            "stage": None,
            "home_team": [h[0] for h in home_split],
            "away_team": [a[0] for a in away_split],
            "home_state": raw.get("home_team_state", pd.Series([None] * len(raw))),
            "away_state": raw.get("away_team_state", pd.Series([None] * len(raw))),
            "home_goal": raw["home_goal"],
            "away_goal": raw["away_goal"],
            "arena": None,
        }
    )
    return _finalize_matches(out)


def _load_cup(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, encoding="utf-8")
    home_split = raw["home_team"].astype(str).map(_split_state)
    away_split = raw["away_team"].astype(str).map(_split_state)
    out = pd.DataFrame(
        {
            "competition": COMPETITION_CUP,
            "date": raw["datetime"],
            "season": raw["season"],
            "round": raw["round"],
            "stage": raw["round"],
            "home_team": [h[0] for h in home_split],
            "away_team": [a[0] for a in away_split],
            "home_state": [h[1] for h in home_split],
            "away_state": [a[1] for a in away_split],
            "home_goal": raw["home_goal"],
            "away_goal": raw["away_goal"],
            "arena": None,
        }
    )
    return _finalize_matches(out)


def _load_libertadores(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, encoding="utf-8")
    home_split = raw["home_team"].astype(str).map(_split_state)
    away_split = raw["away_team"].astype(str).map(_split_state)
    out = pd.DataFrame(
        {
            "competition": COMPETITION_LIBERTADORES,
            "date": raw["datetime"],
            "season": raw["season"],
            "round": None,
            "stage": raw["stage"],
            "home_team": [h[0] for h in home_split],
            "away_team": [a[0] for a in away_split],
            "home_state": [h[1] for h in home_split],
            "away_state": [a[1] for a in away_split],
            "home_goal": raw["home_goal"],
            "away_goal": raw["away_goal"],
            "arena": None,
        }
    )
    return _finalize_matches(out)


def _load_extended(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, encoding="utf-8")
    date_combined = raw["date"].astype(str) + " " + raw["time"].fillna("").astype(str)
    out = pd.DataFrame(
        {
            "competition": raw["tournament"].fillna(COMPETITION_EXTENDED),
            "date": date_combined,
            "season": pd.to_datetime(raw["date"], errors="coerce").dt.year,
            "round": None,
            "stage": None,
            "home_team": raw["home"].astype(str),
            "away_team": raw["away"].astype(str),
            "home_state": None,
            "away_state": None,
            "home_goal": raw["home_goal"],
            "away_goal": raw["away_goal"],
            "arena": None,
        }
    )
    df = _finalize_matches(out)
    extras = raw[
        [
            "home_corner",
            "away_corner",
            "home_attack",
            "away_attack",
            "home_shots",
            "away_shots",
            "ht_result",
            "at_result",
            "total_corners",
        ]
    ].reset_index(drop=True)
    df = df.reset_index(drop=True)
    return pd.concat([df, extras], axis=1)


def _load_historical(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, encoding="utf-8")
    out = pd.DataFrame(
        {
            "competition": COMPETITION_HISTORICAL,
            "date": pd.to_datetime(raw["Data"], dayfirst=True, errors="coerce"),
            "season": raw["Ano"],
            "round": raw["Rodada"],
            "stage": None,
            "home_team": raw["Equipe_mandante"].astype(str),
            "away_team": raw["Equipe_visitante"].astype(str),
            "home_state": raw.get("Mandante_UF", pd.Series([None] * len(raw))),
            "away_state": raw.get("Visitante_UF", pd.Series([None] * len(raw))),
            "home_goal": raw["Gols_mandante"],
            "away_goal": raw["Gols_visitante"],
            "arena": raw.get("Arena", pd.Series([None] * len(raw))),
        }
    )
    return _finalize_matches(out)


def _load_fifa(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, encoding="utf-8")
    # Drop the leading BOM column that csv preserves as ''.
    drop_cols = [c for c in raw.columns if c.strip() == "" or c == "﻿"]
    if drop_cols:
        raw = raw.drop(columns=drop_cols)
    raw["club_norm"] = raw["Club"].fillna("").map(normalize_team_name)
    raw["nationality_norm"] = raw["Nationality"].fillna("").str.lower().str.strip()
    raw["name_norm"] = raw["Name"].fillna("").map(lambda s: _strip_accents(str(s)).lower())
    return raw


@dataclass
class SoccerData:
    """In-memory bundle of every dataset, normalised to a shared schema.

    Call :meth:`SoccerData.load` once at startup, then pass the instance to
    the query helpers. The combined ``matches`` frame is the union of every
    match source — useful for cross-competition queries — while the per-source
    frames are kept around for cases where you specifically want one league.
    """

    brasileirao: pd.DataFrame
    cup: pd.DataFrame
    libertadores: pd.DataFrame
    extended: pd.DataFrame
    historical: pd.DataFrame
    fifa: pd.DataFrame
    matches: pd.DataFrame = field(init=False)

    def __post_init__(self) -> None:
        # Keep only canonical columns when concatenating so dtypes stay aligned.
        frames = [
            self.brasileirao[_MATCH_COLUMNS],
            self.cup[_MATCH_COLUMNS],
            self.libertadores[_MATCH_COLUMNS],
            self.extended[_MATCH_COLUMNS],
            self.historical[_MATCH_COLUMNS],
        ]
        self.matches = pd.concat(frames, ignore_index=True)

    @classmethod
    def load(cls, data_dir: Path | str | None = None) -> "SoccerData":
        directory = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        return cls(
            brasileirao=_load_brasileirao(directory / BRASILEIRAO_FILE),
            cup=_load_cup(directory / CUP_FILE),
            libertadores=_load_libertadores(directory / LIBERTADORES_FILE),
            extended=_load_extended(directory / EXTENDED_FILE),
            historical=_load_historical(directory / HISTORICAL_FILE),
            fifa=_load_fifa(directory / FIFA_FILE),
        )

    def competitions(self) -> list[str]:
        return sorted(self.matches["competition"].dropna().unique().tolist())

    def seasons(self, competition: str | None = None) -> list[int]:
        df = self.matches if competition is None else self.matches[self.matches["competition"] == competition]
        return sorted(int(s) for s in df["season"].dropna().unique())

    def team_aliases(self) -> dict[str, set[str]]:
        """Return the set of raw display names observed per normalised key."""
        out: dict[str, set[str]] = {}
        for col in ("home_team", "away_team"):
            grouped = self.matches[[col, f"{col}_norm"]].dropna().drop_duplicates()
            for raw, norm in zip(grouped[col], grouped[f"{col}_norm"]):
                if not norm:
                    continue
                out.setdefault(norm, set()).add(str(raw))
        return out


def candidate_normalizations(query: str) -> set[str]:
    """Return every normalised key that ``query`` could match.

    Useful for fuzzy "did the user mean X or Y" style lookups — but most
    queries should just call :func:`normalize_team_name` and compare against
    the ``home_team_norm`` / ``away_team_norm`` columns.
    """
    base = normalize_team_name(query)
    if not base:
        return set()
    candidates = {base}
    # Allow common short forms — "Sao Paulo" matches both raw "Sao Paulo" and "Sao Paulo FC"
    tokens = base.split()
    if len(tokens) > 1:
        candidates.add(tokens[0])
    return candidates


def match_team(query: str, norm: str | None) -> bool:
    """Predicate: does ``norm`` (already-normalised) match the user's ``query``?"""
    if not norm:
        return False
    base = normalize_team_name(query)
    if not base:
        return False
    return base == norm or base in norm.split() or norm.startswith(base) or base in norm
