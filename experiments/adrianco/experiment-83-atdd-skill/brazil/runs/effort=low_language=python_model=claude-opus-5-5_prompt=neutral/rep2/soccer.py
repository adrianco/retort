"""Brazilian soccer knowledge base: loads the Kaggle CSVs and answers queries.

Standard library only. All query functions return formatted text.
"""
from __future__ import annotations

import csv
import os
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import lru_cache

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kaggle")

BR_STATES = {
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg", "pa",
    "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc", "sp", "se", "to",
}
# Bases shared by several clubs: keep the state unless it is the "default" club.
AMBIGUOUS_DEFAULT_STATE = {
    "atletico": None, "america": "mg", "botafogo": "rj", "fluminense": "rj",
    "santos": "sp", "santa cruz": "pe", "juventude": "rs", "vitoria": "ba",
    "guarani": "sp", "operario": None, "nacional": None, "sao jose": None,
    "bragantino": "sp", "internacional": "rs", "gremio": "rs", "portuguesa": "sp",
    "boavista": "rj", "ypiranga": None, "remo": "pa", "tupi": "mg", "caxias": "rs",
}
ALIASES = {
    "athletico paranaense": "atletico-pr", "atletico paranaense": "atletico-pr",
    "athletico": "atletico-pr", "athletico-pr": "atletico-pr",
    "atletico mineiro": "atletico-mg", "atletico goianiense": "atletico-go",
    "vasco da gama": "vasco", "red bull bragantino": "bragantino",
    "sport recife": "sport", "nautico capibaribe": "nautico",
    "portuguesa desportos": "portuguesa", "fortaleza ec": "fortaleza",
    "ec bahia": "bahia", "ec vitoria": "vitoria", "ec juventude": "juventude",
    "santa cruz fc": "santa cruz", "america fc natal": "america-rn",
    "sport club corinthians paulista": "corinthians", "sc corinthians": "corinthians",
    "se palmeiras": "palmeiras", "sao paulo fc": "sao paulo", "spfc": "sao paulo",
    "cr flamengo": "flamengo", "clube de regatas do flamengo": "flamengo",
    "fluminense fc": "fluminense", "gremio fbpa": "gremio",
    "sc internacional": "internacional", "santos fc": "santos",
    "cruzeiro ec": "cruzeiro", "botafogo fr": "botafogo", "galo": "atletico-mg",
    "furacao": "atletico-pr", "verdao": "palmeiras", "timao": "corinthians",
    "mengao": "flamengo", "tricolor": "sao paulo", "peixe": "santos",
    "clube do remo": "remo", "goias ec": "goias", "ceara sc": "ceara",
    "coritiba fc": "coritiba", "chapecoense af": "chapecoense",
}

COMPETITIONS = {
    "serie a": "Brasileirão Serie A", "brasileirao": "Brasileirão Serie A",
    "brasileiro": "Brasileirão Serie A", "campeonato brasileiro": "Brasileirão Serie A",
    "league": "Brasileirão Serie A",
    "serie b": "Brasileirão Serie B", "serie c": "Brasileirão Serie C",
    "copa do brasil": "Copa do Brasil", "brazilian cup": "Copa do Brasil", "cup": "Copa do Brasil",
    "libertadores": "Copa Libertadores", "copa libertadores": "Copa Libertadores",
}

DERBIES = [
    ("flamengo", "fluminense", "Fla-Flu"), ("flamengo", "vasco", "Clássico dos Milhões"),
    ("flamengo", "botafogo", "Clássico da Rivalidade"), ("fluminense", "vasco", "Clássico dos Gigantes"),
    ("botafogo", "fluminense", "Clássico Vovô"), ("botafogo", "vasco", "Clássico da Amizade"),
    ("corinthians", "palmeiras", "Derby Paulista"), ("corinthians", "sao paulo", "Majestoso"),
    ("palmeiras", "sao paulo", "Choque-Rei"), ("palmeiras", "santos", "Clássico da Saudade"),
    ("corinthians", "santos", "Clássico Alvinegro"), ("santos", "sao paulo", "San-São"),
    ("gremio", "internacional", "Grenal"), ("atletico-mg", "cruzeiro", "Clássico Mineiro"),
    ("atletico-pr", "coritiba", "Atletiba"), ("bahia", "vitoria", "Ba-Vi"),
    ("ceara", "fortaleza", "Clássico-Rei"), ("nautico", "sport", "Clássico dos Clássicos"),
    ("santa cruz", "sport", "Clássico das Multidões"), ("avai", "figueirense", "Clássico da Ilha"),
    ("goias", "vila nova", "Derby Goiano"),
]
DERBY_LOOKUP = {frozenset((a, b)): n for a, b, n in DERBIES}


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


