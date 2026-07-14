"""Team name normalization.

The source CSVs spell the same club in several incompatible ways: with a
state suffix ("Palmeiras-SP"), with a country suffix ("Barcelona-EQU"),
with a parenthetical qualifier ("Guaraní (PAR)"), with old/new brand names
("Atletico Paranaense" vs "Athletico-PR"), or as a bare short name
("Flamengo"). Matching across datasets requires collapsing all of these to
one canonical key while still keeping a readable display name.
"""

from __future__ import annotations

import re
import unicodedata

# Trailing " - XX" / "-XX" state or country qualifiers, e.g. "Flamengo-RJ",
# "Boca Juniors - ARG", "Barcelona-EQU". Requires a dash so we don't clip
# legitimate short words.
_SUFFIX_RE = re.compile(r"\s*-\s*[A-Za-z]{2,4}$")
# A trailing parenthetical short code, e.g. "Guaraní (PAR)". This is a
# qualifier just like a dash-suffix (it disambiguates same-named clubs from
# different countries) so it must be preserved, not discarded like a
# descriptive parenthetical aside.
_PAREN_CODE_RE = re.compile(r"\(\s*([A-Za-z]{2,4})\s*\)\s*$")
_PAREN_RE = re.compile(r"\s*\([^)]*\)")
_WS_RE = re.compile(r"\s+")


def _paren_code_to_suffix(text: str) -> str:
    match = _PAREN_CODE_RE.search(text)
    if not match:
        return text
    return f"{text[:match.start()].rstrip()}-{match.group(1)}"

# Maps a generic-normalized variant -> the generic-normalized canonical key.
# Only needed where different datasets use genuinely different words for the
# same club (rebrands, abbreviations, alternate short forms). State-suffix
# and punctuation differences are already handled by the generic normalizer.
_ALIASES: dict[str, str] = {
    # Athletico Paranaense rebranded from "Atletico Paranaense" in 2018.
    "atletico paranaense": "athletico paranaense",
    "athletico paranaense": "athletico paranaense",
    "atletico pr": "athletico paranaense",
    "athletico pr": "athletico paranaense",
    "athletico": "athletico paranaense",
    # Atletico Mineiro / Atletico-MG
    "atletico mineiro": "atletico mg",
    # Sport Club do Recife
    "sport recife": "sport",
    "sport club do recife": "sport",
    "sport pe": "sport",
    # Nautico
    "nautico pe": "nautico",
    "clube nautico capibaribe": "nautico",
    # America-MG
    "america mg": "america mg",
    "america fc": "america mg",
    "america fc minas gerais": "america mg",
    "america futebol clube mg": "america mg",
    # Vasco da Gama
    "vasco": "vasco da gama",
    "vasco rj": "vasco da gama",
    "clube de regatas vasco da gama": "vasco da gama",
    # Sao Paulo
    "sao paulo sp": "sao paulo",
    "sao paulo futebol clube": "sao paulo",
    # Corinthians
    "corinthians sp": "corinthians",
    "sport club corinthians paulista": "corinthians",
    # Botafogo (Rio) - do not merge with Botafogo-PB / Botafogo-SP.
    "botafogo rj": "botafogo",
    # Red Bull Bragantino
    "red bull bragantino sp": "red bull bragantino",
    "bragantino sp": "red bull bragantino",
    "rb bragantino": "red bull bragantino",
    # Cross-state abbreviated forms seen in Brasileirao_Matches.csv
    "csa al": "csa",
    "cuiaba mt": "cuiaba",
    "goias go": "goias",
    "bahia ba": "bahia",
    "vitoria ba": "vitoria",
    "ceara ce": "ceara",
    "fortaleza ce": "fortaleza",
    "avai sc": "avai",
    "chapecoense sc": "chapecoense",
    "coritiba pr": "coritiba",
    "criciuma sc": "criciuma",
    "cruzeiro mg": "cruzeiro",
    "figueirense sc": "figueirense",
    "gremio rs": "gremio",
    "internacional rs": "internacional",
    "joinville sc": "joinville",
    "juventude rs": "juventude",
    "parana pr": "parana",
    "ponte preta sp": "ponte preta",
    "portuguesa sp": "portuguesa",
    "santa cruz pe": "santa cruz",
    "santos sp": "santos",
    "flamengo rj": "flamengo",
    "fluminense rj": "fluminense",
    "palmeiras sp": "palmeiras",
    "atletico go": "atletico go",
}

