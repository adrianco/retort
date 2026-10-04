"""Brazilian soccer knowledge base: loads the Kaggle CSVs and answers queries.

Pure standard library (csv) so it runs without extra dependencies.
"""
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

BR_STATES = {
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg", "pa",
    "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc", "sp", "se", "to",
}

# Bases that refer to different clubs depending on state; default state if missing.
AMBIGUOUS = {"atletico": "mg", "botafogo": "rj", "america": "mg", "nacional": None}

ALIASES = {
    "athletico": "atletico",
    "athletico paranaense": "atletico-pr",
    "atletico paranaense": "atletico-pr",
    "atletico mineiro": "atletico-mg",
    "atletico goianiense": "atletico-go",
    "vasco da gama": "vasco",
    "ec bahia": "bahia",
    "esporte clube bahia": "bahia",
    "fortaleza fc": "fortaleza",
    "fortaleza esporte clube": "fortaleza",
    "sport recife": "sport",
    "sport club do recife": "sport",
    "nautico capibaribe": "nautico",
    "red bull bragantino": "bragantino",
    "rb bragantino": "bragantino",
    "clube do remo": "remo",
    "ceara sporting club": "ceara",
    "sport club corinthians paulista": "corinthians",
    "sociedade esportiva palmeiras": "palmeiras",
    "sao paulo fc": "sao paulo",
    "sao paulo futebol clube": "sao paulo",
    "clube de regatas do flamengo": "flamengo",
    "fluminense fc": "fluminense",
    "gremio fbpa": "gremio",
    "santos fc": "santos",
    "cruzeiro ec": "cruzeiro",
    "sc internacional": "internacional",
    "csa": "csa",
    "fla": "flamengo",
    "flu": "fluminense",
    "galo": "atletico-mg",
    "timao": "corinthians",
    "verdao": "palmeiras",
    "tricolor paulista": "sao paulo",
}

PRETTY = {
    "sao paulo": "São Paulo", "gremio": "Grêmio", "goias": "Goiás", "avai": "Avaí",
    "vitoria": "Vitória", "ceara": "Ceará", "criciuma": "Criciúma", "nautico": "Náutico",
    "parana": "Paraná", "cuiaba": "Cuiabá", "atletico-mg": "Atlético-MG",
    "atletico-pr": "Athletico-PR", "atletico-go": "Atlético-GO", "botafogo-rj": "Botafogo",
    "botafogo-sp": "Botafogo-SP", "america-mg": "América-MG", "america-rn": "América-RN",
    "sao caetano": "São Caetano", "santo andre": "Santo André", "csa": "CSA",
    "gremio prudente": "Grêmio Prudente", "vasco": "Vasco da Gama",
}

DERBIES = {
    frozenset({"flamengo", "fluminense"}): "Fla-Flu",
    frozenset({"corinthians", "palmeiras"}): "Derby Paulista",
    frozenset({"sao paulo", "corinthians"}): "Majestoso",
    frozenset({"sao paulo", "palmeiras"}): "Choque-Rei",
    frozenset({"santos", "corinthians"}): "Clássico Alvinegro",
    frozenset({"santos", "palmeiras"}): "Clássico da Saudade",
    frozenset({"sao paulo", "santos"}): "San-São",
    frozenset({"gremio", "internacional"}): "Grenal",
    frozenset({"atletico-mg", "cruzeiro"}): "Clássico Mineiro",
    frozenset({"flamengo", "vasco"}): "Clássico dos Milhões",
    frozenset({"botafogo-rj", "flamengo"}): "Clássico da Rivalidade",
    frozenset({"fluminense", "vasco"}): "Clássico dos Gigantes",
    frozenset({"botafogo-rj", "fluminense"}): "Clássico Vovô",
    frozenset({"botafogo-rj", "vasco"}): "Clássico da Amizade",
    frozenset({"bahia", "vitoria"}): "Ba-Vi",
    frozenset({"atletico-pr", "coritiba"}): "Atletiba",
    frozenset({"sport", "santa cruz"}): "Clássico das Multidões",
    frozenset({"ceara", "fortaleza"}): "Clássico-Rei",
}

