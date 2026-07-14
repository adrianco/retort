"""Team-name normalization helpers.

The provided CSV files spell each club a few different ways:

    "Palmeiras-SP"            -> with Brazilian state suffix
    "Palmeiras"               -> bare name
    "Sao Paulo" / "São Paulo" -> accented vs. unaccented
    "Nacional (URU)"          -> with country suffix in Libertadores
    "Atlético-MG" / "Atletico Mineiro"

To answer queries like "show me all Flamengo matches" we collapse every
spelling to a single canonical key so equality checks work across datasets.
The strategy is:

    1. Detect and remove a trailing state ("-SP", " - RJ") or country
       ("(URU)") suffix, remembering the state so ambiguous bases like
       "Atlético" can be split into Mineiro / Paranaense / Goianiense.
    2. Strip diacritics, lowercase, collapse whitespace.
    3. Look up (base, state) in STATE_NAMES for clubs whose only
       distinguishing feature is their state.
    4. Fall back to an alias table for informal names ("Galo" -> Mineiro,
       "Flu" -> Fluminense).
    5. As a last resort strip a few generic-club words ("FC", "EC", "Sport
       Club do Recife" -> "sport recife").

The alias table is intentionally small — just enough to cover the example
questions in the spec and the obvious traditional rivalries.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

_BRAZILIAN_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT",
    "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO",
    "RR", "SC", "SP", "SE", "TO",
}
_STATE_SUFFIX_RE = re.compile(
    r"\s*[-–]\s*(" + "|".join(sorted(_BRAZILIAN_STATES)) + r")\b",
    re.IGNORECASE,
)
_COUNTRY_SUFFIX_RE = re.compile(r"\s*\(([A-Z]{2,4})\)\s*$")

# Generic words that can be dropped without changing identity.
# Note: "atletico" / "athletico" are NOT here, because the only thing
# distinguishing Atlético-MG / Atlético-PR / Atlético-GO is their state,
# and we resolve those via STATE_NAMES.
_GENERIC_WORDS = {
    "fc", "ec", "sc", "ac", "se", "aa", "ca", "cd", "cr",
    "esporte", "clube", "club", "futebol", "sport",
    "associacao", "association",
    "do", "de", "da", "dos", "das",
}

# (normalized-base, state-abbrev) -> canonical key for clubs that share a
# base name across multiple states.
STATE_NAMES: dict[tuple[str, str], str] = {
    ("atletico", "MG"): "atletico mineiro",
    ("atletico", "PR"): "athletico paranaense",
    ("athletico", "PR"): "athletico paranaense",
    ("atletico", "GO"): "atletico goianiense",
    ("america", "MG"): "america mineiro",
    ("america", "RN"): "america rn",
    ("botafogo", "RJ"): "botafogo",
    ("botafogo", "SP"): "botafogo sp",
    ("botafogo", "PB"): "botafogo pb",
    ("portuguesa", "SP"): "portuguesa",
    ("portuguesa", "RJ"): "portuguesa rj",
    ("gremio", "RS"): "gremio",
    ("gremio prudente", "SP"): "gremio prudente",
    ("santa cruz", "PE"): "santa cruz",
    ("santo andre", "SP"): "santo andre",
    ("sao caetano", "SP"): "sao caetano",
    ("juventude", "RS"): "juventude",
}

CANONICAL_LABELS: dict[str, str] = {
    "flamengo": "Flamengo",
    "fluminense": "Fluminense",
    "vasco": "Vasco da Gama",
    "botafogo": "Botafogo",
    "botafogo sp": "Botafogo-SP",
    "botafogo pb": "Botafogo-PB",
    "palmeiras": "Palmeiras",
    "santos": "Santos",
    "sao paulo": "São Paulo",
    "corinthians": "Corinthians",
    "gremio": "Grêmio",
    "internacional": "Internacional",
    "cruzeiro": "Cruzeiro",
    "atletico mineiro": "Atlético Mineiro",
    "athletico paranaense": "Athletico Paranaense",
    "atletico goianiense": "Atlético Goianiense",
    "america mineiro": "América Mineiro",
    "america rn": "América-RN",
    "bahia": "Bahia",
    "vitoria": "Vitória",
    "fortaleza": "Fortaleza",
    "ceara": "Ceará",
    "sport recife": "Sport Recife",
    "coritiba": "Coritiba",
    "goias": "Goiás",
    "chapecoense": "Chapecoense",
    "avai": "Avaí",
    "figueirense": "Figueirense",
    "ponte preta": "Ponte Preta",
    "guarani": "Guarani",
    "portuguesa": "Portuguesa",
    "portuguesa rj": "Portuguesa-RJ",
    "juventude": "Juventude",
    "criciuma": "Criciúma",
    "nautico": "Náutico",
    "parana": "Paraná",
    "paysandu": "Paysandu",
    "csa": "CSA",
    "santa cruz": "Santa Cruz",
    "santo andre": "Santo André",
    "sao caetano": "São Caetano",
    "gremio prudente": "Grêmio Prudente",
    "joinville": "Joinville",
    "ipatinga": "Ipatinga",
    "brasiliense": "Brasiliense",
    "barueri": "Barueri",
}

# Informal-name -> canonical key alias table. Keys are already normalized
# (lowercase, no diacritics, no state suffix).
ALIASES: dict[str, str] = {
    "galo": "atletico mineiro",
    "atletico mg": "atletico mineiro",
    "atletico minas": "atletico mineiro",
    "mineiro": "atletico mineiro",
    "atletico pr": "athletico paranaense",
    "atletico paranaense": "athletico paranaense",
    "athletico pr": "athletico paranaense",
    "furacao": "athletico paranaense",
    "atletico go": "atletico goianiense",
    "flu": "fluminense",
    "fla": "flamengo",
    "mengo": "flamengo",
    "rubro negro": "flamengo",
    "tricolor paulista": "sao paulo",
    "spfc": "sao paulo",
    "sao paulo futebol clube": "sao paulo",
    "verdao": "palmeiras",
    "peixe": "santos",
    "timao": "corinthians",
    "sport club corinthians paulista": "corinthians",
    "raposa": "cruzeiro",
    "colorado": "internacional",
    "inter": "internacional",
    "imortal": "gremio",
    "vasco da gama": "vasco",
    "cr vasco": "vasco",
    "club regatas vasco": "vasco",
    "esquadrao": "bahia",
    "esporte clube bahia": "bahia",
    "leao": "fortaleza",
    "leao do pici": "fortaleza",
    "fortaleza esporte clube": "fortaleza",
    "tricolor de aco": "bahia",
    "leao da barra": "vitoria",
    "alvinegro praiano": "santos",
    "sport club do recife": "sport recife",
    "sport recife": "sport recife",
    "sport": "sport recife",
    "america mg": "america mineiro",
    "america minas": "america mineiro",
    "america rn": "america rn",
}


def _strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


@lru_cache(maxsize=8192)
def normalize_team(name: str | None) -> str:
    """Return a canonical key for a team name suitable for equality matching.

    Lookup order (first hit wins):
      1. (base, state) in STATE_NAMES — for clubs that share a base name
         across states (Atlético-MG vs. Atlético-PR).
      2. Full base / generic-stripped core in ALIASES or CANONICAL_LABELS.
      3. Multi-token (length >= 2) sub-spans of the base in ALIASES or
         CANONICAL_LABELS — collapses "Sport Club do Recife" -> sport recife.
      4. Single-token sub-spans against CANONICAL_LABELS only — extracts
         "corinthians" from "Sport Club Corinthians Paulista". Single-token
         ALIASES are deliberately NOT matched here to avoid spurious hits
         (e.g. "sport" inside an unrelated club name).
      5. Fallback: the generic-stripped core itself.
    """
    if name is None:
        return ""
    value = str(name).strip()
    if not value:
        return ""

    # Pull off any country suffix like "(URU)" and any Brazilian state
    # suffix like "-SP", remembering the state for STATE_NAMES lookup.
    value = _COUNTRY_SUFFIX_RE.sub("", value)
    state: str | None = None
    state_match = _STATE_SUFFIX_RE.search(value)
    if state_match:
        state = state_match.group(1).upper()
        value = _STATE_SUFFIX_RE.sub("", value)

    value = _strip_accents(value).lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    tokens = [tok for tok in value.split() if tok]
    if not tokens:
        return ""

    base = " ".join(tokens)
    core_tokens = [t for t in tokens if t not in _GENERIC_WORDS] or tokens
    core = " ".join(core_tokens)

    if state is not None:
        keyed = STATE_NAMES.get((base, state)) or STATE_NAMES.get((core, state))
        if keyed:
            return keyed

    for candidate in (base, core):
        if candidate in ALIASES:
            return ALIASES[candidate]
        if candidate in CANONICAL_LABELS:
            return candidate

    # Multi-token spans (length >= 2) — longest first.
    for length in range(len(tokens), 1, -1):
        for start in range(len(tokens) - length + 1):
            span = " ".join(tokens[start : start + length])
            if span in ALIASES:
                return ALIASES[span]
            if span in CANONICAL_LABELS:
                return span

    # Single-token canonicals only — pulls "corinthians" out of a longer name.
    for tok in core_tokens:
        if tok in CANONICAL_LABELS:
            return tok

    return core


def label_for(team_key: str) -> str:
    """Return a human-friendly display label for a canonical team key."""
    if not team_key:
        return ""
    return CANONICAL_LABELS.get(team_key, team_key.title())


def teams_match(a: str | None, b: str | None) -> bool:
    """Equality check that ignores spelling differences."""
    return normalize_team(a) == normalize_team(b) and bool(normalize_team(a))
