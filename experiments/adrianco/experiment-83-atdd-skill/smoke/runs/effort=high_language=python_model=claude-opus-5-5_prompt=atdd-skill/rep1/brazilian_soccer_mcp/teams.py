"""
Team identity: turns the many spellings of a club found across the
datasets into one stable key and a readable display name.

The datasets disagree on how they name clubs:
  - state suffixes: "Palmeiras-SP", "América - MG", "Botafogo RJ"
  - accents: "São Paulo" / "Sao Paulo", "Grêmio" / "Gremio"
  - full names: "Sport Club Corinthians Paulista", "Ceará Sporting Club"
  - foreign country tags: "Guaraní (PAR)", "Barcelona-EQU"
Some short names are shared by different clubs ("Atlético" is a club in
MG, PR and GO), so a known club is only matched when the state agrees.
"""

import re
import unicodedata

STATES = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR",
          "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"}

# (display name, home state, other names it is known by — accent-free, lower case)
KNOWN_CLUBS = [
    ("Flamengo", "RJ", ["flamengo", "cr flamengo", "clube de regatas do flamengo"]),
    ("Fluminense", "RJ", ["fluminense", "fluminense football club"]),
    ("Botafogo", "RJ", ["botafogo", "botafogo fr", "botafogo de futebol e regatas"]),
    ("Vasco da Gama", "RJ", ["vasco", "vasco da gama", "cr vasco da gama", "club de regatas vasco da gama"]),
    ("Corinthians", "SP", ["corinthians", "sc corinthians", "sport club corinthians paulista",
                           "corinthians paulista"]),
    ("Palmeiras", "SP", ["palmeiras", "se palmeiras", "sociedade esportiva palmeiras"]),
    ("São Paulo", "SP", ["sao paulo", "sao paulo futebol clube"]),
    ("Santos", "SP", ["santos", "santos futebol clube"]),
    ("Red Bull Bragantino", "SP", ["bragantino", "red bull bragantino", "rb bragantino",
                                   "clube atletico bragantino"]),
    ("Ponte Preta", "SP", ["ponte preta", "aa ponte preta"]),
    ("Portuguesa", "SP", ["portuguesa", "portuguesa desportos", "associacao portuguesa de desportos"]),
    ("Guarani", "SP", ["guarani"]),
    ("Grêmio", "RS", ["gremio", "gremio fbpa", "gremio foot-ball porto alegrense"]),
    ("Internacional", "RS", ["internacional", "sc internacional", "sport club internacional"]),
    ("Juventude", "RS", ["juventude", "ec juventude", "esporte clube juventude"]),
    ("Atlético Mineiro", "MG", ["atletico", "atletico mineiro", "clube atletico mineiro"]),
    ("Cruzeiro", "MG", ["cruzeiro", "cruzeiro esporte clube"]),
    ("América Mineiro", "MG", ["america", "america mineiro", "america fc (minas gerais)"]),
    ("América-RN", "RN", ["america", "america fc natal", "america de natal"]),
    ("Athletico Paranaense", "PR", ["atletico", "athletico", "atletico paranaense", "athletico paranaense",
                                    "club athletico paranaense"]),
    ("Coritiba", "PR", ["coritiba"]),
    ("Paraná", "PR", ["parana", "parana clube"]),
    ("Atlético Goianiense", "GO", ["atletico", "atletico goianiense"]),
    ("Goiás", "GO", ["goias", "goias esporte clube"]),
    ("Bahia", "BA", ["bahia", "ec bahia", "esporte clube bahia"]),
    ("Vitória", "BA", ["vitoria", "ec vitoria", "esporte clube vitoria"]),
    ("Sport Recife", "PE", ["sport", "sport recife", "sport club do recife"]),
    ("Náutico", "PE", ["nautico", "nautico capibaribe", "clube nautico capibaribe"]),
    ("Santa Cruz", "PE", ["santa cruz"]),
    ("Ceará", "CE", ["ceara", "ceara sporting club"]),
    ("Fortaleza", "CE", ["fortaleza", "fortaleza esporte clube"]),
    ("Chapecoense", "SC", ["chapecoense", "associacao chapecoense de futebol"]),
    ("Avaí", "SC", ["avai"]),
    ("Figueirense", "SC", ["figueirense"]),
    ("Criciúma", "SC", ["criciuma"]),
    ("Joinville", "SC", ["joinville"]),
    ("Cuiabá", "MT", ["cuiaba"]),
    ("CSA", "AL", ["csa"]),
]

# Short names shared by clubs in different states, and which one a bare name means.
DEFAULT_FOR_BARE_NAME = {"botafogo": "Botafogo"}