COMPETITIONS = {
    "brasileirao": "Brasileirão", "serie a": "Brasileirão", "brasileiro": "Brasileirão",
    "campeonato brasileiro": "Brasileirão", "serie b": "Serie B", "serie c": "Serie C",
    "copa do brasil": "Copa do Brasil", "brazilian cup": "Copa do Brasil", "cup": "Copa do Brasil",
    "libertadores": "Libertadores", "copa libertadores": "Libertadores",
}

_FILLER = re.compile(
    r"\b(futebol clube|football club|esporte clube|sport club|sporting club|"
    r"esporte c|fc|ec|sc|ac|clube)\b"
)


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def normalize_team(name: str) -> str:
    """Return a canonical key for a team name, handling suffixes/accents/aliases."""
    if not name:
        return ""
    s = strip_accents(name).lower().strip()
    s = re.sub(r"\s+", " ", s)
    if s in ALIASES:
        return ALIASES[s]
    state = None
    m = re.search(r"\(([^)]*)\)", s)
    if m:
        s = (s[: m.start()] + s[m.end():]).strip()
    m = re.match(r"^(.*?)\s*-\s*([a-z]{2,3})$", s) or re.match(r"^(.*?)\s+([a-z]{2})$", s)
    if m and m.group(2) in BR_STATES:
        s, state = m.group(1).strip(), m.group(2)
    elif m and "-" in s:  # foreign suffix like Barcelona-EQU: keep as is
        pass
    if s in ALIASES:
        s = ALIASES[s]
    if "-" in s and s.split("-")[-1] in BR_STATES:
        return s
    stripped = _FILLER.sub("", s).strip()
    stripped = re.sub(r"\s+", " ", stripped)
    if stripped and stripped != s:
        s = ALIASES.get(stripped, stripped)
        if "-" in s and s.split("-")[-1] in BR_STATES:
            return s
    if s in AMBIGUOUS:
        st = state or AMBIGUOUS[s]
        return f"{s}-{st}" if st else s
    return s


def display_team(key: str) -> str:
    if key in PRETTY:
        return PRETTY[key]
    base, _, state = key.rpartition("-")
    if state not in BR_STATES:
        base, state = key, ""
    words = " ".join(w if w in ("de", "da", "do", "dos") else w.capitalize() for w in base.split())
    return f"{words}-{state.upper()}" if state else words


def parse_date(s: str) -> date | None:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _int(v) -> int | None:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def normalize_competition(c: str | None) -> str | None:
    if not c:
        return None
    k = strip_accents(c).lower().strip()
    return COMPETITIONS.get(k, c)


@dataclass
class Match:
    date: date | None
    home: str
    away: str
    home_goal: int
    away_goal: int
    competition: str
    season: int | None
    round: str = ""
    source: str = ""
    home_raw: str = ""
    away_raw: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def total_goals(self) -> int:
        return self.home_goal + self.away_goal

    def involves(self, key: str) -> bool:
        return key in (self.home, self.away)

    def result_for(self, key: str) -> str:
        gf, ga = (self.home_goal, self.away_goal) if self.home == key else (self.away_goal, self.home_goal)
        return "W" if gf > ga else "L" if gf < ga else "D"

    def format(self) -> str:
        d = self.date.isoformat() if self.date else "????-??-??"
        detail = self.competition
        if self.round:
            detail += f" {'Round ' if self.round.isdigit() else ''}{self.round}"
        elif self.season and self.competition == "Brasileirão":
            detail += f" {self.season}"
        return (f"{d}: {display_team(self.home)} {self.home_goal}-{self.away_goal} "
                f"{display_team(self.away)} ({detail})")

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat() if self.date else None,
            "home_team": display_team(self.home), "away_team": display_team(self.away),
            "home_goal": self.home_goal, "away_goal": self.away_goal,
            "competition": self.competition, "season": self.season, "round": self.round,
            "source": self.source, **self.extra,
        }


