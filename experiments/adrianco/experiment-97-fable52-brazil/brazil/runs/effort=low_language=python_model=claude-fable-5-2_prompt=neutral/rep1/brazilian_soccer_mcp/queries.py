"""In-memory knowledge base: teams, matches, competitions and players, plus the
query/statistics functions exposed by the MCP server."""
from __future__ import annotations

import datetime as dt
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

from . import data
from .data import COPA_BR, LIBERTADORES, SERIE_A, SERIE_B, SERIE_C, Match, Player, parse_date
from .teams import CURATED, norm, parse_team, team_key

RIVALRIES = [
    ("Flamengo", "Fluminense", "Fla-Flu"),
    ("Flamengo", "Vasco", "Clássico dos Milhões"),
    ("Flamengo", "Botafogo", "Clássico da Rivalidade"),
    ("Fluminense", "Vasco", "Clássico dos Gigantes"),
    ("Botafogo", "Fluminense", "Clássico Vovô"),
    ("Botafogo", "Vasco", "Clássico da Amizade"),
    ("Corinthians", "Palmeiras", "Derby Paulista"),
    ("Corinthians", "São Paulo", "Majestoso"),
    ("Palmeiras", "São Paulo", "Choque-Rei"),
    ("Santos", "São Paulo", "San-São"),
    ("Corinthians", "Santos", "Clássico Alvinegro"),
    ("Palmeiras", "Santos", "Clássico da Saudade"),
    ("Grêmio", "Internacional", "Grenal"),
    ("Atlético-MG", "Cruzeiro", "Clássico Mineiro"),
    ("Athletico-PR", "Coritiba", "Atletiba"),
    ("Bahia", "Vitória", "Ba-Vi"),
    ("Ceará", "Fortaleza", "Clássico-Rei"),
    ("Náutico", "Sport", "Clássico dos Clássicos"),
    ("Santa Cruz", "Sport", "Clássico das Multidões"),
    ("Náutico", "Santa Cruz", "Clássico das Emoções"),
    ("Avaí", "Figueirense", "Clássico de Florianópolis"),
    ("Goiás", "Vila Nova", "Derby do Cerrado"),
    ("Paysandu", "Remo", "Re-Pa"),
    ("CRB", "CSA", "Clássico das Multidões (AL)"),
]
_RIVALRY = {frozenset((a, b)): name for a, b, name in RIVALRIES}

POSITION_GROUPS = {
    "goalkeeper": {"GK"},
    "defender": {"CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"},
    "midfielder": {"CM", "LCM", "RCM", "CDM", "LDM", "RDM", "CAM", "LAM", "RAM", "LM", "RM"},
    "forward": {"ST", "CF", "LF", "RF", "LS", "RS", "LW", "RW"},
}
_POSITION_ALIASES = {"keeper": "goalkeeper", "goalie": "goalkeeper", "attacker": "forward",
                     "striker": "forward", "winger": "forward", "back": "defender"}

RANK_METRICS = {
    "win_rate": lambda r: (r["win_rate"], r["points"], r["goal_difference"]),
    "points": lambda r: (r["points"], r["wins"], r["goal_difference"], r["goals_for"]),
    "points_per_match": lambda r: (r["points_per_match"], r["goal_difference"]),
    "wins": lambda r: (r["wins"], r["goal_difference"]),
    "goals_for": lambda r: (r["goals_for"], r["goal_difference"]),
    "goals_against": lambda r: (-r["goals_against"], r["goal_difference"]),  # fewest first
    "goal_difference": lambda r: (r["goal_difference"], r["goals_for"]),
}


def resolve_competition(name: Optional[str]) -> Optional[str]:
    if name is None or not str(name).strip():
        return None
    n = norm(name)
    if "libertadores" in n:
        return LIBERTADORES
    if "copa" in n or "cup" in n:
        return COPA_BR
    if "serie b" in n or n == "b":
        return SERIE_B
    if "serie c" in n or n == "c":
        return SERIE_C
    if any(k in n for k in ("brasileir", "serie a", "campeonato brasileiro")) or n in ("a", "league"):
        return SERIE_A
    raise ValueError(f"Unknown competition {name!r}. Known: {', '.join(data.COMPETITIONS)}")


