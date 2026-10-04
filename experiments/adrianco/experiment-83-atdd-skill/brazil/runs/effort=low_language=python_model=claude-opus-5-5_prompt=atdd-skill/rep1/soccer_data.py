"""Loading and normalising the Brazilian soccer datasets, plus query logic."""
import csv
import os
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kaggle")

BRASILEIRAO = "Brasileirão"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Libertadores"
SERIE_B = "Serie B"
SERIE_C = "Serie C"

STATES = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB",
          "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"}
AMBIGUOUS = {"atletico", "athletico", "america", "botafogo", "bragantino", "gremio", "nacional",
             "guarani", "river plate", "universitario", "libertad", "sport", "vitoria", "operario"}
ALIASES = {
    "atletico mg": "atletico mineiro", "atletico mineiro mg": "atletico mineiro",
    "atletico go": "atletico goianiense", "atletico goianiense go": "atletico goianiense",
    "atletico pr": "athletico paranaense", "athletico pr": "athletico paranaense",
    "athletico": "athletico paranaense", "atletico paranaense": "athletico paranaense",
    "atletico paranaense pr": "athletico paranaense", "athletico paranaense pr": "athletico paranaense",
    "america mg": "america mineiro", "america fc minas gerais": "america mineiro",
    "botafogo rj": "botafogo", "vasco da gama": "vasco", "vasco da gama rj": "vasco",
    "red bull bragantino": "bragantino", "bragantino sp": "bragantino", "red bull bragantino sp": "bragantino",
    "gremio rs": "gremio", "sport pe": "sport", "sport recife": "sport", "sport club do recife": "sport",
    "vitoria ba": "vitoria", "sao paulo fc": "sao paulo", "ceara sporting club": "ceara",
    "sport club corinthians paulista": "corinthians", "se palmeiras": "palmeiras",
    "cr flamengo": "flamengo", "clube de regatas do flamengo": "flamengo",
    "csa al": "csa", "nautico capibaribe": "nautico", "santa cruz fc": "santa cruz",
    "ec bahia": "bahia", "ec juventude": "juventude", "fortaleza ec": "fortaleza", "fortaleza fc": "fortaleza",
    "portuguesa desportos": "portuguesa", "c s a": "csa",
}
TRADITIONAL_DERBIES = [
    ("flamengo", "fluminense", "Fla-Flu"), ("flamengo", "vasco", "Clássico dos Milhões"),
    ("flamengo", "botafogo", "Clássico da Rivalidade"), ("fluminense", "vasco", "Clássico dos Gigantes"),
    ("botafogo", "fluminense", "Clássico Vovô"), ("botafogo", "vasco", "Clássico da Amizade"),
    ("corinthians", "palmeiras", "Derby Paulista"), ("corinthians", "sao paulo", "Majestoso"),
    ("palmeiras", "sao paulo", "Choque-Rei"), ("palmeiras", "santos", "Clássico da Saudade"),
    ("corinthians", "santos", "Clássico Alvinegro"), ("santos", "sao paulo", "San-São"),
    ("gremio", "internacional", "Grenal"), ("atletico mineiro", "cruzeiro", "Clássico Mineiro"),
    ("bahia", "vitoria", "Ba-Vi"), ("athletico paranaense", "coritiba", "Atletiba"),
    ("ceara", "fortaleza", "Clássico-Rei"), ("nautico", "sport", "Clássico dos Clássicos"),
    ("santa cruz", "sport", "Clássico das Multidões"),
]
DERBY_LOOKUP = {frozenset((a, b)): name for a, b, name in TRADITIONAL_DERBIES}


