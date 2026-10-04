"""Query layer: every public function answers one family of questions.

Each function returns a ``dict`` with a human readable ``"text"`` answer (formatted
like the examples in TASK.md) and a machine readable ``"data"`` payload.  Invalid
input raises :class:`QueryError` with a helpful message (e.g. team suggestions).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable

from .data import (COMPETITIONS, COPA_DO_BRASIL, FILES, LIBERTADORES, SERIE_A, SERIE_B, SERIE_C, Match,
                   Player, SoccerDB, get_db, parse_date)
from .teams import Team, fold


class QueryError(ValueError):
    """Raised for invalid user input; the message is meant to be shown to the user."""


# --------------------------------------------------------------------------- parameter parsing

_COMPETITION_ALIASES = {
    SERIE_A: ["brasileirao", "brasileirao serie a", "serie a", "campeonato brasileiro", "brazilian league",
              "league", "brasileiro", "a"],
    SERIE_B: ["serie b", "brasileirao serie b", "b"],
    SERIE_C: ["serie c", "brasileirao serie c", "c"],
    COPA_DO_BRASIL: ["copa do brasil", "brazilian cup", "cup", "copa", "brazil cup"],
    LIBERTADORES: ["libertadores", "copa libertadores", "conmebol libertadores"],
}


def parse_competition(value: str | None) -> str | None:
    """Map free text ("Brasileirão", "serie a", "cup", "Libertadores") to a canonical competition name."""
    if value is None or not str(value).strip() or fold(str(value)) in {"all", "any"}:
        return None
    key = fold(str(value))
    for comp, aliases in _COMPETITION_ALIASES.items():
        if key == fold(comp) or key in aliases:
            return comp
    # Free text such as "Copa Libertadores da América" or "brasileirao 2019 serie b": most specific first.
    for comp, words in ((LIBERTADORES, ["libertadores"]), (COPA_DO_BRASIL, ["copa do brasil", "brazilian cup"]),
                        (SERIE_B, ["serie b"]), (SERIE_C, ["serie c"]),
                        (SERIE_A, ["serie a", "brasileirao", "brasileiro"])):
        if any(w in key for w in words):
            return comp
    raise QueryError(f"Unknown competition '{value}'. Choose one of: {', '.join(COMPETITIONS)}.")


def _season(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise QueryError(f"Season must be a year such as 2019, got '{value}'.") from None


def _date(value, name: str) -> date | None:
    if value is None or value == "":
        return None
    d = parse_date(str(value))
    if d is None:
        raise QueryError(f"Could not parse {name} '{value}'. Use YYYY-MM-DD or DD/MM/YYYY.")
    return d


def _venue(value: str | None) -> str:
    v = fold(value or "all")
    if v in {"all", "any", "either", "both", ""}:
        return "all"
    if v in {"home", "casa", "mandante"}:
        return "home"
    if v in {"away", "fora", "visitante"}:
        return "away"
    raise QueryError(f"venue must be 'home', 'away' or 'all', got '{value}'.")


def _limit(value, default: int, maximum: int = 500) -> int:
    if value is None or value == "":
        return default
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise QueryError(f"limit must be an integer, got '{value}'.") from None
    return max(1, min(n, maximum))


def _team(db: SoccerDB, name: str | None, role: str = "team") -> Team:
    if not name or not str(name).strip():
        raise QueryError(f"Please provide a {role} name.")
    team = db.find_team(str(name))
    if team is None:
        raise QueryError(f"No team matching '{name}' was found in the match data.")
    return team


def _pct(num: int, den: int) -> str:
    return f"{100.0 * num / den:.1f}%" if den else "n/a"


# --------------------------------------------------------------------------- derbies

DERBIES: list[tuple[str, str, str]] = [
    ("Fla-Flu", "flamengo", "fluminense"),
    ("Clássico dos Milhões", "flamengo", "vasco-da-gama"),
    ("Clássico da Rivalidade", "flamengo", "botafogo"),
    ("Clássico dos Gigantes", "fluminense", "vasco-da-gama"),
    ("Clássico Vovô", "botafogo", "fluminense"),
    ("Clássico da Amizade", "botafogo", "vasco-da-gama"),
    ("Derby Paulista", "corinthians", "palmeiras"),
    ("Choque-Rei", "palmeiras", "sao-paulo"),
    ("Majestoso", "corinthians", "sao-paulo"),
    ("San-São", "santos", "sao-paulo"),
    ("Clássico Alvinegro", "corinthians", "santos"),
    ("Clássico da Saudade", "palmeiras", "santos"),
    ("Grenal", "gremio", "internacional"),
    ("Clássico Mineiro", "atletico-mineiro", "cruzeiro"),
    ("Atletiba", "athletico-paranaense", "coritiba"),
    ("Ba-Vi", "bahia", "vitoria"),
    ("Clássico-Rei", "ceara", "fortaleza"),
    ("Clássico dos Clássicos", "nautico", "sport-recife"),
    ("Clássico das Multidões", "santa-cruz", "sport-recife"),
    ("Clássico da Ilha", "avai", "figueirense"),
    ("Derby Campineiro", "guarani", "ponte-preta"),
    ("Clássico Goiano", "atletico-goianiense", "goias"),
]
_DERBY_BY_PAIR = {frozenset((a, b)): name for name, a, b in DERBIES}


def derby_name(a: str, b: str) -> str | None:
    return _DERBY_BY_PAIR.get(frozenset((a, b)))


# --------------------------------------------------------------------------- records

@dataclass
class Record:
    team: Team
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    form: list[str] = field(default_factory=list)

    def add(self, gf: int, ga: int) -> None:
        self.played += 1
        self.goals_for += gf
        self.goals_against += ga
        if gf > ga:
            self.wins += 1
            self.form.append("W")
        elif gf == ga:
            self.draws += 1
            self.form.append("D")
        else:
            self.losses += 1
            self.form.append("L")

    @property
    def points(self) -> int:
        return 3 * self.wins + self.draws

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float:
        return self.wins / self.played if self.played else 0.0

    def to_dict(self) -> dict:
        return {"team": self.team.name, "played": self.played, "wins": self.wins, "draws": self.draws,
                "losses": self.losses, "goals_for": self.goals_for, "goals_against": self.goals_against,
                "goal_difference": self.goal_difference, "points": self.points,
                "win_rate": round(100 * self.win_rate, 1)}


def _record_for(team: Team, matches: Iterable[Match], venue: str = "all") -> Record:
    rec = Record(team)
    for m in sorted(matches, key=lambda m: m.date or date.min):
        if m.home.id == team.id and venue in ("all", "home"):
            rec.add(m.home_goals, m.away_goals)
        elif m.away.id == team.id and venue in ("all", "away"):
            rec.add(m.away_goals, m.home_goals)
    return rec


def _table(matches: Iterable[Match], venue: str = "all") -> list[Record]:
    recs: dict[str, Record] = {}
    for m in matches:
        if venue in ("all", "home"):
            recs.setdefault(m.home.id, Record(m.home)).add(m.home_goals, m.away_goals)
        if venue in ("all", "away"):
            recs.setdefault(m.away.id, Record(m.away)).add(m.away_goals, m.home_goals)
    return sorted(recs.values(), key=lambda r: (-r.points, -r.wins, -r.goal_difference, -r.goals_for,
                                                r.team.name))


def _filter(db: SoccerDB, team: Team | None = None, opponent: Team | None = None,
            competition: str | None = None, season: int | None = None, date_from: date | None = None,
            date_to: date | None = None, venue: str = "all", stage: str | None = None) -> list[Match]:
    pool = db.matches_by_team.get(team.id, []) if team else db.matches
    out = []
    stage_key = _stage_key(stage) if stage else None
    for m in pool:
        if competition and m.competition != competition:
            continue
        if season is not None and m.season != season:
            continue
        if date_from and (m.date is None or m.date < date_from):
            continue
        if date_to and (m.date is None or m.date > date_to):
            continue
        if team:
            if venue == "home" and m.home.id != team.id:
                continue
            if venue == "away" and m.away.id != team.id:
                continue
        if opponent and not m.involves(opponent.id):
            continue
        if stage_key and stage_key != _stage_key(m.stage or "") and stage_key != fold(m.round or ""):
            continue
        out.append(m)
    return out


def _stage_key(stage: str) -> str:
    """'Semi-finals', 'semifinal', 'SEMI FINAL' -> 'semifinal'; 'Group Stage' -> 'group'."""
    key = fold(stage).replace(" ", "").replace("stage", "")
    return key[:-1] if key.endswith("s") else key


def _filters_text(competition=None, season=None, date_from=None, date_to=None, venue="all", stage=None) -> str:
    bits = []
    if season is not None:
        bits.append(str(season))
    if competition:
        bits.append(competition)
    if stage:
        bits.append(f"stage '{stage}'")
    if date_from or date_to:
        bits.append(f"{date_from or '…'} to {date_to or '…'}")
    if venue != "all":
        bits.append(f"{venue} matches only")
    return ", ".join(bits)


# --------------------------------------------------------------------------- match queries

def search_matches(team: str | None = None, opponent: str | None = None, competition: str | None = None,
                   season=None, date_from=None, date_to=None, venue: str | None = "all",
                   stage: str | None = None, limit=20, order: str = "desc", db: SoccerDB | None = None) -> dict:
    """Find matches by team(s), competition, season, date range, venue and stage/round."""
    db = db or get_db()
    t = _team(db, team) if team else None
    o = _team(db, opponent, "opponent") if opponent else None
    if o and not t:
        t, o = o, None
    comp, season_, venue_ = parse_competition(competition), _season(season), _venue(venue)
    d_from, d_to = _date(date_from, "date_from"), _date(date_to, "date_to")
    limit_ = _limit(limit, 20)
    matches = _filter(db, t, o, comp, season_, d_from, d_to, venue_ if t else "all", stage)
    matches.sort(key=lambda m: m.date or date.min, reverse=(order != "asc"))

    if t and o:
        title = f"{t.name} vs {o.name}"
        if (dn := derby_name(t.id, o.id)):
            title += f" ({dn} derby)"
    elif t:
        title = f"Matches involving {t.name}"
    else:
        title = "Matches"
    filt = _filters_text(comp, season_, d_from, d_to, venue_ if t else "all", stage)
    lines = [f"{title}{' — ' + filt if filt else ''}:"]
    if not matches:
        lines.append("- No matches found in the dataset.")
    for m in matches[:limit_]:
        lines.append(f"- {m.line()}")
    if len(matches) > limit_:
        lines.append(f"- ... ({len(matches) - limit_} more matches in dataset)")
    lines.append(f"Total matches found: {len(matches)}")
    data = {"total": len(matches), "matches": [m.to_dict() for m in matches[:limit_]]}
    if t and o and matches:
        rec = _record_for(t, matches)
        lines.append(f"Head-to-head in dataset: {t.name} {rec.wins} wins, {o.name} {rec.losses} wins, "
                     f"{rec.draws} draws")
        data["head_to_head"] = {t.name: rec.wins, o.name: rec.losses, "draws": rec.draws}
    elif t and matches:
        rec = _record_for(t, matches, venue_)
        lines.append(f"Record in these matches: {rec.wins}W {rec.draws}D {rec.losses}L, "
                     f"goals {rec.goals_for}-{rec.goals_against}")
        data["record"] = rec.to_dict()
    return {"text": "\n".join(lines), "data": data}


def head_to_head(team_a: str, team_b: str, competition: str | None = None, season=None,
                 limit=10, db: SoccerDB | None = None) -> dict:
    """Head-to-head record between two teams, with last meeting, biggest wins and per-competition split."""
    db = db or get_db()
    a, b = _team(db, team_a, "first team"), _team(db, team_b, "second team")
    if a.id == b.id:
        raise QueryError("Please provide two different teams.")
    comp, season_ = parse_competition(competition), _season(season)
    matches = _filter(db, a, b, comp, season_)
    matches.sort(key=lambda m: m.date or date.min, reverse=True)
    title = f"{a.name} vs {b.name}"
    if (dn := derby_name(a.id, b.id)):
        title += f" ({dn} derby)"
    filt = _filters_text(comp, season_)
    lines = [f"{title}{' — ' + filt if filt else ''}:"]
    if not matches:
        lines.append("No matches between these teams were found in the dataset.")
        return {"text": "\n".join(lines), "data": {"total": 0, "team_a": a.name, "team_b": b.name}}
    rec = _record_for(a, matches)
    limit_ = _limit(limit, 10)
    for m in matches[:limit_]:
        lines.append(f"- {m.line()}")
    if len(matches) > limit_:
        lines.append(f"- ... ({len(matches) - limit_} more matches in dataset)")
    lines.append("")
    lines.append(f"Head-to-head in dataset: {a.name} {rec.wins} wins, {b.name} {rec.losses} wins, "
                 f"{rec.draws} draws ({rec.played} matches)")
    lines.append(f"Goals: {a.name} {rec.goals_for}, {b.name} {rec.goals_against}")
    last = matches[0]
    lines.append(f"Last meeting: {last.line()}")
    by_comp = defaultdict(list)
    for m in matches:
        by_comp[m.competition].append(m)
    split = {}
    if len(by_comp) > 1:
        lines.append("By competition:")
    for c, ms in sorted(by_comp.items(), key=lambda kv: -len(kv[1])):
        r = _record_for(a, ms)
        split[c] = {"matches": r.played, a.name: r.wins, b.name: r.losses, "draws": r.draws}
        if len(by_comp) > 1:
            lines.append(f"- {c}: {r.played} matches — {a.name} {r.wins}, {b.name} {r.losses}, draws {r.draws}")
    biggest = max(matches, key=lambda m: (m.margin, m.total_goals))
    if biggest.margin:
        lines.append(f"Biggest win: {biggest.line()}")
    data = {"team_a": a.name, "team_b": b.name, "derby": derby_name(a.id, b.id), "total": rec.played,
            "wins_a": rec.wins, "wins_b": rec.losses, "draws": rec.draws, "goals_a": rec.goals_for,
            "goals_b": rec.goals_against, "last_meeting": last.to_dict(), "by_competition": split,
            "matches": [m.to_dict() for m in matches[:limit_]]}
    return {"text": "\n".join(lines), "data": data}


# --------------------------------------------------------------------------- team queries

def team_record(team: str, season=None, competition: str | None = None, venue: str | None = "all",
                db: SoccerDB | None = None) -> dict:
    """Win/draw/loss record, goals and win rate, optionally filtered by season, competition and venue."""
    db = db or get_db()
    t = _team(db, team)
    comp, season_, venue_ = parse_competition(competition), _season(season), _venue(venue)
    matches = _filter(db, t, None, comp, season_, venue=venue_)
    rec = _record_for(t, matches, venue_)
    scope = []
    if season_:
        scope.append(str(season_))
    scope.append(comp or "all competitions")
    label = {"home": "home record", "away": "away record", "all": "record"}[venue_]
    lines = [f"{t.name} {label} ({' '.join(scope)}):"]
    if not rec.played:
        lines.append("- No matches found in the dataset for these filters.")
        return {"text": "\n".join(lines), "data": rec.to_dict()}
    lines += [
        f"- Matches: {rec.played}",
        f"- Wins: {rec.wins}, Draws: {rec.draws}, Losses: {rec.losses}",
        f"- Goals For: {rec.goals_for}, Goals Against: {rec.goals_against}",
        f"- Win rate: {_pct(rec.wins, rec.played)}",
        f"- Points (3 per win): {rec.points} ({rec.points / rec.played:.2f} per match)",
        f"- Last 5: {' '.join(rec.form[-5:])}",
    ]
    data = rec.to_dict()
    if venue_ == "all":
        home, away = _record_for(t, matches, "home"), _record_for(t, matches, "away")
        lines.append(f"- Home: {home.wins}W {home.draws}D {home.losses}L ({_pct(home.wins, home.played)} wins)"
                     f" | Away: {away.wins}W {away.draws}D {away.losses}L ({_pct(away.wins, away.played)} wins)")
        data["home"], data["away"] = home.to_dict(), away.to_dict()
    if not comp:
        by_comp = defaultdict(list)
        for m in matches:
            by_comp[m.competition].append(m)
        if len(by_comp) > 1:
            lines.append("By competition:")
            data["by_competition"] = {}
            for c in COMPETITIONS:
                if c in by_comp:
                    r = _record_for(t, by_comp[c], venue_)
                    data["by_competition"][c] = r.to_dict()
                    lines.append(f"- {c}: {r.played} matches, {r.wins}W {r.draws}D {r.losses}L, "
                                 f"goals {r.goals_for}-{r.goals_against}, win rate {_pct(r.wins, r.played)}")
    return {"text": "\n".join(lines), "data": data}


def team_profile(team: str, db: SoccerDB | None = None) -> dict:
    """Overview of a club across all files: competitions played, seasons, record, titles, FIFA squad."""
    db = db or get_db()
    t = _team(db, team)
    matches = db.matches_by_team.get(t.id, [])
    lines = [f"{t.name}" + (f" ({t.state})" if t.state and f"({t.state})" not in t.name else "") + ":"]
    rec = _record_for(t, matches)
    lines.append(f"Matches in dataset: {rec.played} ({rec.wins}W {rec.draws}D {rec.losses}L, "
                 f"goals {rec.goals_for}-{rec.goals_against})")
    lines.append("Competitions played:")
    comps = {}
    for c in COMPETITIONS:
        ms = [m for m in matches if m.competition == c]
        if not ms:
            continue
        seasons = sorted({m.season for m in ms})
        r = _record_for(t, ms)
        comps[c] = {"matches": len(ms), "seasons": seasons, "record": r.to_dict()}
        lines.append(f"- {c}: {len(ms)} matches in {len(seasons)} season(s) "
                     f"({_season_ranges(seasons)}), {r.wins}W {r.draws}D {r.losses}L")
    titles = []
    for season in sorted({m.season for m in matches if m.competition == SERIE_A}):
        table = _table(m for m in db.matches if m.competition == SERIE_A and m.season == season)
        if table and table[0].team.id == t.id and _season_complete(db, SERIE_A, season):
            titles.append(season)
    if titles:
        lines.append(f"Brasileirão titles (calculated from matches): {', '.join(map(str, titles))}")
    for comp in (COPA_DO_BRASIL, LIBERTADORES):
        won = [f["season"] for f in _finals(db, comp) if f.get("winner_id") == t.id]
        if won:
            lines.append(f"{comp} titles (from final results in dataset): {', '.join(map(str, won))}")
    players = [p for p in db.players if p.club_team and p.club_team.id == t.id]
    if players:
        avg = sum(p.overall for p in players) / len(players)
        top = ", ".join(f"{p.name} ({p.overall})" for p in players[:5])
        lines.append(f"FIFA squad: {len(players)} players, average overall {avg:.1f}; top: {top}")
    else:
        lines.append("FIFA squad: club not present in the FIFA player dataset.")
    data = {"team": t.name, "state": t.state, "record": rec.to_dict(), "competitions": comps,
            "brasileirao_titles": titles, "fifa_players": [p.name for p in players]}
    return {"text": "\n".join(lines), "data": data}


def _season_ranges(seasons: list[int]) -> str:
    out, start, prev = [], None, None
    for s in seasons:
        if start is None:
            start = prev = s
        elif s == prev + 1:
            prev = s
        else:
            out.append(f"{start}-{prev}" if start != prev else str(start))
            start = prev = s
    if start is not None:
        out.append(f"{start}-{prev}" if start != prev else str(start))
    return ", ".join(out)


# --------------------------------------------------------------------------- competition queries

def _relegation_spots(season: int, teams: int) -> int:
    if teams >= 20 and season >= 2004:
        return 4
    if season == 2003:
        return 2
    return 4 if teams >= 20 else 0


def _season_complete(db: SoccerDB, comp: str, season: int) -> bool:
    ms = [m for m in db.matches if m.competition == comp and m.season == season]
    teams = {m.home.id for m in ms} | {m.away.id for m in ms}
    return bool(teams) and len(ms) >= len(teams) * (len(teams) - 1)


def standings(season, competition: str | None = SERIE_A, top=None, db: SoccerDB | None = None) -> dict:
    """League table calculated from match results (3 pts win, 1 draw), with champion and relegated teams."""
    db = db or get_db()
    season_ = _season(season)
    if season_ is None:
        raise QueryError("Please provide a season, e.g. 2019.")
    comp = parse_competition(competition) or SERIE_A
    if comp in (COPA_DO_BRASIL, LIBERTADORES):
        raise QueryError(f"{comp} is a knockout competition; use the knockout_bracket or finals tools.")
    matches = [m for m in db.matches if m.competition == comp and m.season == season_]
    if not matches:
        seasons = sorted({m.season for m in db.matches if m.competition == comp})
        raise QueryError(f"No {comp} matches for {season_}. Seasons available: {_season_ranges(seasons)}.")
    table = _table(matches)
    complete = len(matches) >= len(table) * (len(table) - 1)
    rel = _relegation_spots(season_, len(table)) if comp == SERIE_A else 0
    title = f"{season_} {comp} {'Final Standings' if complete else 'Standings'} (calculated from matches)"
    lines = [title + ":"]
    top_n = _limit(top, len(table), len(table))
    for i, r in enumerate(table[:top_n], 1):
        tag = ""
        if i == 1 and complete and comp == SERIE_A:
            tag = " - Champion"
        elif rel and i > len(table) - rel:
            tag = " - Relegated"
        lines.append(f"{i}. {r.team.name} - {r.points} pts ({r.wins}W, {r.draws}D, {r.losses}L, "
                     f"GF {r.goals_for}, GA {r.goals_against}, GD {r.goal_difference:+d}){tag}")
    if top_n < len(table) and rel:
        lines.append("...")
        for i, r in enumerate(table[-rel:], len(table) - rel + 1):
            lines.append(f"{i}. {r.team.name} - {r.points} pts ({r.wins}W, {r.draws}D, {r.losses}L) - Relegated")
    if not complete:
        lines.append(f"Note: dataset has {len(matches)} of {len(table) * (len(table) - 1)} expected matches "
                     "for a double round-robin; table may be partial"
                     + (" (Série C uses a group/playoff format)." if comp == SERIE_C else "."))
    if comp == SERIE_A and complete:
        lines.append(f"Champion: {table[0].team.name}")
        if rel:
            lines.append(f"Relegated: {', '.join(r.team.name for r in table[-rel:])}")
    lines.append("Note: calculated purely from results; official tables may differ (points deductions, "
                 "tie-break rules).")
    data = {"season": season_, "competition": comp, "complete": complete,
            "champion": table[0].team.name if complete else None,
            "relegated": [r.team.name for r in table[-rel:]] if rel and complete else [],
            "table": [dict(position=i, **r.to_dict()) for i, r in enumerate(table, 1)]}
    return {"text": "\n".join(lines), "data": data}


_STAGE_ORDER = ["Group stage", "Round of 16", "Quarter-finals", "Semi-finals", "Final"]


def _ties(matches: list[Match]) -> list[dict]:
    """Group the legs of knockout ties and compute aggregates."""
    groups: dict[frozenset, list[Match]] = defaultdict(list)
    for m in matches:
        groups[frozenset((m.home.id, m.away.id))].append(m)
    ties = []
    for legs in groups.values():
        legs.sort(key=lambda m: m.date or date.min)
        a, b = legs[0].home, legs[0].away
        ga = sum(m.home_goals if m.home.id == a.id else m.away_goals for m in legs)
        gb = sum(m.home_goals if m.home.id == b.id else m.away_goals for m in legs)
        ties.append({"team_a": a, "team_b": b, "goals_a": ga, "goals_b": gb, "legs": legs,
                     "winner": a if ga > gb else b if gb > ga else None})
    ties.sort(key=lambda t: t["legs"][0].date or date.min)
    return ties


def _tie_line(tie: dict, advanced: Team | None = None) -> str:
    legs = "; ".join(f"{m.date or '?'} {m.home.name} {m.home_goals}-{m.away_goals} {m.away.name}"
                     for m in tie["legs"])
    a, b = tie["team_a"], tie["team_b"]
    winner = tie["winner"] or advanced
    result = f"{a.name} {tie['goals_a']}-{tie['goals_b']} {b.name}"
    if len(tie["legs"]) > 1:
        result += " on aggregate"
    if tie["winner"]:
        result += f" → {winner.name}"
    elif advanced:
        result += f" → {advanced.name} (level on goals; away goals/penalties not in data)"
    else:
        result += " (level on goals; decided by away goals/penalties, not in data)"
    return f"- {result}  [{legs}]"


def knockout_bracket(season, competition: str | None = LIBERTADORES, db: SoccerDB | None = None) -> dict:
    """Knockout ties (round of 16 to final) with aggregate scores for Libertadores or Copa do Brasil."""
    db = db or get_db()
    season_ = _season(season)
    if season_ is None:
        raise QueryError("Please provide a season, e.g. 2018.")
    comp = parse_competition(competition) or LIBERTADORES
    if comp not in (LIBERTADORES, COPA_DO_BRASIL):
        raise QueryError("Brackets are available for Copa Libertadores and Copa do Brasil.")
    matches = [m for m in db.matches if m.competition == comp and m.season == season_]
    if not matches:
        seasons = sorted({m.season for m in db.matches if m.competition == comp})
        raise QueryError(f"No {comp} matches for {season_}. Seasons available: {_season_ranges(seasons)}.")
    stages = [s for s in _STAGE_ORDER[1:] if any(m.stage == s for m in matches)]
    lines = [f"{season_} {comp} knockout bracket:"]
    data = {"season": season_, "competition": comp, "stages": {}}
    for i, stage in enumerate(stages):
        nxt = {t for m in matches if i + 1 < len(stages) and m.stage == stages[i + 1]
               for t in (m.home.id, m.away.id)}
        lines.append(f"{stage}:")
        stage_data = []
        for tie in _ties([m for m in matches if m.stage == stage]):
            advanced = None
            if tie["winner"] is None:
                a, b = tie["team_a"], tie["team_b"]
                advanced = a if a.id in nxt else b if b.id in nxt else None
            lines.append(_tie_line(tie, advanced))
            w = tie["winner"] or advanced
            stage_data.append({"team_a": tie["team_a"].name, "team_b": tie["team_b"].name,
                               "aggregate": f"{tie['goals_a']}-{tie['goals_b']}",
                               "winner": w.name if w else None,
                               "legs": [m.to_dict() for m in tie["legs"]]})
        data["stages"][stage] = stage_data
    if not stages:
        lines.append("No knockout-stage information for this season in the dataset.")
    final = data["stages"].get("Final")
    if final and final[0]["winner"]:
        lines.append(f"Champion: {final[0]['winner']}")
        data["champion"] = final[0]["winner"]
    return {"text": "\n".join(lines), "data": data}


def _finals(db: SoccerDB, comp: str) -> list[dict]:
    out = []
    for season in sorted({m.season for m in db.matches if m.competition == comp and m.stage == "Final"}):
        legs = [m for m in db.matches if m.competition == comp and m.season == season and m.stage == "Final"]
        for tie in _ties(legs):
            out.append({"season": season, "tie": tie,
                        "winner_id": tie["winner"].id if tie["winner"] else None})
    return out


def finals(competition: str | None = COPA_DO_BRASIL, season=None, db: SoccerDB | None = None) -> dict:
    """All finals (with aggregate score and winner) of Copa do Brasil or Copa Libertadores."""
    db = db or get_db()
    comp = parse_competition(competition) or COPA_DO_BRASIL
    if comp not in (LIBERTADORES, COPA_DO_BRASIL):
        raise QueryError("Finals are available for Copa do Brasil and Copa Libertadores.")
    season_ = _season(season)
    items = [f for f in _finals(db, comp) if season_ is None or f["season"] == season_]
    lines = [f"{comp} finals in dataset:"]
    data = []
    for f in items:
        lines.append(f"{f['season']}: " + _tie_line(f["tie"])[2:])
        tie = f["tie"]
        data.append({"season": f["season"], "team_a": tie["team_a"].name, "team_b": tie["team_b"].name,
                     "aggregate": f"{tie['goals_a']}-{tie['goals_b']}",
                     "winner": tie["winner"].name if tie["winner"] else None,
                     "legs": [m.to_dict() for m in tie["legs"]]})
    if not items:
        lines.append("- No finals found for these filters.")
    return {"text": "\n".join(lines), "data": {"competition": comp, "finals": data}}


# --------------------------------------------------------------------------- statistics

_METRICS = {
    "points": ("points", True), "wins": ("wins", True), "win_rate": ("win_rate", True),
    "goals_for": ("goals_for", True), "goals_scored": ("goals_for", True), "goals": ("goals_for", True),
    "goals_against": ("goals_against", False), "goals_conceded": ("goals_against", False),
    "goal_difference": ("goal_difference", True), "losses": ("losses", True), "draws": ("draws", True),
}


def team_rankings(metric: str = "win_rate", competition: str | None = SERIE_A, season=None,
                  venue: str | None = "all", min_matches=None, limit=10, db: SoccerDB | None = None) -> dict:
    """Rank teams by a metric (win_rate, points, goals_for, goals_against, goal_difference, wins...)."""
    db = db or get_db()
    key = fold(metric or "win_rate").replace(" ", "_")
    if key not in _METRICS:
        raise QueryError(f"Unknown metric '{metric}'. Choose one of: {', '.join(sorted(_METRICS))}.")
    attr, desc = _METRICS[key]
    comp, season_, venue_ = parse_competition(competition), _season(season), _venue(venue)
    matches = _filter(db, None, None, comp, season_)
    table = _table(matches, venue_)
    if min_matches is None:
        min_matches = 10 if season_ else 38
    min_m = int(min_matches)
    table = [r for r in table if r.played >= min_m]
    table.sort(key=lambda r: ((-1 if desc else 1) * getattr(r, attr), -r.played, r.team.name))
    limit_ = _limit(limit, 10)
    scope = " ".join(x for x in [str(season_) if season_ else "", comp or "all competitions"] if x)
    venue_txt = {"all": "", "home": " (home matches)", "away": " (away matches)"}[venue_]
    lines = [f"Teams ranked by {attr.replace('_', ' ')}{venue_txt} — {scope} (min {min_m} matches):"]
    for i, r in enumerate(table[:limit_], 1):
        value = _pct(r.wins, r.played) if attr == "win_rate" else getattr(r, attr)
        lines.append(f"{i}. {r.team.name} - {attr.replace('_', ' ')}: {value} "
                     f"({r.played} matches, {r.wins}W {r.draws}D {r.losses}L, GF {r.goals_for}, GA {r.goals_against})")
    if not table:
        lines.append("- No teams meet the criteria.")
    return {"text": "\n".join(lines),
            "data": {"metric": attr, "venue": venue_, "ranking": [r.to_dict() for r in table[:limit_]]}}


def competition_stats(competition: str | None = None, season=None, db: SoccerDB | None = None) -> dict:
    """Goals per match, home/draw/away rates, common scorelines and extended stats for a competition/season."""
    db = db or get_db()
    comp, season_ = parse_competition(competition), _season(season)
    matches = _filter(db, None, None, comp, season_)
    scope = " ".join(x for x in [str(season_) if season_ else "", comp or "all competitions"] if x)
    if not matches:
        raise QueryError(f"No matches found for {scope}.")
    n = len(matches)
    goals = sum(m.total_goals for m in matches)
    hw = sum(1 for m in matches if m.home_goals > m.away_goals)
    dr = sum(1 for m in matches if m.home_goals == m.away_goals)
    aw = n - hw - dr
    scorelines = Counter(f"{m.home_goals}-{m.away_goals}" for m in matches).most_common(5)
    highest = max(matches, key=lambda m: (m.total_goals, m.margin))
    lines = [f"Statistics — {scope}:",
             f"- Matches: {n}",
             f"- Total goals: {goals}",
             f"- Average goals per match: {goals / n:.2f}",
             f"- Home goals per match: {sum(m.home_goals for m in matches) / n:.2f}, "
             f"away goals per match: {sum(m.away_goals for m in matches) / n:.2f}",
             f"- Home win rate: {_pct(hw, n)}, Draw rate: {_pct(dr, n)}, Away win rate: {_pct(aw, n)}",
             f"- Most common scorelines: {', '.join(f'{s} ({c})' for s, c in scorelines)}",
             f"- Highest-scoring match: {highest.line()}"]
    data = {"scope": scope, "matches": n, "goals": goals, "avg_goals": round(goals / n, 2),
            "home_win_rate": round(100 * hw / n, 1), "draw_rate": round(100 * dr / n, 1),
            "away_win_rate": round(100 * aw / n, 1), "common_scorelines": scorelines}
    with_stats = [m for m in matches if "home_shots" in m.stats]
    if with_stats:
        k = len(with_stats)
        corners = sum(m.stats.get("home_corner", 0) + m.stats.get("away_corner", 0) for m in with_stats) / k
        shots = sum(m.stats.get("home_shots", 0) + m.stats.get("away_shots", 0) for m in with_stats) / k
        lines.append(f"- Extended stats ({k} matches): {corners:.1f} corners and {shots:.1f} shots per match")
        data.update(avg_corners=round(corners, 1), avg_shots=round(shots, 1))
    if not comp:
        lines.append("By competition:")
        for c in COMPETITIONS:
            ms = [m for m in matches if m.competition == c]
            if ms:
                lines.append(f"- {c}: {len(ms)} matches, {sum(m.total_goals for m in ms) / len(ms):.2f} goals/match, "
                             f"home win rate {_pct(sum(1 for m in ms if m.home_goals > m.away_goals), len(ms))}")
    return {"text": "\n".join(lines), "data": data}


def biggest_wins(competition: str | None = None, season=None, team: str | None = None, limit=10,
                 db: SoccerDB | None = None) -> dict:
    """Largest victory margins (ties broken by goals scored)."""
    db = db or get_db()
    t = _team(db, team) if team else None
    comp, season_ = parse_competition(competition), _season(season)
    matches = [m for m in _filter(db, t, None, comp, season_) if m.margin > 0]
    if t:
        matches = [m for m in matches if m.winner and m.winner.id == t.id]
    matches.sort(key=lambda m: (-m.margin, -max(m.home_goals, m.away_goals), m.date or date.min))
    limit_ = _limit(limit, 10)
    scope = " ".join(x for x in [str(season_) if season_ else "", comp or "all competitions"] if x)
    lines = [f"Biggest victories{' by ' + t.name if t else ''} — {scope}:"]
    for i, m in enumerate(matches[:limit_], 1):
        d = m.date.isoformat() if m.date else "?"
        lines.append(f"{i}. {d}: {m.home.name} {m.home_goals}-{m.away_goals} {m.away.name} ({m.label()})")
    if not matches:
        lines.append("- No wins found.")
    return {"text": "\n".join(lines), "data": {"matches": [m.to_dict() for m in matches[:limit_]]}}


def derbies(season=None, rivalry: str | None = None, competition: str | None = None, limit=50,
            db: SoccerDB | None = None) -> dict:
    """Matches between traditional rivals (Fla-Flu, Grenal, Derby Paulista, ...)."""
    db = db or get_db()
    comp, season_ = parse_competition(competition), _season(season)
    wanted = None
    if rivalry:
        key = fold(rivalry)
        wanted = {frozenset((a, b)) for name, a, b in DERBIES if key in fold(name) or fold(name) in key}
        if not wanted:
            raise QueryError(f"Unknown rivalry '{rivalry}'. Known derbies: {', '.join(n for n, _, _ in DERBIES)}.")
    pairs = wanted or set(_DERBY_BY_PAIR)
    matches = [m for m in _filter(db, None, None, comp, season_) if frozenset((m.home.id, m.away.id)) in pairs]
    matches.sort(key=lambda m: m.date or date.min, reverse=True)
    limit_ = _limit(limit, 50)
    scope = " ".join(x for x in [str(season_) if season_ else "", comp or ""] if x)
    lines = [f"Derby matches{' — ' + scope if scope else ''}:"]
    for m in matches[:limit_]:
        lines.append(f"- [{derby_name(m.home.id, m.away.id)}] {m.line()}")
    if len(matches) > limit_:
        lines.append(f"- ... ({len(matches) - limit_} more)")
    lines.append(f"Total derby matches: {len(matches)}")
    counts = Counter(derby_name(m.home.id, m.away.id) for m in matches)
    if len(counts) > 1:
        lines.append("By rivalry: " + ", ".join(f"{k} ({v})" for k, v in counts.most_common()))
    return {"text": "\n".join(lines),
            "data": {"total": len(matches), "by_rivalry": dict(counts),
                     "matches": [dict(m.to_dict(), derby=derby_name(m.home.id, m.away.id))
                                 for m in matches[:limit_]]}}


def compare_seasons(season_a, season_b, competition: str | None = SERIE_A, db: SoccerDB | None = None) -> dict:
    """Side-by-side statistics for two seasons of a competition."""
    db = db or get_db()
    comp = parse_competition(competition) or SERIE_A
    sa, sb = _season(season_a), _season(season_b)
    if sa is None or sb is None:
        raise QueryError("Please provide two seasons to compare.")
    rows = []
    for s in (sa, sb):
        stats = competition_stats(comp, s, db=db)["data"]
        row = dict(stats, season=s)
        if comp in (SERIE_A, SERIE_B):
            st = standings(s, comp, db=db)["data"]
            top = st["table"][0]
            row.update(leader=top["team"], leader_points=top["points"], champion=st["champion"],
                       relegated=st["relegated"],
                       best_attack=max(st["table"], key=lambda r: r["goals_for"])["team"],
                       best_defence=min(st["table"], key=lambda r: r["goals_against"])["team"])
        rows.append(row)
    a, b = rows
    lines = [f"{comp}: {sa} vs {sb}",
             f"- Matches: {a['matches']} vs {b['matches']}",
             f"- Goals: {a['goals']} vs {b['goals']}",
             f"- Average goals per match: {a['avg_goals']:.2f} vs {b['avg_goals']:.2f}",
             f"- Home win rate: {a['home_win_rate']}% vs {b['home_win_rate']}%",
             f"- Draw rate: {a['draw_rate']}% vs {b['draw_rate']}%",
             f"- Away win rate: {a['away_win_rate']}% vs {b['away_win_rate']}%"]
    if "leader" in a:
        lines += [f"- Champion/leader: {a['leader']} ({a['leader_points']} pts) vs {b['leader']} ({b['leader_points']} pts)",
                  f"- Best attack: {a['best_attack']} vs {b['best_attack']}",
                  f"- Best defence: {a['best_defence']} vs {b['best_defence']}"]
        if a["relegated"] or b["relegated"]:
            lines.append(f"- Relegated: {', '.join(a['relegated']) or 'n/a'} vs {', '.join(b['relegated']) or 'n/a'}")
    return {"text": "\n".join(lines), "data": {"competition": comp, "seasons": rows}}


# --------------------------------------------------------------------------- players

_NATIONALITY = {
    "brazilian": "Brazil", "brasil": "Brazil", "brasileiro": "Brazil", "argentine": "Argentina",
    "argentinian": "Argentina", "uruguayan": "Uruguay", "colombian": "Colombia", "chilean": "Chile",
    "paraguayan": "Paraguay", "peruvian": "Peru", "ecuadorian": "Ecuador", "venezuelan": "Venezuela",
    "bolivian": "Bolivia", "portuguese": "Portugal", "spanish": "Spain", "french": "France",
    "german": "Germany", "english": "England", "italian": "Italy", "dutch": "Netherlands",
    "belgian": "Belgium", "mexican": "Mexico", "american": "United States", "usa": "United States",
}

POSITION_GROUPS = {
    "forward": {"ST", "CF", "LW", "RW", "LS", "RS", "LF", "RF"},
    "midfielder": {"CM", "CAM", "CDM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"},
    "defender": {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
    "goalkeeper": {"GK"},
}
_POSITION_WORDS = {"forwards": "forward", "attacker": "forward", "attackers": "forward", "striker": "forward",
                   "strikers": "forward", "winger": "forward", "wingers": "forward", "midfielders": "midfielder",
                   "midfield": "midfielder", "defenders": "defender", "defence": "defender", "defense": "defender",
                   "goalkeepers": "goalkeeper", "keeper": "goalkeeper", "keepers": "goalkeeper"}


def _positions(value: str | None) -> set[str] | None:
    if not value:
        return None
    out: set[str] = set()
    for part in str(value).replace("/", ",").split(","):
        p = part.strip()
        if not p:
            continue
        word = _POSITION_WORDS.get(p.lower(), p.lower())
        if word in POSITION_GROUPS:
            out |= POSITION_GROUPS[word]
        else:
            out.add(p.upper())
    return out


def _nationality(value: str | None) -> str | None:
    if not value:
        return None
    return _NATIONALITY.get(fold(value), value)


def _club_filter(db: SoccerDB, club: str):
    """Return a predicate for a club name: canonical match for Brazilian clubs, else substring."""
    from .teams import normalize_team
    team = normalize_team(club)
    q = fold(club)
    if team.known:
        return lambda p: (p.club_team is not None and p.club_team.id == team.id)
    return lambda p: q in fold(p.club)


def _player_matches(name: str, p: Player) -> int:
    """0 = exact, 1 = all words contained, 2 = partial; -1 = no match."""
    q, n = fold(name), fold(p.name)
    if q == n:
        return 0
    words = q.split()
    if all(w in n.split() or w in n for w in words):
        return 1
    if any(len(w) >= 4 and w in n for w in words):
        return 2
    return -1


def search_players(name: str | None = None, nationality: str | None = None, club: str | None = None,
                   position: str | None = None, min_overall=None, max_age=None,
                   brazilian_clubs_only: bool = False, sort_by: str = "overall", limit=20,
                   db: SoccerDB | None = None) -> dict:
    """Search FIFA players by name, nationality, club, position, rating and age."""
    db = db or get_db()
    nat = _nationality(nationality)
    positions = _positions(position)
    club_pred = _club_filter(db, club) if club else None
    min_o = int(min_overall) if min_overall not in (None, "") else None
    max_a = int(max_age) if max_age not in (None, "") else None
    sort_key = fold(sort_by or "overall").replace(" ", "_")
    sorters = {"overall": lambda p: (-p.overall, p.name), "potential": lambda p: (-p.potential, p.name),
               "age": lambda p: (p.age or 99, -p.overall), "value": lambda p: (-(p.value_eur or 0), p.name),
               "name": lambda p: fold(p.name)}
    if sort_key not in sorters:
        raise QueryError(f"sort_by must be one of {', '.join(sorters)}.")
    results = []
    for p in db.players:
        if nat and fold(p.nationality) != fold(nat):
            continue
        if positions and p.position not in positions:
            continue
        if club_pred and not club_pred(p):
            continue
        if min_o is not None and p.overall < min_o:
            continue
        if max_a is not None and (p.age is None or p.age > max_a):
            continue
        if brazilian_clubs_only and not p.at_brazilian_club:
            continue
        rank = _player_matches(name, p) if name else 0
        if rank < 0:
            continue
        results.append((rank, p))
    if name and any(r < 2 for r, _ in results):
        results = [(r, p) for r, p in results if r < 2]
    if name:
        results.sort(key=lambda rp: (rp[0], sorters[sort_key](rp[1])))
    else:
        results.sort(key=lambda rp: sorters[sort_key](rp[1]))
    players = [p for _, p in results]
    limit_ = _limit(limit, 20)
    crit = [f"name '{name}'" if name else "", f"nationality {nat}" if nat else "", f"club '{club}'" if club else "",
            f"position {position}" if position else "", f"overall ≥ {min_o}" if min_o else "",
            f"age ≤ {max_a}" if max_a else "", "at Brazilian clubs" if brazilian_clubs_only else ""]
    crit_txt = ", ".join(c for c in crit if c) or "all players"
    lines = [f"Players ({crit_txt}) — {len(players)} found, sorted by {sort_key}:"]
    for i, p in enumerate(players[:limit_], 1):
        lines.append(f"{i}. {p.line()}, Age: {p.age}, Nationality: {p.nationality}")
    if len(players) > limit_:
        lines.append(f"... ({len(players) - limit_} more)")
    if not players:
        lines.append("- No players found in the FIFA dataset.")
        if club:
            lines.append(_missing_club_note(db))
    return {"text": "\n".join(lines),
            "data": {"total": len(players), "players": [p.to_dict() for p in players[:limit_]]}}


def _missing_club_note(db: SoccerDB) -> str:
    clubs = sorted({p.club_team.name for p in db.players if p.club_team})
    return ("Note: the FIFA dataset only contains these Brazilian clubs: " + ", ".join(clubs) +
            " (e.g. Flamengo, Palmeiras, Corinthians and São Paulo are not licensed in it).")


def player_profile(name: str, db: SoccerDB | None = None) -> dict:
    """Detailed profile (ratings and attributes) for the best name match; lists similar names otherwise."""
    db = db or get_db()
    if not name or not name.strip():
        raise QueryError("Please provide a player name.")
    ranked = sorted(((r, p) for p in db.players if (r := _player_matches(name, p)) >= 0),
                    key=lambda rp: (rp[0], -rp[1].overall))
    if not ranked or ranked[0][0] == 2:
        suggestions = [p.name + f" ({p.club or 'no club'})" for _, p in ranked[:8]]
        text = f"No player named '{name}' found in the FIFA dataset."
        if suggestions:
            text += " Similar names: " + "; ".join(suggestions)
        return {"text": text, "data": {"found": False, "suggestions": suggestions}}
    p = ranked[0][1]
    attrs = p.attributes
    top_attrs = sorted(((k, v) for k, v in attrs.items() if not k.startswith("GK") or p.position == "GK"),
                       key=lambda kv: -kv[1])[:6]
    lines = [f"{p.name}",
             f"- Club: {p.club or 'Free agent'}" + (" (Brazilian club)" if p.at_brazilian_club else ""),
             f"- Nationality: {p.nationality}, Age: {p.age}",
             f"- Position: {p.position or '?'}, Jersey number: {p.jersey_number or '?'}",
             f"- Overall: {p.overall}, Potential: {p.potential}",
             f"- Height: {p.height_cm or '?'} cm, Weight: {p.weight_kg or '?'} kg, Preferred foot: {p.preferred_foot}",
             f"- Value: €{(p.value_eur or 0) / 1e6:.1f}M, Wage: €{(p.wage_eur or 0) / 1e3:.0f}K, "
             f"Contract until: {p.contract_until or '?'}",
             "- Best attributes: " + ", ".join(f"{k} {v}" for k, v in top_attrs)]
    others = [q for r, q in ranked[1:6] if r <= 1]
    if others:
        lines.append("Other matching players: " + "; ".join(f"{q.name} ({q.club or 'no club'}, {q.overall})"
                                                           for q in others))
    if p.club_team:
        rec = _record_for(p.club_team, db.matches_by_team.get(p.club_team.id, []))
        if rec.played:
            lines.append(f"Club match record in dataset ({p.club_team.name}): {rec.played} matches, "
                         f"{rec.wins}W {rec.draws}D {rec.losses}L")
    return {"text": "\n".join(lines), "data": {"found": True, "player": p.to_dict(),
                                                "other_matches": [q.name for q in others]}}


def club_players(team: str, position: str | None = None, limit=30, db: SoccerDB | None = None) -> dict:
    """Players registered at a club in the FIFA data, best first, plus the club's match record (cross-file)."""
    db = db or get_db()
    if not team or not team.strip():
        raise QueryError("Please provide a club name.")
    pred = _club_filter(db, team)
    positions = _positions(position)
    players = [p for p in db.players if pred(p) and (not positions or p.position in positions)]
    limit_ = _limit(limit, 30)
    club_name = players[0].club if players else team
    lines = [f"Players at {club_name} (FIFA data){' — ' + position if position else ''}:"]
    for i, p in enumerate(players[:limit_], 1):
        lines.append(f"{i}. {p.name} - Overall: {p.overall}, Position: {p.position or '?'}, Age: {p.age}, "
                     f"Nationality: {p.nationality}")
    if players:
        avg = sum(p.overall for p in players) / len(players)
        brazilians = sum(1 for p in players if p.nationality == "Brazil")
        lines.append(f"Total: {len(players)} players, average overall {avg:.1f}, {brazilians} Brazilian")
    else:
        lines.append("- No players found for this club in the FIFA dataset.")
        lines.append(_missing_club_note(db))
    match_team = db.find_team(team)
    data = {"club": club_name, "total": len(players), "players": [p.to_dict() for p in players[:limit_]]}
    if match_team and players and players[0].club_team and match_team.id == players[0].club_team.id:
        rec = _record_for(match_team, db.matches_by_team.get(match_team.id, []))
        lines.append(f"Match record in dataset: {rec.played} matches, {rec.wins}W {rec.draws}D {rec.losses}L")
        data["match_record"] = rec.to_dict()
    return {"text": "\n".join(lines), "data": data}