@lru_cache(maxsize=None)
def normalize_team(name: str) -> str:
    """Return a canonical key for a team name across all dataset variants."""
    if not name:
        return ""
    s = strip_accents(name).lower().strip()
    s = re.sub(r"\(.*?\)", " ", s)
    s = s.replace(".", "").replace("'", "")
    s = re.sub(r"\s+", " ", s).strip()
    if s in ALIASES:
        return ALIASES[s]
    state = None
    m = re.match(r"^(.*?)(?:\s*-\s*|\s+)([a-z]{2})$", s)
    if m and m.group(2) in BR_STATES and m.group(1):
        s, state = m.group(1).strip(), m.group(2)
    s = re.sub(r"\s+(fc|ec|sc|ac|futebol clube|esporte clube)$", "", s).strip()
    s = ALIASES.get(s, s)
    if "-" in s:  # alias already carries a state
        return s
    if s in AMBIGUOUS_DEFAULT_STATE and state and state != AMBIGUOUS_DEFAULT_STATE[s]:
        return f"{s}-{state}"
    return s


def normalize_competition(name: str | None) -> str | None:
    if not name:
        return None
    s = strip_accents(name).lower().strip()
    if s in COMPETITIONS:
        return COMPETITIONS[s]
    for k, v in COMPETITIONS.items():
        if k in s:
            return v
    return name


def parse_date(s: str) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M", "%m/%d/%Y"):
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
    home: str
    away: str
    home_goal: int
    away_goal: int
    competition: str
    season: int | None
    stage: str = ""
    source: str = ""
    venue: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def home_key(self):
        return normalize_team(self.home)

    @property
    def away_key(self):
        return normalize_team(self.away)

    def result_for(self, key: str) -> str:
        gf, ga = (self.home_goal, self.away_goal) if self.home_key == key else (self.away_goal, self.home_goal)
        return "W" if gf > ga else "L" if gf < ga else "D"

    def describe(self) -> str:
        d = self.date.isoformat() if self.date else "????-??-??"
        stage = f" {self.stage}" if self.stage else ""
        s = f"{d}: {display_name(self.home)} {self.home_goal}-{self.away_goal} {display_name(self.away)} ({self.competition}{stage})"
        if self.venue:
            s += f" @ {self.venue}"
        if self.extra:
            s += " [" + ", ".join(f"{k}: {v}" for k, v in self.extra.items()) + "]"
        return s


def display_name(raw: str) -> str:
    key = normalize_team(raw)
    return KB.get().names.get(key, raw) if KB._inst else raw