def strip_accents(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize_team(name):
    """Canonical key for a team name across datasets ('Palmeiras-SP' -> 'palmeiras')."""
    if not name:
        return ""
    raw = strip_accents(name.strip())
    raw = re.sub(r"\(antigo[^)]*\)", "", raw, flags=re.I)
    state = None
    m = re.match(r"^(.*?)\s*(?:-\s*|\s+)([A-Z]{2})$", raw.strip())
    if m and m.group(2) in STATES:
        raw, state = m.group(1), m.group(2)
    else:  # foreign suffixes: "(URU)", "-EQU", "-PAR"
        raw = re.sub(r"\s*\(([A-Z]{3})\)$|-([A-Z]{3})$", "", raw.strip())
    key = re.sub(r"[^a-z0-9 ]", " ", raw.lower())
    key = re.sub(r"\s+", " ", key).strip()
    if state and key in AMBIGUOUS:
        key = f"{key} {state.lower()}"
    return ALIASES.get(key, key)


def display_team(name):
    """Readable team name without the state suffix."""
    name = re.sub(r"\(antigo[^)]*\)", "", name).strip()
    m = re.match(r"^(.*?)\s*(?:-\s*|\s+)([A-Z]{2})$", name)
    if m and m.group(2) in STATES and normalize_team(m.group(1)) == normalize_team(name):
        return m.group(1).strip()
    return name.strip()


def parse_date(text):
    text = (text or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def to_int(text):
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def normalize_competition(text):
    if not text:
        return None
    key = strip_accents(text).lower()
    if "libert" in key:
        return LIBERTADORES
    if "copa" in key or "cup" in key:
        return COPA_DO_BRASIL
    if "serie b" in key:
        return SERIE_B
    if "serie c" in key:
        return SERIE_C
    if "brasileir" in key or "serie a" in key or "campeonato" in key:
        return BRASILEIRAO
    return text


@dataclass
class Match:
    date: object
    home: str
    away: str
    home_goals: int
    away_goals: int
    competition: str
    season: int
    source: str
    round: str = ""
    stage: str = ""
    arena: str = ""
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        self.home_key = normalize_team(self.home)
        self.away_key = normalize_team(self.away)

    @property
    def home_name(self):
        return display_team(self.home)

    @property
    def away_name(self):
        return display_team(self.away)

    def describe(self):
        label = self.competition
        if self.round:
            label += f" Round {self.round}"
        if self.stage:
            label += f" - {self.stage}"
        line = (f"{self.date.isoformat() if self.date else '????-??-??'}: {self.home_name} "
                f"{self.home_goals}-{self.away_goals} {self.away_name} ({label}, {self.season})")
        if self.arena:
            line += f" @ {self.arena}"
        if self.extra:
            line += " [" + ", ".join(f"{k}: {v}" for k, v in self.extra.items()) + "]"
        return line


class SoccerData:
    def __init__(self, data_dir=DATA_DIR):
        self.data_dir = data_dir
        self.source_counts = {}
        self.matches = []
        self.players = []
        self._load()

    def _rows(self, filename):
        with open(os.path.join(self.data_dir, filename), encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        self.source_counts[filename] = len(rows)
        return rows

    def _load(self):
        loaded = []
        for r in self._rows("Brasileirao_Matches.csv"):
            loaded.append(Match(parse_date(r["datetime"]), r["home_team"], r["away_team"],
                                to_int(r["home_goal"]), to_int(r["away_goal"]), BRASILEIRAO,
                                to_int(r["season"]), "Brasileirao_Matches.csv", round=r["round"]))
        for r in self._rows("novo_campeonato_brasileiro.csv"):
            loaded.append(Match(parse_date(r["Data"]), r["Equipe_mandante"], r["Equipe_visitante"],
                                to_int(r["Gols_mandante"]), to_int(r["Gols_visitante"]), BRASILEIRAO,
                                to_int(r["Ano"]), "novo_campeonato_brasileiro.csv",
                                round=r["Rodada"], arena=r.get("Arena", "")))
        cup_rounds = defaultdict(int)
        cup_rows = self._rows("Brazilian_Cup_Matches.csv")
        for r in cup_rows:
            cup_rounds[r["season"]] = max(cup_rounds[r["season"]], to_int(r["round"]) or 0)
        for r in cup_rows:
            stage = "final" if to_int(r["round"]) == cup_rounds[r["season"]] else ""
            loaded.append(Match(parse_date(r["datetime"]), r["home_team"], r["away_team"],
                                to_int(r["home_goal"]), to_int(r["away_goal"]), COPA_DO_BRASIL,
                                to_int(r["season"]), "Brazilian_Cup_Matches.csv", round=r["round"], stage=stage))
        for r in self._rows("Libertadores_Matches.csv"):
            d = parse_date(r["datetime"])
            season = to_int(r["season"]) or (d.year if d else None)
            loaded.append(Match(d, r["home_team"], r["away_team"], to_int(r["home_goal"]),
                                to_int(r["away_goal"]), LIBERTADORES, season,
                                "Libertadores_Matches.csv", stage=r["stage"]))
        for r in self._rows("BR-Football-Dataset.csv"):
            d = parse_date(r["date"])
            extra = {}
            for label, h, a in (("corners", "home_corner", "away_corner"), ("shots", "home_shots", "away_shots"),
                                ("attacks", "home_attack", "away_attack")):
                if to_int(r[h]) is not None and to_int(r[a]) is not None:
                    extra[label] = f"{to_int(r[h])}-{to_int(r[a])}"
            comp = normalize_competition(r["tournament"])
            season = d.year if d else None
            if d and comp in (BRASILEIRAO, SERIE_B, SERIE_C) and d.month <= 2:
                season -= 1  # e.g. the 2020 season finished in February 2021
            loaded.append(Match(d, r["home"], r["away"], to_int(r["home_goal"]), to_int(r["away_goal"]),
                                comp, season,
                                "BR-Football-Dataset.csv", extra=extra))
        # The same fixture may appear in several files: keep the first (richest-first order above),
        # but merge extended statistics in.
        seen = {}
        for m in loaded:
            if m.home_goals is None or m.away_goals is None:
                continue
            league = m.competition in (BRASILEIRAO, SERIE_B, SERIE_C)
            key = (m.season if league else m.date, m.home_key, m.away_key, m.competition)
            if key in seen:
                if m.extra and not seen[key].extra:
                    seen[key].extra = m.extra
                continue
            seen[key] = m
            self.matches.append(m)
        self.matches.sort(key=lambda m: (m.date is None, m.date), reverse=True)

        for r in self._rows("fifa_data.csv"):
            self.players.append({
                "id": r["ID"], "name": r["Name"], "age": to_int(r["Age"]), "nationality": r["Nationality"],
                "overall": to_int(r["Overall"]) or 0, "potential": to_int(r["Potential"]) or 0,
                "club": r["Club"], "position": r["Position"], "jersey": r["Jersey Number"],
                "height": r["Height"], "weight": r["Weight"], "value": r["Value"],
                "foot": r["Preferred Foot"],
                "skills": {k: r.get(k) for k in ("Crossing", "Finishing", "Dribbling", "ShortPassing",
                                                  "SprintSpeed", "Stamina", "StandingTackle")},
                "_name": strip_accents(r["Name"]).lower(), "_club": normalize_team(r["Club"]),
            })
        self.players.sort(key=lambda p: -p["overall"])
        self.brazilian_club_keys = {m.home_key for m in self.matches if m.competition in (BRASILEIRAO, SERIE_B)}

    # --- team resolution --------------------------------------------------
    def team_matcher(self, query):
        """Return predicate over canonical keys: exact match, else word-prefix match."""
        q = normalize_team(query)
        keys = {m.home_key for m in self.matches} | {m.away_key for m in self.matches}
        if q in keys:
            return lambda k: k == q
        loose = {k for k in keys if re.search(rf"\b{re.escape(q)}\b", k)}
        return lambda k: k in loose

    def team_display(self, query):
        match = self.team_matcher(query)
        for m in self.matches:
            if match(m.home_key):
                return m.home_name
            if match(m.away_key):
                return m.away_name
        return query

    # --- matches ----------------------------------------------------------
    def find_matches(self, team=None, opponent=None, competition=None, season=None, date_from=None,
                     date_to=None, stage=None, venue="all"):
        comp = normalize_competition(competition)
        t = self.team_matcher(team) if team else None
        o = self.team_matcher(opponent) if opponent else None
        dfrom, dto = parse_date(date_from), parse_date(date_to)
        out = []
        for m in self.matches:
            if comp and m.competition != comp:
                continue
            if season and m.season != int(season):
                continue
            if dfrom and (not m.date or m.date < dfrom):
                continue
            if dto and (not m.date or m.date > dto):
                continue
            if stage and stage.strip().lower() != m.stage.lower():
                continue
            if t:
                home_ok = t(m.home_key) and (not o or o(m.away_key))
                away_ok = t(m.away_key) and (not o or o(m.home_key))
                if venue == "home":
                    away_ok = False
                elif venue == "away":
                    home_ok = False
                if not (home_ok or away_ok):
                    continue
            elif o and not (o(m.home_key) or o(m.away_key)):
                continue
            out.append(m)
        return out

    @staticmethod
    def record(matches, team_match):
        rec = dict(matches=0, wins=0, draws=0, losses=0, gf=0, ga=0)
        for m in matches:
            if team_match(m.home_key):
                gf, ga = m.home_goals, m.away_goals
            elif team_match(m.away_key):
                gf, ga = m.away_goals, m.home_goals
            else:
                continue
            rec["matches"] += 1
            rec["gf"] += gf
            rec["ga"] += ga
            rec["wins" if gf > ga else "losses" if gf < ga else "draws"] += 1
        return rec

    def table(self, matches):
        teams = defaultdict(lambda: dict(name="", matches=0, wins=0, draws=0, losses=0, gf=0, ga=0))
        for m in matches:
            for key, name, gf, ga in ((m.home_key, m.home_name, m.home_goals, m.away_goals),
                                      (m.away_key, m.away_name, m.away_goals, m.home_goals)):
                t = teams[key]
                t["name"] = t["name"] or name
                t["matches"] += 1
                t["gf"] += gf
                t["ga"] += ga
                t["wins" if gf > ga else "losses" if gf < ga else "draws"] += 1
        rows = list(teams.values())
        for r in rows:
            r["points"] = 3 * r["wins"] + r["draws"]
            r["gd"] = r["gf"] - r["ga"]
        rows.sort(key=lambda r: (-r["points"], -r["wins"], -r["gd"], -r["gf"], r["name"]))
        return rows

    def season_matches(self, season, competition=BRASILEIRAO):
        return self.find_matches(competition=competition, season=season)

    # --- players ----------------------------------------------------------
    def find_players(self, name=None, nationality=None, club=None, position=None, min_overall=None):
        name_q = strip_accents(name).lower() if name else None
        nat_q = strip_accents(nationality).lower() if nationality else None
        if nat_q in ("brazilian", "brasil"):
            nat_q = "brazil"
        club_m = None
        if club:
            ck = normalize_team(club)
            club_m = lambda k: k == ck or re.search(rf"\b{re.escape(ck)}\b", k) is not None
        out = []
        for p in self.players:
            if name_q and name_q not in p["_name"]:
                continue
            if nat_q and strip_accents(p["nationality"]).lower() != nat_q:
                continue
            if club_m and not club_m(p["_club"]):
                continue
            if position and p["position"].upper() not in _positions(position):
                continue
            if min_overall and p["overall"] < min_overall:
                continue
            out.append(p)
        return out

    def is_brazilian_club(self, player):
        return bool(player["club"]) and player["_club"] in self.brazilian_club_keys


POSITION_GROUPS = {
    "forward": {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"},
    "striker": {"ST", "CF", "LS", "RS"},
    "midfielder": {"CM", "CAM", "CDM", "LM", "RM", "LCM", "RCM", "LAM", "RAM", "LDM", "RDM"},
    "defender": {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
    "goalkeeper": {"GK"},
}


def _positions(position):
    key = position.lower().rstrip("s")
    return POSITION_GROUPS.get(key, {position.upper()})