def brazilian_players_overview(limit=10, db: SoccerDB | None = None) -> dict:
    """Top-rated Brazilian players and a summary of Brazilian players at Brazilian clubs."""
    db = db or get_db()
    limit_ = _limit(limit, 10)
    brazilians = [p for p in db.players if p.nationality == "Brazil"]
    lines = [f"Top-rated Brazilian players in dataset ({len(brazilians)} Brazilian players in total):"]
    for i, p in enumerate(brazilians[:limit_], 1):
        lines.append(f"{i}. {p.line()}")
    by_club: dict[str, list[Player]] = defaultdict(list)
    for p in brazilians:
        if p.at_brazilian_club:
            by_club[p.club].append(p)
    lines.append("")
    lines.append("Brazilian players at Brazilian clubs:")
    clubs = sorted(by_club.items(), key=lambda kv: (-len(kv[1]), -sum(p.overall for p in kv[1]) / len(kv[1])))
    summary = []
    for club, ps in clubs:
        avg = sum(p.overall for p in ps) / len(ps)
        summary.append({"club": club, "players": len(ps), "avg_overall": round(avg, 1)})
        lines.append(f"- {club}: {len(ps)} players (avg rating: {avg:.0f})")
    abroad = Counter(p.club for p in brazilians if p.club and not p.at_brazilian_club).most_common(5)
    lines.append("Top foreign clubs by number of Brazilians: " + ", ".join(f"{c} ({n})" for c, n in abroad))
    return {"text": "\n".join(lines),
            "data": {"total_brazilians": len(brazilians), "top": [p.to_dict() for p in brazilians[:limit_]],
                     "brazilian_clubs": summary}}


