"""Team-name normalisation.

The datasets spell the same club many ways ("Palmeiras-SP", "Palmeiras - SP",
"Palmeiras", "Sao Paulo", "São Paulo - SP", "Atletico Mineiro", "Atlético-MG"...).
`team_key` maps any spelling to a stable key:

* well-known clubs -> their canonical display name (e.g. "Atlético-MG")
* everything else  -> "<normalised base>|<STATE or country suffix>"
"""
from __future__ import annotations

import re
import unicodedata

STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}


def norm(text: str) -> str:
    """Lower-case, accent-free, punctuation-free form used for comparisons."""
    s = unicodedata.normalize("NFKD", str(text))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"\b([a-z])\.\s*", r"\1", s)  # "C. R. B." -> "crb"
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


# base name -> (display name, home state) for clubs whose bare name is unambiguous.
DEFAULTS = {
    norm(d): (d, st)
    for d, st in [
        ("Flamengo", "RJ"), ("Fluminense", "RJ"), ("Botafogo", "RJ"), ("Vasco", "RJ"),
        ("Palmeiras", "SP"), ("Corinthians", "SP"), ("Santos", "SP"), ("São Paulo", "SP"),
        ("Ponte Preta", "SP"), ("Portuguesa", "SP"), ("Guarani", "SP"),
        ("Red Bull Bragantino", "SP"), ("Grêmio", "RS"), ("Internacional", "RS"),
        ("Juventude", "RS"), ("Cruzeiro", "MG"), ("Bahia", "BA"), ("Vitória", "BA"),
        ("Sport", "PE"), ("Náutico", "PE"), ("Santa Cruz", "PE"), ("Fortaleza", "CE"),
        ("Ceará", "CE"), ("Goiás", "GO"), ("Vila Nova", "GO"), ("Coritiba", "PR"),
        ("Paraná", "PR"), ("Avaí", "SC"), ("Figueirense", "SC"), ("Chapecoense", "SC"),
        ("Criciúma", "SC"), ("Joinville", "SC"), ("Cuiabá", "MT"), ("CSA", "AL"),
        ("CRB", "AL"), ("Paysandu", "PA"), ("Remo", "PA"),
    ]
}

# (base, state) -> display for clubs that need the state to be identified.
QUALIFIED = {
    ("atletico", "MG"): "Atlético-MG",
    ("atletico", "GO"): "Atlético-GO",
    ("atletico", "PR"): "Athletico-PR",
    ("america", "MG"): "América-MG",
    ("america", "RN"): "América-RN",
}

# alternative base names -> (base, state or None)
SYNONYMS = {
    "atletico mineiro": ("atletico", "MG"),
    "clube atletico mineiro": ("atletico", "MG"),
    "galo": ("atletico", "MG"),
    "atletico goianiense": ("atletico", "GO"),
    "athletico paranaense": ("atletico", "PR"),
    "atletico paranaense": ("atletico", "PR"),
    "athletico": ("atletico", "PR"),
    "america mineiro": ("america", "MG"),
    "america de natal": ("america", "RN"),
    "america natal": ("america", "RN"),
    "vasco da gama": ("vasco", None),
    "sport recife": ("sport", None),
    "sport club do recife": ("sport", None),
    "bragantino": ("red bull bragantino", None),
    "rb bragantino": ("red bull bragantino", None),
    "corinthians paulista": ("corinthians", None),
    "sport club corinthians paulista": ("corinthians", None),
    "ceara sporting club": ("ceara", None),
    "nautico capibaribe": ("nautico", None),
    "portuguesa desportos": ("portuguesa", None),
    "cs alagoano": ("csa", None),
    "clube do remo": ("remo", None),
    "ca parana": ("parana", None),
    "parana clube": ("parana", None),
    "ec juventude": ("juventude", None),
    "brasil de pelotas": ("brasil", "RS"),
    "sao paulo fc": ("sao paulo", None),
    "gremio fbpa": ("gremio", None),
    "mengao": ("flamengo", None),
    "boavista sport club": ("boavista", None),
    "boavista saquarema": ("boavista", None),
    "america fc natal": ("america", "RN"),
    "sampaio correia": ("sampaio correa", None),
}

# Whole-string overrides (checked before any parsing).
FULL = {
    "america fc minas gerais": ("america", "MG"),
}

CURATED = {d for d, _ in DEFAULTS.values()} | set(QUALIFIED.values())

_AFFIXES = {"fc", "ec"}


def parse_team(raw: str) -> tuple[str, str, str]:
    """Return (normalised base, suffix, pretty name without suffix)."""
    text = str(raw).strip()
    if norm(text) in FULL:
        base, suffix = FULL[norm(text)]
        return base, suffix, text
    suffix = ""
    m = re.search(r"\s*\(([^)]*)\)", text)
    if m:
        inner = m.group(1).strip()
        if re.fullmatch(r"[A-Za-z]{2,3}", inner):
            suffix = inner.upper()
        text = (text[: m.start()] + text[m.end():]).strip()
    m = re.search(r"\s*-\s*([A-Za-z]{2,3})$", text)
    if m and (len(m.group(1)) == 3 or m.group(1).upper() in STATES):
        suffix = m.group(1).upper()
        text = text[: m.start()].strip()
    else:
        m = re.search(r"\s+([A-Z]{2})$", text)
        if m and m.group(1) in STATES:
            suffix = m.group(1)
            text = text[: m.start()].strip()
    base = norm(text)
    tokens = base.split()
    while len(tokens) > 1 and tokens[0] in _AFFIXES:
        tokens = tokens[1:]
    while len(tokens) > 1 and tokens[-1] in _AFFIXES:
        tokens = tokens[:-1]
    base = " ".join(tokens)
    if base in SYNONYMS:
        base, st = SYNONYMS[base]
        suffix = st or suffix
    return base, suffix, text


def team_key(raw: str) -> tuple[str, str]:
    """Return (key, display guess). Curated clubs use their display name as key."""
    base, suffix, pretty = parse_team(raw)
    if (base, suffix) in QUALIFIED:
        name = QUALIFIED[(base, suffix)]
        return name, name
    if base in DEFAULTS:
        name, state = DEFAULTS[base]
        if not suffix or suffix == state:
            return name, name
    return f"{base}|{suffix}", (f"{pretty}-{suffix}" if suffix else pretty)
