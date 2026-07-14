"""Player search and statistics functions."""
import pandas as pd

BRAZILIAN_CLUBS = [
    "Flamengo", "Palmeiras", "Corinthians", "Santos", "São Paulo", "Sao Paulo",
    "Fluminense", "Vasco", "Botafogo", "Grêmio", "Gremio", "Internacional",
    "Athletico", "Atletico", "Cruzeiro", "Bahia", "Fortaleza", "Ceará", "Ceara",
    "Sport", "Bragantino", "Cuiabá", "Cuiaba", "Goiás", "Goias", "Coritiba",
    "Avaí", "Avai", "Juventude", "América", "America", "Chapecoense", "Vitória",
    "Vitoria", "Paraná", "Parana",
]


def search_players_by_name(df: pd.DataFrame, name: str) -> pd.DataFrame:
    mask = df["Name"].str.contains(name, case=False, na=False)
    return df[mask].copy()


def search_players_by_nationality(df: pd.DataFrame, nationality: str) -> pd.DataFrame:
    mask = df["Nationality"].str.contains(nationality, case=False, na=False)
    return df[mask].copy()


def search_players_by_club(df: pd.DataFrame, club: str) -> pd.DataFrame:
    mask = df["Club"].str.contains(club, case=False, na=False)
    return df[mask].copy()


def search_players_by_position(df: pd.DataFrame, position: str) -> pd.DataFrame:
    mask = df["Position"].str.contains(position, case=False, na=False)
    return df[mask].copy()


def get_top_rated_players(df: pd.DataFrame, nationality: str = None, club: str = None, limit: int = 20) -> pd.DataFrame:
    sub = df.copy()
    if nationality:
        sub = sub[sub["Nationality"].str.contains(nationality, case=False, na=False)]
    if club:
        sub = sub[sub["Club"].str.contains(club, case=False, na=False)]
    sub = sub.dropna(subset=["Overall"])
    return sub.sort_values("Overall", ascending=False).head(limit)


def format_player_info(player: pd.Series) -> str:
    name = player.get("Name", "Unknown")
    overall = int(player["Overall"]) if pd.notna(player.get("Overall")) else "?"
    position = player.get("Position", "?")
    club = player.get("Club", "?")
    nationality = player.get("Nationality", "?")
    age = player.get("Age", "?")
    return f"{name} | Overall: {overall} | Pos: {position} | Club: {club} | Nationality: {nationality} | Age: {age}"


def get_players_at_brazilian_clubs(df: pd.DataFrame) -> dict:
    """Return stats (count, avg_rating) for players at known Brazilian clubs."""
    result = {}
    for club in BRAZILIAN_CLUBS:
        sub = df[df["Club"].str.contains(club, case=False, na=False)]
        if len(sub) == 0:
            continue
        avg = sub["Overall"].mean()
        result[club] = {
            "count": len(sub),
            "avg_rating": round(float(avg), 1) if pd.notna(avg) else 0,
        }
    return result
