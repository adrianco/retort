"""Brazilian soccer knowledge base built from the provided Kaggle CSV files."""
import csv
import os
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kaggle")

BRASILEIRAO = "Brasileirão"
COMPETITION_ALIASES = {
    "brasileirao": BRASILEIRAO, "serie a": BRASILEIRAO, "brasileirao serie a": BRASILEIRAO,
    "campeonato brasileiro": BRASILEIRAO,
    "copa do brasil": "Copa do Brasil", "brazilian cup": "Copa do Brasil",
    "libertadores": "Libertadores", "copa libertadores": "Libertadores",
    "serie b": "Serie B", "serie c": "Serie C",
}
DERBIES = [
    ("flamengo", "fluminense"), ("flamengo", "vasco"), ("flamengo", "botafogo"),
    ("fluminense", "vasco"), ("fluminense", "botafogo"), ("vasco", "botafogo"),
    ("corinthians", "palmeiras"), ("corinthians", "sao paulo"), ("corinthians", "santos"),
    ("palmeiras", "sao paulo"), ("palmeiras", "santos"), ("sao paulo", "santos"),
    ("gremio", "internacional"), ("atletico mg", "cruzeiro"), ("bahia", "vitoria"),
    ("athletico pr", "coritiba"), ("sport", "santa cruz"), ("ceara", "fortaleza"),
]


def fold(text):
    text = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in text if not unicodedata.combining(c)).lower().strip()


_SUFFIX = re.compile(r"(\s*-\s*[A-Za-z]{2,3}|\s*\([A-Za-z]{2,3}\))$")
# Same club, different spellings across files -> canonical key
_KEY_ALIASES = {
    "athletico": "athletico pr", "atletico pr": "athletico pr", "atletico paranaense": "athletico pr",
    "athletico paranaense": "athletico pr",
    "atletico": "atletico mg", "atletico mineiro": "atletico mg",
    "vasco da gama": "vasco", "sport recife": "sport", "america": "america mg",
    "sport club corinthians paulista": "corinthians", "sociedade esportiva palmeiras": "palmeiras",
    "sao paulo fc": "sao paulo", "gremio fbpa": "gremio", "cr flamengo": "flamengo",
    "santos fc": "santos", "botafogo rj": "botafogo",
}