# --------------------------------------------------------------------------- meta

def dataset_info(db: SoccerDB | None = None) -> dict:
    """Which files were loaded, how many rows, and coverage per competition and season."""
    db = db or get_db()
    lines = ["Datasets loaded:"]
    for name in FILES.values():
        rows = db.source_rows.get(name, 0)
        skipped = db.skipped_rows.get(name, 0)
        merged = db.merged_rows.get(name, 0)
        extra = []
        if skipped:
            extra.append(f"{skipped} skipped (missing score/unplayed or spurious)")
        if merged:
            extra.append(f"{merged} merged with the same match from another file")
        lines.append(f"- {name}: {rows} rows" + (f" ({'; '.join(extra)})" if extra else ""))
    lines.append(f"Unified matches: {len(db.matches)}; teams: {len(db.matches_by_team)}; players: {len(db.players)}")
    coverage = {}
    for c in COMPETITIONS:
        seasons = sorted({m.season for m in db.matches if m.competition == c})
        n = sum(1 for m in db.matches if m.competition == c)
        coverage[c] = {"matches": n, "seasons": seasons}
        lines.append(f"- {c}: {n} matches, seasons {_season_ranges(seasons)}")
    lines.append(f"Score disagreements between files (primary file kept): {db.score_conflicts}")
    return {"text": "\n".join(lines), "data": {"files": db.source_rows, "matches": len(db.matches),
                                                "players": len(db.players), "coverage": coverage}}


def find_team(name: str, db: SoccerDB | None = None) -> dict:
    """Show how a team name is resolved (normalisation) and the closest candidates."""
    db = db or get_db()
    cands = db.find_teams(name, limit=8)
    if not cands:
        raise QueryError(f"No team matching '{name}'.")
    lines = [f"Team name '{name}' resolves to: {cands[0].name}" + (f" ({cands[0].state})" if cands[0].state else "")]
    if len(cands) > 1:
        lines.append("Other candidates: " + ", ".join(
            f"{t.name} ({len(db.matches_by_team.get(t.id, []))} matches)" for t in cands[1:]))
    comps = db.competitions_for(cands[0].id)
    lines.append("Matches by competition: " + ", ".join(f"{c}: {n}" for c, n in comps.most_common()))
    return {"text": "\n".join(lines), "data": {"team": cands[0].name, "id": cands[0].id,
                                                "candidates": [t.name for t in cands]}}