def _open(name):
    return open(os.path.join(DATA_DIR, name), encoding="utf-8-sig", newline="")


def load_matches(data_dir: str | None = None) -> dict[str, list[Match]]:
    """Load every match file; returns {source_filename: [Match, ...]}."""
    global DATA_DIR
    if data_dir:
        DATA_DIR = data_dir
    out: dict[str, list[Match]] = {}

    def add(src, d, h, a, hg, ag, comp, season, rnd="", extra=None):
        hg, ag = _int(hg), _int(ag)
        if hg is None or ag is None or not h or not a:
            return
        out.setdefault(src, []).append(Match(
            d, normalize_team(h), normalize_team(a), hg, ag, comp,
            _int(season) or (d.year if d else None), str(rnd or "").strip(), src, h, a, extra or {}))

    src = "Brasileirao_Matches.csv"
    with _open(src) as f:
        for r in csv.DictReader(f):
            add(src, parse_date(r["datetime"]), r["home_team"], r["away_team"], r["home_goal"],
                r["away_goal"], "Brasileirão", r["season"], r["round"])
    src = "Brazilian_Cup_Matches.csv"
    with _open(src) as f:
        for r in csv.DictReader(f):
            add(src, parse_date(r["datetime"]), r["home_team"], r["away_team"], r["home_goal"],
                r["away_goal"], "Copa do Brasil", r["season"], r["round"])
    src = "Libertadores_Matches.csv"
    with _open(src) as f:
        for r in csv.DictReader(f):
            add(src, parse_date(r["datetime"]), r["home_team"], r["away_team"], r["home_goal"],
                r["away_goal"], "Libertadores", r["season"], r["stage"])
    src = "BR-Football-Dataset.csv"
    tmap = {"Serie A": "Brasileirão", "Serie B": "Serie B", "Serie C": "Serie C",
            "Copa do Brasil": "Copa do Brasil"}
    with _open(src) as f:
        for r in csv.DictReader(f):
            d = parse_date(r["date"])
            extra = {k: _int(r.get(k)) for k in ("home_corner", "away_corner", "home_attack",
                                                 "away_attack", "home_shots", "away_shots")}
            comp = tmap.get(r["tournament"], r["tournament"])
            season = d.year if d else None
            if d and comp != "Copa do Brasil" and d.month <= 2:
                season -= 1  # league seasons that run into Jan/Feb (e.g. 2020 season)
            add(src, d, r["home"], r["away"], r["home_goal"], r["away_goal"], comp, season, "", extra)
    src = "novo_campeonato_brasileiro.csv"
    with _open(src) as f:
        for r in csv.DictReader(f):
            add(src, parse_date(r["Data"]), r["Equipe_mandante"], r["Equipe_visitante"],
                r["Gols_mandante"], r["Gols_visitante"], "Brasileirão", r["Ano"], r["Rodada"],
                {"arena": r.get("Arena", "")})
    return out


def load_players() -> list[dict]:
    players = []
    with _open("fifa_data.csv") as f:
        for r in csv.DictReader(f):
            r = {k.strip(): v for k, v in r.items() if k and k.strip()}
            for k in ("Age", "Overall", "Potential", "ID"):
                r[k] = _int(r.get(k))
            r["_name_key"] = strip_accents(r.get("Name", "")).lower()
            r["_club_key"] = normalize_team(r.get("Club", "")) if r.get("Club") else ""
            players.append(r)
    return players


