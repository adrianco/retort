"""Load every provided CSV into a uniform schema.

All match-style datasets are mapped into a single canonical DataFrame with
these columns:

    competition       — short name ("Brasileirão", "Copa do Brasil", ...)
    season            — int year
    round             — string / int / NaN (per source)
    stage             — string for cup-style competitions, else None
    date              — pandas Timestamp (timezone-naive)
    home_team_raw     — original home team string
    away_team_raw     — original away team string
    home_team         — normalized canonical key (lowercase, no diacritics)
    away_team         — normalized canonical key
    home_team_display — display-friendly name (state suffix stripped)
    away_team_display — display-friendly name
    home_goal         — int
    away_goal         — int
    home_state        — two-letter state code (when known)
    away_state        — two-letter state code
    arena             — stadium name when known
    source            — which CSV file the row came from

The FIFA player dataset is exposed as its own DataFrame in
:attr:`SoccerData.players`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd

from brazilian_soccer_mcp.normalize import display_team, normalize_team

DATA_DIR_DEFAULT = Path("data/kaggle")

# ---- per-file readers ------------------------------------------------------


def _parse_date(value) -> Optional[pd.Timestamp]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return pd.NaT
    return pd.to_datetime(value, errors="coerce", dayfirst=False)


def _parse_date_brazilian(value) -> Optional[pd.Timestamp]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return pd.NaT
    return pd.to_datetime(value, errors="coerce", dayfirst=True)


def _load_brasileirao(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    n = len(df)
    out = pd.DataFrame(index=range(n))
    out["competition"] = ["Brasileirão Série A"] * n
    out["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64").values
    out["round"] = df["round"].astype(str).values
    out["stage"] = [None] * n
    out["date"] = df["datetime"].apply(_parse_date).values
    out["home_team_raw"] = df["home_team"].values
    out["away_team_raw"] = df["away_team"].values
    out["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce").astype("Int64").values
    out["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce").astype("Int64").values
    out["home_state"] = df["home_team_state"].values
    out["away_state"] = df["away_team_state"].values
    out["arena"] = [None] * n
    out["source"] = [path.name] * n
    return out


def _load_brazilian_cup(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    n = len(df)
    out = pd.DataFrame(index=range(n))
    out["competition"] = ["Copa do Brasil"] * n
    out["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64").values
    out["round"] = df["round"].astype(str).values
    out["stage"] = [None] * n
    out["date"] = df["datetime"].apply(_parse_date).values
    out["home_team_raw"] = df["home_team"].values
    out["away_team_raw"] = df["away_team"].values
    out["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce").astype("Int64").values
    out["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce").astype("Int64").values
    out["home_state"] = [None] * n
    out["away_state"] = [None] * n
    out["arena"] = [None] * n
    out["source"] = [path.name] * n
    return out


def _load_libertadores(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    n = len(df)
    out = pd.DataFrame(index=range(n))
    out["competition"] = ["Copa Libertadores"] * n
    out["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64").values
    out["round"] = [None] * n
    out["stage"] = df["stage"].values
    out["date"] = df["datetime"].apply(_parse_date).values
    out["home_team_raw"] = df["home_team"].values
    out["away_team_raw"] = df["away_team"].values
    out["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce").astype("Int64").values
    out["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce").astype("Int64").values
    out["home_state"] = [None] * n
    out["away_state"] = [None] * n
    out["arena"] = [None] * n
    out["source"] = [path.name] * n
    return out


_BR_FOOTBALL_TOURNAMENT_MAP = {
    "Serie A": "Brasileirão Série A",
    "Serie B": "Brasileirão Série B",
    "Serie C": "Brasileirão Série C",
    "Copa do Brasil": "Copa do Brasil",
}


def _load_br_football(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    n = len(df)
    out = pd.DataFrame(index=range(n))
    tournament = df["tournament"].fillna("Unknown").astype(str)
    out["competition"] = tournament.map(
        lambda t: _BR_FOOTBALL_TOURNAMENT_MAP.get(t, t)
    ).values
    parsed_date = df["date"].apply(_parse_date)
    out["season"] = parsed_date.dt.year.astype("Int64").values
    out["round"] = [None] * n
    out["stage"] = [None] * n
    out["date"] = parsed_date.values
    out["home_team_raw"] = df["home"].values
    out["away_team_raw"] = df["away"].values
    out["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce").astype("Int64").values
    out["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce").astype("Int64").values
    out["home_state"] = [None] * n
    out["away_state"] = [None] * n
    out["arena"] = [None] * n
    out["home_corner"] = pd.to_numeric(df.get("home_corner"), errors="coerce").values
    out["away_corner"] = pd.to_numeric(df.get("away_corner"), errors="coerce").values
    out["home_shots"] = pd.to_numeric(df.get("home_shots"), errors="coerce").values
    out["away_shots"] = pd.to_numeric(df.get("away_shots"), errors="coerce").values
    out["total_corners"] = pd.to_numeric(df.get("total_corners"), errors="coerce").values
    out["source"] = [path.name] * n
    return out


def _load_novo_campeonato(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    n = len(df)
    out = pd.DataFrame(index=range(n))
    out["competition"] = ["Brasileirão Série A"] * n
    out["season"] = pd.to_numeric(df["Ano"], errors="coerce").astype("Int64").values
    out["round"] = df["Rodada"].astype(str).values
    out["stage"] = [None] * n
    out["date"] = df["Data"].apply(_parse_date_brazilian).values
    out["home_team_raw"] = df["Equipe_mandante"].values
    out["away_team_raw"] = df["Equipe_visitante"].values
    out["home_goal"] = pd.to_numeric(df["Gols_mandante"], errors="coerce").astype("Int64").values
    out["away_goal"] = pd.to_numeric(df["Gols_visitante"], errors="coerce").astype("Int64").values
    out["home_state"] = df["Mandante_UF"].values
    out["away_state"] = df["Visitante_UF"].values
    out["arena"] = df["Arena"].values
    out["source"] = [path.name] * n
    return out


def _load_fifa(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    keep = [
        "ID", "Name", "Age", "Nationality", "Overall", "Potential",
        "Club", "Position", "Jersey Number", "Height", "Weight",
        "Preferred Foot", "Value", "Wage",
    ]
    keep = [c for c in keep if c in df.columns]
    out = df[keep].copy()
    out.rename(
        columns={
            "Name": "name",
            "Age": "age",
            "Nationality": "nationality",
            "Overall": "overall",
            "Potential": "potential",
            "Club": "club",
            "Position": "position",
            "Jersey Number": "jersey_number",
            "Height": "height",
            "Weight": "weight",
            "Preferred Foot": "preferred_foot",
            "Value": "value",
            "Wage": "wage",
            "ID": "fifa_id",
        },
        inplace=True,
    )
    out["club"] = out["club"].fillna("")
    out["club_norm"] = out["club"].apply(normalize_team)
    out["name_norm"] = out["name"].fillna("").str.lower()
    return out


# ---- public container ------------------------------------------------------


@dataclass
class SoccerData:
    """Container for all loaded data."""

    matches: pd.DataFrame = field(default_factory=pd.DataFrame)
    players: pd.DataFrame = field(default_factory=pd.DataFrame)
    sources: dict = field(default_factory=dict)

    @property
    def competitions(self) -> list:
        return sorted(self.matches["competition"].dropna().unique().tolist())

    @property
    def seasons(self) -> list:
        return sorted(
            int(s) for s in self.matches["season"].dropna().unique() if pd.notna(s)
        )

    @property
    def teams(self) -> list:
        """All canonical team keys seen in match data."""
        keys = set(self.matches["home_team"].dropna()) | set(
            self.matches["away_team"].dropna()
        )
        return sorted(k for k in keys if k)


_STAT_COLUMNS = (
    "home_corner", "away_corner", "home_shots", "away_shots", "total_corners"
)


def _dedupe_matches(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse rows that describe the same match from different files.

    Two rows are considered duplicates when they share
    (season, competition, home_team, away_team). This works because in
    Brasileirão each pair (home, away) plays exactly once per season, and
    cup ties have a fixed home/away assignment per leg.

    The richest row (most non-null stat columns) wins; stats from siblings
    are merged in so corner/shot data isn't lost.
    """
    if df.empty:
        return df
    df = df.copy()
    df["_richness"] = sum(
        df[c].notna().astype(int) for c in _STAT_COLUMNS if c in df.columns
    )
    # Tie-break: prefer rows with non-null dates and round info
    df["_richness"] = (
        df["_richness"]
        + df["date"].notna().astype(int)
        + df["round"].notna().astype(int)
    )
    df = df.sort_values("_richness", ascending=False)
    keys = ["season", "competition", "home_team", "away_team"]
    keep_idx = df.drop_duplicates(subset=keys, keep="first").index
    if any(c in df.columns for c in _STAT_COLUMNS):
        for col in _STAT_COLUMNS:
            if col not in df.columns:
                continue
            df[col] = df.groupby(keys)[col].transform(lambda s: s.ffill().bfill())
    out = df.loc[keep_idx].drop(columns=["_richness"])
    return out


