import os
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "kaggle"


def _normalize_team_name(name: str) -> str:
    if not isinstance(name, str):
        return str(name)
    name = name.strip()
    suffixes = [
        "-SP", "-RJ", "-MG", "-RS", "-PR", "-SC", "-BA", "-PE",
        "-CE", "-GO", "-PA", "-DF", "-RN", "-AL", "-SE", "-MA",
        "-MT", "-MS", "-ES", "-PB", "-PI", "-AM", "-AP", "-RO",
        "-RR", "-TO", "-AC",
    ]
    for s in suffixes:
        if name.endswith(s):
            name = name[: -len(s)]
            break
    return name.strip()


def _parse_date(series: pd.Series) -> pd.Series:
    out = pd.to_datetime(series, format="%Y-%m-%d %H:%M:%S", errors="coerce")
    mask = out.isna()
    if mask.any():
        out[mask] = pd.to_datetime(series[mask], format="%Y-%m-%d", errors="coerce")
    mask = out.isna()
    if mask.any():
        out[mask] = pd.to_datetime(series[mask], format="%d/%m/%Y", errors="coerce")
    mask = out.isna()
    if mask.any():
        out[mask] = pd.to_datetime(series[mask], errors="coerce")
    return out


def load_brasileirao(data_dir: Path | None = None) -> pd.DataFrame:
    p = (data_dir or DATA_DIR) / "Brasileirao_Matches.csv"
    df = pd.read_csv(p, encoding="utf-8")
    df["competition"] = "Brasileirao"
    df["date"] = _parse_date(df["datetime"])
    df["home"] = df["home_team"].apply(_normalize_team_name)
    df["away"] = df["away_team"].apply(_normalize_team_name)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["season"] = pd.to_numeric(df["season"], errors="coerce")
    df["round"] = df["round"].astype(str)
    return df[["date", "home", "away", "home_goal", "away_goal", "season", "round", "competition"]]


def load_copa_do_brasil(data_dir: Path | None = None) -> pd.DataFrame:
    p = (data_dir or DATA_DIR) / "Brazilian_Cup_Matches.csv"
    df = pd.read_csv(p, encoding="utf-8")
    df["competition"] = "Copa do Brasil"
    df["date"] = _parse_date(df["datetime"])
    df["home"] = df["home_team"].apply(_normalize_team_name)
    df["away"] = df["away_team"].apply(_normalize_team_name)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["season"] = pd.to_numeric(df["season"], errors="coerce")
    df["round"] = df["round"].astype(str)
    return df[["date", "home", "away", "home_goal", "away_goal", "season", "round", "competition"]]


def load_libertadores(data_dir: Path | None = None) -> pd.DataFrame:
    p = (data_dir or DATA_DIR) / "Libertadores_Matches.csv"
    df = pd.read_csv(p, encoding="utf-8")
    df["competition"] = "Copa Libertadores"
    df["date"] = _parse_date(df["datetime"])
    df["home"] = df["home_team"].apply(_normalize_team_name)
    df["away"] = df["away_team"].apply(_normalize_team_name)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["season"] = pd.to_numeric(df["season"], errors="coerce")
    df["round"] = df.get("stage", pd.Series([""] * len(df))).astype(str)
    return df[["date", "home", "away", "home_goal", "away_goal", "season", "round", "competition"]]


def load_br_football(data_dir: Path | None = None) -> pd.DataFrame:
    p = (data_dir or DATA_DIR) / "BR-Football-Dataset.csv"
    df = pd.read_csv(p, encoding="utf-8")
    df["competition"] = df["tournament"].fillna("Unknown")
    df["date"] = _parse_date(df["date"])
    df["home"] = df["home"].apply(_normalize_team_name)
    df["away"] = df["away"].apply(_normalize_team_name)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["season"] = df["date"].dt.year
    df["round"] = ""
    cols = ["date", "home", "away", "home_goal", "away_goal", "season", "round", "competition"]
    extra = {}
    for c in ["home_corner", "away_corner", "home_attack", "away_attack",
              "home_shots", "away_shots", "total_corners"]:
        if c in df.columns:
            extra[c] = pd.to_numeric(df[c], errors="coerce")
    out = df[cols].copy()
    for k, v in extra.items():
        out[k] = v
    return out


