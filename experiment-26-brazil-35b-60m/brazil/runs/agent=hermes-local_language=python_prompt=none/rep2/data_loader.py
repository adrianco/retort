"""Data loading and normalization for the Brazilian Soccer MCP Server."""

import re
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data" / "kaggle"


# ---------------------------------------------------------------------------
# Team name normalisation
# ---------------------------------------------------------------------------

CANONICAL_TEAMS: dict[str, str] = {
    "flamengo-rj": "flamengo",
    "flamengo": "flamengo",
    "fluminense-rj": "fluminense",
    "fluminense": "fluminense",
    "palmeiras-sp": "palmeiras",
    "palmeiras": "palmeiras",
    "santos-sp": "santos",
    "santos": "santos",
    "corinthians": "corinthians",
    "sc corinthians paulista": "corinthians",
    "sport club corinthians paulista": "corinthians",
    "sao paulo-sp": "sao paulo",
    "sao paulo": "sao paulo",
    "sao paulo fc": "sao paulo",
    "gremio": "gremio",
    "atletico-mg": "atletico-mg",
    "atletico mineiro": "atletico-mg",
    "cruzeiro": "cruzeiro",
    "botafogo": "botafogo",
    "vasco": "vasco",
    "vasco da gama": "vasco",
    "internacional": "internacional",
    "sport": "sport",
    "sport-recife": "sport",
    "bahia": "bahia",
    "fortaleza": "fortaleza",
    "ceara": "ceara",
    "coritiba": "coritiba",
    "athletico-pr": "athletico-pr",
    "americ-mg": "america-mg",
    "america minas gerais": "america-mg",
    "boavista-rj": "boavista",
    "boavista sport club (antigo esporte club barreira) - rj": "boavista",
    "boavista sport club": "boavista",
    "botafogo-sp": "botafogo-sp",
    "botafogo sp": "botafogo-sp",
    "avai": "avai",
    "avai-fc": "avai",
    "ponte-preta": "ponte-preta",
    "ponte catorze": "ponte-preta",
    "rem": "rem",
    "atletico-go": "atletico-go",
    "goias": "goias",
    "goiases": "goias",
    "sport club do nascimento": "flamengo",
    "sport club internacional": "internacional",
}

BRAZILIAN_CLUB_KEYWORDS = {
    "esporte clube",
    "corinthians",
    "flamengo",
    "fluminense",
    "palmeiras",
    "santos",
    "sao paulo",
    "gremio",
    "internacional",
    "botafogo",
    "vasco",
    "cruzeiro",
    "bahia",
    "fortaleza",
    "sport",
    "ceara",
    "coritiba",
    "athletico",
    "america",
    "avai",
    "ponte",
    "rem",
    "goias",
    "boavista",
}

NON_BRAZILIAN_KEYWORDS = {
    "fc barcelona",
    "real madrid",
    "manchester",
    "juventus",
    "paris",
    "lyon",
    "roma",
    "milan",
    "bayern",
    "borussia",
    "chelsea",
    "liverpool",
    "arsenal",
    "tottenham",
    "inter milan",
    "atletico madrid",
}


def _strip_state_suffix(name: str) -> str:
    """Remove trailing '-XX' state suffix from team names."""
    name = name.strip()
    return re.sub(r"\s*-\w{2}\s*$", "", name)


def _clean_parenthetical(name: str) -> str:
    """Remove parenthetical annotations like '(antigo Esporte Clube Barreira)'."""
    cleaned = re.sub(r"\s*\(antigo\s+.*?\)\s*", " ", name, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*\([^)]*\)\s*", " ", cleaned)
    return cleaned


