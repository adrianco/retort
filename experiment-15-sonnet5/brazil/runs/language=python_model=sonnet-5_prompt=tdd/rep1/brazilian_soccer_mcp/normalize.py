import datetime
import math
import re
import unicodedata

BR_UF_CODES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

# Base names shared by multiple, unrelated clubs in different states -
# the state must stay part of the canonical key so they are not merged.
AMBIGUOUS_BASES = {"atletico", "america"}

# Full legal names (already accent/case/punctuation normalized) mapped to
# the short base name used elsewhere in the datasets.
FULL_NAME_ALIASES = {
    "sport club corinthians paulista": "corinthians",
    "sociedade esportiva palmeiras": "palmeiras",
    "clube de regatas do flamengo": "flamengo",
    "sao paulo futebol clube": "sao paulo",
    "fluminense football club": "fluminense",
    "clube de regatas vasco da gama": "vasco",
    "botafogo de futebol e regatas": "botafogo",
    "gremio foot ball porto alegrense": "gremio",
    "sport club internacional": "internacional",
    "cruzeiro esporte clube": "cruzeiro",
    "esporte clube bahia": "bahia",
    "sport club recife": "sport",
    "clube atletico mineiro": "atletico mg",
    "club athletico paranaense": "athletico pr",
}

_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y")


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


def _clean_base(text: str) -> str:
    text = _strip_accents(text).lower()
    text = text.replace(".", "")
    text = re.sub(r"[,()]", " ", text)
    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_state(cleaned: str):
    parts = cleaned.split(" ")
    if len(parts) > 1 and parts[-1].upper() in BR_UF_CODES:
        return " ".join(parts[:-1]), parts[-1].upper()
    return cleaned, None


def canonical_team_key(raw: str) -> str:
    cleaned = _clean_base(str(raw))
    cleaned = FULL_NAME_ALIASES.get(cleaned, cleaned)
    base, state = _split_state(cleaned)
    base = FULL_NAME_ALIASES.get(base, base)
    if base in AMBIGUOUS_BASES and state:
        return f"{base} {state.lower()}"
    return base


def display_team_name(raw: str) -> str:
    key = canonical_team_key(raw)
    return " ".join(word.capitalize() for word in key.split(" "))


def parse_date(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None
