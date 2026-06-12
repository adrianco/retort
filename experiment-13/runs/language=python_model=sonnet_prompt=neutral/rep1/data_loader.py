import unicodedata
import re
from pathlib import Path

import pandas as pd


def normalize_team(name) -> str:
    """Normalize a team name: strip state suffix, remove accents, lowercase."""
    if not isinstance(name, str) or not name.strip():
        return ""
    # Remove parenthetical parts like "(antigo Esporte Clube...)"
    name = re.sub(r"\s*\([^)]*\)\s*", " ", name).strip()
    # Remove trailing state suffix like "- RJ", "-SP", "– MG"
    name = re.sub(r"\s*[-–]\s*[A-Z]{2}\s*$", "", name).strip()
    # Strip diacritics
    nfkd = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in nfkd if not unicodedata.combining(c))
    return name.lower().strip()


class DataLoader:
    """Loads all six soccer CSV datasets and provides a unified matches view."""

    DATA_DIR = Path(__file__).parent / "data" / "kaggle"

    def __init__(self, data_dir: str | None = None):
        self.data_dir = Path(data_dir) if data_dir else self.DATA_DIR
        self.brasileirao = self._load_brasileirao()
        self.copa_brasil = self._load_copa_brasil()
        self.libertadores = self._load_libertadores()
        self.extended = self._load_extended()
        self.historico = self._load_historico()
        self.fifa = self._load_fifa()
        self.all_matches = self._build_unified()

    # ------------------------------------------------------------------ #
    # Private loaders                                                      #
    # ------------------------------------------------------------------ #

    def _finalize(self, df: pd.DataFrame, default_comp: str, src: str) -> pd.DataFrame:
        """Apply common type coercions and add norm/source columns."""
        out = df.copy()
        if "competition" not in out.columns:
            out["competition"] = default_comp
        out["source"] = src
        if "round_info" not in out.columns:
            out["round_info"] = ""
        if "season" not in out.columns:
            out["season"] = pd.NA

        out["home_team_norm"] = out["home_team"].apply(normalize_team)
        out["away_team_norm"] = out["away_team"].apply(normalize_team)
        out["home_goal"] = pd.to_numeric(out["home_goal"], errors="coerce")
        out["away_goal"] = pd.to_numeric(out["away_goal"], errors="coerce")
        out["season"] = pd.to_numeric(out["season"], errors="coerce").astype("Int64")
        out["round_info"] = out["round_info"].fillna("").astype(str)
        out["competition"] = out["competition"].fillna(default_comp).astype(str)

        return out[
            [
                "date",
                "home_team",
                "away_team",
                "home_goal",
                "away_goal",
                "competition",
                "season",
                "home_team_norm",
                "away_team_norm",
                "round_info",
                "source",
            ]
        ]

    def _load_brasileirao(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "Brasileirao_Matches.csv")
        df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
        df["round_info"] = "Round " + df["round"].astype(str)
        return self._finalize(df, "Brasileirão", "brasileirao")

    def _load_copa_brasil(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "Brazilian_Cup_Matches.csv")
        df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
        df["round_info"] = df["round"].astype(str)
        return self._finalize(df, "Copa do Brasil", "copa_brasil")

    def _load_libertadores(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "Libertadores_Matches.csv")
        df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
        df["round_info"] = df["stage"].fillna("").astype(str)
        return self._finalize(df, "Copa Libertadores", "libertadores")

    def _load_extended(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "BR-Football-Dataset.csv")
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["season"] = df["date"].dt.year
        df = df.rename(
            columns={"home": "home_team", "away": "away_team", "tournament": "competition"}
        )
        return self._finalize(df, "BR Football", "extended")

    def _load_historico(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "novo_campeonato_brasileiro.csv")
        df["date"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
        df["season"] = df["Ano"]
        df["home_team"] = df["Equipe_mandante"]
        df["away_team"] = df["Equipe_visitante"]
        df["home_goal"] = df["Gols_mandante"]
        df["away_goal"] = df["Gols_visitante"]
        df["round_info"] = "Round " + df["Rodada"].astype(str)
        return self._finalize(df, "Brasileirão", "historico")

    def _load_fifa(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "fifa_data.csv", encoding="utf-8-sig")
        # First column is an unnamed row-index artifact
        if df.columns[0] in ("", "Unnamed: 0"):
            df = df.rename(columns={df.columns[0]: "_idx"})
        df["name_norm"] = df["Name"].apply(
            lambda x: normalize_team(str(x)) if pd.notna(x) else ""
        )
        df["club_norm"] = df["Club"].apply(
            lambda x: normalize_team(str(x)) if pd.notna(x) else ""
        )
        df["nationality_norm"] = df["Nationality"].apply(
            lambda x: normalize_team(str(x)) if pd.notna(x) else ""
        )
        df["Overall"] = pd.to_numeric(df["Overall"], errors="coerce")
        df["Potential"] = pd.to_numeric(df["Potential"], errors="coerce")
        df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
        return df

    def _build_unified(self) -> pd.DataFrame:
        return pd.concat(
            [
                self.brasileirao,
                self.copa_brasil,
                self.libertadores,
                self.extended,
                self.historico,
            ],
            ignore_index=True,
        )