# Nice display names for canonical keys (accents restored, standard casing).
_CANONICAL_DISPLAY: dict[str, str] = {
    "athletico paranaense": "Athletico Paranaense",
    "atletico mg": "Atletico-MG",
    "atletico go": "Atletico-GO",
    "sport": "Sport",
    "nautico": "Nautico",
    "america mg": "America-MG",
    "vasco da gama": "Vasco da Gama",
    "sao paulo": "Sao Paulo",
    "corinthians": "Corinthians",
    "botafogo": "Botafogo",
    "red bull bragantino": "Red Bull Bragantino",
    "csa": "CSA",
    "cuiaba": "Cuiaba",
    "goias": "Goias",
    "bahia": "Bahia",
    "vitoria": "Vitoria",
    "ceara": "Ceara",
    "fortaleza": "Fortaleza",
    "avai": "Avai",
    "chapecoense": "Chapecoense",
    "coritiba": "Coritiba",
    "criciuma": "Criciuma",
    "cruzeiro": "Cruzeiro",
    "figueirense": "Figueirense",
    "gremio": "Gremio",
    "internacional": "Internacional",
    "joinville": "Joinville",
    "juventude": "Juventude",
    "parana": "Parana",
    "ponte preta": "Ponte Preta",
    "portuguesa": "Portuguesa",
    "santa cruz": "Santa Cruz",
    "santos": "Santos",
    "flamengo": "Flamengo",
    "fluminense": "Fluminense",
    "palmeiras": "Palmeiras",
}


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def _strip_suffix_and_noise(raw: str) -> str:
    text = raw.strip()
    text = _PAREN_RE.sub("", text)
    text = _SUFFIX_RE.sub("", text)
    text = text.replace(".", "")
    return _WS_RE.sub(" ", text).strip(" -")


def normalize_team(raw: str) -> tuple[str, str]:
    """Return (canonical_key, display_name) for a raw team name.

    canonical_key is a lowercase, accent-free string that is stable across
    all datasets for the same club. display_name is a human-readable label.

    Two candidate keys are tried against the alias table: one that keeps the
    trailing state/country code as a word (so e.g. "Atletico - MG" and
    "Atletico - PR" stay distinguishable) and one with the suffix removed
    entirely. The suffix-preserving key is tried first since it disambiguates
    same-named clubs from different states.
    """
    if raw is None:
        return "", ""
    with_suffix = _paren_code_to_suffix(str(raw).strip())
    no_paren = _PAREN_RE.sub("", with_suffix).strip()
    ascii_lower = strip_accents(no_paren).lower().replace(".", "")
    suffix_key = _WS_RE.sub(" ", ascii_lower.replace("-", " ")).strip()
    stripped_key = _WS_RE.sub(" ", _SUFFIX_RE.sub("", ascii_lower)).strip(" -")

    # Prefer the alias table, then the suffix-preserving key (safer default:
    # it never merges two different states' clubs of the same short name),
    # falling back to the fully-stripped key only if that's all we have.
    canonical_key = _ALIASES.get(suffix_key) or _ALIASES.get(stripped_key) or suffix_key or stripped_key

    display = _CANONICAL_DISPLAY.get(canonical_key)
    if display is None:
        cleaned = _strip_suffix_and_noise(no_paren)
        display = cleaned if cleaned else str(raw).strip()
    return canonical_key, display


def teams_match(raw_a: str, raw_b: str) -> bool:
    return normalize_team(raw_a)[0] == normalize_team(raw_b)[0]
