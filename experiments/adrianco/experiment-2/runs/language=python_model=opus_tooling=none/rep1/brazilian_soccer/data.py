"""Data loading and query layer for Brazilian soccer datasets."""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from typing import Iterable

import pandas as pd


DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle"
)


def _strip_accents(s: str) -> str:
    if not isinstance(s, str):
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_team(name: object) -> str:
    """Normalize team names across datasets.

    Drops state suffixes (e.g. "-SP", " - MG", "(URU)"), strips accents,
    lowercases, collapses whitespace, and trims common prefixes/suffixes
    like "Sport Club", "Esporte Clube", "FC".
    """
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    s = str(name).strip()
    # Remove trailing country/state codes in parentheses like "(URU)"
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s)
    # Remove trailing " - XX" or "-XX" state/country tags
    s = re.sub(r"\s*-\s*[A-Za-z]{2,3}\s*$", "", s)
    s = _strip_accents(s).lower()
    # Remove common club affix noise
    for token in (
        "sport club corinthians paulista",
        "esporte clube",
        "sport club",
        "futebol clube",
        "futebol e regatas",
        "clube de regatas",
        "clube",
        "s.c.",
        "f.c.",
        "ec",
        "sc",
        "fc",
    ):
        s = re.sub(rf"\b{re.escape(token)}\b", " ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Known aliases
    aliases = {
        "corinthians paulista": "corinthians",
        "gremio": "gremio",
        "atletico mineiro": "atletico mg",
        "atletico paranaense": "athletico pr",
        "athletico paranaense": "athletico pr",
        "atletico pr": "athletico pr",
        "sao paulo": "sao paulo",
        "america": "america",
    }
    return aliases.get(s, s)


def _parse_date(val: object) -> datetime | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, datetime):
        return val
    s = str(val).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        return pd.to_datetime(s, errors="coerce").to_pydatetime()
    except Exception:
        return None


