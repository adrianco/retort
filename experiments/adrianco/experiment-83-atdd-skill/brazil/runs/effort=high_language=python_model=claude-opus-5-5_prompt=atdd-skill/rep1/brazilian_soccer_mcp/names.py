"""Normalising the many spellings of Brazilian clubs, competitions and nationalities.

The datasets write the same club as "Palmeiras-SP", "Palmeiras - SP", "Palmeiras" or
"Sociedade Esportiva Palmeiras", with and without accents. Every spelling is reduced to a
canonical key (e.g. "palmeiras", "atletico-mg"); a state suffix is kept in the key only when
it is not the club's home state, so "Flamengo - PI" stays distinct from Flamengo (RJ).
"""
import re
import unicodedata

STATES = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR",
          "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"}

HOME_STATE = {
    "flamengo": "RJ", "fluminense": "RJ", "botafogo": "RJ", "vasco": "RJ", "palmeiras": "SP",
    "corinthians": "SP", "santos": "SP", "sao paulo": "SP", "gremio": "RS", "internacional": "RS",
    "juventude": "RS", "cruzeiro": "MG", "bahia": "BA", "vitoria": "BA", "sport": "PE", "nautico": "PE",
    "santa cruz": "PE", "ceara": "CE", "fortaleza": "CE", "coritiba": "PR", "parana": "PR", "avai": "SC",
    "figueirense": "SC", "chapecoense": "SC", "criciuma": "SC", "joinville": "SC", "goias": "GO",
    "ponte preta": "SP", "portuguesa": "SP", "guarani": "SP", "bragantino": "SP", "csa": "AL", "crb": "AL",
    "cuiaba": "MT", "paysandu": "PA", "remo": "PA", "abc": "RN", "sao caetano": "SP", "santo andre": "SP",
    "barueri": "SP", "gremio prudente": "SP", "ipatinga": "MG", "brasiliense": "DF", "vila nova": "GO",
}

# Club names that mean a specific club only together with a state.
STATE_SPECIFIC = {
    ("atletico", "MG"): "atletico-mg", ("atletico", "PR"): "athletico-pr", ("athletico", "PR"): "athletico-pr",
    ("atletico", "GO"): "atletico-go", ("america", "MG"): "america-mg", ("america", "RN"): "america-rn",
    ("vasco da gama", "RJ"): "vasco", ("red bull bragantino", "SP"): "bragantino",
}

ALIASES = {
    "vasco da gama": "vasco", "atletico mineiro": "atletico-mg", "atletico paranaense": "athletico-pr",
    "athletico paranaense": "athletico-pr", "athletico": "athletico-pr", "atletico goianiense": "atletico-go",
    "america mineiro": "america-mg", "america fc minas gerais": "america-mg", "america fc natal": "america-rn",
    "sport recife": "sport", "sport club do recife": "sport", "sport club recife": "sport",
    "sport club corinthians paulista": "corinthians", "corinthians paulista": "corinthians",
    "red bull bragantino": "bragantino", "rb bragantino": "bragantino", "ceara sporting club": "ceara",
    "gremio foot ball porto alegrense": "gremio", "sport club internacional": "internacional",
    "clube de regatas do flamengo": "flamengo", "botafogo de futebol e regatas": "botafogo",
    "associacao chapecoense de futebol": "chapecoense", "clube atletico mineiro": "atletico-mg",
    "club athletico paranaense": "athletico-pr", "clube de regatas vasco da gama": "vasco",
}

AFFIXES = ["sociedade esportiva", "esporte clube", "futebol clube", "sport club", "clube de regatas", "fbpa",
           "fc", "ec", "sc", "cr", "fr", "af", "ac", "clube", "club"]