class KB:
    _inst: "KB | None" = None

    @classmethod
    def get(cls) -> "KB":
        if cls._inst is None:
            cls._inst = KB(DATA_DIR)
        return cls._inst

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.sources: dict[str, list[Match]] = {}
        self.players: list[dict] = []
        self.names: dict[str, str] = {}
        self._canonical = None
        self._load()

    def _read(self, fname):
        with open(os.path.join(self.data_dir, fname), encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def _load(self):
        name_votes: dict[str, Counter] = defaultdict(Counter)

        def pretty(raw):
            r = raw.strip()
            r = re.sub(r"\s*\(.*?\)", "", r)
            m = re.match(r"^(.*?)\s*-\s*([A-Z]{2})$", r)
            if m and m.group(2).lower() in BR_STATES and "-" not in normalize_team(r):
                r = m.group(1)
            return r.strip()

        def add(src, m):
            self.sources.setdefault(src, []).append(m)
            for raw in (m.home, m.away):
                weight = 3 if src == "historical" else 1  # accented names
                name_votes[normalize_team(raw)][pretty(raw)] += weight

        for r in self._read("Brasileirao_Matches.csv"):
            add("brasileirao", Match(parse_date(r["datetime"]), r["home_team"], r["away_team"],
                                     _int(r["home_goal"]), _int(r["away_goal"]), "Brasileirão Serie A",
                                     _int(r["season"]), f"Round {r['round']}", "Brasileirao_Matches.csv"))
        for r in self._read("Brazilian_Cup_Matches.csv"):
            add("cup", Match(parse_date(r["datetime"]), r["home_team"], r["away_team"],
                             _int(r["home_goal"]), _int(r["away_goal"]), "Copa do Brasil",
                             _int(r["season"]), f"Round {r['round']}", "Brazilian_Cup_Matches.csv"))
        for r in self._read("Libertadores_Matches.csv"):
            add("libertadores", Match(parse_date(r["datetime"]), r["home_team"], r["away_team"],
                                      _int(r["home_goal"]), _int(r["away_goal"]), "Copa Libertadores",
                                      _int(r["season"]), r["stage"].strip(), "Libertadores_Matches.csv"))
        for r in self._read("BR-Football-Dataset.csv"):
            d = parse_date(r["date"])
            hg, ag = _int(r["home_goal"]), _int(r["away_goal"])
            if hg is None or ag is None:
                continue
            extra = {}
            for label, h, a in (("corners", "home_corner", "away_corner"), ("shots", "home_shots", "away_shots"),
                                ("attacks", "home_attack", "away_attack")):
                if _int(r[h]) is not None and _int(r[a]) is not None:
                    extra[label] = f"{_int(r[h])}-{_int(r[a])}"
            add("extended", Match(d, r["home"], r["away"], hg, ag,
                                  normalize_competition(r["tournament"]) or r["tournament"],
                                  d.year if d else None, "", "BR-Football-Dataset.csv", extra=extra))
        for r in self._read("novo_campeonato_brasileiro.csv"):
            add("historical", Match(parse_date(r["Data"]), r["Equipe_mandante"], r["Equipe_visitante"],
                                    _int(r["Gols_mandante"]), _int(r["Gols_visitante"]), "Brasileirão Serie A",
                                    _int(r["Ano"]), f"Round {r['Rodada']}", "novo_campeonato_brasileiro.csv",
                                    venue=r.get("Arena", "").strip()))
        for src in self.sources:
            self.sources[src] = [m for m in self.sources[src] if m.home_goal is not None and m.away_goal is not None]
        self.names = {k: v.most_common(1)[0][0] for k, v in name_votes.items()}

        for r in self._read("fifa_data.csv"):
            r = {k.strip(): v for k, v in r.items() if k}
            r["Overall"] = _int(r.get("Overall")) or 0
            r["Potential"] = _int(r.get("Potential")) or 0
            r["Age"] = _int(r.get("Age"))
            r["_name"] = strip_accents(r.get("Name", "")).lower()
            r["_club"] = normalize_team(r.get("Club", "")) if r.get("Club") else ""
            self.players.append(r)
        self.brazilian_club_keys = {m.home_key for s in ("brasileirao", "historical") for m in self.sources[s]}
        self.brazilian_club_keys |= {m.home_key for m in self.sources["extended"]
                                     if m.competition in ("Brasileirão Serie A", "Brasileirão Serie B")}

    # ---- helpers ----
    def all_matches(self, competition: str | None = None) -> list[Match]:
        """Canonical, de-duplicated match list. Overlapping files are combined so each
        competition/season comes from one primary source; BR-Football fills in later years."""
        if self._canonical is None:
            ext = self.sources["extended"]
            last_cup = max(m.season for m in self.sources["cup"])
            canon = list(self.sources["brasileirao"])
            canon += [m for m in self.sources["historical"] if m.season < 2012]
            canon += [m for m in ext if m.competition == "Brasileirão Serie A" and m.season > 2022]
            canon += self.sources["cup"]
            canon += [m for m in ext if m.competition == "Copa do Brasil" and m.season > last_cup]
            canon += self.sources["libertadores"]
            canon += [m for m in ext if m.competition not in ("Brasileirão Serie A", "Copa do Brasil")]
            self._canonical = canon
        if competition:
            return [m for m in self._canonical if m.competition == competition]
        return self._canonical

    def league_matches(self, season: int) -> list[Match]:
        """Single authoritative source for a Serie A season."""
        for src in ("brasileirao", "historical"):
            ms = [m for m in self.sources[src] if m.season == season]
            if ms:
                return ms
        return [m for m in self.sources["extended"] if m.season == season and m.competition == "Brasileirão Serie A"]

    def team_keys(self) -> set[str]:
        return set(self.names)

    def resolve_team(self, query: str) -> set[str]:
        """Map a user query to one or more canonical team keys."""
        key = normalize_team(query)
        keys = self.team_keys()
        if key in keys:
            return {key}
        q = strip_accents(query).lower().strip()
        hits = {k for k in keys if k.startswith(key + "-") or key in k or q in k}
        return hits or {key}


def _team_filter(kb: KB, team):
    return kb.resolve_team(team) if team else None


def _match_has(m: Match, keys) -> bool:
    return m.home_key in keys or m.away_key in keys


def _sort(ms):
    return sorted(ms, key=lambda m: m.date or date.min, reverse=True)


def _name(kb, keys):
    k = sorted(keys, key=len)[0]
    return kb.names.get(k, k.title())


# ---------------------------------------------------------------- queries

def search_matches(team=None, opponent=None, competition=None, season=None, date_from=None, date_to=None,
                   venue="any", stage=None, limit=20) -> str:
    kb = KB.get()
    comp = normalize_competition(competition)
    tk, ok = _team_filter(kb, team), _team_filter(kb, opponent)
    df, dt = parse_date(date_from) if date_from else None, parse_date(date_to) if date_to else None
    out = []
    for m in kb.all_matches(comp):
        if season and m.season != int(season):
            continue
        if df and (not m.date or m.date < df):
            continue
        if dt and (not m.date or m.date > dt):
            continue
        if stage and strip_accents(stage).lower() not in strip_accents(m.stage).lower():
            continue
        if tk:
            if venue == "home" and m.home_key not in tk:
                continue
            if venue == "away" and m.away_key not in tk:
                continue
            if not _match_has(m, tk):
                continue
        if ok and not _match_has(m, ok):
            continue
        if tk and ok and not ((m.home_key in tk and m.away_key in ok) or (m.home_key in ok and m.away_key in tk)):
            continue
        out.append(m)
    out = _sort(out)
    if not out:
        return "No matches found for the given criteria."
    title = "Matches"
    if tk:
        title += f" for {_name(kb, tk)}"
    if ok:
        title += f" vs {_name(kb, ok)}"
    lines = [f"{title} ({len(out)} found):"]
    lines += [f"- {m.describe()}" for m in out[: int(limit)]]
    if len(out) > int(limit):
        lines.append(f"- ... ({len(out) - int(limit)} more matches in dataset)")
    return "\n".join(lines)


def last_match(team, opponent=None) -> str:
    kb = KB.get()
    tk, ok = kb.resolve_team(team), _team_filter(kb, opponent)
    ms = [m for m in kb.all_matches() if _match_has(m, tk) and (not ok or _match_has(m, ok))]
    if ok:
        ms = [m for m in ms if not (m.home_key in tk and m.away_key in tk)]
    if not ms:
        return "No matches found."
    m = _sort(ms)[0]
    return f"Most recent match in dataset: {m.describe()}\nScore: {display_name(m.home)} {m.home_goal}, {display_name(m.away)} {m.away_goal}"


def head_to_head(team_a, team_b, competition=None, limit=10) -> str:
    kb = KB.get()
    ak, bk = kb.resolve_team(team_a), kb.resolve_team(team_b)
    comp = normalize_competition(competition)
    ms = [m for m in kb.all_matches(comp)
          if (m.home_key in ak and m.away_key in bk) or (m.home_key in bk and m.away_key in ak)]
    if not ms:
        return f"No matches found between {team_a} and {team_b}."
    ms = _sort(ms)
    an, bn = _name(kb, ak), _name(kb, bk)
    aw = bw = dr = ag = bg = 0
    for m in ms:
        a_home = m.home_key in ak
        ga, gb = (m.home_goal, m.away_goal) if a_home else (m.away_goal, m.home_goal)
        ag += ga
        bg += gb
        aw += ga > gb
        bw += gb > ga
        dr += ga == gb
    derby = DERBY_LOOKUP.get(frozenset((sorted(ak)[0], sorted(bk)[0])))
    lines = [f"{an} vs {bn}" + (f" ({derby} derby)" if derby else "") + ":"]
    lines += [f"- {m.describe()}" for m in ms[:limit]]
    if len(ms) > limit:
        lines.append(f"- ... ({len(ms) - limit} more matches in dataset)")
    lines.append(f"\nHead-to-head in dataset ({len(ms)} matches): {an} {aw} wins, {bn} {bw} wins, {dr} draws")
    lines.append(f"Goals: {an} {ag}, {bn} {bg}")
    return "\n".join(lines)


def _record(ms, keys):
    r = dict(matches=0, wins=0, draws=0, losses=0, gf=0, ga=0)
    for m in ms:
        home = m.home_key in keys
        gf, ga = (m.home_goal, m.away_goal) if home else (m.away_goal, m.home_goal)
        r["matches"] += 1
        r["gf"] += gf
        r["ga"] += ga
        r["wins" if gf > ga else "losses" if gf < ga else "draws"] += 1
    return r


def team_record(team, season=None, competition=None, venue="any") -> str:
    kb = KB.get()
    keys = kb.resolve_team(team)
    comp = normalize_competition(competition)
    if comp == "Brasileirão Serie A" and season:
        ms = kb.league_matches(int(season))
    else:
        ms = kb.all_matches(comp)
    ms = [m for m in ms if _match_has(m, keys) and (not season or m.season == int(season))]
    if venue == "home":
        ms = [m for m in ms if m.home_key in keys]
    elif venue == "away":
        ms = [m for m in ms if m.away_key in keys]
    if not ms:
        return f"No matches found for {team}."
    r = _record(ms, keys)
    label = {"home": "home record", "away": "away record"}.get(venue, "record")
    ctx = ", ".join(x for x in [str(season) if season else "", comp or "all competitions"] if x)
    lines = [f"{_name(kb, keys)} {label} ({ctx}):",
             f"- Matches: {r['matches']}",
             f"- Wins: {r['wins']}, Draws: {r['draws']}, Losses: {r['losses']}",
             f"- Goals For: {r['gf']}, Goals Against: {r['ga']}",
             f"- Win rate: {100 * r['wins'] / r['matches']:.1f}%"]
    if not comp:
        by = defaultdict(list)
        for m in ms:
            by[m.competition].append(m)
        lines.append("By competition:")
        for c, cm in sorted(by.items()):
            cr = _record(cm, keys)
            lines.append(f"  - {c}: {cr['matches']} matches, {cr['wins']}W {cr['draws']}D {cr['losses']}L, GF {cr['gf']} GA {cr['ga']}")
    return "\n".join(lines)


def compute_standings(season: int):
    kb = KB.get()
    table = defaultdict(lambda: dict(p=0, w=0, d=0, l=0, gf=0, ga=0, pts=0))
    for m in kb.league_matches(int(season)):
        for key, gf, ga in ((m.home_key, m.home_goal, m.away_goal), (m.away_key, m.away_goal, m.home_goal)):
            t = table[key]
            t["p"] += 1
            t["gf"] += gf
            t["ga"] += ga
            if gf > ga:
                t["w"] += 1
                t["pts"] += 3
            elif gf == ga:
                t["d"] += 1
                t["pts"] += 1
            else:
                t["l"] += 1
    rows = sorted(table.items(), key=lambda kv: (-kv[1]["pts"], -kv[1]["w"], -(kv[1]["gf"] - kv[1]["ga"]), -kv[1]["gf"]))
    return [(kb.names.get(k, k), v) for k, v in rows]


def standings(season, top=None) -> str:
    rows = compute_standings(int(season))
    if not rows:
        return f"No Brasileirão data for {season}."
    n = len(rows)
    lines = [f"{season} Brasileirão Final Standings (calculated from matches):"]
    for i, (name, t) in enumerate(rows[: int(top) if top else n], 1):
        tag = " - Champion" if i == 1 else " - Relegated" if n >= 20 and i > n - 4 else ""
        lines.append(f"{i}. {name} - {t['pts']} pts ({t['w']}W, {t['d']}D, {t['l']}L, GF {t['gf']}, GA {t['ga']}, GD {t['gf'] - t['ga']:+d}){tag}")
    return "\n".join(lines)


def champion(season) -> str:
    rows = compute_standings(int(season))
    if not rows:
        return f"No Brasileirão data for {season}."
    name, t = rows[0]
    return f"{name} won the {season} Brasileirão with {t['pts']} points ({t['w']}W, {t['d']}D, {t['l']}L), calculated from match results."


def relegated(season) -> str:
    rows = compute_standings(int(season))
    if len(rows) < 20:
        return f"Insufficient data for {season}."
    lines = [f"Teams relegated from the {season} Brasileirão (bottom 4, calculated):"]
    for i, (name, t) in enumerate(rows[-4:], len(rows) - 3):
        lines.append(f"{i}. {name} - {t['pts']} pts")
    return "\n".join(lines)


def _filtered(competition=None, season=None):
    kb = KB.get()
    comp = normalize_competition(competition)
    if comp == "Brasileirão Serie A" and season:
        return kb.league_matches(int(season))
    return [m for m in kb.all_matches(comp) if not season or m.season == int(season)]


def league_stats(competition=None, season=None) -> str:
    ms = _filtered(competition, season)
    if not ms:
        return "No matches found."
    n = len(ms)
    goals = sum(m.home_goal + m.away_goal for m in ms)
    hw = sum(m.home_goal > m.away_goal for m in ms)
    aw = sum(m.home_goal < m.away_goal for m in ms)
    ctx = " ".join(x for x in [normalize_competition(competition) or "All competitions", str(season) if season else ""] if x)
    return "\n".join([
        f"Statistics - {ctx}:",
        f"- Matches: {n}",
        f"- Total goals: {goals}",
        f"- Average goals per match: {goals / n:.2f}",
        f"- Home win rate: {100 * hw / n:.1f}%",
        f"- Away win rate: {100 * aw / n:.1f}%",
        f"- Draw rate: {100 * (n - hw - aw) / n:.1f}%",
    ])


def biggest_wins(competition=None, season=None, team=None, limit=10) -> str:
    kb = KB.get()
    ms = _filtered(competition, season)
    if team:
        keys = kb.resolve_team(team)
        ms = [m for m in ms if _match_has(m, keys)]
    ms = sorted(ms, key=lambda m: (-abs(m.home_goal - m.away_goal), -(m.home_goal + m.away_goal), m.date or date.min))
    if not ms:
        return "No matches found."
    lines = ["Biggest victories in dataset:"]
    lines += [f"{i}. {m.describe()}" for i, m in enumerate(ms[: int(limit)], 1)]
    return "\n".join(lines)


def best_records(competition=None, season=None, venue="any", min_matches=10, limit=10, sort_by="win_rate") -> str:
    kb = KB.get()
    ms = _filtered(competition, season)
    per = defaultdict(list)
    for m in ms:
        if venue in ("any", "home"):
            per[m.home_key].append(m)
        if venue in ("any", "away"):
            per[m.away_key].append(m)
    rows = []
    for k, tms in per.items():
        if len(tms) < int(min_matches):
            continue
        r = _record(tms, {k})
        r["win_rate"] = r["wins"] / r["matches"]
        r["goals"] = r["gf"]
        r["points_per_game"] = (3 * r["wins"] + r["draws"]) / r["matches"]
        rows.append((kb.names.get(k, k), r))
    key = sort_by if sort_by in ("win_rate", "goals", "points_per_game") else "win_rate"
    rows.sort(key=lambda x: -x[1][key])
    if not rows:
        return "No teams meet the criteria."
    label = {"home": "home", "away": "away"}.get(venue, "overall")
    ctx = " ".join(x for x in [normalize_competition(competition) or "all competitions", str(season) if season else ""] if x)
    lines = [f"Best {label} records by {key.replace('_', ' ')} ({ctx}, min {min_matches} matches):"]
    for i, (n, r) in enumerate(rows[: int(limit)], 1):
        lines.append(f"{i}. {n} - {r['matches']} matches, {r['wins']}W {r['draws']}D {r['losses']}L, "
                     f"GF {r['gf']} GA {r['ga']}, win rate {100 * r['win_rate']:.1f}%")
    return "\n".join(lines)


def top_scoring_teams(season=None, competition="Brasileirão Serie A", limit=10) -> str:
    return best_records(competition, season, "any", 1, limit, "goals")


def team_competitions(team) -> str:
    kb = KB.get()
    keys = kb.resolve_team(team)
    by = defaultdict(list)
    for src, ms in kb.sources.items():
        for m in ms:
            if _match_has(m, keys):
                by[m.competition].append(m)
    if not by:
        return f"No matches found for {team}."
    lines = [f"Competitions played by {_name(kb, keys)} (all data files):"]
    for c, ms in sorted(by.items()):
        seasons = sorted({m.season for m in ms if m.season})
        files = sorted({m.source for m in ms})
        lines.append(f"- {c}: seasons {seasons[0]}-{seasons[-1]} ({len(seasons)} seasons), sources: {', '.join(files)}")
    return "\n".join(lines)


def derbies(season=None, competition=None, limit=50) -> str:
    kb = KB.get()
    out = []
    for m in kb.all_matches(normalize_competition(competition)):
        if season and m.season != int(season):
            continue
        n = DERBY_LOOKUP.get(frozenset((m.home_key, m.away_key)))
        if n:
            out.append((n, m))
    if not out:
        return "No derby matches found."
    out.sort(key=lambda x: x[1].date or date.min, reverse=True)
    lines = [f"Derby matches{' in ' + str(season) if season else ''} ({len(out)} found):"]
    lines += [f"- [{n}] {m.describe()}" for n, m in out[: int(limit)]]
    return "\n".join(lines)


def compare_seasons(seasons, competition="Brasileirão Serie A") -> str:
    lines = [f"Season comparison ({normalize_competition(competition)}):"]
    for s in seasons:
        ms = _filtered(competition, int(s))
        if not ms:
            lines.append(f"- {s}: no data")
            continue
        n = len(ms)
        g = sum(m.home_goal + m.away_goal for m in ms)
        hw = sum(m.home_goal > m.away_goal for m in ms)
        dr = sum(m.home_goal == m.away_goal for m in ms)
        champ = ""
        if normalize_competition(competition) == "Brasileirão Serie A":
            rows = compute_standings(int(s))
            champ = f", champion: {rows[0][0]} ({rows[0][1]['pts']} pts)"
        lines.append(f"- {s}: {n} matches, {g} goals ({g / n:.2f}/match), home wins {100 * hw / n:.1f}%, draws {100 * dr / n:.1f}%{champ}")
    return "\n".join(lines)


def libertadores_bracket(season) -> str:
    kb = KB.get()
    ms = [m for m in kb.sources["libertadores"] if m.season == int(season) and m.stage != "group stage"]
    if not ms:
        return f"No Libertadores knockout data for {season}."
    order = ["round of 16", "quarterfinals", "semifinals", "final"]
    lines = [f"{season} Copa Libertadores knockout bracket:"]
    for st in order:
        sm = sorted([m for m in ms if m.stage == st], key=lambda m: m.date or date.min)
        if sm:
            lines.append(f"{st.title()}:")
            lines += [f"  - {m.describe()}" for m in sm]
    return "\n".join(lines)


# ---- players ----

def _fmt_player(p, detailed=False):
    s = (f"{p['Name']} - Overall: {p['Overall']}, Potential: {p['Potential']}, Position: {p.get('Position') or '?'}, "
         f"Age: {p['Age']}, Nationality: {p['Nationality']}, Club: {p.get('Club') or 'Free agent'}")
    if detailed:
        attrs = ["Crossing", "Finishing", "Dribbling", "ShortPassing", "BallControl", "SprintSpeed", "Stamina",
                 "Strength", "Vision", "StandingTackle"]
        s += (f"\n    Jersey: {p.get('Jersey Number')}, Height: {p.get('Height')}, Weight: {p.get('Weight')}, "
              f"Foot: {p.get('Preferred Foot')}, Value: {p.get('Value')}, Wage: {p.get('Wage')}\n    "
              + ", ".join(f"{a}: {p.get(a)}" for a in attrs if p.get(a)))
    return s


POSITION_GROUPS = {
    "forward": {"ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"},
    "striker": {"ST", "CF", "LS", "RS"},
    "midfielder": {"CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"},
    "defender": {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
    "goalkeeper": {"GK"},
}


def _find_players(name=None, nationality=None, club=None, position=None, min_overall=None):
    kb = KB.get()
    res = kb.players
    if name:
        q = strip_accents(name).lower().strip()
        toks = q.split()
        res = [p for p in res if q in p["_name"] or all(t in p["_name"] for t in toks)]
        if not res and toks:  # e.g. "Gabriel Barbosa" -> "Gabriel" / "Gabigol"
            res = [p for p in kb.players if any(t in p["_name"].split() for t in toks if len(t) > 3)]
    if nationality:
        q = strip_accents(nationality).lower()
        q = {"brazilian": "brazil", "argentine": "argentina", "argentinian": "argentina"}.get(q, q)
        res = [p for p in res if strip_accents(p["Nationality"]).lower() == q]
    if club:
        ck = kb.resolve_team(club) | {normalize_team(club)}
        cq = strip_accents(club).lower()
        exact = [p for p in res if p["_club"] in ck]
        res = exact or [p for p in res if p["_club"] and cq in strip_accents(p["Club"]).lower()]
    if position:
        pos = POSITION_GROUPS.get(position.lower().rstrip("s"), {position.upper()})
        res = [p for p in res if p.get("Position") in pos]
    if min_overall:
        res = [p for p in res if p["Overall"] >= int(min_overall)]
    return sorted(res, key=lambda p: (-p["Overall"], p["Name"]))


def search_players(name=None, nationality=None, club=None, position=None, min_overall=None, limit=20) -> str:
    res = _find_players(name, nationality, club, position, min_overall)
    if not res:
        msg = "No players found."
        if club:
            msg += (" Note: the FIFA dataset lacks several Brazilian clubs (e.g. Flamengo, Corinthians, Palmeiras, "
                    "São Paulo) due to licensing.")
        return msg
    detailed = len(res) <= 3
    crit = ", ".join(f"{k}={v}" for k, v in dict(name=name, nationality=nationality, club=club,
                                                   position=position, min_overall=min_overall).items() if v)
    lines = [f"Players ({crit}) - {len(res)} found, sorted by overall rating:"]
    lines += [f"{i}. {_fmt_player(p, detailed)}" for i, p in enumerate(res[: int(limit)], 1)]
    if len(res) > int(limit):
        lines.append(f"... ({len(res) - int(limit)} more)")
    return "\n".join(lines)


def brazilian_clubs_summary(nationality="Brazil") -> str:
    kb = KB.get()
    by = defaultdict(list)
    for p in kb.players:
        if p["_club"] and p["_club"] in kb.brazilian_club_keys:
            by[p["Club"]].append(p)
    if not by:
        return "No players at Brazilian clubs in dataset."
    lines = ["Players at Brazilian clubs (FIFA dataset):"]
    for c, ps in sorted(by.items(), key=lambda kv: -len(kv[1])):
        br = [p for p in ps if p["Nationality"] == nationality]
        avg = sum(p["Overall"] for p in ps) / len(ps)
        best = max(ps, key=lambda p: p["Overall"])
        lines.append(f"- {c}: {len(ps)} players ({len(br)} {nationality}), avg rating {avg:.0f}, best: {best['Name']} ({best['Overall']})")
    return "\n".join(lines)


def club_profile(team) -> str:
    """Cross-file query: match record plus FIFA squad for a club."""
    kb = KB.get()
    parts = [team_record(team), team_competitions(team)]
    keys = kb.resolve_team(team)
    ps = sorted([p for p in kb.players if p["_club"] in keys], key=lambda p: -p["Overall"])
    if ps:
        parts.append(f"FIFA squad ({len(ps)} players, avg rating {sum(p['Overall'] for p in ps) / len(ps):.1f}):\n"
                     + "\n".join(f"  - {_fmt_player(p)}" for p in ps[:10]))
    else:
        parts.append("FIFA squad: no players listed for this club in the FIFA dataset.")
    return "\n\n".join(parts)


def dataset_info() -> str:
    kb = KB.get()
    lines = ["Loaded datasets:"]
    for src, ms in kb.sources.items():
        seasons = sorted({m.season for m in ms if m.season})
        lines.append(f"- {ms[0].source}: {len(ms)} matches, seasons {seasons[0]}-{seasons[-1]}")
    lines.append(f"- fifa_data.csv: {len(kb.players)} players")
    return "\n".join(lines)
