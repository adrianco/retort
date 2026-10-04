"""
Team identity: recognising one club however a dataset writes its name.

The datasets name clubs inconsistently:
  "Palmeiras-SP", "Palmeiras - SP", "Palmeiras", "Sociedade Esportiva Palmeiras",
  "Sao Paulo" / "São Paulo", "Atletico-PR" / "Athletico Paranaense" / "Athletico",
  "Barcelona-EQU", "Nacional (URU)", "C. R. B. - AL", "Fortaleza EC" ...

A raw name is parsed into (base name, qualifier), where the qualifier is a
Brazilian state (RJ, SP, ...) or a country code (URU, PAR, ...). The pair is
turned into a stable key such as "palmeiras|SP".

Clubs from different states can share a base name (Botafogo-RJ / Botafogo-PB,
Santos-SP / Santos-AP), so an unqualified name is resolved to:
  1. the well-known club for that name (DEFAULT_STATE), else
  2. the only Brazilian state that name has been seen with - but only for
     names from Brazilian domestic datasets: "River Plate" in the Libertadores
     is the Argentine club, not River Plate-SE from the Copa do Brasil - else
  3. the bare name.

TeamRegistry is built from every raw name in every dataset, then answers
key_for(raw_name) for loading and resolve(question_text) for queries.
"""
import collections
import difflib

from .text import has_accents, plain

BRAZILIAN_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
    "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}
COUNTRY_CODES = {"URU", "PAR", "EQU", "ECU", "PER", "CHI", "BOL", "COL", "VEN", "ARG", "MEX"}

# Full or alternative names (in plain form) -> (base, qualifier)
ALIASES = {
    "sociedade esportiva palmeiras": ("palmeiras", "SP"),
    "se palmeiras": ("palmeiras", "SP"),
    "sport club corinthians paulista": ("corinthians", "SP"),
    "sao paulo futebol clube": ("sao paulo", "SP"),
    "clube de regatas do flamengo": ("flamengo", "RJ"),
    "cr flamengo": ("flamengo", "RJ"),
    "vasco": ("vasco da gama", "RJ"),
    "cr vasco da gama": ("vasco da gama", "RJ"),
    "atletico mineiro": ("atletico", "MG"),
    "clube atletico mineiro": ("atletico", "MG"),
    "atletico paranaense": ("athletico", "PR"),
    "athletico paranaense": ("athletico", "PR"),
    "club athletico paranaense": ("athletico", "PR"),
    "atletico goianiense": ("atletico", "GO"),
    "america mineiro": ("america", "MG"),
    "america fc minas gerais": ("america", "MG"),
    "america fc natal": ("america", "RN"),
    "sport recife": ("sport", "PE"),
    "sport club do recife": ("sport", "PE"),
    "sport club recife": ("sport", "PE"),
    "nautico capibaribe": ("nautico", "PE"),
    "clube nautico capibaribe": ("nautico", "PE"),
    "ceara sporting club": ("ceara", "CE"),
    "red bull bragantino": ("bragantino", "SP"),
    "rb bragantino": ("bragantino", "SP"),
    "portuguesa desportos": ("portuguesa", "SP"),
    "gremio novorizontino": ("novorizontino", "SP"),
    "gremio foot ball porto alegrense": ("gremio", "RS"),
    "sport club internacional": ("internacional", "RS"),
    "clube do remo": ("remo", "PA"),
    "associacao chapecoense de futebol": ("chapecoense", "SC"),
    "cs alagoano": ("csa", "AL"),
    "barueri": ("gremio barueri", "SP"),
    "corinthians paulista": ("corinthians", "SP"),
}
# Qualified forms that are really another club's canonical form
REQUALIFY = {("atletico", "PR"): ("athletico", "PR")}