_GENERIC_SUFFIXES = {"fc", "ec", "ac", "cf"}
_HYPHEN_STATE = re.compile(r"^(.*?)\s*-\s*([A-Z]{2})$")
_SPACE_STATE = re.compile(r"^(.*?)\s+([A-Z]{2})$")
_FOREIGN_TAG = re.compile(r"^(.*?)\s*(?:-\s*([A-Z]{3})|\(([A-Z]{3})\))$")


def fold(text):
    """Accent-free, lower-case, single-spaced text for comparisons."""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    text = text.lower().replace(".", "")
    return " ".join(text.split())


def strip_accents(text):
    return unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()


def _club_key(display):
    return fold(display)


_ALIASES = {}
for _display, _state, _names in KNOWN_CLUBS:
    for _name in _names:
        _ALIASES.setdefault(_name, []).append((_display, _state))


class TeamName:
    """A parsed team name: base name, optional Brazilian state, optional foreign country tag."""

    def __init__(self, raw):
        self.raw = raw
        text = " ".join(str(raw).replace(" ", " ").split())
        self.state = None
        self.country = None
        whole = fold(text)
        if whole in _ALIASES:
            self.base_text = text
            return
        foreign = _FOREIGN_TAG.match(text)
        hyphen_state = _HYPHEN_STATE.match(text)
        space_state = _SPACE_STATE.match(text)
        if hyphen_state and hyphen_state.group(2) in STATES:
            text, self.state = hyphen_state.group(1), hyphen_state.group(2)
        elif space_state and space_state.group(2) in STATES - {"SC"}:
            text, self.state = space_state.group(1), space_state.group(2)
        elif foreign:
            text, self.country = foreign.group(1), foreign.group(2) or foreign.group(3)
        text = re.sub(r"\s*\((?:antigo|ex)[^)]*\)", "", text, flags=re.IGNORECASE).strip()
        self.base_text = text

    @property
    def base(self):
        words = fold(self.base_text).split()
        while len(words) > 1 and words[-1] in _GENERIC_SUFFIXES:
            words.pop()
        return " ".join(words)

    def identify(self):
        """Return (key, display name) for this team."""
        base = fold(self.base_text) if fold(self.base_text) in _ALIASES else self.base
        if self.country:
            return f"{base} ({self.country.lower()})", f"{self.base_text} ({self.country})"
        candidates = _ALIASES.get(base, [])
        if candidates:
            if self.state:
                for display, state in candidates:
                    if state == self.state:
                        return _club_key(display), display
                return f"{base}-{self.state.lower()}", f"{self.base_text.strip()}-{self.state}"
            if len(candidates) == 1:
                display = candidates[0][0]
                return _club_key(display), display
            if base in DEFAULT_FOR_BARE_NAME:
                display = DEFAULT_FOR_BARE_NAME[base]
                return _club_key(display), display
            return base, self.base_text
        return base, self.base_text


class TeamRegistry:
    """Every team seen in the match data, keyed by identity, with the best display name."""

    def __init__(self):
        self._display = {}

    def register(self, raw_name):
        key, display = TeamName(raw_name).identify()
        current = self._display.get(key)
        if current is None or (_is_plain_ascii(current) and not _is_plain_ascii(display)
                               and fold(current) == fold(display)):
            self._display[key] = display
        return key

    def display(self, key):
        return self._display.get(key, key)

    def keys(self):
        return self._display.keys()

    def __contains__(self, key):
        return key in self._display

    def resolve(self, query, among=None):
        """Find the key for a team the user asked about, or None.

        Exact identity first; otherwise the best-known team whose name
        contains every word of the query. `among` optionally maps key ->
        number of matches, used to prefer the most prominent candidate.
        """
        if not query or not str(query).strip():
            return None
        key, _ = TeamName(query).identify()
        if key in self._display:
            return key
        words = fold(strip_accents(query)).replace("-", " ").split()
        candidates = []
        for candidate, display in self._display.items():
            haystack = (fold(display) + " " + candidate).replace("-", " ").split()
            if all(any(h.startswith(w) for h in haystack) for w in words):
                candidates.append(candidate)
        if not candidates:
            return None
        weight = among or {}
        return max(candidates, key=lambda c: (weight.get(c, 0), -len(c)))

    def suggestions(self, query, limit=5):
        words = fold(query).split()
        found = [self._display[k] for k in self._display
                 if any(w[:4] in fold(self._display[k]) for w in words if len(w) >= 3)]
        return sorted(found)[:limit]


def identify(raw_name):
    return TeamName(raw_name).identify()


def _is_plain_ascii(text):
    return strip_accents(text) == text