def _attach_normalized_team_columns(df: pd.DataFrame) -> pd.DataFrame:
    df["home_team"] = df["home_team_raw"].apply(normalize_team)
    df["away_team"] = df["away_team_raw"].apply(normalize_team)
    df["home_team_display"] = df["home_team_raw"].apply(display_team)
    df["away_team_display"] = df["away_team_raw"].apply(display_team)
    return df


def load_data(data_dir: Path | str = DATA_DIR_DEFAULT) -> SoccerData:
    """Load all six datasets from ``data_dir`` into a :class:`SoccerData`."""
    data_dir = Path(data_dir)
    files = {
        "brasileirao": data_dir / "Brasileirao_Matches.csv",
        "copa_brasil": data_dir / "Brazilian_Cup_Matches.csv",
        "libertadores": data_dir / "Libertadores_Matches.csv",
        "br_football": data_dir / "BR-Football-Dataset.csv",
        "novo_brasileirao": data_dir / "novo_campeonato_brasileiro.csv",
        "fifa": data_dir / "fifa_data.csv",
    }
    for key, path in files.items():
        if not path.exists():
            raise FileNotFoundError(f"Expected dataset missing: {path}")

    match_frames = [
        _load_brasileirao(files["brasileirao"]),
        _load_brazilian_cup(files["copa_brasil"]),
        _load_libertadores(files["libertadores"]),
        _load_br_football(files["br_football"]),
        _load_novo_campeonato(files["novo_brasileirao"]),
    ]

    matches = pd.concat(match_frames, ignore_index=True, sort=False)
    matches = _attach_normalized_team_columns(matches)
    # Drop rows that have no usable score or team info
    matches = matches.dropna(subset=["home_team", "away_team"])
    matches = matches[(matches["home_team"] != "") & (matches["away_team"] != "")]
    # Drop pathological rows where the same team appears as both home and away
    # (a small amount of these exist in the raw data, e.g. forfeited cup ties)
    matches = matches[matches["home_team"] != matches["away_team"]]
    matches = _dedupe_matches(matches)
    matches = matches.reset_index(drop=True)

    players = _load_fifa(files["fifa"])

    return SoccerData(
        matches=matches,
        players=players,
        sources={k: str(p) for k, p in files.items()},
    )