DISPLAY = {
    "sao paulo": "São Paulo", "gremio": "Grêmio", "atletico-mg": "Atlético-MG", "athletico-pr": "Athletico-PR",
    "atletico-go": "Atlético-GO", "america-mg": "América-MG", "america-rn": "América-RN", "vasco": "Vasco",
    "goias": "Goiás", "ceara": "Ceará", "avai": "Avaí", "vitoria": "Vitória", "criciuma": "Criciúma",
    "nautico": "Náutico", "parana": "Paraná", "cuiaba": "Cuiabá", "bragantino": "Bragantino",
    "sao caetano": "São Caetano", "santo andre": "Santo André", "gremio prudente": "Grêmio Prudente",
    "csa": "CSA", "crb": "CRB", "abc": "ABC", "flamengo": "Flamengo", "fluminense": "Fluminense",
    "botafogo": "Botafogo", "palmeiras": "Palmeiras", "corinthians": "Corinthians", "santos": "Santos",
    "internacional": "Internacional", "cruzeiro": "Cruzeiro", "bahia": "Bahia", "sport": "Sport",
}

RIVALRIES = {
    frozenset({"flamengo", "fluminense"}): "Fla-Flu",
    frozenset({"flamengo", "vasco"}): "Clássico dos Milhões",
    frozenset({"flamengo", "botafogo"}): "Clássico da Rivalidade",
    frozenset({"fluminense", "vasco"}): "Clássico dos Gigantes",
    frozenset({"botafogo", "fluminense"}): "Clássico Vovô",
    frozenset({"botafogo", "vasco"}): "Clássico da Amizade",
    frozenset({"corinthians", "palmeiras"}): "Derby Paulista",
    frozenset({"palmeiras", "sao paulo"}): "Choque-Rei",
    frozenset({"corinthians", "sao paulo"}): "Majestoso",
    frozenset({"santos", "sao paulo"}): "San-São",
    frozenset({"corinthians", "santos"}): "Clássico Alvinegro",
    frozenset({"palmeiras", "santos"}): "Clássico da Saudade",
    frozenset({"gremio", "internacional"}): "Grenal",
    frozenset({"atletico-mg", "cruzeiro"}): "Clássico Mineiro",
    frozenset({"bahia", "vitoria"}): "Ba-Vi",
    frozenset({"athletico-pr", "coritiba"}): "Atletiba",
    frozenset({"ceara", "fortaleza"}): "Clássico-Rei",
    frozenset({"santa cruz", "sport"}): "Clássico das Multidões",
    frozenset({"nautico", "sport"}): "Clássico dos Clássicos",
    frozenset({"avai", "figueirense"}): "Clássico da Ilha",
    frozenset({"paysandu", "remo"}): "Re-Pa",
    frozenset({"atletico-go", "goias"}): "Clássico Goiano",
}

COMPETITIONS = {
    "Brasileirão": ["brasileirao", "brasileiro", "campeonato brasileiro", "serie a", "brasileirao serie a",
                    "brazilian league", "brazilian serie a", "league"],
    "Série B": ["serie b", "brasileirao serie b"],
    "Série C": ["serie c", "brasileirao serie c"],
    "Copa do Brasil": ["copa do brasil", "brazilian cup", "brazil cup", "cup"],
    "Copa Libertadores": ["copa libertadores", "libertadores", "conmebol libertadores"],
}
LEAGUES = ("Brasileirão", "Série B", "Série C")
DOMESTIC = ("Brasileirão", "Série B", "Série C", "Copa do Brasil")

STAGES = {
    "final": ["final", "finals", "the final"],
    "semifinals": ["semifinal", "semifinals", "semi final", "semi finals", "semis"],
    "quarterfinals": ["quarterfinal", "quarterfinals", "quarter final", "quarter finals"],
    "round of 16": ["round of 16", "last 16", "eighth finals", "round of sixteen"],
    "group stage": ["group stage", "group", "groups", "group phase"],
}

DEMONYMS = {
    "brazilian": "brazil", "argentine": "argentina", "argentinian": "argentina", "uruguayan": "uruguay",
    "paraguayan": "paraguay", "chilean": "chile", "colombian": "colombia", "peruvian": "peru",
    "ecuadorian": "ecuador", "venezuelan": "venezuela", "bolivian": "bolivia", "portuguese": "portugal",
    "spanish": "spain", "french": "france", "german": "germany", "italian": "italy", "english": "england",
    "dutch": "netherlands", "belgian": "belgium", "mexican": "mexico", "american": "united states",
}