def normalize_team_name(name: str) -> str:
    """Normalise a team name to a canonical lowercase short form."""
    if not name or not isinstance(name, str):
        return ""

    cleaned = _clean_parenthetical(name)
    cleaned = _strip_state_suffix(cleaned.strip())
    key = cleaned.lower().strip()

    # 1. Try exact match in canonical map
    if key in CANONICAL_TEAMS:
        return CANONICAL_TEAMS[key]

    # 2. Try if key is itself a canonical value
    if key in CANONICAL_TEAMS.values():
        return key

    # 3. Check if the key matches any known canonical team name (key is the mapped value)
    for mapped_key, mapped in CANONICAL_TEAMS.items():
        if mapped == key:
            return key

    # 4. Keyword-based fuzzy match using specific team keywords
    #    Use the most specific matches first to avoid collisions.
    #    For instance, "corinthians" keyword should map to "corinthians" not "sport"
    team_specific_keywords = {
        "corinthians": "corinthians",
        "flamengo": "flamengo",
        "fluminense": "fluminense",
        "palmeiras": "palmeiras",
        "santos": "santos",
        "sao paulo": "sao paulo",
        "gremio": "gremio",
        "internacional": "internacional",
        "botafogo": "botafogo",
        "vasco": "vasco",
        "cruzeiro": "cruzeiro",
        "bahia": "bahia",
        "fortaleza": "fortaleza",
        "athletico-pr": "athletico-pr",
        "athletico mineiro": "atletico-mg",
        "atletico-mg": "atletico-mg",
        "athletico-mg": "atletico-mg",
        "america-mg": "america-mg",
        "americ-mg": "america-mg",
        "sport": "sport",
        "ceara": "ceara",
        "coritiba": "coritiba",
        "avai": "avai",
        "ponte-preta": "ponte-preta",
        "ponte": "ponte-preta",
        "rem": "rem",
        "atletico-go": "atletico-go",
        "goias": "goias",
        "boavista": "boavista",
        "botafogo-sp": "botafogo-sp",
    }

    # Sort by keyword length descending so longest/most specific match wins
    for kw in sorted(team_specific_keywords.keys(), key=len, reverse=True):
        if kw in key:
            return team_specific_keywords[kw]

    return key


def is_brazilian_club(name: str) -> bool:
    """Heuristic to decide if a name refers to a Brazilian club."""
    name_lower = name.lower()

    # If it matches a known non-Brazilian club, it is not Brazilian
    if any(kw in name_lower for kw in NON_BRAZILIAN_KEYWORDS):
        return False

    # Check Brazilian keywords
    return any(kw in name_lower for kw in BRAZILIAN_CLUB_KEYWORDS)


# ---------------------------------------------------------------------------
# Data loading functions
# ---------------------------------------------------------------------------

def load_brasileirao_matches() -> pd.DataFrame:
    """Load Brasileirao Serie A matches."""
    path = DATA_DIR / "Brasileirao_Matches.csv"
    df = pd.read_csv(path, encoding="utf-8")
    df["competition"] = "Brasileirao"
    return df


def load_brazilian_cup_matches() -> pd.DataFrame:
    """Load Copa do Brasil matches."""
    path = DATA_DIR / "Brazilian_Cup_Matches.csv"
    df = pd.read_csv(path, encoding="utf-8")
    df["competition"] = "Copa do Brasil"
    return df


def load_libertadores_matches() -> pd.DataFrame:
    """Load Copa Libertadores matches."""
    path = DATA_DIR / "Libertadores_Matches.csv"
    df = pd.read_csv(path, encoding="utf-8")
    df["competition"] = "Libertadores"
    return df


def load_extended_stats() -> pd.DataFrame:
    """Load extended match statistics (BR-Football-Dataset)."""
    path = DATA_DIR / "BR-Football-Dataset.csv"
    df = pd.read_csv(path, encoding="utf-8")
    df["competition"] = df["tournament"]
    return df


def load_historic_matches() -> pd.DataFrame:
    """Load historical Brasileirao matches (2003-2019)."""
    path = DATA_DIR / "novo_campeonato_brasileiro.csv"
    df = pd.read_csv(path, encoding="utf-8", engine="python")
    df["competition"] = "Brasileirao"
    return df


def load_fifa_players() -> pd.DataFrame:
    """Load FIFA player database."""
    path = DATA_DIR / "fifa_data.csv"
    df = pd.read_csv(path, encoding="utf-8-sig")
    return df


def load_all_data() -> dict:
    """Load every CSV and return as a dict of DataFrames."""
    return {
        "brasileirao": load_brasileirao_matches(),
        "copa_brasil": load_brazilian_cup_matches(),
        "libertadores": load_libertadores_matches(),
        "extended_stats": load_extended_stats(),
        "historic": load_historic_matches(),
        "players": load_fifa_players(),
    }


if __name__ == "__main__":
    data = load_all_data()
    for name, df in data.items():
        print(f"{name}: {len(df)} rows, {len(df.columns)} cols")
        print(f"  columns: {list(df.columns)[:10]}")
        print()
