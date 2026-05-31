"""Team name and string normalization utilities.

The provided datasets use multiple naming conventions for the same team:
- With state suffix: "Palmeiras-SP", "Flamengo-RJ"
- Without suffix: "Palmeiras", "Flamengo"
- Long form: "Sport Club Corinthians Paulista"
- Portuguese accents and punctuation: "São Paulo", "Grêmio", "Atlético-MG"

`normalize_team` reduces all of these to a canonical lowercase ASCII key so
matches can be made across files.
"""

from __future__ import annotations

import re
import unicodedata

_STATE_SUFFIXES = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
    "RO", "RR", "RS", "SC", "SE", "SP", "TO",
}

# Common long-form -> short-form aliases. Lowercase ASCII keys.
#
# Both pre- and post-state-suffix-stripped forms are listed so that names
# like "Atletico-MG" and "Atletico Mineiro" both resolve to the same key.
_ALIASES = {
    # Corinthians
    "sport club corinthians paulista": "corinthians",
    "corinthians sp": "corinthians",
    # Palmeiras
    "sociedade esportiva palmeiras": "palmeiras",
    # Flamengo
    "clube de regatas do flamengo": "flamengo",
    # Fluminense
    "fluminense football club": "fluminense",
    # Vasco
    "club de regatas vasco da gama": "vasco",
    "vasco da gama": "vasco",
    "vasco da gama rj": "vasco",
    # Sao Paulo
    "sao paulo futebol clube": "sao paulo",
    "sao paulo fc": "sao paulo",
    # Santos
    "santos futebol clube": "santos",
    "santos fc": "santos",
    # Gremio
    "gremio foot ball porto alegrense": "gremio",
    "gremio football porto alegrense": "gremio",
    # Internacional
    "sport club internacional": "internacional",
    "internacional rs": "internacional",
    # Atlético Mineiro
    "clube atletico mineiro": "atletico mineiro",
    "atletico-mg": "atletico mineiro",
    "atletico mg": "atletico mineiro",
    # Athletico Paranaense
    "athletico-pr": "athletico paranaense",
    "athletico pr": "athletico paranaense",
    "atletico-pr": "athletico paranaense",
    "atletico pr": "athletico paranaense",
    "atletico paranaense": "athletico paranaense",
    # Atletico Goianiense
    "atletico-go": "atletico goianiense",
    "atletico go": "atletico goianiense",
    "atletico goianiense": "atletico goianiense",
    # Atletico Acreano
    "atletico-ac": "atletico acreano",
    "atletico ac": "atletico acreano",
    # Botafogo variations (state suffix is meaningful)
    "botafogo-rj": "botafogo",
    "botafogo rj": "botafogo",
    "botafogo fr rj": "botafogo",
    "botafogo-sp": "botafogo sp",
    "botafogo sp": "botafogo sp",
    "botafogo-pb": "botafogo pb",
    "botafogo pb": "botafogo pb",
    # Santos (FC of SP) vs Santos AP
    "santos-sp": "santos",
    "santos sp": "santos",
    "santos-ap": "santos ap",
    "santos ap": "santos ap",
    # Operario state-specific
    "operario-pr": "operario pr",
    "operario pr": "operario pr",
    "operario-ms": "operario ms",
    "operario ms": "operario ms",
    # Bragantino state-specific
    "bragantino-pa": "bragantino pa",
    "bragantino pa": "bragantino pa",
    # Bahia
    "esporte clube bahia": "bahia",
    "ec bahia": "bahia",
    # Cruzeiro
    "cruzeiro esporte clube": "cruzeiro",
    # Botafogo
    "botafogo de futebol e regatas": "botafogo",
    "botafogo fr": "botafogo",
    "botafogo rj": "botafogo",
    # Fortaleza
    "fortaleza esporte clube": "fortaleza",
    "fortaleza fc": "fortaleza",
    "fortaleza ec": "fortaleza",
    # Ceara
    "ceara sporting club": "ceara",
    # America
    "america-mg": "america mineiro",
    "america mg": "america mineiro",
    # Ponte Preta
    "ac ponte preta": "ponte preta",
    "associacao atletica ponte preta": "ponte preta",
}

# Tokens that should be stripped wholesale when they appear as a word.
# NOTE: "atletico" is intentionally NOT in this list because it's part of the
# canonical names "atletico mineiro" / "atletico goianiense" / "atletico
# acreano" and stripping it would collide them all.
_GENERIC_TOKENS = {
    "fc", "ec", "ad", "ce", "se", "cr",  # club acronyms (kept: ac as in 'atletico clube' could be useful; treated below)
    "futebol", "clube", "club", "sport", "esporte", "esportivo",
    "associacao", "atletica", "sociedade", "regatas",
    "sc",  # often part of Sport Club / Santa Catarina; ambiguous enough to drop
}