@dataclass
class SoccerData:
    """Unified access to all soccer datasets."""

    data_dir: str = DEFAULT_DATA_DIR
    brasileirao: pd.DataFrame = field(default_factory=pd.DataFrame)
    cup: pd.DataFrame = field(default_factory=pd.DataFrame)
    libertadores: pd.DataFrame = field(default_factory=pd.DataFrame)
    extended: pd.DataFrame = field(default_factory=pd.DataFrame)
    historical: pd.DataFrame = field(default_factory=pd.DataFrame)
    players: pd.DataFrame = field(default_factory=pd.DataFrame)
    matches: pd.DataFrame = field(default_factory=pd.DataFrame)

    def __post_init__(self) -> None:
        self.load()

    # ---------- Loading ----------
    def load(self) -> None:
        d = self.data_dir
        self.brasileirao = self._load_matches(
            os.path.join(d, "Brasileirao_Matches.csv"),
            tournament="Brasileirão Serie A",
            home="home_team",
            away="away_team",
            hg="home_goal",
            ag="away_goal",
            date="datetime",
            season="season",
            round_col="round",
        )
        self.cup = self._load_matches(
            os.path.join(d, "Brazilian_Cup_Matches.csv"),
            tournament="Copa do Brasil",
            home="home_team",
            away="away_team",
            hg="home_goal",
            ag="away_goal",
            date="datetime",
            season="season",
            round_col="round",
        )
        self.libertadores = self._load_matches(
            os.path.join(d, "Libertadores_Matches.csv"),
            tournament="Copa Libertadores",
            home="home_team",
            away="away_team",
            hg="home_goal",
            ag="away_goal",
            date="datetime",
            season="season",
            stage="stage",
        )
        self.extended = self._load_matches(
            os.path.join(d, "BR-Football-Dataset.csv"),
            tournament_col="tournament",
            home="home",
            away="away",
            hg="home_goal",
            ag="away_goal",
            date="date",
        )
        self.historical = self._load_matches(
            os.path.join(d, "novo_campeonato_brasileiro.csv"),
            tournament="Brasileirão (historical)",
            home="Equipe_mandante",
            away="Equipe_visitante",
            hg="Gols_mandante",
            ag="Gols_visitante",
            date="Data",
            season="Ano",
            round_col="Rodada",
            arena="Arena",
        )

        frames = [self.brasileirao, self.cup, self.libertadores,
                  self.extended, self.historical]
        self.matches = pd.concat(frames, ignore_index=True, sort=False)

        # Players
        p_path = os.path.join(d, "fifa_data.csv")
        players = pd.read_csv(p_path, encoding="utf-8")
        players.columns = [c.strip().lstrip("\ufeff") for c in players.columns]
        self.players = players

    @staticmethod
    def _load_matches(
        path: str,
        *,
        tournament: str | None = None,
        tournament_col: str | None = None,
        home: str,
        away: str,
        hg: str,
        ag: str,
        date: str,
        season: str | None = None,
        round_col: str | None = None,
        stage: str | None = None,
        arena: str | None = None,
    ) -> pd.DataFrame:
        df = pd.read_csv(path, encoding="utf-8")
        out = pd.DataFrame()
        out["home_team"] = df[home].astype(str)
        out["away_team"] = df[away].astype(str)
        out["home_goal"] = pd.to_numeric(df[hg], errors="coerce")
        out["away_goal"] = pd.to_numeric(df[ag], errors="coerce")
        out["datetime"] = df[date].apply(_parse_date)
        out["season"] = (
            pd.to_numeric(df[season], errors="coerce").astype("Int64")
            if season and season in df.columns
            else out["datetime"].apply(lambda d: d.year if d else None)
        )
        out["round"] = df[round_col].astype(str) if round_col and round_col in df.columns else None
        out["stage"] = df[stage] if stage and stage in df.columns else None
        out["arena"] = df[arena] if arena and arena in df.columns else None
        if tournament_col and tournament_col in df.columns:
            out["tournament"] = df[tournament_col].astype(str)
        else:
            out["tournament"] = tournament or ""
        out["home_norm"] = out["home_team"].apply(normalize_team)
        out["away_norm"] = out["away_team"].apply(normalize_team)
        return out

    # ---------- Queries ----------
    def find_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        season: int | None = None,
        competition: str | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        df = self.matches
        if competition:
            c = competition.lower()
            df = df[df["tournament"].str.lower().str.contains(c, na=False)]
        if season is not None:
            df = df[df["season"] == season]
        if team:
            t = normalize_team(team)
            df = df[(df["home_norm"] == t) | (df["away_norm"] == t)]
        if opponent:
            o = normalize_team(opponent)
            df = df[(df["home_norm"] == o) | (df["away_norm"] == o)]
        df = df.sort_values("datetime", na_position="last")
        if limit:
            df = df.head(limit)
        return df

    def head_to_head(self, team_a: str, team_b: str) -> dict:
        a = normalize_team(team_a)
        b = normalize_team(team_b)
        df = self.matches
        mask = (
            ((df["home_norm"] == a) & (df["away_norm"] == b))
            | ((df["home_norm"] == b) & (df["away_norm"] == a))
        )
        sub = df[mask].dropna(subset=["home_goal", "away_goal"])
        a_wins = b_wins = draws = 0
        for _, r in sub.iterrows():
            hg, ag = r["home_goal"], r["away_goal"]
            if hg == ag:
                draws += 1
            elif (r["home_norm"] == a and hg > ag) or (r["away_norm"] == a and ag > hg):
                a_wins += 1
            else:
                b_wins += 1
        return {
            "team_a": team_a,
            "team_b": team_b,
            "matches": int(len(sub)),
            "team_a_wins": a_wins,
            "team_b_wins": b_wins,
            "draws": draws,
        }

    def team_stats(
        self,
        team: str,
        season: int | None = None,
        competition: str | None = None,
        home_only: bool = False,
        away_only: bool = False,
    ) -> dict:
        t = normalize_team(team)
        df = self.find_matches(team=team, season=season, competition=competition)
        df = df.dropna(subset=["home_goal", "away_goal"])
        if home_only:
            df = df[df["home_norm"] == t]
        if away_only:
            df = df[df["away_norm"] == t]
        wins = draws = losses = gf = ga = 0
        for _, r in df.iterrows():
            is_home = r["home_norm"] == t
            team_goals = r["home_goal"] if is_home else r["away_goal"]
            opp_goals = r["away_goal"] if is_home else r["home_goal"]
            gf += int(team_goals)
            ga += int(opp_goals)
            if team_goals > opp_goals:
                wins += 1
            elif team_goals < opp_goals:
                losses += 1
            else:
                draws += 1
        total = wins + draws + losses
        return {
            "team": team,
            "season": season,
            "competition": competition,
            "matches": total,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": gf,
            "goals_against": ga,
            "goal_difference": gf - ga,
            "points": wins * 3 + draws,
            "win_rate": (wins / total) if total else 0.0,
        }

    def standings(self, season: int, competition: str = "Brasileirão") -> pd.DataFrame:
        df = self.find_matches(season=season, competition=competition)
        df = df.dropna(subset=["home_goal", "away_goal"])
        teams: dict[str, dict] = {}
        for _, r in df.iterrows():
            for key, team, gf, ga in (
                (r["home_norm"], r["home_team"], r["home_goal"], r["away_goal"]),
                (r["away_norm"], r["away_team"], r["away_goal"], r["home_goal"]),
            ):
                if not key:
                    continue
                t = teams.setdefault(
                    key,
                    {"team": team, "P": 0, "W": 0, "D": 0, "L": 0,
                     "GF": 0, "GA": 0, "Pts": 0},
                )
                t["P"] += 1
                t["GF"] += int(gf)
                t["GA"] += int(ga)
                if gf > ga:
                    t["W"] += 1
                    t["Pts"] += 3
                elif gf == ga:
                    t["D"] += 1
                    t["Pts"] += 1
                else:
                    t["L"] += 1
        table = pd.DataFrame(list(teams.values()))
        if table.empty:
            return table
        table["GD"] = table["GF"] - table["GA"]
        return table.sort_values(
            ["Pts", "W", "GD", "GF"], ascending=[False, False, False, False]
        ).reset_index(drop=True)

    def biggest_wins(self, limit: int = 10, competition: str | None = None) -> pd.DataFrame:
        df = self.matches.dropna(subset=["home_goal", "away_goal"]).copy()
        if competition:
            df = df[df["tournament"].str.lower().str.contains(competition.lower(), na=False)]
        df["margin"] = (df["home_goal"] - df["away_goal"]).abs()
        return df.sort_values(["margin", "home_goal", "away_goal"], ascending=False).head(limit)

    def average_goals(self, competition: str | None = None, season: int | None = None) -> dict:
        df = self.matches.dropna(subset=["home_goal", "away_goal"])
        if competition:
            df = df[df["tournament"].str.lower().str.contains(competition.lower(), na=False)]
        if season is not None:
            df = df[df["season"] == season]
        if len(df) == 0:
            return {"matches": 0, "avg_goals": 0.0, "home_win_rate": 0.0}
        total_goals = (df["home_goal"] + df["away_goal"]).sum()
        home_wins = (df["home_goal"] > df["away_goal"]).sum()
        return {
            "matches": int(len(df)),
            "avg_goals": float(total_goals / len(df)),
            "home_win_rate": float(home_wins / len(df)),
        }

    # ---------- Players ----------
    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        limit: int = 25,
    ) -> pd.DataFrame:
        df = self.players
        if name:
            df = df[df["Name"].str.contains(name, case=False, na=False)]
        if nationality:
            df = df[df["Nationality"].str.contains(nationality, case=False, na=False)]
        if club:
            df = df[df["Club"].fillna("").str.contains(club, case=False, na=False)]
        if position:
            df = df[df["Position"].fillna("").str.contains(position, case=False, na=False)]
        if min_overall is not None:
            df = df[df["Overall"] >= min_overall]
        cols = [c for c in ["Name", "Age", "Nationality", "Overall",
                            "Potential", "Club", "Position", "Jersey Number"]
                if c in df.columns]
        return df.sort_values("Overall", ascending=False).head(limit)[cols]


@lru_cache(maxsize=1)
def get_data(data_dir: str | None = None) -> SoccerData:
    return SoccerData(data_dir=data_dir or DEFAULT_DATA_DIR)
