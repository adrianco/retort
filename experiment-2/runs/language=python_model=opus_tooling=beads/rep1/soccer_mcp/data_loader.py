"""Load and normalize Brazilian soccer datasets."""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

DATA_DIR = Path(os.environ.get("SOCCER_DATA_DIR", Path(__file__).resolve().parent.parent / "data" / "kaggle"))


STATE_SUFFIX_RE = re.compile(r"\s*[-–]\s*[A-Z]{2,3}\s*$")


def strip_accents(s: str) -> str:
    if not isinstance(s, str):
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


TEAM_ALIASES = {
    "atletico mineiro": "atletico-mg",
    "atletico-mg": "atletico-mg",
    "atletico goianiense": "atletico-go",
    "atletico-go": "atletico-go",
    "atletico paranaense": "athletico-pr",
    "athletico paranaense": "athletico-pr",
    "athletico-pr": "athletico-pr",
    "atletico-pr": "athletico-pr",
    "america mineiro": "america-mg",
    "america-mg": "america-mg",
    "america-rn": "america-rn",
    "sao paulo": "sao paulo",
    "gremio": "gremio",
    "flamengo": "flamengo",
    "fluminense": "fluminense",
    "palmeiras": "palmeiras",
    "santos": "santos",
    "corinthians": "corinthians",
    "internacional": "internacional",
    "cruzeiro": "cruzeiro",
    "bahia": "bahia",
    "vasco": "vasco",
    "vasco da gama": "vasco",
    "botafogo": "botafogo",
    "athletic club": "athletic-mg",
}


def normalize_team(name: object) -> str:
    """Canonical form: lowercase, accent-stripped. Preserves state suffix when present
    to disambiguate clubs sharing a short name (Atlético-MG vs Atlético-PR)."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    s = str(name).strip()
    s = strip_accents(s).lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s*[-–]\s*", "-", s).strip("-").strip()
    if s in TEAM_ALIASES:
        return TEAM_ALIASES[s]
    # partial match for long names (e.g. "clube de regatas do flamengo")
    for alias, canonical in TEAM_ALIASES.items():
        if alias in s.split():
            pass  # avoid false positives like "santos" in arbitrary strings
    return s


def team_key(name: object) -> str:
    """Canonical short key: like normalize_team but strips trailing state suffix."""
    c = normalize_team(name)
    return re.sub(r"-[a-z]{2,3}$", "", c).strip()


def team_matches(query: str, canonical: str) -> bool:
    """Return True if the user query refers to the given canonical team name."""
    if not query or not canonical:
        return False
    q = normalize_team(query)
    if not q:
        return False
    if canonical == q:
        return True
    # allow matching ignoring state suffix either side
    return team_key(canonical) == team_key(q)


def _parse_date(val) -> Optional[pd.Timestamp]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return pd.to_datetime(val, errors="coerce", dayfirst=False)
    except Exception:
        return None


@dataclass
class Datasets:
    brasileirao: pd.DataFrame
    copa_brasil: pd.DataFrame
    libertadores: pd.DataFrame
    br_football: pd.DataFrame
    historico: pd.DataFrame
    fifa: pd.DataFrame
    matches: pd.DataFrame  # unified

    def summary(self) -> dict:
        return {
            "brasileirao": len(self.brasileirao),
            "copa_brasil": len(self.copa_brasil),
            "libertadores": len(self.libertadores),
            "br_football": len(self.br_football),
            "historico": len(self.historico),
            "fifa_players": len(self.fifa),
            "unified_matches": len(self.matches),
        }


def _std(df: pd.DataFrame, competition: str, *, home_col: str, away_col: str,
         hg: str, ag: str, date_col: str, season_col: Optional[str] = None,
         stage_col: Optional[str] = None, round_col: Optional[str] = None) -> pd.DataFrame:
    out = pd.DataFrame()
    out["competition"] = [competition] * len(df)
    out["date"] = pd.to_datetime(df[date_col], errors="coerce")
    out["home_team_raw"] = df[home_col].astype(str)
    out["away_team_raw"] = df[away_col].astype(str)
    out["home_team"] = out["home_team_raw"].map(normalize_team)
    out["away_team"] = out["away_team_raw"].map(normalize_team)
    out["home_key"] = out["home_team"].map(team_key)
    out["away_key"] = out["away_team"].map(team_key)
    out["home_goal"] = pd.to_numeric(df[hg], errors="coerce")
    out["away_goal"] = pd.to_numeric(df[ag], errors="coerce")
    if season_col and season_col in df.columns:
        out["season"] = pd.to_numeric(df[season_col], errors="coerce").astype("Int64")
    else:
        out["season"] = out["date"].dt.year.astype("Int64")
    out["stage"] = df[stage_col].astype(str) if stage_col and stage_col in df.columns else ""
    out["round"] = df[round_col].astype(str) if round_col and round_col in df.columns else ""
    return out


def load_all(data_dir: Path | str | None = None) -> Datasets:
    base = Path(data_dir) if data_dir else DATA_DIR

    bras = pd.read_csv(base / "Brasileirao_Matches.csv")
    copa = pd.read_csv(base / "Brazilian_Cup_Matches.csv")
    liber = pd.read_csv(base / "Libertadores_Matches.csv")
    brfoot = pd.read_csv(base / "BR-Football-Dataset.csv")
    hist = pd.read_csv(base / "novo_campeonato_brasileiro.csv")
    fifa = pd.read_csv(base / "fifa_data.csv", low_memory=False)

    # Historico date is DD/MM/YYYY
    hist["_date"] = pd.to_datetime(hist["Data"], dayfirst=True, errors="coerce")
    # BR-football date
    brfoot["_date"] = pd.to_datetime(brfoot["date"], errors="coerce")

    std_bras = _std(bras, "Brasileirão",
                    home_col="home_team", away_col="away_team",
                    hg="home_goal", ag="away_goal",
                    date_col="datetime", season_col="season", round_col="round")
    std_copa = _std(copa, "Copa do Brasil",
                    home_col="home_team", away_col="away_team",
                    hg="home_goal", ag="away_goal",
                    date_col="datetime", season_col="season", round_col="round")
    std_liber = _std(liber, "Copa Libertadores",
                     home_col="home_team", away_col="away_team",
                     hg="home_goal", ag="away_goal",
                     date_col="datetime", season_col="season", stage_col="stage")
    std_brfoot = _std(brfoot, "BR-Football",
                      home_col="home", away_col="away",
                      hg="home_goal", ag="away_goal",
                      date_col="_date")
    # Use the actual tournament column as the competition where possible
    std_brfoot["competition"] = brfoot["tournament"].astype(str).fillna("BR-Football")

    std_hist = _std(hist, "Brasileirão (histórico)",
                    home_col="Equipe_mandante", away_col="Equipe_visitante",
                    hg="Gols_mandante", ag="Gols_visitante",
                    date_col="_date", season_col="Ano", round_col="Rodada")

    unified = pd.concat([std_bras, std_copa, std_liber, std_brfoot, std_hist],
                       ignore_index=True)
    unified = unified.dropna(subset=["home_team", "away_team"])

    # Normalize FIFA columns we care about
    if "Nationality" in fifa.columns:
        fifa["Nationality"] = fifa["Nationality"].astype(str)
    if "Club" in fifa.columns:
        fifa["Club"] = fifa["Club"].astype(str)
    if "Name" in fifa.columns:
        fifa["Name"] = fifa["Name"].astype(str)

    return Datasets(
        brasileirao=bras, copa_brasil=copa, libertadores=liber,
        br_football=brfoot, historico=hist, fifa=fifa, matches=unified,
    )