# Base names that have multiple clubs across states — DO NOT strip the
# state suffix during normalization. Anything in this set requires an
# explicit alias entry to canonicalize.
_AMBIGUOUS_BASE_NAMES = {
    "atletico", "botafogo", "santos", "operario", "bragantino", "americano",
    "nacional", "sport",
}

_BRAZILIAN_STATE_NAMES = {
    "ac": "Acre", "al": "Alagoas", "am": "Amazonas", "ap": "Amapá",
    "ba": "Bahia", "ce": "Ceará", "df": "Distrito Federal", "es": "Espírito Santo",
    "go": "Goiás", "ma": "Maranhão", "mg": "Minas Gerais", "ms": "Mato Grosso do Sul",
    "mt": "Mato Grosso", "pa": "Pará", "pb": "Paraíba", "pe": "Pernambuco",
    "pi": "Piauí", "pr": "Paraná", "rj": "Rio de Janeiro", "rn": "Rio Grande do Norte",
    "ro": "Rondônia", "rr": "Roraima", "rs": "Rio Grande do Sul", "sc": "Santa Catarina",
    "se": "Sergipe", "sp": "São Paulo", "to": "Tocantins",
}


def strip_accents(text: str) -> str:
    """Remove combining marks so 'São Paulo' becomes 'Sao Paulo'."""
    if text is None:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _strip_state_suffix(token: str) -> str:
    """Drop a trailing two-letter state code: 'Palmeiras-SP' -> 'Palmeiras'."""
    # Patterns: "Palmeiras-SP", "Palmeiras - SP", "Palmeiras SP", "Palmeiras (SP)"
    m = re.match(r"^(.*?)[\s\-(]+([A-Z]{2})\)?\s*$", token)
    if m and m.group(2) in _STATE_SUFFIXES:
        return m.group(1).strip()
    return token


def _strip_country_suffix(token: str) -> str:
    """Drop a trailing country code.

    Handles both ``Nacional (URU)`` and ``Barcelona-EQU``.
    Only 3-letter codes are treated as country suffixes when hyphenated
    (otherwise 2-letter state codes would also match).
    """
    token = re.sub(r"\s*\([A-Z]{2,4}\)\s*$", "", token).strip()
    token = re.sub(r"\s*[\-]\s*[A-Z]{3,4}\s*$", "", token).strip()
    return token


def normalize_team(name: str) -> str:
    """Return the canonical team key.

    The key is lowercase, ASCII-only, with state/country suffixes removed and
    long-form aliases collapsed. Empty/None inputs return ''.

    Lookup order:
      1. Strip country code if present (e.g. ``(URU)``).
      2. Lowercase + ASCII; alias lookup on the full string.
      3. Strip state suffix; alias lookup again.
      4. Final cleanup (drop stop tokens like ``fc``); alias lookup again.
    """
    if name is None:
        return ""
    text = str(name).strip()
    if not text:
        return ""
    text = _strip_country_suffix(text)

    def _clean(s: str) -> str:
        s = strip_accents(s).lower()
        s = re.sub(r"[^a-z0-9\s]", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    canonical_values = set(_ALIASES.values())

    # Step 1: try alias on the raw lowercase string (state suffix intact)
    full = _clean(text)
    if full in _ALIASES:
        return _ALIASES[full]
    if full in canonical_values:
        return full

    # Step 2: strip state suffix and try again, BUT only if the base name
    # isn't a known ambiguous name (Atletico/Botafogo/Santos/...).
    stripped = _strip_state_suffix(text)
    short = _clean(stripped)
    if short in _ALIASES:
        return _ALIASES[short]
    if short in canonical_values:
        return short
    # Detect if stripping has produced an ambiguous bare name with no alias
    if short in _AMBIGUOUS_BASE_NAMES:
        # Fall back to the full (state-suffixed) form; better to keep state
        # than to collapse different clubs together.
        return full

    # Step 3: remove generic club acronym tokens (FC, EC, ...) anywhere
    tokens = [t for t in short.split() if t not in _GENERIC_TOKENS]
    cleaned = " ".join(tokens).strip() or short
    if cleaned in _ALIASES:
        return _ALIASES[cleaned]
    return cleaned


def display_team(name: str) -> str:
    """Best-effort human-readable team name (preserves accents)."""
    if name is None:
        return ""
    text = str(name).strip()
    text = _strip_country_suffix(text)
    text = _strip_state_suffix(text)
    return text


def state_full_name(code: str) -> str:
    """Map a two-letter state code to its full name (or echo the input)."""
    if not code:
        return ""
    return _BRAZILIAN_STATE_NAMES.get(code.lower(), code)


def normalize_text(text: str) -> str:
    """Lowercase, accent-stripped form of arbitrary text for fuzzy search."""
    return strip_accents(text or "").lower().strip()


def team_matches(query: str, candidate: str) -> bool:
    """Loose match: True if either name normalizes to a substring of the other."""
    q = normalize_team(query)
    c = normalize_team(candidate)
    if not q or not c:
        return False
    return q == c or q in c or c in q