def load_historical_brasileirao(data_dir: Path | None = None) -> pd.DataFrame:
    p = (data_dir or DATA_DIR) / "novo_campeonato_brasileiro.csv"
    df = pd.read_csv(p, encoding="utf-8")
    df["competition"] = "Brasileirao"
    df["date"] = _parse_date(df["Data"])
    df["home"] = df["Equipe_mandante"].apply(_normalize_team_name)
    df["away"] = df["Equipe_visitante"].apply(_normalize_team_name)
    df["home_goal"] = pd.to_numeric(df["Gols_mandante"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["Gols_visitante"], errors="coerce")
    df["season"] = pd.to_numeric(df["Ano"], errors="coerce")
    df["round"] = df["Rodada"].astype(str)
    df["arena"] = df.get("Arena", pd.Series([""] * len(df)))
    return df[["date", "home", "away", "home_goal", "away_goal", "season", "round", "competition", "arena"]]


def load_fifa_players(data_dir: Path | None = None) -> pd.DataFrame:
    p = (data_dir or DATA_DIR) / "fifa_data.csv"
    df = pd.read_csv(p, encoding="utf-8")
    cols_keep = [
        "ID", "Name", "Age", "Nationality", "Overall", "Potential",
        "Club", "Position", "Jersey Number", "Height", "Weight",
        "Preferred Foot", "Work Rate",
        "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing",
        "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
        "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
        "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
        "Aggression", "Interceptions", "Positioning", "Vision",
        "Penalties", "Composure", "Marking", "StandingTackle", "SlidingTackle",
        "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
        "Value", "Wage", "Release Clause",
    ]
    existing = [c for c in cols_keep if c in df.columns]
    out = df[existing].copy()
    for c in ["Overall", "Potential", "Age"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


class BrazilianSoccerData:
    def __init__(self, data_dir: Path | None = None):
        self._data_dir = data_dir or DATA_DIR
        self._matches: pd.DataFrame | None = None
        self._br_football: pd.DataFrame | None = None
        self._historical: pd.DataFrame | None = None
        self._players: pd.DataFrame | None = None
        self._all_matches: pd.DataFrame | None = None

    def _load(self):
        if self._matches is not None:
            return
        brasileirao = load_brasileirao(self._data_dir)
        copa = load_copa_do_brasil(self._data_dir)
        libertadores = load_libertadores(self._data_dir)
        self._matches = pd.concat([brasileirao, copa, libertadores], ignore_index=True)
        self._br_football = load_br_football(self._data_dir)
        self._historical = load_historical_brasileirao(self._data_dir)
        self._players = load_fifa_players(self._data_dir)

        common_cols = ["date", "home", "away", "home_goal", "away_goal", "season", "round", "competition"]
        self._all_matches = pd.concat([
            self._matches[common_cols],
            self._br_football[common_cols],
            self._historical[common_cols],
        ], ignore_index=True)
        self._all_matches = self._all_matches.sort_values("date", ascending=False, na_position="last")

    @property
    def all_matches(self) -> pd.DataFrame:
        self._load()
        return self._all_matches

    @property
    def br_football(self) -> pd.DataFrame:
        self._load()
        return self._br_football

    @property
    def historical(self) -> pd.DataFrame:
        self._load()
        return self._historical

    @property
    def players(self) -> pd.DataFrame:
        self._load()
        return self._players

    def _team_matches(self, team: str, home: bool = True, away: bool = True) -> pd.Series:
        t = _normalize_team_name(team).lower()
        masks = []
        if home:
            masks.append(self.all_matches["home"].str.lower().str.contains(t, na=False))
        if away:
            masks.append(self.all_matches["away"].str.lower().str.contains(t, na=False))
        if not masks:
            return pd.Series([False] * len(self.all_matches))
        combined = masks[0]
        for m in masks[1:]:
            combined = combined | m
        return combined

    def search_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
    ) -> pd.DataFrame:
        self._load()
        df = self.all_matches.copy()
        if team:
            df = df[self._team_matches(team)]
        if opponent:
            opp = _normalize_team_name(opponent).lower()
            mask = (
                df["home"].str.lower().str.contains(opp, na=False)
                | df["away"].str.lower().str.contains(opp, na=False)
            )
            df = df[mask]
        if competition:
            comp_lower = competition.lower()
            df = df[df["competition"].str.lower().str.contains(comp_lower, na=False)]
        if season is not None:
            df = df[df["season"] == season]
        if date_from:
            dt_from = pd.to_datetime(date_from, errors="coerce")
            if pd.notna(dt_from):
                df = df[df["date"] >= dt_from]
        if date_to:
            dt_to = pd.to_datetime(date_to, errors="coerce")
            if pd.notna(dt_to):
                df = df[df["date"] <= dt_to]
        return df.head(limit)

    def team_statistics(
        self,
        team: str,
        competition: str | None = None,
        season: int | None = None,
        home_only: bool = False,
        away_only: bool = False,
    ) -> dict:
        self._load()
        t = _normalize_team_name(team).lower()
        df = self.all_matches
        if competition:
            df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]
        if season is not None:
            df = df[df["season"] == season]

        home_mask = df["home"].str.lower().str.contains(t, na=False)
        away_mask = df["away"].str.lower().str.contains(t, na=False)

        if home_only:
            matches = df[home_mask]
        elif away_only:
            matches = df[away_mask]
        else:
            matches = df[home_mask | away_mask]

        if matches.empty:
            return {"team": team, "matches": 0, "wins": 0, "draws": 0, "losses": 0,
                    "goals_for": 0, "goals_against": 0}

        home_matches = matches[matches["home"].str.lower().str.contains(t, na=False)]
        away_matches = matches[matches["away"].str.lower().str.contains(t, na=False)]

        home_wins = (home_matches["home_goal"] > home_matches["away_goal"]).sum()
        away_wins = (away_matches["away_goal"] > away_matches["home_goal"]).sum()
        home_draws = (home_matches["home_goal"] == home_matches["away_goal"]).sum()
        away_draws = (away_matches["away_goal"] == away_matches["home_goal"]).sum()
        home_losses = (home_matches["home_goal"] < home_matches["away_goal"]).sum()
        away_losses = (away_matches["away_goal"] < away_matches["home_goal"]).sum()

        goals_for = home_matches["home_goal"].sum() + away_matches["away_goal"].sum()
        goals_against = home_matches["away_goal"].sum() + away_matches["home_goal"].sum()

        total = len(matches)
        wins = int(home_wins + away_wins)
        draws = int(home_draws + away_draws)
        losses = int(home_losses + away_losses)

        return {
            "team": team,
            "matches": total,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": int(goals_for),
            "goals_against": int(goals_against),
            "win_rate": round(wins / total * 100, 1) if total > 0 else 0.0,
            "points": wins * 3 + draws,
        }

    def head_to_head(self, team1: str, team2: str, competition: str | None = None) -> dict:
        matches = self.search_matches(team=team1, opponent=team2, competition=competition, limit=10000)
        t1 = _normalize_team_name(team1).lower()
        t2 = _normalize_team_name(team2).lower()

        t1_wins = 0
        t2_wins = 0
        draws = 0

        for _, row in matches.iterrows():
            h = row["home"].lower()
            a = row["away"].lower()
            hg, ag = row["home_goal"], row["away_goal"]
            if pd.isna(hg) or pd.isna(ag):
                continue
            if t1 in h and t2 in a:
                if hg > ag:
                    t1_wins += 1
                elif ag > hg:
                    t2_wins += 1
                else:
                    draws += 1
            elif t2 in h and t1 in a:
                if hg > ag:
                    t2_wins += 1
                elif ag > hg:
                    t1_wins += 1
                else:
                    draws += 1

        return {
            "team1": team1,
            "team2": team2,
            "total_matches": len(matches),
            f"{team1}_wins": t1_wins,
            f"{team2}_wins": t2_wins,
            "draws": draws,
        }

    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        limit: int = 50,
    ) -> pd.DataFrame:
        self._load()
        df = self.players.copy()
        if name:
            df = df[df["Name"].str.lower().str.contains(name.lower(), na=False)]
        if nationality:
            df = df[df["Nationality"].str.lower().str.contains(nationality.lower(), na=False)]
        if club:
            df = df[df["Club"].str.lower().str.contains(club.lower(), na=False)]
        if position:
            df = df[df["Position"].str.lower().str.contains(position.lower(), na=False)]
        if min_overall is not None:
            df = df[df["Overall"] >= min_overall]
        return df.sort_values("Overall", ascending=False).head(limit)

    def competition_standings(self, competition: str, season: int) -> pd.DataFrame:
        self._load()
        comp = competition.lower()
        df = self.all_matches
        df = df[df["competition"].str.lower().str.contains(comp, na=False)]
        df = df[df["season"] == season]

        if df.empty:
            return pd.DataFrame()

        teams = set(df["home"].tolist() + df["away"].tolist())
        rows = []
        for team in teams:
            stats = self.team_statistics(team, competition=competition, season=season)
            rows.append(stats)

        standings = pd.DataFrame(rows)
        standings = standings.sort_values(
            ["points", "wins", "goals_for"], ascending=[False, False, False]
        ).reset_index(drop=True)
        standings.index = standings.index + 1
        return standings

    def match_statistics(
        self,
        team: str | None = None,
        competition: str | None = None,
        season: int | None = None,
    ) -> dict:
        self._load()
        df = self.all_matches
        if competition:
            df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]
        if season is not None:
            df = df[df["season"] == season]
        if team:
            t = _normalize_team_name(team).lower()
            df = df[
                df["home"].str.lower().str.contains(t, na=False)
                | df["away"].str.lower().str.contains(t, na=False)
            ]

        valid = df.dropna(subset=["home_goal", "away_goal"])
        total_matches = len(valid)
        if total_matches == 0:
            return {"total_matches": 0}

        total_goals = valid["home_goal"].sum() + valid["away_goal"].sum()
        home_wins = (valid["home_goal"] > valid["away_goal"]).sum()
        away_wins = (valid["away_goal"] > valid["home_goal"]).sum()
        draws_count = (valid["home_goal"] == valid["away_goal"]).sum()

        goal_diff = (valid["home_goal"] - valid["away_goal"]).abs()
        biggest_idx = goal_diff.idxmax()
        biggest = valid.loc[biggest_idx]

        return {
            "total_matches": total_matches,
            "total_goals": int(total_goals),
            "avg_goals_per_match": round(float(total_goals / total_matches), 2),
            "home_wins": int(home_wins),
            "away_wins": int(away_wins),
            "draws": int(draws_count),
            "home_win_rate": round(float(home_wins / total_matches * 100), 1),
            "away_win_rate": round(float(away_wins / total_matches * 100), 1),
            "draw_rate": round(float(draws_count / total_matches * 100), 1),
            "biggest_win": {
                "date": str(biggest["date"]),
                "home": biggest["home"],
                "away": biggest["away"],
                "score": f"{int(biggest['home_goal'])}-{int(biggest['away_goal'])}",
            },
        }