# The famous club a bare name refers to
DEFAULT_STATE = {
    "flamengo": "RJ", "fluminense": "RJ", "botafogo": "RJ", "vasco da gama": "RJ",
    "santos": "SP", "sao paulo": "SP", "palmeiras": "SP", "corinthians": "SP", "guarani": "SP",
    "bragantino": "SP", "portuguesa": "SP", "ponte preta": "SP", "america": "MG", "cruzeiro": "MG",
    "internacional": "RS", "juventude": "RS", "gremio": "RS", "vitoria": "BA", "bahia": "BA",
    "nautico": "PE", "sport": "PE", "santa cruz": "PE", "operario": "PR", "athletico": "PR", "coritiba": "PR",
    "parana": "PR", "remo": "PA", "ceara": "CE", "fortaleza": "CE", "goias": "GO", "avai": "SC",
    "figueirense": "SC", "chapecoense": "SC", "criciuma": "SC", "cuiaba": "MT", "csa": "AL", "crb": "AL",
    "libertad": "PAR",
}

DISPLAY_NAMES = {
    "flamengo|RJ": "Flamengo", "fluminense|RJ": "Fluminense", "vasco da gama|RJ": "Vasco da Gama",
    "botafogo|RJ": "Botafogo", "sao paulo|SP": "São Paulo", "palmeiras|SP": "Palmeiras",
    "corinthians|SP": "Corinthians", "santos|SP": "Santos", "gremio|RS": "Grêmio",
    "internacional|RS": "Internacional", "atletico|MG": "Atlético-MG", "athletico|PR": "Athletico-PR",
    "atletico|GO": "Atlético-GO", "america|MG": "América-MG", "america|RN": "América-RN",
    "bragantino|SP": "Red Bull Bragantino", "sport|PE": "Sport", "nautico|PE": "Náutico", "ceara|CE": "Ceará",
    "goias|GO": "Goiás", "avai|SC": "Avaí", "criciuma|SC": "Criciúma", "vitoria|BA": "Vitória",
    "parana|PR": "Paraná", "cuiaba|MT": "Cuiabá", "csa|AL": "CSA", "crb|AL": "CRB", "abc|RN": "ABC",
    "juventude|RS": "Juventude", "guarani|SP": "Guarani", "santa cruz|PE": "Santa Cruz",
    "portuguesa|SP": "Portuguesa", "bahia|BA": "Bahia", "fortaleza|CE": "Fortaleza", "coritiba|PR": "Coritiba",
    "cruzeiro|MG": "Cruzeiro", "chapecoense|SC": "Chapecoense", "figueirense|SC": "Figueirense",
    "ponte preta|SP": "Ponte Preta", "gremio barueri|SP": "Grêmio Barueri",
}

NOISE_WORDS = {"fc", "ec", "sc", "ac", "cr", "se", "fr", "clube", "club", "futebol", "esporte"}
TRAILING_NOISE_WORDS = NOISE_WORDS | {"sport"}


def parse_name(raw):
    """Split a raw team name into (plain base name, qualifier or None, display base)."""
    name = " ".join((raw or "").split())
    qualifier = None
    if "(" in name and name.endswith(")"):
        inside = name[name.rindex("(") + 1:-1].strip()
        if inside.upper() in COUNTRY_CODES:
            qualifier = inside.upper()
            name = name[:name.rindex("(")].strip()
    whole = plain(name)
    if whole in ALIASES:
        return (*ALIASES[whole], name)
    while qualifier is None:
        for separator in (" - ", "-", " "):
            head, _, tail = name.rpartition(separator)
            code = tail.strip()
            if head.strip() and ((code.upper() in COUNTRY_CODES and separator != " ")
                                 or (code in BRAZILIAN_STATES) or (separator != " " and code.upper() in BRAZILIAN_STATES)):
                qualifier, name = code.upper(), head.strip()
                break
        else:
            break
    name = _strip_parenthetical(name)
    base = plain(name)
    if base in ALIASES:
        alias_base, alias_qualifier = ALIASES[base]
        return alias_base, qualifier or alias_qualifier, name
    words = base.split()
    while len(words) > 1 and words[0] in NOISE_WORDS:
        words.pop(0)
    while len(words) > 1 and words[-1] in TRAILING_NOISE_WORDS:
        words.pop()
    base = " ".join(words)
    if base in ALIASES:
        alias_base, alias_qualifier = ALIASES[base]
        return alias_base, qualifier or alias_qualifier, name
    base, qualifier = REQUALIFY.get((base, qualifier), (base, qualifier))
    return base, qualifier, name


