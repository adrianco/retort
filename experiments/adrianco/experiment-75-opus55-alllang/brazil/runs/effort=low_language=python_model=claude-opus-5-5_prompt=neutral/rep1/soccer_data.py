"""Data loading, team-name normalization and query engine for Brazilian soccer data."""
from __future__ import annotations

import csv
import os
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import lru_cache

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kaggle")

UFS = {"ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg", "pa",
       "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc", "sp", "se", "to"}
COUNTRY_CODES = {"equ", "uru", "par", "arg", "chi", "col", "per", "bol", "ven", "mex", "ecu"}

# Names whose identity depends on the state suffix.
STATE_DEPENDENT = {"atletico", "america", "botafogo", "bragantino", "atlético"}
DEFAULT_STATE = {"america": "mg", "botafogo": "rj", "bragantino": "sp"}

# normalized base name (or base-uf) -> canonical key
ALIASES = {
    "atletico-mg": "atletico mineiro", "atletico mineiro": "atletico mineiro",
    "atletico-pr": "athletico paranaense", "athletico-pr": "athletico paranaense",
    "athletico": "athletico paranaense", "atletico paranaense": "athletico paranaense",
    "athletico paranaense": "athletico paranaense",
    "atletico-go": "atletico goianiense", "atletico goianiense": "atletico goianiense",
    "vasco da gama": "vasco", "cr vasco da gama": "vasco",
    "red bull bragantino": "bragantino-sp", "rb bragantino": "bragantino-sp",
    "sport recife": "sport", "sport club do recife": "sport",
    "america fc natal": "america-rn", "america fc (minas gerais)": "america-mg",
    "america fc minas gerais": "america-mg",
    "ceara sporting club": "ceara", "gremio": "gremio", "gremio fbpa": "gremio",
    "sport club corinthians paulista": "corinthians", "sc corinthians paulista": "corinthians",
    "se palmeiras": "palmeiras", "sao paulo fc": "sao paulo", "santos fc": "santos",
    "cr flamengo": "flamengo", "fluminense fc": "fluminense", "ec bahia": "bahia",
    "ec vitoria": "vitoria", "a.b.c.": "abc", "c.r.b.": "crb", "c.s.a.": "csa",
    "a.s.a.": "asa", "c.r.a.c.": "crac", "c. r. b.": "crb", "parana clube": "parana",
    "fortaleza ec": "fortaleza", "fortaleza esporte clube": "fortaleza",
    "cuiaba esporte clube": "cuiaba", "goias ec": "goias",
    "botafogo pb": "botafogo-pb", "botafogo sp": "botafogo-sp", "botafogo rj": "botafogo-rj",
}

DISPLAY = {
    "atletico mineiro": "Atlético Mineiro", "athletico paranaense": "Athletico Paranaense",
    "atletico goianiense": "Atlético Goianiense", "sao paulo": "São Paulo", "gremio": "Grêmio",
    "vasco": "Vasco da Gama", "bragantino-sp": "Bragantino", "america-mg": "América-MG",
    "botafogo-rj": "Botafogo", "ceara": "Ceará", "goias": "Goiás", "avai": "Avaí",
    "vitoria": "Vitória", "cuiaba": "Cuiabá", "criciuma": "Criciúma", "nautico": "Náutico",
    "parana": "Paraná", "sport": "Sport Recife",
}

RIVALRIES = {
    frozenset({"flamengo", "fluminense"}): "Fla-Flu",
    frozenset({"corinthians", "palmeiras"}): "Derby Paulista",
    frozenset({"corinthians", "sao paulo"}): "Majestoso",
    frozenset({"palmeiras", "sao paulo"}): "Choque-Rei",
    frozenset({"santos", "corinthians"}): "Clássico Alvinegro",
    frozenset({"santos", "sao paulo"}): "San-São",
    frozenset({"santos", "palmeiras"}): "Clássico da Saudade",
    frozenset({"gremio", "internacional"}): "Grenal",
    frozenset({"atletico mineiro", "cruzeiro"}): "Clássico Mineiro",
    frozenset({"flamengo", "vasco"}): "Clássico dos Milhões",
    frozenset({"flamengo", "botafogo-rj"}): "Clássico da Rivalidade",
    frozenset({"fluminense", "vasco"}): "Clássico dos Gigantes",
    frozenset({"botafogo-rj", "vasco"}): "Clássico da Amizade",
    frozenset({"bahia", "vitoria"}): "Ba-Vi",
    frozenset({"athletico paranaense", "coritiba"}): "Atletiba",
    frozenset({"ceara", "fortaleza"}): "Clássico-Rei",
    frozenset({"sport", "nautico"}): "Clássico dos Clássicos",
}