FORWARD_POS = {"ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"}
MID_POS = {"CM", "CAM", "CDM", "LM", "RM", "LCM", "RCM", "LAM", "RAM", "LDM", "RDM"}
DEF_POS = {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"}
POSITION_GROUPS = {"forward": FORWARD_POS, "forwards": FORWARD_POS, "attacker": FORWARD_POS,
                   "midfielder": MID_POS, "midfielders": MID_POS, "defender": DEF_POS,
                   "defenders": DEF_POS, "goalkeeper": {"GK"}, "goalkeepers": {"GK"}}


LEAGUES = {"Brasileirão", "Serie B", "Serie C"}


class SoccerDB:
    def __init__(self, data_dir: str | None = None):
        self.by_source = load_matches(data_dir)
        self.players = load_players()
        self.all_matches = [m for ms in self.by_source.values() for m in ms]
        self.matches = self._dedupe(self.all_matches)
        self.brazilian_teams = {t for m in self.matches if m.competition != "Libertadores"
                                for t in (m.home, m.away)}

    @staticmethod
    def _dedupe(matches):
        # Prefer sources with richer data; overlapping files describe the same match.
        prio = {"BR-Football-Dataset.csv": 0, "Brasileirao_Matches.csv": 1,
                "novo_campeonato_brasileiro.csv": 2, "Brazilian_Cup_Matches.csv": 1,
                "Libertadores_Matches.csv": 1}
        best = {}
        cup_index = defaultdict(list)
        for m in sorted(matches, key=lambda m: prio.get(m.source, 9)):
            if m.competition in LEAGUES:
                k = (m.competition, m.season, m.home, m.away)
            else:
                k = (m.competition, m.home, m.away, m.date)
                for other in cup_index[(m.competition, m.home, m.away)]:
                    if m.date and other.date and abs((m.date - other.date).days) <= 3:
                        k = (m.competition, m.home, m.away, other.date)
                        break
            if k not in best:
                best[k] = m
                if m.competition not in LEAGUES:
                    cup_index[(m.competition, m.home, m.away)].append(m)
            elif not best[k].round and m.round:
                best[k].round = m.round
        return sorted(best.values(), key=lambda m: (m.date or date.min))

    # ---------------------------------------------------------------- matches
    def resolve_team(self, name: str) -> str:
        key = normalize_team(name)
        known = {t for m in self.matches for t in (m.home, m.away)}
        if key in known:
            return key
        # e.g. "Botafogo" -> botafogo-rj handled; try prefix matches like "Atletico" + state
        cands = [t for t in known if t.startswith(key)]
        return min(cands, key=len) if cands else key

    def find_matches(self, team=None, opponent=None, venue="any", competition=None,
                     season=None, date_from=None, date_to=None, stage=None,
                     dedupe=True, limit=None) -> list[Match]:
        pool = self.matches if dedupe else self.all_matches
        t = self.resolve_team(team) if team else None
        o = self.resolve_team(opponent) if opponent else None
        comp = normalize_competition(competition)
        df = parse_date(date_from) if isinstance(date_from, str) else date_from
        dt = parse_date(date_to) if isinstance(date_to, str) else date_to
        stage_k = strip_accents(stage).lower() if stage else None
        res = []
        for m in pool:
            if t:
                if venue == "home" and m.home != t:
                    continue
                if venue == "away" and m.away != t:
                    continue
                if not m.involves(t):
                    continue
            if o and not m.involves(o):
                continue
            if comp and m.competition != comp:
                continue
            if season and m.season != int(season):
                continue
            if df and (not m.date or m.date < df):
                continue
            if dt and (not m.date or m.date > dt):
                continue
            if stage_k and strip_accents(m.round).lower() != stage_k:
                continue
            res.append(m)
        res.sort(key=lambda m: m.date or date.min, reverse=True)
        return res[:limit] if limit else res

    def cup_finals(self, competition="Copa do Brasil") -> list[Match]:
        comp = normalize_competition(competition)
        ms = [m for m in self.matches if m.competition == comp]
        if comp == "Libertadores":
            return sorted([m for m in ms if m.round == "final"], key=lambda m: m.date or date.min)
        finals = []
        by_season = defaultdict(list)
        for m in ms:
            if m.round.isdigit():
                by_season[m.season].append(m)
        for s, lst in sorted(by_season.items()):
            mx = max(int(m.round) for m in lst)
            finals += sorted([m for m in lst if int(m.round) == mx], key=lambda m: m.date)
        return finals

    def derbies(self, season=None, team=None) -> list[tuple[str, Match]]:
        out = []
        for m in self.find_matches(team=team, season=season):
            name = DERBIES.get(frozenset({m.home, m.away}))
            if name:
                out.append((name, m))
        return out

    # ------------------------------------------------------------ team stats
    @staticmethod
    def record(matches, key, venue="any") -> dict:
        r = {"matches": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0}
        for m in matches:
            if venue == "home" and m.home != key or venue == "away" and m.away != key:
                continue
            if not m.involves(key):
                continue
            home = m.home == key
            gf, ga = (m.home_goal, m.away_goal) if home else (m.away_goal, m.home_goal)
            r["matches"] += 1
            r["goals_for"] += gf
            r["goals_against"] += ga
            r[{"W": "wins", "D": "draws", "L": "losses"}[m.result_for(key)]] += 1
        r["points"] = r["wins"] * 3 + r["draws"]
        r["goal_difference"] = r["goals_for"] - r["goals_against"]
        r["win_rate"] = round(100 * r["wins"] / r["matches"], 1) if r["matches"] else 0.0
        return r

    def team_record(self, team, season=None, competition=None, venue="any") -> dict:
        key = self.resolve_team(team)
        ms = self.find_matches(team=key, season=season, competition=competition, venue=venue)
        r = self.record(ms, key, venue)
        r["team"] = display_team(key)
        return r

    def head_to_head(self, team_a, team_b, competition=None, season=None) -> dict:
        a, b = self.resolve_team(team_a), self.resolve_team(team_b)
        ms = self.find_matches(team=a, opponent=b, competition=competition, season=season)
        ra = self.record(ms, a)
        return {"team_a": display_team(a), "team_b": display_team(b), "matches": ms,
                "a_wins": ra["wins"], "b_wins": ra["losses"], "draws": ra["draws"],
                "a_goals": ra["goals_for"], "b_goals": ra["goals_against"]}

    def competitions_for_team(self, team) -> dict[str, int]:
        key = self.resolve_team(team)
        out = defaultdict(int)
        for m in self.matches:
            if m.involves(key):
                out[m.competition] += 1
        return dict(out)

    # ------------------------------------------------------------- standings
    def standings(self, season, competition="Brasileirão") -> list[dict]:
        comp = normalize_competition(competition)
        ms = [m for m in self.matches if m.season == int(season) and m.competition == comp]
        if comp == "Brasileirão":
            # Prefer the single most complete source for a season to avoid date-mismatch dupes.
            per_src = defaultdict(list)
            for m in self.all_matches:
                if m.season == int(season) and m.competition == comp:
                    per_src[m.source].append(m)
            if per_src:
                order = ["Brasileirao_Matches.csv", "novo_campeonato_brasileiro.csv",
                         "BR-Football-Dataset.csv"]
                ms = max(per_src.values(), key=lambda l: (min(len(l), 380),
                         -order.index(l[0].source)))
        teams = {t for m in ms for t in (m.home, m.away)}
        table = []
        for t in teams:
            r = self.record(ms, t)
            r["team"] = display_team(t)
            r["key"] = t
            table.append(r)
        table.sort(key=lambda r: (-r["points"], -r["wins"], -r["goal_difference"], -r["goals_for"],
                                  r["team"]))
        for i, r in enumerate(table, 1):
            r["position"] = i
        return table

    # ------------------------------------------------------------ statistics
    def stats(self, competition=None, season=None, team=None) -> dict:
        ms = self.find_matches(team=team, competition=competition, season=season)
        n = len(ms)
        if not n:
            return {"matches": 0}
        hw = sum(m.home_goal > m.away_goal for m in ms)
        aw = sum(m.home_goal < m.away_goal for m in ms)
        goals = sum(m.total_goals for m in ms)
        return {"matches": n, "total_goals": goals, "avg_goals": round(goals / n, 2),
                "home_win_rate": round(100 * hw / n, 1), "away_win_rate": round(100 * aw / n, 1),
                "draw_rate": round(100 * (n - hw - aw) / n, 1)}

    def biggest_wins(self, competition=None, season=None, team=None, limit=10) -> list[Match]:
        ms = self.find_matches(team=team, competition=competition, season=season)
        return sorted(ms, key=lambda m: (-abs(m.home_goal - m.away_goal), -m.total_goals,
                                         m.date or date.min))[:limit]

    def best_records(self, venue="home", competition="Brasileirão", season=None,
                     min_matches=None, limit=10) -> list[dict]:
        ms = self.find_matches(competition=competition, season=season)
        teams = {t for m in ms for t in (m.home, m.away)}
        if min_matches is None:
            min_matches = 10 if season else 50
        rows = []
        for t in teams:
            r = self.record(ms, t, venue)
            if r["matches"] >= min_matches:
                r["team"] = display_team(t)
                rows.append(r)
        rows.sort(key=lambda r: (-r["win_rate"], -r["points"]))
        return rows[:limit]

    def top_scoring_teams(self, season=None, competition="Brasileirão", limit=10) -> list[dict]:
        return sorted(self.standings(season, competition) if season else
                      self.best_records("any", competition, None, 1, 10 ** 6),
                      key=lambda r: -r["goals_for"])[:limit]

    # --------------------------------------------------------------- players
    def search_players(self, name=None, nationality=None, club=None, position=None,
                       min_overall=None, brazilian_clubs_only=False, limit=20) -> list[dict]:
        nk = strip_accents(name).lower() if name else None
        nat = strip_accents(nationality).lower() if nationality else None
        if nat in ("brazilian", "brasil", "brasileiro"):
            nat = "brazil"
        ck = normalize_team(club) if club else None
        ck_raw = strip_accents(club).lower() if club else None
        pos = None
        if position:
            pos = POSITION_GROUPS.get(position.lower(), {position.upper()})
        res = []
        for p in self.players:
            if nk and not all(tok in p["_name_key"] for tok in nk.split()):
                continue
            if nat and strip_accents(p.get("Nationality", "")).lower() != nat:
                continue
            if ck and p["_club_key"] != ck and ck_raw not in strip_accents(p.get("Club", "")).lower():
                continue
            if pos and p.get("Position") not in pos:
                continue
            if min_overall and (p["Overall"] or 0) < min_overall:
                continue
            if brazilian_clubs_only and p["_club_key"] not in self.brazilian_teams:
                continue
            res.append(p)
        # exact club key matches first, then rating
        res.sort(key=lambda p: (ck is not None and p["_club_key"] != ck, -(p["Overall"] or 0)))
        return res[:limit] if limit else res

    def brazilian_club_summary(self) -> list[dict]:
        agg = defaultdict(list)
        for p in self.players:
            if p["_club_key"] in self.brazilian_teams and (p.get("Nationality") == "Brazil"):
                agg[p["Club"]].append(p["Overall"] or 0)
        rows = [{"club": c, "players": len(v), "avg_rating": round(sum(v) / len(v), 1)}
                for c, v in agg.items()]
        return sorted(rows, key=lambda r: (-r["players"], -r["avg_rating"]))

    def team_profile(self, team) -> dict:
        """Cross-file: match record + FIFA squad for a club."""
        key = self.resolve_team(team)
        squad = [p for p in self.players if p["_club_key"] == key]
        return {"team": display_team(key), "record": self.team_record(key),
                "competitions": self.competitions_for_team(key),
                "squad": sorted(squad, key=lambda p: -(p["Overall"] or 0))}


@lru_cache(maxsize=1)
def get_db() -> SoccerDB:
    return SoccerDB()


def format_player(p: dict) -> str:
    return (f"{p['Name']} - Overall: {p['Overall']}, Potential: {p['Potential']}, "
            f"Position: {p.get('Position') or '?'}, Age: {p['Age']}, "
            f"Nationality: {p.get('Nationality')}, Club: {p.get('Club') or 'Free agent'}")