def display_name(raw):
    raw = raw.strip()
    m = re.match(r"^(Atl[eé]tico|Athletico|Am[eé]rica)\s*-\s*([A-Z]{2})$", raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return _SUFFIX.sub("", raw).strip()


def team_key(raw):
    raw = raw.strip()
    m = re.match(r"^(Atl[eé]tico|Athletico|Am[eé]rica)\s*-\s*([A-Z]{2})$", raw)
    base = f"{fold(m.group(1))} {m.group(2).lower()}" if m else fold(_SUFFIX.sub("", raw))
    base = re.sub(r"[-_.]", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    if base == "athletico pr" or base == "atletico pr":
        return "athletico pr"
    return _KEY_ALIASES.get(base, base)


def competition_name(text):
    return COMPETITION_ALIASES.get(fold(text), text)


def parse_date(text):
    text = str(text).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


@dataclass
class Match:
    date: date
    home: str
    away: str
    home_goal: int
    away_goal: int
    competition: str
    season: int
    stage: str = ""
    source: str = ""
    extra: dict = None

    @property
    def home_key(self):
        return team_key(self.home)

    @property
    def away_key(self):
        return team_key(self.away)

    def describe(self):
        detail = f", {self.stage}" if self.stage else ""
        return (f"- {self.date.isoformat()}: {self.home} {self.home_goal}-{self.away_goal} {self.away} "
                f"({self.competition} {self.season}{detail})")


def _read(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


class SoccerData:
    def __init__(self):
        self.matches = []
        self.names = {}
        self._load_matches()
        self.players = self._load_players()

    # ---------------------------------------------------------------- loading
    def _add(self, batch):
        """Add a source's matches, skipping (competition, season) pairs a better source already covers."""
        covered = {(m.competition, m.season) for m in self.matches}
        for m in batch:
            if m.date is None or m.home_goal is None or m.away_goal is None:
                continue
            if (m.competition, m.season) in covered:
                continue
            for raw in (m.home, m.away):
                self.names.setdefault(team_key(raw), raw)
            self.matches.append(m)

    def _load_matches(self):
        def mk(row, d, h, a, hg, ag, comp, season, stage="", source="", extra=None):
            dt = parse_date(row[d])
            return Match(dt, display_name(row[h]), display_name(row[a]), _int(row[hg]), _int(row[ag]),
                         comp, _int(row[season]) if season else (dt.year if dt else None), stage, source, extra)

        self._add([mk(r, "datetime", "home_team", "away_team", "home_goal", "away_goal", BRASILEIRAO, "season",
                      f"Round {r['round']}", "Brasileirao_Matches.csv") for r in _read("Brasileirao_Matches.csv")])
        self._add([mk(r, "Data", "Equipe_mandante", "Equipe_visitante", "Gols_mandante", "Gols_visitante",
                      BRASILEIRAO, "Ano", f"Round {r['Rodada']}", "novo_campeonato_brasileiro.csv",
                      {"arena": r.get("Arena")}) for r in _read("novo_campeonato_brasileiro.csv")])

        cup = _read("Brazilian_Cup_Matches.csv")
        last_round = defaultdict(int)
        for r in cup:
            last_round[r["season"]] = max(last_round[r["season"]], _int(r["round"]) or 0)
        self._add([mk(r, "datetime", "home_team", "away_team", "home_goal", "away_goal", "Copa do Brasil",
                      "season", "final" if _int(r["round"]) == last_round[r["season"]] else f"Round {r['round']}",
                      "Brazilian_Cup_Matches.csv") for r in cup])
        self._add([mk(r, "datetime", "home_team", "away_team", "home_goal", "away_goal", "Libertadores",
                      "season", r["stage"], "Libertadores_Matches.csv") for r in _read("Libertadores_Matches.csv")])

        extended = []
        for r in _read("BR-Football-Dataset.csv"):
            extra = {k: r[k] for k in ("home_corner", "away_corner", "home_attack", "away_attack",
                                       "home_shots", "away_shots", "total_corners")}
            extended.append(mk(r, "date", "home", "away", "home_goal", "away_goal",
                               competition_name(r["tournament"]), None, "", "BR-Football-Dataset.csv", extra))
        self._add(extended)
        self.matches.sort(key=lambda m: m.date, reverse=True)

    def _load_players(self):
        players = []
        for r in _read("fifa_data.csv"):
            players.append({
                "name": r["Name"], "age": _int(r["Age"]), "nationality": r["Nationality"],
                "overall": _int(r["Overall"]) or 0, "potential": _int(r["Potential"]), "club": r["Club"],
                "position": r["Position"], "jersey": r["Jersey Number"], "height": r["Height"],
                "weight": r["Weight"], "value": r["Value"],
            })
        return players

    # ---------------------------------------------------------------- helpers
    def resolve_team(self, query):
        """Return the set of team keys a user's team name refers to."""
        q = team_key(query)
        keys = {m.home_key for m in self.matches} | {m.away_key for m in self.matches}
        if q in keys:
            return {q}
        return {k for k in keys if re.search(rf"\b{re.escape(q)}\b", k)} or {q}

    def name_of(self, key):
        return display_name(self.names.get(key, key))

    def filter_matches(self, team=None, opponent=None, competition=None, season=None, stage=None,
                       date_from=None, date_to=None, venue="all"):
        ts = self.resolve_team(team) if team else None
        os_ = self.resolve_team(opponent) if opponent else None
        comp = competition_name(competition) if competition else None
        d0, d1 = (parse_date(date_from) if date_from else None), (parse_date(date_to) if date_to else None)
        out = []
        for m in self.matches:
            if comp and m.competition != comp:
                continue
            if season and m.season != int(season):
                continue
            if stage and fold(stage) not in fold(m.stage):
                continue
            if d0 and m.date < d0 or d1 and m.date > d1:
                continue
            if ts:
                home, away = m.home_key in ts, m.away_key in ts
                if venue == "home" and not home or venue == "away" and not away or not (home or away):
                    continue
                if os_ and not ((home and m.away_key in os_) or (away and m.home_key in os_)):
                    continue
            out.append(m)
        return out

    @staticmethod
    def tally(matches, keys):
        r = dict(matches=0, wins=0, draws=0, losses=0, goals_for=0, goals_against=0)
        for m in matches:
            if m.home_key in keys:
                gf, ga = m.home_goal, m.away_goal
            elif m.away_key in keys:
                gf, ga = m.away_goal, m.home_goal
            else:
                continue
            r["matches"] += 1
            r["goals_for"] += gf
            r["goals_against"] += ga
            r["wins" if gf > ga else "losses" if gf < ga else "draws"] += 1
        return r

    def table(self, season, competition=BRASILEIRAO):
        rows = defaultdict(lambda: dict(matches=0, wins=0, draws=0, losses=0, goals_for=0, goals_against=0))
        for m in self.filter_matches(competition=competition, season=season):
            for key, gf, ga in ((m.home_key, m.home_goal, m.away_goal), (m.away_key, m.away_goal, m.home_goal)):
                r = rows[key]
                r["matches"] += 1
                r["goals_for"] += gf
                r["goals_against"] += ga
                r["wins" if gf > ga else "losses" if gf < ga else "draws"] += 1
        table = []
        for key, r in rows.items():
            r["team"] = self.name_of(key)
            r["points"] = 3 * r["wins"] + r["draws"]
            r["goal_diff"] = r["goals_for"] - r["goals_against"]
            table.append(r)
        table.sort(key=lambda r: (-r["points"], -r["wins"], -r["goal_diff"], -r["goals_for"]))
        return table

    def is_derby(self, m):
        pair = {m.home_key, m.away_key}
        return any(pair == {a, b} for a, b in DERBIES)

    def brazilian_club_names(self):
        keys = {m.home_key for m in self.matches if m.competition != "Libertadores"} | \
               {m.away_key for m in self.matches if m.competition != "Libertadores"}
        by_club = defaultdict(list)
        for p in self.players:
            if p["club"]:
                by_club[p["club"]].append(p)
        clubs = []
        for club, ps in by_club.items():
            if team_key(club) in keys and sum(p["nationality"] == "Brazil" for p in ps) > len(ps) / 2:
                clubs.append(club)
        return clubs