COMPETITIONS = {
    "brasileirao": "Brasileirão Série A", "serie a": "Brasileirão Série A",
    "copa do brasil": "Copa do Brasil", "libertadores": "Copa Libertadores",
    "serie b": "Brasileirão Série B", "serie c": "Brasileirão Série C",
}


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def normalize_team(name: str) -> str:
    """Return a canonical key for a team name, handling suffixes, accents and aliases."""
    s = strip_accents(name or "").lower().strip()
    s = re.sub(r"\(antigo[^)]*\)", "", s)
    s = re.sub(r"\((uru|par|arg|chi|col|per|bol|ven|mex|equ|ecu)\)", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s in ALIASES:
        return ALIASES[s]
    s = re.sub(r"^(ec|fc) |\s+(fc|ec)$", "", s)
    base, uf = s, None
    m = re.match(r"^(.*?)(?:\s*-\s*|\s+)([a-z]{2,3})$", s)
    if m and (m.group(2) in UFS or m.group(2) in COUNTRY_CODES):
        base, uf = m.group(1).strip(), m.group(2)
        if uf in COUNTRY_CODES:
            uf = None
    if base in STATE_DEPENDENT:
        key = f"{base}-{uf or DEFAULT_STATE.get(base, '')}".rstrip("-")
        return ALIASES.get(key, key)
    return ALIASES.get(base, base)


def display_team(key: str, raw: str | None = None) -> str:
    if key in DISPLAY:
        return DISPLAY[key]
    if raw:
        return raw
    return key.title()


def parse_date(s: str) -> date | None:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _int(v) -> int | None:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


@dataclass
class Match:
    date: date | None
    home: str          # canonical key
    away: str
    home_name: str     # display name
    away_name: str
    home_goals: int
    away_goals: int
    competition: str
    season: int | None
    round: str = ""
    source: str = ""
    extra: dict = field(default_factory=dict)

    def involves(self, key: str) -> bool:
        return key in (self.home, self.away)

    def result_for(self, key: str) -> str:
        gf, ga = (self.home_goals, self.away_goals) if key == self.home else (self.away_goals, self.home_goals)
        return "W" if gf > ga else "L" if gf < ga else "D"

    def format(self) -> str:
        d = self.date.isoformat() if self.date else "unknown date"
        ctx = self.competition + (f" {self.round}" if self.round else "")
        rival = RIVALRIES.get(frozenset({self.home, self.away}))
        tag = f" [{rival}]" if rival else ""
        return f"{d}: {self.home_name} {self.home_goals}-{self.away_goals} {self.away_name} ({ctx}){tag}"

    def to_dict(self) -> dict:
        return {"date": self.date.isoformat() if self.date else None, "home": self.home_name,
                "away": self.away_name, "home_goals": self.home_goals, "away_goals": self.away_goals,
                "competition": self.competition, "season": self.season, "round": self.round,
                "source": self.source, **self.extra}


def _read(fname):
    with open(os.path.join(DATA_DIR, fname), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _mk(raw_home, raw_away, hg, ag, d, comp, season, rnd, src, extra=None):
    hg, ag = _int(hg), _int(ag)
    if hg is None or ag is None:
        return None
    hk, ak = normalize_team(raw_home), normalize_team(raw_away)
    clean = lambda r: re.sub(r"\s*-\s*[A-Z]{2}$", "", r.strip())
    return Match(d, hk, ak, display_team(hk, clean(raw_home)), display_team(ak, clean(raw_away)),
                 hg, ag, comp, season if season is not None else (d.year if d else None),
                 str(rnd or ""), src, extra or {})


class SoccerDB:
    def __init__(self, data_dir: str = DATA_DIR):
        global DATA_DIR
        DATA_DIR = data_dir
        self.sources: dict[str, list[Match]] = {}
        self._load_matches()
        self.players = _read("fifa_data.csv")
        for p in self.players:
            p["_name_norm"] = strip_accents(p["Name"]).lower()
            p["_club_key"] = normalize_team(p.get("Club", ""))
            p["_overall"] = _int(p.get("Overall")) or 0
        self.matches = self._dedupe()

    # ---------------- loading ----------------
    def _load_matches(self):
        S = self.sources
        S["Brasileirao_Matches.csv"] = [m for r in _read("Brasileirao_Matches.csv") if (m := _mk(
            r["home_team"], r["away_team"], r["home_goal"], r["away_goal"], parse_date(r["datetime"]),
            "Brasileirão Série A", _int(r["season"]), f"Round {r['round']}", "Brasileirao_Matches.csv"))]
        S["Brazilian_Cup_Matches.csv"] = [m for r in _read("Brazilian_Cup_Matches.csv") if (m := _mk(
            r["home_team"], r["away_team"], r["home_goal"], r["away_goal"], parse_date(r["datetime"]),
            "Copa do Brasil", _int(r["season"]), f"Round {r['round']}", "Brazilian_Cup_Matches.csv"))]
        S["Libertadores_Matches.csv"] = [m for r in _read("Libertadores_Matches.csv") if (m := _mk(
            r["home_team"], r["away_team"], r["home_goal"], r["away_goal"], parse_date(r["datetime"]),
            "Copa Libertadores", _int(r["season"]), r["stage"], "Libertadores_Matches.csv"))]
        tour = {"Serie A": "Brasileirão Série A", "Serie B": "Brasileirão Série B",
                "Serie C": "Brasileirão Série C", "Copa do Brasil": "Copa do Brasil"}
        br = []
        for r in _read("BR-Football-Dataset.csv"):
            extra = {k: _int(r.get(k)) for k in ("home_corner", "away_corner", "home_attack",
                                                    "away_attack", "home_shots", "away_shots", "total_corners")}
            m = _mk(r["home"], r["away"], r["home_goal"], r["away_goal"], parse_date(r["date"]),
                    tour.get(r["tournament"], r["tournament"]), None, "", "BR-Football-Dataset.csv", extra)
            if m:
                br.append(m)
        S["BR-Football-Dataset.csv"] = br
        S["novo_campeonato_brasileiro.csv"] = [m for r in _read("novo_campeonato_brasileiro.csv") if (m := _mk(
            r["Equipe_mandante"], r["Equipe_visitante"], r["Gols_mandante"], r["Gols_visitante"],
            parse_date(r["Data"]), "Brasileirão Série A", _int(r["Ano"]), f"Round {r['Rodada']}",
            "novo_campeonato_brasileiro.csv", {"arena": r.get("Arena", "")}))]

    def _dedupe(self) -> list[Match]:
        seen, out = set(), []
        order = ["Brasileirao_Matches.csv", "novo_campeonato_brasileiro.csv", "Brazilian_Cup_Matches.csv",
                 "Libertadores_Matches.csv", "BR-Football-Dataset.csv"]
        for src in order:
            for m in self.sources[src]:
                keys = [(m.competition, m.date.toordinal() + d, m.home, m.away) for d in range(-3, 4)] \
                    if m.date else [(m.competition, m.season, m.round, m.home, m.away)]
                if any(k in seen for k in keys):
                    continue
                seen.update(keys)
                out.append(m)
        out.sort(key=lambda m: m.date or date.min, reverse=True)
        return out

    # ---------------- helpers ----------------
    def team_keys(self) -> set[str]:
        return {m.home for m in self.matches} | {m.away for m in self.matches}

    def resolve_team(self, name: str) -> str:
        key = normalize_team(name)
        keys = self.team_keys()
        if key in keys:
            return key
        cands = [k for k in keys if k.startswith(key) or key in k]
        if cands:
            return min(cands, key=lambda k: (len(k), k))
        return key

    def team_name(self, key: str) -> str:
        for m in self.matches:
            if m.home == key:
                return m.home_name
        return display_team(key)

    @staticmethod
    def _comp_filter(comp: str | None):
        if not comp:
            return None
        c = strip_accents(comp).lower()
        for k, v in COMPETITIONS.items():
            if k in c:
                return v
        return comp

    def find_matches(self, team: str | None = None, opponent: str | None = None, venue: str = "any",
                     competition: str | None = None, season: int | None = None,
                     date_from: str | None = None, date_to: str | None = None,
                     round_contains: str | None = None) -> list[Match]:
        t = self.resolve_team(team) if team else None
        o = self.resolve_team(opponent) if opponent else None
        comp = self._comp_filter(competition)
        df, dt = parse_date(date_from) if date_from else None, parse_date(date_to) if date_to else None
        out = []
        for m in self.matches:
            if t:
                if venue == "home" and m.home != t or venue == "away" and m.away != t or not m.involves(t):
                    continue
            if o and not m.involves(o):
                continue
            if comp and m.competition != comp:
                continue
            if season and m.season != int(season):
                continue
            if df and (not m.date or m.date < df) or dt and (not m.date or m.date > dt):
                continue
            if round_contains and not re.search(rf"\b{re.escape(round_contains.lower())}\b", m.round.lower()):
                continue
            out.append(m)
        return out

    @staticmethod
    def record(matches: list[Match], key: str) -> dict:
        r = {"matches": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0}
        for m in matches:
            if not m.involves(key):
                continue
            gf, ga = (m.home_goals, m.away_goals) if m.home == key else (m.away_goals, m.home_goals)
            r["matches"] += 1
            r["goals_for"] += gf
            r["goals_against"] += ga
            r[{"W": "wins", "D": "draws", "L": "losses"}[m.result_for(key)]] += 1
        r["points"] = r["wins"] * 3 + r["draws"]
        r["win_rate"] = round(100 * r["wins"] / r["matches"], 1) if r["matches"] else 0.0
        return r

    def team_stats(self, team: str, season: int | None = None, competition: str | None = None,
                   venue: str = "any") -> dict:
        key = self.resolve_team(team)
        ms = self.find_matches(team=key, season=season, competition=competition, venue=venue)
        return {"team": self.team_name(key), **self.record(ms, key)}

    def head_to_head(self, a: str, b: str, competition: str | None = None) -> dict:
        ka, kb = self.resolve_team(a), self.resolve_team(b)
        ms = self.find_matches(team=ka, opponent=kb, competition=competition)
        ra = self.record(ms, ka)
        return {"team_a": self.team_name(ka), "team_b": self.team_name(kb), "matches": ms,
                "a_wins": ra["wins"], "b_wins": ra["losses"], "draws": ra["draws"],
                "a_goals": ra["goals_for"], "b_goals": ra["goals_against"],
                "rivalry": RIVALRIES.get(frozenset({ka, kb}))}

    def _league_matches(self, season: int) -> list[Match]:
        for src in ("Brasileirao_Matches.csv", "novo_campeonato_brasileiro.csv"):
            ms = [m for m in self.sources[src] if m.season == season]
            if ms:
                return ms
        return [m for m in self.matches if m.season == season and m.competition == "Brasileirão Série A"]

    def standings(self, season: int) -> list[dict]:
        ms = self._league_matches(int(season))
        keys = {m.home for m in ms} | {m.away for m in ms}
        table = []
        for k in keys:
            r = self.record(ms, k)
            r["team"] = self.team_name(k)
            r["goal_diff"] = r["goals_for"] - r["goals_against"]
            table.append(r)
        table.sort(key=lambda r: (-r["points"], -r["wins"], -r["goal_diff"], -r["goals_for"], r["team"]))
        for i, r in enumerate(table, 1):
            r["position"] = i
        return table

    def rankings(self, metric: str = "home_win_rate", competition: str | None = "Brasileirão",
                 season: int | None = None, min_matches: int = 10, limit: int = 10) -> list[dict]:
        venue = {"home_win_rate": "home", "away_win_rate": "away"}.get(metric, "any")
        ms = self.find_matches(competition=competition, season=season)
        per = defaultdict(list)
        for m in ms:
            if venue in ("any", "home"):
                per[m.home].append(m)
            if venue in ("any", "away"):
                per[m.away].append(m)
        rows = []
        for k, lst in per.items():
            r = self.record(lst, k)
            if r["matches"] < min_matches:
                continue
            r["team"] = self.team_name(k)
            rows.append(r)
        sort_key = {"goals_for": "goals_for", "goals_against": "goals_against", "points": "points",
                    "wins": "wins"}.get(metric, "win_rate")
        rows.sort(key=lambda r: (-r[sort_key], -r["matches"]))
        return rows[:limit]

    def aggregate(self, competition: str | None = None, season: int | None = None) -> dict:
        ms = self.find_matches(competition=competition, season=season)
        n = len(ms)
        if not n:
            return {"matches": 0}
        goals = sum(m.home_goals + m.away_goals for m in ms)
        hw = sum(m.home_goals > m.away_goals for m in ms)
        aw = sum(m.home_goals < m.away_goals for m in ms)
        return {"matches": n, "total_goals": goals, "avg_goals": round(goals / n, 2),
                "home_win_rate": round(100 * hw / n, 1), "away_win_rate": round(100 * aw / n, 1),
                "draw_rate": round(100 * (n - hw - aw) / n, 1)}

    def biggest_wins(self, competition: str | None = None, season: int | None = None,
                     team: str | None = None, limit: int = 10) -> list[Match]:
        ms = self.find_matches(team=team, competition=competition, season=season)
        return sorted(ms, key=lambda m: (-abs(m.home_goals - m.away_goals),
                                         -(m.home_goals + m.away_goals)))[:limit]

    def competitions_for(self, team: str) -> dict:
        key = self.resolve_team(team)
        out = defaultdict(set)
        for m in self.matches:
            if m.involves(key):
                out[m.competition].add(m.season)
        return {c: sorted(s for s in v if s) for c, v in out.items()}

    def derbies(self, season: int | None = None, competition: str | None = None) -> list[Match]:
        return [m for m in self.find_matches(season=season, competition=competition)
                if frozenset({m.home, m.away}) in RIVALRIES]

    # ---------------- players ----------------
    def search_players(self, name: str | None = None, nationality: str | None = None,
                       club: str | None = None, position: str | None = None,
                       min_overall: int | None = None, limit: int = 20) -> list[dict]:
        n = strip_accents(name).lower() if name else None
        nat = strip_accents(nationality).lower() if nationality else None
        ck = normalize_team(club) if club else None
        cl = strip_accents(club).lower() if club else None
        pos = {p.strip().upper() for p in position.split(",")} if position else None
        if position and position.lower() in ("forward", "forwards", "attacker", "striker"):
            pos = {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"}
        elif position and position.lower() in ("goalkeeper", "keeper"):
            pos = {"GK"}
        elif position and position.lower() in ("defender", "defenders"):
            pos = {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"}
        elif position and position.lower() in ("midfielder", "midfielders"):
            pos = {"CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"}
        out = []
        for p in self.players:
            if n and n not in p["_name_norm"]:
                continue
            if nat and strip_accents(p["Nationality"]).lower() != nat:
                continue
            if club and not (p["_club_key"] == ck or cl in strip_accents(p["Club"]).lower()):
                continue
            if pos and p["Position"].upper() not in pos:
                continue
            if min_overall and p["_overall"] < min_overall:
                continue
            out.append(p)
        out.sort(key=lambda p: -p["_overall"])
        return [self.player_summary(p) for p in out[:limit]]

    @staticmethod
    def player_summary(p: dict) -> dict:
        keys = ["Name", "Age", "Nationality", "Overall", "Potential", "Club", "Position",
                "Jersey Number", "Height", "Weight", "Value", "Preferred Foot",
                "Crossing", "Finishing", "Dribbling", "ShortPassing", "SprintSpeed", "Reactions"]
        return {k: p.get(k, "") for k in keys}

    def brazilian_club_players(self) -> list[dict]:
        """Group Brazilian players at clubs that appear in Brazilian match data."""
        br_keys = {m.home for s in ("Brasileirao_Matches.csv", "novo_campeonato_brasileiro.csv",
                                    "Brazilian_Cup_Matches.csv") for m in self.sources[s]}
        groups = defaultdict(list)
        for p in self.players:
            if p["Nationality"] == "Brazil" and p["_club_key"] in br_keys:
                groups[p["Club"]].append(p["_overall"])
        rows = [{"club": c, "players": len(v), "avg_rating": round(sum(v) / len(v), 1)}
                for c, v in groups.items()]
        return sorted(rows, key=lambda r: (-r["players"], -r["avg_rating"]))

    def club_profile(self, team: str) -> dict:
        """Cross-file query: players from FIFA data plus match record."""
        key = self.resolve_team(team)
        players = [self.player_summary(p) for p in sorted(self.players, key=lambda p: -p["_overall"])
                   if p["_club_key"] == key]
        return {"team": self.team_name(key), "record": self.record(self.find_matches(team=key), key),
                "competitions": self.competitions_for(key), "players": players}


@lru_cache(maxsize=1)
def get_db() -> SoccerDB:
    return SoccerDB()
