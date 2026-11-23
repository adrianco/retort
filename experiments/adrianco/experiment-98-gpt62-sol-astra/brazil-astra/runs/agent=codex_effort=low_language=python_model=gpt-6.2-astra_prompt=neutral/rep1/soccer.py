"""In-memory soccer graph. Matches link two clubs to a competition season."""
import csv
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "kaggle"
LEAGUE = "Brasileirão"
CUP = "Copa do Brasil"
LIB = "Libertadores"
FILES = ("Brasileirao_Matches", "Brazilian_Cup_Matches", "Libertadores_Matches",
         "novo_campeonato_brasileiro", "BR-Football-Dataset")
STATES = "ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to".split()


@lru_cache(maxsize=65536)
def fold(value):
    return "".join(c for c in unicodedata.normalize("NFKD", value.casefold().strip())
                   if not unicodedata.combining(c))


ALIASES = {
    "sport club corinthians paulista": "corinthians", "sao paulo fc": "sao paulo",
    "sociedade esportiva palmeiras": "palmeiras", "clube de regatas do flamengo": "flamengo",
    "atletico mineiro": "atletico-mg", "atletico goianiense": "atletico-go",
    "athletico": "atletico-pr", "athletico-pr": "atletico-pr",
    "atletico paranaense": "atletico-pr", "athletico paranaense": "atletico-pr",
    "america mineiro": "america-mg", "america fc natal": "america-rn",
    "vasco da gama": "vasco", "red bull bragantino": "bragantino",
    "ec bahia": "bahia", "fortaleza ec": "fortaleza", "fortaleza fc": "fortaleza",
    "sport recife": "sport", "ec vitoria": "vitoria", "ec juventude": "juventude",
    "chapecoense af": "chapecoense", "santos fc": "santos", "santa cruz fc": "santa cruz",
}
# Unqualified names used in the league and player datasets.
DEFAULT_STATE = dict(botafogo="rj", fluminense="rj", bragantino="sp", juventude="rs",
                     internacional="rs", flamengo="rj", santos="sp", cruzeiro="mg")
DEFAULT_STATE["santa cruz"] = "pe"


@lru_cache(maxsize=8192)
def club(value):
    name = fold(value)
    m = re.fullmatch(r"(.+?)\s*[- ]\s*([a-z]{2})", name)
    if m and m[2] in STATES:
        name, state = m[1].strip(), m[2]
        if name in {"atletico", "america", "operario", "rio branco", "sao raimundo", "ypiranga"} or (
                name in DEFAULT_STATE and state != DEFAULT_STATE[name]):
            name += "-" + state
    return ALIASES.get(name, name)


def competition(value):
    return {"serie a": LEAGUE, "brasileirao": LEAGUE, "brasileirao serie a": LEAGUE,
            "copa libertadores": LIB, "libertadores": LIB, "copa do brasil": CUP,
            "serie b": "Serie B", "serie c": "Serie C"}.get(fold(value), value)


def day(value):
    if value in ("NA", "", "-"):
        return None
    if "/" in value:
        d, m, y = value.split("/")
        value = f"{y}-{m}-{d}"
    return date.fromisoformat(value[:10]).isoformat()


def goals(value):
    return None if value in ("", "NA", "-") else int(float(value))


def page(rows, limit, offset):
    if not 1 <= limit <= 200 or offset < 0:
        raise ValueError("Use limit 1–200 and a nonnegative offset")
    return dict(total=len(rows), offset=offset, results=rows[offset:offset + limit])


DERBIES = {frozenset(pair) for group in [
    ["flamengo", "fluminense", "vasco", "botafogo"], ["palmeiras", "santos", "sao paulo", "corinthians"],
    ["gremio", "internacional"], ["atletico-mg", "cruzeiro"], ["bahia", "vitoria"],
    ["fortaleza", "ceara"], ["atletico-pr", "coritiba"]]
    for i, a in enumerate(group) for pair in [(a, b) for b in group[i+1:]]}


