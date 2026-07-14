import os
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "kaggle"

TEAM_NAME_MAP = {
    "palmeiras-sp": "Palmeiras",
    "flamengo-rj": "Flamengo",
    "fluminense-rj": "Fluminense",
    "corinthians-sp": "Corinthians",
    "santos-sp": "Santos",
    "são paulo-sp": "São Paulo",
    "sao paulo-sp": "São Paulo",
    "sao paulo": "São Paulo",
    "são paulo": "São Paulo",
    "grêmio-rs": "Grêmio",
    "gremio-rs": "Grêmio",
    "gremio": "Grêmio",
    "grêmio": "Grêmio",
    "internacional-rs": "Internacional",
    "atlético-mg": "Atlético-MG",
    "atletico-mg": "Atlético-MG",
    "atletico mineiro": "Atlético-MG",
    "atlético mineiro": "Atlético-MG",
    "cruzeiro-mg": "Cruzeiro",
    "vasco-rj": "Vasco",
    "vasco da gama": "Vasco",
    "vasco da gama-rj": "Vasco",
    "botafogo-rj": "Botafogo",
    "sport-pe": "Sport",
    "coritiba-pr": "Coritiba",
    "athletico-pr": "Athletico-PR",
    "atletico-pr": "Athletico-PR",
    "athletico paranaense": "Athletico-PR",
    "bahia-ba": "Bahia",
    "fortaleza-ce": "Fortaleza",
    "ceará-ce": "Ceará",
    "ceara-ce": "Ceará",
    "goiás-go": "Goiás",
    "goias-go": "Goiás",
    "avaí-sc": "Avaí",
    "avai-sc": "Avaí",
    "chapecoense-sc": "Chapecoense",
    "portuguesa-sp": "Portuguesa",
    "náutico-pe": "Náutico",
    "nautico-pe": "Náutico",
    "figueirense-sc": "Figueirense",
    "ponte preta-sp": "Ponte Preta",
    "criciúma-sc": "Criciúma",
    "criciuma-sc": "Criciúma",
    "vitória-ba": "Vitória",
    "vitoria-ba": "Vitória",
    "juventude-rs": "Juventude",
    "america-mg": "América-MG",
    "américa-mg": "América-MG",
    "cuiabá-mt": "Cuiabá",
    "cuiaba-mt": "Cuiabá",
    "bragantino-sp": "Bragantino",
    "red bull bragantino-sp": "Bragantino",
    "red bull bragantino": "Bragantino",
    "paraná-pr": "Paraná",
    "parana-pr": "Paraná",
    "guarani-sp": "Guarani",
    "flamengo - rj": "Flamengo",
    "fluminense - rj": "Fluminense",
    "palmeiras - sp": "Palmeiras",
    "corinthians - sp": "Corinthians",
    "santos - sp": "Santos",
    "américa - mg": "América-MG",
    "america - mg": "América-MG",
}


def normalize_team_name(name: str) -> str:
    if not isinstance(name, str):
        return str(name)
    stripped = name.strip()
    key = stripped.lower()
    if key in TEAM_NAME_MAP:
        return TEAM_NAME_MAP[key]
    if "-" in stripped:
        base = stripped.rsplit("-", 1)[0].strip()
        base_key = base.lower()
        if base_key in TEAM_NAME_MAP:
            return TEAM_NAME_MAP[base_key]
        return base
    return stripped


def team_matches(name: str, query: str) -> bool:
    n = normalize_team_name(name).lower()
    q = normalize_team_name(query).lower()
    if q == n:
        return True
    if q in n or n in q:
        return True
    return False


