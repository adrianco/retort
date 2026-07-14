"""Team name normalization.

The datasets use inconsistent naming conventions for Brazilian clubs:
- With state suffix: "Palmeiras-SP", "Flamengo-RJ"
- With separator and spaces: "America - MG"
- Long form: "Sport Club Corinthians Paulista"
- Accent variation: "Sao Paulo" vs "São Paulo"

normalize_team_name produces a canonical, lower-case, accent-stripped key that
preserves any 2-letter state suffix as a trailing token (e.g. "atletico mg")
so distinct clubs in different states don't collapse. ``strip_state_suffix``
removes that trailing token for queries that don't specify a state.
"""

from __future__ import annotations

import re
import unicodedata

BRAZILIAN_STATES = {
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma",
    "mt", "ms", "mg", "pa", "pb", "pr", "pe", "pi", "rj", "rn",
    "rs", "ro", "rr", "sc", "sp", "se", "to",
}

# Foreign country tags that occasionally appear in Libertadores data; treat
# them like state suffixes so the short form is just the club name.
COUNTRY_SUFFIXES = {
    "uru", "arg", "chi", "col", "ven", "par", "per", "ecu", "bol",
    "bra", "mex", "eq", "equ", "esa",
}

_BOILERPLATE_WORDS = {
    "esporte", "clube", "club", "futebol", "sport", "sc", "fc", "ec",
    "associacao", "atletica", "sociedade", "regatas", "regatta",
    "paulista", "paulistano",
    "de", "do", "da", "dos", "das",
}

_PAREN_COUNTRY_RE = re.compile(r"\(\s*([A-Za-z]{2,4})\s*\)")
_PAREN_RE = re.compile(r"\(.*?\)")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")

# Manual aliases applied to the *short* form (no state) so that long club
# names collapse to their colloquial reference.
_SHORT_ALIASES: dict[str, str] = {
    "atletico paranaense": "athletico",
    "athletico paranaense": "athletico",
    "atletico mineiro": "atletico",
    "america mineiro": "america",
    "sport club corinthians paulista": "corinthians",
    "fluminense football club": "fluminense",
    "clube de regatas do flamengo": "flamengo",
    "sociedade esportiva palmeiras": "palmeiras",
    "santos futebol clube": "santos",
}


def _strip_accents(value: str) -> str:
    nfkd = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _clean_tokens(value: str) -> list[str]:
    # Rewrite parenthetical country codes like "(URU)" into a trailing token so
    # the country suffix can be preserved by the caller.
    cleaned = _PAREN_COUNTRY_RE.sub(r" \1 ", value)
    cleaned = _PAREN_RE.sub(" ", cleaned)
    cleaned = _strip_accents(cleaned).lower()
    cleaned = cleaned.replace("-", " ").replace("/", " ")
    cleaned = _NON_ALNUM_RE.sub(" ", cleaned).strip()
    return [t for t in cleaned.split() if t]


def normalize_team_name(name: str | None) -> str:
    """Return a canonical, accent-stripped key for a team name.

    The returned key preserves a trailing 2-letter Brazilian state token (or
    a known country tag) so that, for example, ``Atletico-MG`` and
    ``Athletico-PR`` get distinct keys ``"atletico mg"`` and ``"athletico pr"``.
    """
    if name is None:
        return ""
    if not isinstance(name, str):
        name = str(name)
    name = name.strip()
    if not name or name.lower() == "nan":
        return ""

    tokens = _clean_tokens(name)
    if not tokens:
        return ""

    # Split off a trailing state/country suffix if present.
    suffix: str | None = None
    if tokens[-1] in BRAZILIAN_STATES or tokens[-1] in COUNTRY_SUFFIXES:
        suffix = tokens[-1]
        tokens = tokens[:-1]

    # Strip boilerplate words from the body but never to empty.
    if len(tokens) > 1:
        body = [t for t in tokens if t not in _BOILERPLATE_WORDS]
        if body:
            tokens = body

    short = " ".join(tokens)
    short = _SHORT_ALIASES.get(short, short)
    if suffix:
        # Normalize the "atletico"/"athletico" spelling for Paraná to athletico.
        if short == "atletico" and suffix == "pr":
            short = "athletico"
        return f"{short} {suffix}"
    return short


def strip_state_suffix(canonical: str) -> str:
    """Drop a trailing state/country token from an already-normalized key."""
    if not canonical:
        return ""
    parts = canonical.split()
    if len(parts) >= 2 and (parts[-1] in BRAZILIAN_STATES or parts[-1] in COUNTRY_SUFFIXES):
        return " ".join(parts[:-1])
    return canonical


def team_query_matches(query: str, candidate_full: str, candidate_short: str) -> bool:
    """Return True if a query team name matches a stored canonical form.

    If the query specifies a state suffix it must match exactly. Otherwise the
    query matches any candidate whose state-stripped form equals the query.
    """
    qn = normalize_team_name(query)
    if not qn or not candidate_full:
        return False
    qn_short = strip_state_suffix(qn)
    if qn != qn_short:
        # Query was state-qualified: require exact match.
        return qn == candidate_full
    return qn == candidate_short