class Graph:
    def __init__(self, directory=DATA):
        self.matches = []
        self.players = []
        fixtures = defaultdict(list)
        for source in FILES:
            with (directory / (source + ".csv")).open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            rounds = Counter((r.get("season"), r.get("round")) for r in rows)
            for r in rows:
                hist = source == FILES[3]
                extended = source == FILES[4]
                comp = competition(r["tournament"]) if extended else (
                    LEAGUE if hist else (LEAGUE, CUP, LIB)[FILES.index(source)])
                dt = day(r.get("datetime", r.get("Data", r.get("date"))))
                year = r.get("season", r.get("Ano", (dt or "")[:4]))
                season = int(year) if year.isdigit() else None
                if extended and comp in (LEAGUE, "Serie B", "Serie C") and dt < "2021-03" and season == 2021:
                    season = 2020
                home = club(r.get("home_team", r.get("Equipe_mandante", r.get("home"))))
                away = club(r.get("away_team", r.get("Equipe_visitante", r.get("away"))))
                key = (comp, home, away)
                candidates = fixtures[key]
                match = next((x for x in candidates if source not in x["sources"] and
                              (x["date"] == dt or (extended and dt and x["date"] and
                               abs((date.fromisoformat(dt) - date.fromisoformat(x["date"])).days) <= 1) or (comp == LEAGUE and x["season"] == season))), None)
                hg = goals(r.get("home_goal", r.get("Gols_mandante")))
                ag = goals(r.get("away_goal", r.get("Gols_visitante")))
                if match is None:
                    rnd = r.get("round", r.get("Rodada"))
                    stage = r.get("stage")
                    if comp == CUP and rnd and rounds[year, rnd] <= 2 and not any(
                            (year, str(n)) in rounds for n in range(int(rnd)+1, 10)):
                        stage = "final"
                    match = dict(date=dt, home=home, away=away, competition=comp, season=season,
                                 round=rnd, stage=stage, home_goal=hg, away_goal=ag, sources=[])
                    self.matches.append(match)
                    candidates.append(match)
                if match["home_goal"] is None and hg is not None:
                    match.update(home_goal=hg, away_goal=ag, date=dt)
                match["sources"].append(source)
                if hist:
                    match["arena"] = r["Arena"]
                if extended:
                    match["statistics"] = {k: v for k, v in r.items() if k not in
                                           ("home", "away", "date", "home_goal", "away_goal", "tournament")}
        self.fixture_seasons = {m["season"] for m in self.matches if FILES[0] in m["sources"]}
        self.matches.sort(key=lambda x: x["date"] or "", reverse=True)
        for year in (2021, 2022, 2023):
            legs = [m for m in self.matches if m["season"] == year and m["competition"] == CUP][:2]
            if len(legs) == 2 and (legs[0]["home"], legs[0]["away"]) == (legs[1]["away"], legs[1]["home"]):
                for leg in legs:
                    leg["stage"] = "final"
        with (directory / "fifa_data.csv").open(encoding="utf-8-sig", newline="") as stream:
            self.players = sorted(csv.DictReader(stream), key=lambda p: -int(p["Overall"]))

    def select(self, team="", opponent="", venue="either", competition_name="", season=None,
               start="", end="", stage="", source="", derby=False):
        if venue not in ("either", "home", "away") or (opponent or venue != "either") and not team:
            raise ValueError("Specify a team for opponent or venue filters and a valid venue")
        a, b = club(team), club(opponent)
        comp = competition(competition_name)
        lo, hi = day(start), day(end)
        for m in self.matches:
            if (not source and m["competition"] == LEAGUE and m["season"] in self.fixture_seasons
                    and FILES[0] not in m["sources"]):
                continue
            h, v = m["home"], m["away"]
            if a and not ((venue != "away" and h == a and (not b or b == v)) or
                          (venue != "home" and v == a and (not b or b == h))):
                continue
            if comp and comp != m["competition"] or season is not None and season != m["season"]:
                continue
            if lo and (m["date"] or "") < lo or hi and (not m["date"] or m["date"] > hi):
                continue
            if stage and fold(stage) not in (fold(m["stage"] or ""), m["round"]):
                continue
            if source and source.removesuffix(".csv") not in m["sources"]:
                continue
            if not derby or frozenset((h, v)) in DERBIES:
                yield m

    def find_matches(self, limit=20, offset=0, biggest_wins=False, **filters):
        rows = list(self.select(**filters))
        if biggest_wins:
            rows = [m for m in rows if None not in (m["home_goal"], m["away_goal"])
                    and m["home_goal"] != m["away_goal"]]
            rows.sort(key=lambda m: -abs(m["home_goal"] - m["away_goal"]))
        return page(rows, limit, offset)

    def find_players(self, name="", nationality="", team="", position="", details=False, limit=20, offset=0):
        positions = {"ST","CF","LF","RF","LW","RW","LS","RS"} if fold(position) in (
            "forward", "forwards") else {position.upper()}
        nation = fold(nationality)
        rows = [p for p in self.players if fold(name) in fold(p["Name"])
                and (not nation or fold(p["Nationality"]) == ("brazil" if nation == "brazilian" else nation))
                and (not team or club(team) == club(p["Club"]))
                and (not position or p["Position"] in positions)]
        result = page(rows, limit, offset)
        fields = ("ID","Name","Age","Club","Position","Nationality","Overall","Potential")
        if not details:
            result["results"] = [{k:p[k] for k in fields} for p in result["results"]]
        return result

    def statistics(self, team="", venue="either", rank_by="points", limit=50, offset=0, **filters):
        """Compute records from scored fixtures, orienting each score to its club."""
        table = defaultdict(Counter)
        played = total = home_wins = scheduled = 0
        competitions = set()
        if venue not in ("home","away","either") or rank_by not in ("points","win_rate","goals_for","wins"):
            raise ValueError("Unsupported venue or ranking")
        for m in self.select(team=team, venue=venue if team else "either", **filters):
            competitions.add(m["competition"])
            h, a = m["home_goal"], m["away_goal"]
            if None in (h, a):
                scheduled += 1
                continue
            played += 1
            total += h+a
            home_wins += h>a
            for side, gf, ga in (("home", h, a), ("away", a, h)):
                if venue not in ("either", side) or team and club(team) != m[side]:
                    continue
                table[m[side]].update(matches=1, wins=int(gf>ga), draws=int(gf==ga),
                                      losses=int(gf<ga), goals_for=gf, goals_against=ga)
        rows = [dict(team=k, **v, points=3*v["wins"]+v["draws"],
                     goal_difference=v["goals_for"]-v["goals_against"],
                     win_rate=round(100*v["wins"]/v["matches"], 3)) for k,v in table.items()]
        rows.sort(key=lambda r: (-r[rank_by], -r["wins"], -r["goal_difference"], -r["goals_for"], r["team"]))
        return dict(matches=played, unscored=scheduled, competitions=sorted(competitions),
                    goals_per_match=round(total/played, 3) if played else None,
                    home_win_rate=round(100*home_wins/played, 3) if played else None,
                    **page(rows, limit, offset))