def load_brasileirao() -> pd.DataFrame:
    path = DATA_DIR / "Brasileirao_Matches.csv"
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["home_team_norm"] = df["home_team"].apply(normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(normalize_team_name)
    df["competition"] = "Brasileirão"
    return df


def load_copa_do_brasil() -> pd.DataFrame:
    path = DATA_DIR / "Brazilian_Cup_Matches.csv"
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["home_team_norm"] = df["home_team"].apply(normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(normalize_team_name)
    df["competition"] = "Copa do Brasil"
    df["season"] = df["season"].astype(int)
    return df


def load_libertadores() -> pd.DataFrame:
    path = DATA_DIR / "Libertadores_Matches.csv"
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["home_team_norm"] = df["home_team"].apply(normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(normalize_team_name)
    df["competition"] = "Libertadores"
    return df


def load_extended_stats() -> pd.DataFrame:
    path = DATA_DIR / "BR-Football-Dataset.csv"
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["home_norm"] = df["home"].apply(normalize_team_name)
    df["away_norm"] = df["away"].apply(normalize_team_name)
    return df


def load_historical() -> pd.DataFrame:
    path = DATA_DIR / "novo_campeonato_brasileiro.csv"
    df = pd.read_csv(path, encoding="utf-8")
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
    df["home_team_norm"] = df["Equipe_mandante"].apply(normalize_team_name)
    df["away_team_norm"] = df["Equipe_visitante"].apply(normalize_team_name)
    df["competition"] = "Brasileirão"
    return df


def load_fifa_players() -> pd.DataFrame:
    path = DATA_DIR / "fifa_data.csv"
    df = pd.read_csv(path, encoding="utf-8")
    if df.columns[0].startswith("﻿"):
        df = df.rename(columns={df.columns[0]: df.columns[0].lstrip("﻿")})
    first_col = df.columns[0]
    if first_col == "" or first_col == "Unnamed: 0":
        df = df.drop(columns=[first_col])
    return df


class BrazilianSoccerData:
    def __init__(self):
        self.brasileirao = load_brasileirao()
        self.copa_do_brasil = load_copa_do_brasil()
        self.libertadores = load_libertadores()
        self.extended_stats = load_extended_stats()
        self.historical = load_historical()
        self.fifa_players = load_fifa_players()

    def search_matches(
        self,
        team: str | None = None,
        team2: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        limit: int = 50,
    ) -> list[dict]:
        results = []

        for source_name, df, home_col, away_col, hg_col, ag_col, dt_col, comp_col, season_col in [
            ("brasileirao", self.brasileirao, "home_team_norm", "away_team_norm", "home_goal", "away_goal", "datetime", "competition", "season"),
            ("copa_do_brasil", self.copa_do_brasil, "home_team_norm", "away_team_norm", "home_goal", "away_goal", "datetime", "competition", "season"),
            ("libertadores", self.libertadores, "home_team_norm", "away_team_norm", "home_goal", "away_goal", "datetime", "competition", "season"),
        ]:
            filtered = df

            if competition:
                comp_lower = competition.lower()
                comp_map = {
                    "brasileirão": "Brasileirão",
                    "brasileirao": "Brasileirão",
                    "serie a": "Brasileirão",
                    "copa do brasil": "Copa do Brasil",
                    "brazilian cup": "Copa do Brasil",
                    "libertadores": "Libertadores",
                    "copa libertadores": "Libertadores",
                }
                mapped = comp_map.get(comp_lower, competition)
                if comp_col in filtered.columns:
                    filtered = filtered[filtered[comp_col].str.lower() == mapped.lower()]
                    if filtered.empty:
                        continue

            if season is not None and season_col in filtered.columns:
                filtered = filtered[filtered[season_col] == season]

            if team:
                if filtered.empty:
                    continue
                mask_home = filtered[home_col].apply(lambda x: team_matches(x, team)).astype(bool)
                mask_away = filtered[away_col].apply(lambda x: team_matches(x, team)).astype(bool)
                if team2:
                    mask_home2 = filtered[home_col].apply(lambda x: team_matches(x, team2)).astype(bool)
                    mask_away2 = filtered[away_col].apply(lambda x: team_matches(x, team2)).astype(bool)
                    filtered = filtered[
                        ((mask_home) & (mask_away2)) | ((mask_away) & (mask_home2))
                    ]
                else:
                    filtered = filtered[mask_home | mask_away]

            for _, row in filtered.head(limit).iterrows():
                match = {
                    "date": str(row[dt_col]) if pd.notna(row[dt_col]) else None,
                    "home_team": row[home_col],
                    "away_team": row[away_col],
                    "home_goals": int(row[hg_col]) if pd.notna(row[hg_col]) else None,
                    "away_goals": int(row[ag_col]) if pd.notna(row[ag_col]) else None,
                    "competition": row.get(comp_col, source_name),
                    "season": int(row[season_col]) if season_col in row.index and pd.notna(row[season_col]) else None,
                }
                if "round" in row.index and pd.notna(row.get("round")):
                    match["round"] = str(row["round"])
                if "stage" in row.index and pd.notna(row.get("stage")):
                    match["stage"] = str(row["stage"])
                results.append(match)

        results.sort(key=lambda x: x["date"] or "", reverse=True)
        return results[:limit]

    def get_team_stats(
        self,
        team: str,
        competition: str | None = None,
        season: int | None = None,
    ) -> dict:
        matches = self.search_matches(team=team, competition=competition, season=season, limit=10000)
        wins = draws = losses = goals_for = goals_against = 0
        home_matches = away_matches = 0
        home_wins = away_wins = 0

        for m in matches:
            hg = m["home_goals"]
            ag = m["away_goals"]
            if hg is None or ag is None:
                continue
            is_home = team_matches(m["home_team"], team)
            if is_home:
                home_matches += 1
                gf, ga = hg, ag
                if hg > ag:
                    wins += 1
                    home_wins += 1
                elif hg == ag:
                    draws += 1
                else:
                    losses += 1
            else:
                away_matches += 1
                gf, ga = ag, hg
                if ag > hg:
                    wins += 1
                    away_wins += 1
                elif ag == hg:
                    draws += 1
                else:
                    losses += 1
            goals_for += gf
            goals_against += ga

        total = wins + draws + losses
        return {
            "team": normalize_team_name(team),
            "matches": total,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "goal_difference": goals_for - goals_against,
            "points": wins * 3 + draws,
            "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
            "home_matches": home_matches,
            "home_wins": home_wins,
            "away_matches": away_matches,
            "away_wins": away_wins,
            "competition": competition,
            "season": season,
        }

    def head_to_head(self, team1: str, team2: str) -> dict:
        matches = self.search_matches(team=team1, team2=team2, limit=10000)
        t1_wins = t2_wins = draws = t1_goals = t2_goals = 0

        for m in matches:
            hg = m["home_goals"]
            ag = m["away_goals"]
            if hg is None or ag is None:
                continue
            t1_is_home = team_matches(m["home_team"], team1)
            if t1_is_home:
                g1, g2 = hg, ag
            else:
                g1, g2 = ag, hg
            t1_goals += g1
            t2_goals += g2
            if g1 > g2:
                t1_wins += 1
            elif g2 > g1:
                t2_wins += 1
            else:
                draws += 1

        n1 = normalize_team_name(team1)
        n2 = normalize_team_name(team2)
        return {
            "team1": n1,
            "team2": n2,
            "total_matches": len(matches),
            f"{n1}_wins": t1_wins,
            f"{n2}_wins": t2_wins,
            "draws": draws,
            f"{n1}_goals": t1_goals,
            f"{n2}_goals": t2_goals,
            "recent_matches": matches[:10],
        }

    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        limit: int = 50,
    ) -> list[dict]:
        df = self.fifa_players.copy()

        if name:
            df = df[df["Name"].str.contains(name, case=False, na=False)]
        if nationality:
            df = df[df["Nationality"].str.contains(nationality, case=False, na=False)]
        if club:
            df = df[df["Club"].str.contains(club, case=False, na=False)]
        if position:
            df = df[df["Position"].str.contains(position, case=False, na=False)]
        if min_overall is not None:
            df = df[pd.to_numeric(df["Overall"], errors="coerce") >= min_overall]

        df = df.sort_values("Overall", ascending=False)
        cols = ["Name", "Age", "Nationality", "Overall", "Potential", "Club", "Position"]
        available = [c for c in cols if c in df.columns]
        result = df.head(limit)[available].to_dict(orient="records")
        return result

    def get_standings(self, season: int) -> list[dict]:
        df = self.brasileirao[self.brasileirao["season"] == season].copy()

        if df.empty:
            df = self.historical[self.historical["Ano"] == season].copy()
            if df.empty:
                return []
            teams: dict[str, dict] = {}
            for _, row in df.iterrows():
                ht = row["home_team_norm"]
                at = row["away_team_norm"]
                hg = row["Gols_mandante"]
                ag = row["Gols_visitante"]
                if pd.isna(hg) or pd.isna(ag):
                    continue
                hg, ag = int(hg), int(ag)
                for t in [ht, at]:
                    if t not in teams:
                        teams[t] = {"team": t, "points": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0, "matches": 0}
                teams[ht]["matches"] += 1
                teams[at]["matches"] += 1
                teams[ht]["gf"] += hg
                teams[ht]["ga"] += ag
                teams[at]["gf"] += ag
                teams[at]["ga"] += hg
                if hg > ag:
                    teams[ht]["wins"] += 1
                    teams[ht]["points"] += 3
                    teams[at]["losses"] += 1
                elif ag > hg:
                    teams[at]["wins"] += 1
                    teams[at]["points"] += 3
                    teams[ht]["losses"] += 1
                else:
                    teams[ht]["draws"] += 1
                    teams[at]["draws"] += 1
                    teams[ht]["points"] += 1
                    teams[at]["points"] += 1
        else:
            teams = {}
            for _, row in df.iterrows():
                ht = row["home_team_norm"]
                at = row["away_team_norm"]
                hg = row["home_goal"]
                ag = row["away_goal"]
                if pd.isna(hg) or pd.isna(ag):
                    continue
                hg, ag = int(hg), int(ag)
                for t in [ht, at]:
                    if t not in teams:
                        teams[t] = {"team": t, "points": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0, "matches": 0}
                teams[ht]["matches"] += 1
                teams[at]["matches"] += 1
                teams[ht]["gf"] += hg
                teams[ht]["ga"] += ag
                teams[at]["gf"] += ag
                teams[at]["ga"] += hg
                if hg > ag:
                    teams[ht]["wins"] += 1
                    teams[ht]["points"] += 3
                    teams[at]["losses"] += 1
                elif ag > hg:
                    teams[at]["wins"] += 1
                    teams[at]["points"] += 3
                    teams[ht]["losses"] += 1
                else:
                    teams[ht]["draws"] += 1
                    teams[at]["draws"] += 1
                    teams[ht]["points"] += 1
                    teams[at]["points"] += 1

        standings = sorted(
            teams.values(),
            key=lambda t: (t["points"], t["gf"] - t["ga"], t["gf"]),
            reverse=True,
        )
        for i, t in enumerate(standings, 1):
            t["position"] = i
            t["goal_difference"] = t["gf"] - t["ga"]
            t["season"] = season
        return standings

    def get_competition_stats(self, competition: str | None = None) -> dict:
        matches = self.search_matches(competition=competition, limit=100000)
        total = len(matches)
        if total == 0:
            return {"error": "No matches found"}

        total_goals = sum((m["home_goals"] or 0) + (m["away_goals"] or 0) for m in matches)
        home_wins = sum(1 for m in matches if m["home_goals"] is not None and m["away_goals"] is not None and m["home_goals"] > m["away_goals"])
        away_wins = sum(1 for m in matches if m["home_goals"] is not None and m["away_goals"] is not None and m["away_goals"] > m["home_goals"])
        draws = sum(1 for m in matches if m["home_goals"] is not None and m["away_goals"] is not None and m["home_goals"] == m["away_goals"])

        biggest_wins = sorted(
            [m for m in matches if m["home_goals"] is not None and m["away_goals"] is not None],
            key=lambda m: abs(m["home_goals"] - m["away_goals"]),
            reverse=True,
        )[:10]

        highest_scoring = sorted(
            [m for m in matches if m["home_goals"] is not None and m["away_goals"] is not None],
            key=lambda m: m["home_goals"] + m["away_goals"],
            reverse=True,
        )[:10]

        return {
            "competition": competition or "All competitions",
            "total_matches": total,
            "total_goals": total_goals,
            "avg_goals_per_match": round(total_goals / total, 2) if total > 0 else 0,
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_pct": round(home_wins / total * 100, 1) if total > 0 else 0,
            "biggest_wins": biggest_wins,
            "highest_scoring": highest_scoring,
        }