def _season(value) -> Optional[int]:
    if value is None or value == "":
        return None
    return int(value)


def _record(matches: Iterable[Match], teams: set, venue: str = "either") -> dict:
    w = d = l = gf = ga = n = 0
    for m in matches:
        if not m.played:
            continue
        sides = []
        if m.home in teams and venue in ("either", "home"):
            sides.append((m.home_goals, m.away_goals))
        if m.away in teams and venue in ("either", "away"):
            sides.append((m.away_goals, m.home_goals))
        for f, a in sides:
            n += 1
            gf += f
            ga += a
            if f > a:
                w += 1
            elif f == a:
                d += 1
            else:
                l += 1
    pts = 3 * w + d
    return {
        "matches": n, "wins": w, "draws": d, "losses": l, "goals_for": gf,
        "goals_against": ga, "goal_difference": gf - ga, "points": pts,
        "win_rate": round(100 * w / n, 1) if n else 0.0,
        "points_per_match": round(pts / n, 2) if n else 0.0,
    }


class KnowledgeBase:
    def __init__(self, data_dir: Path = data.DATA_DIR):
        raw: list[Match] = []
        # Order matters: the first source seen for a fixture is the primary record.
        for loader in (data.load_brasileirao, data.load_historical, data.load_cup,
                       data.load_libertadores, data.load_extended):
            raw.extend(loader(data_dir))
        self.source_rows = defaultdict(int)
        for m in raw:
            self.source_rows[m.sources[0]] += 1

        # --- team identities -------------------------------------------------
        displays = defaultdict(set)
        for m in raw:
            for side in ("home", "away"):
                key, disp = team_key(getattr(m, side + "_raw"))
                setattr(m, side + "_key", key)
                displays[key].add(disp)
        # A bare name ("Boavista") joins its only state-qualified variant ("Boavista - RJ").
        by_base = defaultdict(set)
        for key in displays:
            if "|" in key:
                by_base[key.split("|")[0]].add(key)
        self._alias = {}
        for base, keys in by_base.items():
            bare = base + "|"
            qualified = keys - {bare}
            if bare in keys and len(qualified) == 1:
                self._alias[bare] = next(iter(qualified))
        self._displays = displays
        self._assign_names(raw)
        self._learn_aliases(raw)
        self._assign_names(raw)

        # --- merge the same fixture reported by several files ----------------
        self.matches: list[Match] = []
        index = defaultdict(list)
        for m in raw:
            dup = None
            for o in index[(m.competition, m.home, m.away)]:
                if m.sources[0] in o.sources and (
                        (m.home_goals, m.away_goals) != (o.home_goals, o.away_goals)):
                    continue  # same file: only exact repeats are merged
                # A league pairing happens once per season; cup ties are matched by date.
                if (m.date and o.date and abs((m.date - o.date).days) <= 3) or (
                        m.season == o.season
                        and (m.competition == SERIE_A or not (m.date and o.date))):
                    dup = o
                    break
            if dup is None:
                index[(m.competition, m.home, m.away)].append(m)
                self.matches.append(m)
                continue
            dup.sources.extend(x for x in m.sources if x not in dup.sources)
            if not dup.played and m.played:
                dup.home_goals, dup.away_goals = m.home_goals, m.away_goals
            dup.arena = dup.arena or m.arena
            dup.round = dup.round or m.round
            dup.date = dup.date or m.date
            dup.stats.update(m.stats)
        self.matches.sort(key=lambda m: (m.date or dt.date(m.season, 12, 31)), reverse=True)

        self.teams = sorted({t for m in self.matches for t in (m.home, m.away)})
        self._team_norm = {t: norm(t) for t in self.teams}
        self._team_set = set(self.teams)
        self._by_team = defaultdict(list)
        for m in self.matches:
            self._by_team[m.home].append(m)
            self._by_team[m.away].append(m)

        # Finals: Libertadores has an explicit stage; the cup's final is its last round.
        self._finals = set()
        last = defaultdict(list)
        for m in self.matches:
            if m.competition == LIBERTADORES and norm(m.round) == "final":
                self._finals.add(id(m))
            elif m.competition == COPA_BR and m.round.isdigit():
                last[m.season].append(m)
        for ms in last.values():
            top = max(int(m.round) for m in ms)
            final = [m for m in ms if int(m.round) == top]
            if len(final) <= 2:
                self._finals.update(id(m) for m in final)

        # --- players ---------------------------------------------------------
        self.players: list[Player] = sorted(data.load_players(data_dir), key=lambda p: -p.overall)
        self._player_club_key = {p.id: team_key(p.club)[0] if p.club else "" for p in self.players}

    def _resolve(self, key: str) -> str:
        seen = set()
        while key in self._alias and key not in seen:
            seen.add(key)
            key = self._alias[key]
        return key

    def _assign_names(self, raw):
        self._names = {}
        for key, cands in self._displays.items():
            if key not in self._alias:
                self._names[key] = min(
                    cands, key=lambda s: (-sum(ord(c) > 127 for c in s), s.count("."), len(s), s))
        for m in raw:
            m.home = self._names[self._resolve(m.home_key)]
            m.away = self._names[self._resolve(m.away_key)]

    def _learn_aliases(self, raw):
        """Learn spellings of smaller clubs from fixtures present in two files.

        If two files report a match in the same competition, within a day, with the
        same score and one identical team, the other team is the same club too
        (e.g. "AE Altos" == "Altos - PI").
        """
        by_side = defaultdict(list)
        for m in raw:
            if m.date and m.sources[0] != "BR-Football-Dataset.csv":
                by_side[(m.competition, "h", m.home, m.date)].append(m)
                by_side[(m.competition, "a", m.away, m.date)].append(m)
        for m in raw:
            if m.sources[0] != "BR-Football-Dataset.csv" or not m.date:
                continue
            for delta in (0, -1, 1):
                day = m.date + dt.timedelta(days=delta)
                for side, same, other in (("h", "home", "away"), ("a", "away", "home")):
                    for o in by_side.get((m.competition, side, getattr(m, same), day), ()):
                        mine = self._resolve(getattr(m, other + "_key"))
                        theirs = self._resolve(getattr(o, other + "_key"))
                        if mine == theirs or "|" not in mine:
                            continue
                        if o.played and (o.home_goals, o.away_goals) != (m.home_goals, m.away_goals):
                            continue
                        self._alias[mine] = theirs

    # ------------------------------------------------------------------ teams
    def find_teams(self, query: str) -> set:
        """Resolve a user-supplied team name to the set of canonical team names."""
        if not query or not str(query).strip():
            raise ValueError("Team name is required")
        key, _ = team_key(query)
        name = self._names.get(self._resolve(key))
        if name in self._team_set:
            return {name}
        q = norm(query)
        base = parse_team(query)[0]
        for needle in (q, base):
            hits = {t for t, n in self._team_norm.items() if needle and needle in n}
            if hits:
                return hits
        raise ValueError(f"No team matching {query!r} in the match data")

    def team_name(self, query: str) -> str:
        return " / ".join(sorted(self.find_teams(query)))

    # ---------------------------------------------------------------- matches
    def search_matches(self, team=None, opponent=None, venue="either", competition=None,
                       season=None, date_from=None, date_to=None, stage=None) -> list[Match]:
        """Matches (newest first) filtered by any combination of criteria."""
        venue = (venue or "either").lower()
        if venue not in ("either", "home", "away"):
            raise ValueError("venue must be 'home', 'away' or 'either'")
        comp = resolve_competition(competition)
        season = _season(season)
        d0 = parse_date(date_from) if date_from else None
        d1 = parse_date(date_to) if date_to else None
        teams = self.find_teams(team) if team else None
        opps = self.find_teams(opponent) if opponent else None
        if teams is None and opps is not None:
            teams, opps = opps, None
        stage_n = norm(str(stage)) if stage not in (None, "") else None
        if stage_n in ("finals", "the final"):
            stage_n = "final"
        if teams is not None:
            pool = {id(m): m for t in teams for m in self._by_team[t]}.values()
            pool = sorted(pool, key=lambda m: (m.date or dt.date(m.season, 12, 31)), reverse=True)
        else:
            pool = self.matches
        out = []
        for m in pool:
            if comp and m.competition != comp:
                continue
            if season is not None and m.season != season:
                continue
            if (d0 or d1) and m.date is None:
                continue
            if d0 and m.date < d0 or d1 and m.date > d1:
                continue
            if teams is not None:
                home_in, away_in = m.home in teams, m.away in teams
                if venue == "home" and not home_in or venue == "away" and not away_in:
                    continue
                if opps is not None and not (home_in and m.away in opps or away_in and m.home in opps):
                    continue
            if stage_n is not None:
                if stage_n == "final":
                    if id(m) not in self._finals:
                        continue
                elif norm(m.round) != stage_n:
                    continue
            out.append(m)
        return out

    def head_to_head(self, team_a, team_b, competition=None, season=None) -> dict:
        a, b = self.find_teams(team_a), self.find_teams(team_b)
        ms = self.search_matches(team_a, team_b, competition=competition, season=season)
        rec = _record(ms, a)
        return {
            "team_a": " / ".join(sorted(a)), "team_b": " / ".join(sorted(b)),
            "rivalry": next((_RIVALRY.get(frozenset((x, y))) for x in a for y in b
                             if frozenset((x, y)) in _RIVALRY), None),
            "matches": rec["matches"], "team_a_wins": rec["wins"], "team_b_wins": rec["losses"],
            "draws": rec["draws"], "team_a_goals": rec["goals_for"],
            "team_b_goals": rec["goals_against"], "match_list": ms,
        }

    def derbies(self, season=None, competition=None) -> list:
        """(rivalry name, match) pairs for matches between traditional rivals."""
        ms = self.search_matches(competition=competition, season=season)
        return [(_RIVALRY[frozenset((m.home, m.away))], m) for m in ms
                if frozenset((m.home, m.away)) in _RIVALRY]

    # ------------------------------------------------------------------ teams
    def team_stats(self, team, season=None, competition=None, venue="either") -> dict:
        teams = self.find_teams(team)
        ms = self.search_matches(team, venue=venue, competition=competition, season=season)
        rec = _record(ms, teams, (venue or "either").lower())
        rec.update(team=" / ".join(sorted(teams)), season=_season(season),
                   competition=resolve_competition(competition), venue=(venue or "either").lower())
        return rec

    def team_competitions(self, team) -> list:
        teams = self.find_teams(team)
        groups = defaultdict(list)
        for m in self.search_matches(team):
            groups[m.competition].append(m)
        out = []
        for comp in data.COMPETITIONS:
            if comp in groups:
                rec = _record(groups[comp], teams)
                rec.update(competition=comp, seasons=sorted({m.season for m in groups[comp]}))
                out.append(rec)
        return out

    def team_profile(self, team) -> dict:
        """Cross-file view: match record per competition plus FIFA squad."""
        teams = self.find_teams(team)
        ms = self.search_matches(team)
        return {
            "team": " / ".join(sorted(teams)), "overall": _record(ms, teams),
            "home": _record(ms, teams, "home"), "away": _record(ms, teams, "away"),
            "competitions": self.team_competitions(team),
            "players": [p for t in sorted(teams) for p in self.search_players(club=t, limit=None)],
        }

    # ----------------------------------------------------------- competitions
    def _table(self, matches, venue="either") -> list:
        teams = sorted({t for m in matches for t in (m.home, m.away)})
        by_team = defaultdict(list)
        for m in matches:
            by_team[m.home].append(m)
            by_team[m.away].append(m)
        rows = []
        for t in teams:
            rec = _record(by_team[t], {t}, venue)
            rec["team"] = t
            rows.append(rec)
        return rows

    def standings(self, season, competition=SERIE_A) -> dict:
        comp = resolve_competition(competition) or SERIE_A
        season = _season(season)
        ms = self.search_matches(competition=comp, season=season)
        if not ms:
            raise ValueError(f"No {comp} matches for season {season}. Available seasons: "
                             f"{self.seasons(comp)}")
        # Drop stray rows (e.g. a friendly mislabelled as a league match in the source).
        counts = defaultdict(int)
        for m in ms:
            counts[m.home] += 1
            counts[m.away] += 1
        median = sorted(counts.values())[len(counts) // 2]
        stray = {t for t, c in counts.items() if c < median / 4}
        ms = [m for m in ms if m.home not in stray and m.away not in stray]
        rows = sorted(self._table(ms), key=RANK_METRICS["points"], reverse=True)
        unplayed = sum(not m.played for m in ms)
        league = comp == SERIE_A
        n = len(rows)
        # Double round-robin; tolerate one missing result (2016 had a cancelled match).
        complete = league and (len(ms) - unplayed) >= n * (n - 1) - 1
        n_releg = 2 if season == 2003 else 4
        for i, r in enumerate(rows, 1):
            r["position"] = i
            r["note"] = ""
            if complete and i == 1:
                r["note"] = "Champion"
            elif complete and i > len(rows) - n_releg:
                r["note"] = "Relegated"
        return {"competition": comp, "season": season, "table": rows, "complete": complete,
                "matches": len(ms), "unplayed": unplayed}

    def seasons(self, competition=None) -> list:
        comp = resolve_competition(competition)
        return sorted({m.season for m in self.matches if not comp or m.competition == comp})

    def bracket(self, season, competition=LIBERTADORES) -> dict:
        """Matches of a cup season grouped by stage/round, in playing order."""
        comp = resolve_competition(competition) or LIBERTADORES
        ms = self.search_matches(competition=comp, season=season)
        if not ms:
            raise ValueError(f"No {comp} matches for season {season}. Available seasons: "
                             f"{self.seasons(comp)}")
        stages = defaultdict(list)
        for m in reversed(ms):
            label = m.round or "unknown stage"
            if id(m) in self._finals:
                label = "final"
            elif label.isdigit():
                label = f"round {label}"
            stages[label].append(m)
        order = sorted(stages, key=lambda s: min((m.date or dt.date.max) for m in stages[s]))
        return {"competition": comp, "season": _season(season),
                "stages": [(s, stages[s]) for s in order]}

    # ------------------------------------------------------------- statistics
    def competition_stats(self, competition=None, season=None) -> dict:
        ms = [m for m in self.search_matches(competition=competition, season=season) if m.played]
        n = len(ms)
        goals = sum(m.home_goals + m.away_goals for m in ms)
        hw = sum(m.home_goals > m.away_goals for m in ms)
        dr = sum(m.home_goals == m.away_goals for m in ms)
        pct = lambda x: round(100 * x / n, 1) if n else 0.0  # noqa: E731
        return {
            "competition": resolve_competition(competition) or "All competitions",
            "season": _season(season), "matches": n, "goals": goals,
            "avg_goals": round(goals / n, 2) if n else 0.0,
            "home_goals": sum(m.home_goals for m in ms), "away_goals": sum(m.away_goals for m in ms),
            "home_win_rate": pct(hw), "draw_rate": pct(dr), "away_win_rate": pct(n - hw - dr),
        }

    def compare_seasons(self, seasons, competition=SERIE_A) -> list:
        out = []
        for s in seasons:
            st = self.competition_stats(competition or SERIE_A, s)
            try:
                table = self.standings(s, competition or SERIE_A)
                st["leader"] = table["table"][0]["team"]
                st["leader_points"] = table["table"][0]["points"]
                best = max(table["table"], key=lambda r: r["goals_for"])
                st["top_scoring_team"], st["top_scoring_goals"] = best["team"], best["goals_for"]
            except ValueError:
                st["leader"] = None
            out.append(st)
        return out

    def rank_teams(self, metric="win_rate", competition=None, season=None, venue="either",
                   min_matches=10, limit=10) -> list:
        """Rank teams by a record metric (best home/away record, most goals...)."""
        if metric not in RANK_METRICS:
            raise ValueError(f"metric must be one of {sorted(RANK_METRICS)}")
        venue = (venue or "either").lower()
        ms = self.search_matches(competition=competition, season=season)
        rows = [r for r in self._table(ms, venue) if r["matches"] >= max(1, int(min_matches))]
        rows.sort(key=RANK_METRICS[metric], reverse=True)
        return rows[:limit] if limit else rows

    def biggest_wins(self, competition=None, season=None, team=None, limit=10) -> list:
        ms = [m for m in self.search_matches(team, competition=competition, season=season)
              if m.played and m.home_goals != m.away_goals]
        ms.sort(key=lambda m: (abs(m.home_goals - m.away_goals), m.home_goals + m.away_goals),
                reverse=True)
        return ms[:limit] if limit else ms

    # ---------------------------------------------------------------- players
    def search_players(self, name=None, nationality=None, club=None, position=None,
                       min_overall=None, limit=20) -> list:
        """Players sorted by overall rating (highest first)."""
        out = self.players
        if nationality:
            nat = norm(nationality)
            nat = {"brazilian": "brazil", "brasil": "brazil", "brasileiro": "brazil"}.get(nat, nat)
            out = [p for p in out if norm(p.nationality) == nat]
        if club:
            cq = norm(club)
            ckey = team_key(club)[0]
            if ckey in CURATED:  # known Brazilian club: exact identity, not "Santos Laguna"
                out = [p for p in out if self._player_club_key[p.id] == ckey]
            else:
                out = [p for p in out if p.club and cq in norm(p.club)]
        if position:
            pq = norm(position).rstrip("s")
            pq = _POSITION_ALIASES.get(pq, pq)
            wanted = POSITION_GROUPS.get(pq) or {position.strip().upper()}
            out = [p for p in out if p.position in wanted]
        if min_overall is not None and min_overall != "":
            out = [p for p in out if p.overall >= int(min_overall)]
        if name:
            tokens = norm(name).split()
            names = [(p, norm(p.name)) for p in out]
            exact = [p for p, n in names if all(t in n for t in tokens)]
            if not exact and len(tokens) > 1:  # e.g. "Gabriel Barbosa" -> "Gabriel"
                exact = [p for p, n in names if n and all(w in tokens for w in n.split())]
            out = exact
        return out[:limit] if limit else list(out)

    def get_player(self, name_or_id) -> Optional[Player]:
        text = str(name_or_id).strip()
        if text.isdigit():
            return next((p for p in self.players if p.id == int(text)), None)
        hits = self.search_players(name=text, limit=None)
        exact = [p for p in hits if norm(p.name) == norm(text)]
        return (exact or hits or [None])[0]

    def club_summary(self, nationality="Brazil", brazilian_clubs_only=True) -> list:
        """Player count and average rating per club for one nationality."""
        groups = defaultdict(list)
        for p in self.search_players(nationality=nationality, limit=None):
            if not p.club:
                continue
            key = self._player_club_key[p.id]
            if brazilian_clubs_only and key not in CURATED:
                continue
            groups[key if key in CURATED else p.club].append(p)
        rows = [{"club": c, "players": len(ps),
                 "avg_overall": round(sum(p.overall for p in ps) / len(ps), 1),
                 "best_player": ps[0].name} for c, ps in groups.items()]
        return sorted(rows, key=lambda r: (-r["players"], -r["avg_overall"], r["club"]))

    # ---------------------------------------------------------------- summary
    def summary(self) -> dict:
        comps = {}
        for c in data.COMPETITIONS:
            ms = [m for m in self.matches if m.competition == c]
            ss = sorted({m.season for m in ms})
            comps[c] = {"matches": len(ms), "seasons": f"{ss[0]}-{ss[-1]}" if ss else ""}
        return {"source_rows": dict(self.source_rows), "unique_matches": len(self.matches),
                "teams": len(self.teams), "players": len(self.players), "competitions": comps}


@lru_cache(maxsize=1)
def load_default() -> KnowledgeBase:
    return KnowledgeBase()