POSITION_GROUPS = {
    "forward": {"ST", "CF", "LW", "RW", "LS", "RS", "LF", "RF"},
    "attacker": {"ST", "CF", "LW", "RW", "LS", "RS", "LF", "RF"},
    "striker": {"ST", "CF", "LS", "RS"},
    "winger": {"LW", "RW", "LM", "RM"},
    "midfielder": {"CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"},
    "defender": {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
    "goalkeeper": {"GK"},
    "keeper": {"GK"},
}

_STATE_DASH = re.compile(r"^(?P<name>.*?)\s*-\s*(?P<state>[A-Za-z]{2})$")
_STATE_SPACE = re.compile(r"^(?P<name>.*\S)\s+(?P<state>[A-Z]{2})$")


def simplify(text):
    """Lower-case ASCII words: 'São Paulo-SP' -> 'sao paulo sp', 'C.R.B.' -> 'crb'."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(char for char in text if not unicodedata.combining(char)).lower().replace(".", " ")
    words = re.sub(r"[^a-z0-9]+", " ", text).split()
    if len(words) > 1 and all(len(word) == 1 for word in words):
        return "".join(words)
    return " ".join(words)


def split_state(raw):
    """'Palmeiras-SP' -> ('Palmeiras', 'SP'); 'Gremio RS' -> ('Gremio', 'RS'); 'Bolívar' -> ('Bolívar', None)."""
    text = raw.strip()
    for pattern in (_STATE_DASH, _STATE_SPACE):
        found = pattern.match(text)
        if found and found["state"].upper() in STATES and found["name"]:
            return found["name"].strip(), found["state"].upper()
    return text, None


def _known(key):
    return key in HOME_STATE or key in DISPLAY or key in ALIASES.values()


def _without_affixes(base):
    words = base.split()
    for affix in AFFIXES:
        affix_words = affix.split()
        size = len(affix_words)
        if words[:size] == affix_words and len(words) > size:
            candidate = " ".join(words[size:])
            if _known(ALIASES.get(candidate, candidate)):
                return ALIASES.get(candidate, candidate)
        if words[-size:] == affix_words and len(words) > size:
            candidate = " ".join(words[:-size])
            if _known(ALIASES.get(candidate, candidate)):
                return ALIASES.get(candidate, candidate)
    return None


def team_key(raw):
    """The canonical identity of a club, however its name is written."""
    name, state = split_state(raw)
    base = simplify(name)
    if state and (base, state) in STATE_SPECIFIC:
        return STATE_SPECIFIC[(base, state)]
    if base in ALIASES:
        return ALIASES[base]
    if not state:
        return _without_affixes(base) or base
    if HOME_STATE.get(base) == state:
        return base
    return f"{base}-{state.lower()}"


def display_name(raw):
    """A readable name for a club the first time it is seen, e.g. 'Flamengo - PI' -> 'Flamengo-PI'."""
    key = team_key(raw)
    if key in DISPLAY:
        return DISPLAY[key]
    name, state = split_state(raw)
    if state and key.endswith("-" + state.lower()):
        return f"{name}-{state}"
    return name


def competition_name(text):
    """The competition a user means, or None when it is not recognised."""
    if text is None:
        return None
    wanted = simplify(text)
    for name, spellings in COMPETITIONS.items():
        if wanted == simplify(name) or wanted in spellings:
            return name
    for name, spellings in COMPETITIONS.items():
        if any(spelling in wanted for spelling in spellings if len(spelling) > 4):
            return name
    return None


def stage_name(text):
    if text is None:
        return None
    wanted = simplify(text)
    for name, spellings in STAGES.items():
        if wanted in spellings:
            return name
    return wanted


def nationality_key(text):
    wanted = simplify(text)
    return DEMONYMS.get(wanted, wanted)


def position_codes(text):
    """The FIFA position codes meant by 'forward', 'defenders', 'ST', ..."""
    wanted = simplify(text)
    if wanted.upper() in {code for codes in POSITION_GROUPS.values() for code in codes}:
        return {wanted.upper()}
    singular = wanted[:-1] if wanted.endswith("s") else wanted
    return POSITION_GROUPS.get(wanted) or POSITION_GROUPS.get(singular) or {wanted.upper()}


def derby_name(first_key, second_key):
    return RIVALRIES.get(frozenset({first_key, second_key}))