def _strip_parenthetical(name):
    while "(" in name and ")" in name and name.index("(") < name.rindex(")"):
        name = (name[:name.index("(")] + name[name.rindex(")") + 1:]).strip()
    return name.strip(" -")


class TeamNotFound(LookupError):
    pass


class TeamRegistry:
    def __init__(self):
        self._states_seen = collections.defaultdict(set)
        self._displays = collections.defaultdict(collections.Counter)
        self._activity = collections.Counter()
        self._keys = {}
        self._display_cache = {}

    # --- building -------------------------------------------------------------------------------------------------

    def observe(self, raw):
        base, qualifier, _ = parse_name(raw)
        if qualifier in BRAZILIAN_STATES:
            self._states_seen[base].add(qualifier)

    def key_for(self, raw, international=False):
        """international: the name comes from a dataset that isn't only Brazilian clubs (Libertadores, FIFA)."""
        key = self._keys.get((raw, international))
        if key is None:
            base, qualifier, display = parse_name(raw)
            key = self._key(base, qualifier, domestic=not international)
            self._keys[(raw, international)] = key
            self._displays[key][display] += 1
            self._display_cache.clear()
        return key

    def count_activity(self, key, amount=1):
        self._activity[key] += amount

    def _key(self, base, qualifier, domestic=True):
        if qualifier is None:
            seen = self._states_seen.get(base, set()) if domestic else set()
            qualifier = DEFAULT_STATE.get(base) or (next(iter(seen)) if len(seen) == 1 else None)
        return f"{base}|{qualifier}" if qualifier else base

    def _keys_sharing_base(self, base):
        return [k for k in self._displays if k.split("|")[0] == base]

    # --- presenting -----------------------------------------------------------------------------------------------

    def display(self, key):
        if key not in self._display_cache:
            self._display_cache[key] = self._display(key)
        return self._display_cache[key]

    def _display(self, key):
        if key in DISPLAY_NAMES:
            return DISPLAY_NAMES[key]
        names = self._displays.get(key)
        if not names:
            return key
        best = max(names, key=lambda n: (has_accents(n), names[n], -len(n)))
        base, _, qualifier = key.partition("|")
        if qualifier and len(self._keys_sharing_base(base)) > 1 and DEFAULT_STATE.get(base) != qualifier:
            best = f"{best}-{qualifier}"
        return best

    # --- answering questions --------------------------------------------------------------------------------------

    def resolve(self, question):
        """Find the key for a team named in a question, e.g. 'gremio', 'Sao Paulo FC', 'Atletico Mineiro'."""
        known = set(self._displays)
        base, qualifier, _ = parse_name(question)
        key = self._key(base, qualifier)
        if key in known and (qualifier or base in DEFAULT_STATE):
            return key
        same_base = [k for k in known if k.split("|")[0] == base and (not qualifier or k.endswith("|" + qualifier))]
        if same_base:
            return self._most_active(same_base)
        wanted = plain(question)
        containing = [k for k in known if wanted and (wanted in plain(self.display(k)) or wanted == k.split("|")[0])]
        if containing:
            return self._most_active(containing)
        within = [k for k in known if len(k.split("|")[0]) >= 4 and f" {k.split('|')[0]} " in f" {wanted} "]
        if within:
            longest = max(len(k.split("|")[0]) for k in within)
            return self._most_active([k for k in within if len(k.split("|")[0]) == longest])
        close = difflib.get_close_matches(base, [k.split("|")[0] for k in known], n=3, cutoff=0.8)
        if close:
            return self._most_active([k for k in known if k.split("|")[0] in close])
        names = {plain(self.display(k)): self.display(k) for k in known}
        suggestions = [names[n] for n in difflib.get_close_matches(wanted, list(names), n=5, cutoff=0.5)]
        hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
        raise TeamNotFound(f"No team called {question!r} appears in the datasets.{hint}")

    def _most_active(self, keys):
        return max(sorted(keys), key=lambda k: self._activity[k])
