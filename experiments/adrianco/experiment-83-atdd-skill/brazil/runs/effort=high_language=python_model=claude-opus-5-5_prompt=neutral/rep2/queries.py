"""Query engine: answers match, team, player, competition and statistics
questions over the loaded datasets and formats human-readable answers.

Every public method of `SoccerQueries` returns a formatted string and is
exposed one-to-one as an MCP tool by server.py.  Lower-level helpers
(`filter_matches`, `standings_table`, `team_records`, `find_players`) return
structured data and are used by tests and by the formatting methods.
"""

from __future__ import annotations

import difflib
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date

from data_loader import (
    COMPETITIONS,
    LEAGUES,
    LIBERTADORES,
    SERIE_A,
    SERIE_B,
    Match,
    Player,
    SoccerData,
    get_data,
    parse_date,
    resolve_competition,
)
from team_names import (
    ALIASES,
    CLUBS_BY_ID,
    DERBIES,
    FIFA_CLUB_TO_TEAM,
    TEAM_TO_FIFA_CLUB,
    canonical_team_id,
    derby_name,
    normalize_text,
)


class QueryError(ValueError):
    """Raised for invalid user input; the message is shown to the user."""


# ---------------------------------------------------------------- records
@dataclass
class Record:
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0

    def add(self, gf: int, ga: int) -> None:
        self.played += 1
        self.goals_for += gf
        self.goals_against += ga
        if gf > ga:
            self.wins += 1
        elif gf == ga:
            self.draws += 1
        else:
            self.losses += 1

    @property
    def points(self) -> int:
        return 3 * self.wins + self.draws

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float:
        return 100.0 * self.wins / self.played if self.played else 0.0

    @property
    def points_per_match(self) -> float:
        return self.points / self.played if self.played else 0.0

    @property
    def goals_per_match(self) -> float:
        return self.goals_for / self.played if self.played else 0.0

    def summary(self) -> str:
        return (f"{self.played} matches, {self.wins}W {self.draws}D {self.losses}L, "
                f"GF {self.goals_for} GA {self.goals_against}, win rate {self.win_rate:.1f}%")


@dataclass
class StandingRow:
    position: int
    team_id: str
    team: str
    record: Record
    note: str = ""


def _pct(n: int, d: int) -> float:
    return 100.0 * n / d if d else 0.0


def _signed(n: int) -> str:
    return f"+{n}" if n > 0 else str(n)


_VENUES = {"any": "all", "all": "all", "both": "all", "": "all", "home": "home", "away": "away"}

_STAGE_ALIASES = {
    "final": "final", "finals": "final", "decisao": "final",
    "semifinal": "semifinals", "semifinals": "semifinals", "semi final": "semifinals", "semi finals": "semifinals",
    "semis": "semifinals", "semi": "semifinals",
    "quarterfinal": "quarterfinals", "quarterfinals": "quarterfinals", "quarter final": "quarterfinals",
    "quarter finals": "quarterfinals", "quarters": "quarterfinals",
    "round of 16": "round of 16", "r16": "round of 16", "last 16": "round of 16", "oitavas": "round of 16",
    "group": "group stage", "group stage": "group stage", "groups": "group stage",
}

_STAGE_ORDER = ["group stage"] + [f"round {i}" for i in range(1, 10)] + [
    "round of 16", "quarterfinals", "semifinals", "final"]

_POSITION_GROUPS = {
    "goalkeeper": {"GK"},
    "defender": {"CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"},
    "midfielder": {"CDM", "LDM", "RDM", "CM", "LCM", "RCM", "CAM", "LAM", "RAM", "LM", "RM"},
    "forward": {"ST", "LS", "RS", "CF", "LF", "RF", "LW", "RW"},
}
_POSITION_WORDS = {
    "gk": "goalkeeper", "goalkeeper": "goalkeeper", "goalkeepers": "goalkeeper", "keeper": "goalkeeper",
    "keepers": "goalkeeper", "goleiro": "goalkeeper",
    "defender": "defender", "defenders": "defender", "defence": "defender", "defense": "defender",
    "midfielder": "midfielder", "midfielders": "midfielder", "midfield": "midfielder",
    "forward": "forward", "forwards": "forward", "attacker": "forward", "attackers": "forward",
    "striker": "forward", "strikers": "forward", "atacante": "forward",
}
_NATIONALITY_WORDS = {
    "brazilian": "brazil", "brasil": "brazil", "argentine": "argentina", "argentinian": "argentina",
    "uruguayan": "uruguay", "paraguayan": "paraguay", "chilean": "chile", "colombian": "colombia",
    "peruvian": "peru", "ecuadorian": "ecuador", "venezuelan": "venezuela", "bolivian": "bolivia",
    "portuguese": "portugal", "spanish": "spain", "french": "france", "german": "germany",
    "italian": "italy", "english": "england", "dutch": "netherlands", "belgian": "belgium",
    "mexican": "mexico", "american": "united states", "usa": "united states",
}

_RANK_METRICS = {
    "points": (lambda r: r.points, False, "pts"),
    "wins": (lambda r: r.wins, False, "wins"),
    "win_rate": (lambda r: r.win_rate, False, "% wins"),
    "goals_for": (lambda r: r.goals_for, False, "goals scored"),
    "goals_against": (lambda r: r.goals_against, True, "goals conceded"),
    "goal_difference": (lambda r: r.goal_difference, False, "goal difference"),
    "goals_per_match": (lambda r: r.goals_per_match, False, "goals per match"),
    "points_per_match": (lambda r: r.points_per_match, False, "points per match"),
    "losses": (lambda r: r.losses, False, "losses"),
    "draws": (lambda r: r.draws, False, "draws"),
}
_METRIC_ALIASES = {
    "goals": "goals_for", "goals scored": "goals_for", "most goals": "goals_for", "attack": "goals_for",
    "conceded": "goals_against", "goals conceded": "goals_against", "defense": "goals_against",
    "defence": "goals_against", "win rate": "win_rate", "winrate": "win_rate", "record": "win_rate",
    "win percentage": "win_rate", "gd": "goal_difference", "goal diff": "goal_difference", "pts": "points",
    "ppg": "points_per_match",
}


class SoccerQueries:
    def __init__(self, data: SoccerData | None = None):
        self.data = data or get_data()
        self._standings_cache: dict[tuple[str, int], list[StandingRow]] = {}
        self._name_index = self._build_name_index()

    # ============================================================ resolution
    def _build_name_index(self) -> dict[str, str]:
        """Normalized name variants -> team id, for fuzzy lookups."""
        index: dict[str, str] = {}
        for tid in self.data.team_names:
            index.setdefault(normalize_text(tid.replace("-", " ")), tid)
            index.setdefault(normalize_text(self.data.team_name(tid)), tid)
            for raw in self.data._raw_names.get(tid, ()):
                index.setdefault(normalize_text(raw), tid)
        for alias, tid in ALIASES.items():
            if tid in self.data.by_team:
                index[alias] = tid
        return index

    def resolve_team(self, query: str) -> str:
        """Map a user-supplied team name to a team id present in the data."""
        if query is None or not str(query).strip():
            raise QueryError("A team name is required.")
        q = str(query).strip()
        tid = canonical_team_id(q)
        if tid in self.data.by_team:
            return tid
        norm = normalize_text(q)
        if norm in self._name_index:
            return self._name_index[norm]
        # Substring match on any known spelling; prefer the most active club.
        hits = {t for name, t in self._name_index.items() if norm and (norm in name.split() or name.startswith(norm)
                                                                       or f" {norm}" in f" {name}")}
        if hits:
            return max(hits, key=lambda t: (t in CLUBS_BY_ID, len(self.data.by_team.get(t, ()))))
        close = difflib.get_close_matches(norm, list(self._name_index), n=5, cutoff=0.75)
        if close:
            tid = self._name_index[close[0]]
            return tid
        raise QueryError(f"Team '{query}' not found in the match data. Try find_team to search for names.")

    def _resolve_comp(self, competition: str | None) -> str | None:
        try:
            return resolve_competition(competition)
        except ValueError as exc:
            raise QueryError(str(exc)) from None

    @staticmethod
    def _resolve_venue(venue: str | None) -> str:
        v = (venue or "all").strip().lower()
        if v not in _VENUES:
            raise QueryError("venue must be 'all', 'home' or 'away'.")
        return _VENUES[v]

    @staticmethod
    def _resolve_stage(stage: str | None) -> str | None:
        if stage is None or not str(stage).strip():
            return None
        key = normalize_text(str(stage))
        if key in _STAGE_ALIASES:
            return _STAGE_ALIASES[key]
        if key.startswith("round ") and key[6:].isdigit():
            return key
        raise QueryError(f"Unknown stage '{stage}'. Try: group stage, round of 16, quarterfinals, semifinals, final.")

    @staticmethod
    def _parse_date_arg(value: str | None, name: str) -> date | None:
        if value is None or not str(value).strip():
            return None
        try:
            return parse_date(str(value))
        except ValueError as exc:
            raise QueryError(f"{name}: {exc}") from None

    def name(self, team_id: str) -> str:
        return self.data.team_name(team_id)

    # ============================================================ match helpers
    def filter_matches(self, team: str | None = None, opponent: str | None = None, competition: str | None = None,
                       season: int | None = None, date_from: str | None = None, date_to: str | None = None,
                       venue: str | None = "all", stage: str | None = None) -> list[Match]:
        """Matches matching all criteria, most recent first."""
        tid = self.resolve_team(team) if team else None
        oid = self.resolve_team(opponent) if opponent else None
        if oid and not tid:
            tid, oid = oid, None
        comp = self._resolve_comp(competition)
        v = self._resolve_venue(venue)
        st = self._resolve_stage(stage)
        d_from = self._parse_date_arg(date_from, "date_from")
        d_to = self._parse_date_arg(date_to, "date_to")
        pool = self.data.by_team.get(tid, []) if tid else self.data.matches
        out = []
        for m in pool:
            if comp and m.competition != comp:
                continue
            if season is not None and m.season != int(season):
                continue
            if st and m.stage != st:
                continue
            if d_from and (m.date is None or m.date < d_from):
                continue
            if d_to and (m.date is None or m.date > d_to):
                continue
            if tid:
                if v == "home" and m.home_id != tid:
                    continue
                if v == "away" and m.away_id != tid:
                    continue
                if oid and not m.involves(oid):
                    continue
            out.append(m)
        out.sort(key=lambda m: (m.date or date.min, m.time or ""), reverse=True)
        return out

    def format_match(self, m: Match, with_competition: bool = True) -> str:
        d = m.date.isoformat() if m.date else f"{m.season} (date unknown)"
        line = f"{d}: {self.name(m.home_id)} {m.home_goals}-{m.away_goals} {self.name(m.away_id)}"
        info = []
        if with_competition:
            info.append(m.competition)
        if m.competition in LEAGUES and m.round:
            info.append(f"Round {m.round}")
        elif m.stage:
            info.append(m.stage)
        if m.arena:
            info.append(m.arena)
        if info:
            line += f" ({', '.join(info)})"
        return line

    @staticmethod
    def team_records(matches: list[Match], venue: str = "all") -> dict[str, Record]:
        recs: dict[str, Record] = defaultdict(Record)
        for m in matches:
            if venue in ("all", "home"):
                recs[m.home_id].add(m.home_goals, m.away_goals)
            if venue in ("all", "away"):
                recs[m.away_id].add(m.away_goals, m.home_goals)
        return recs

    @staticmethod
    def record_for(matches: list[Match], team_id: str, venue: str = "all") -> Record:
        rec = Record()
        for m in matches:
            if m.home_id == team_id and venue in ("all", "home"):
                rec.add(m.home_goals, m.away_goals)
            elif m.away_id == team_id and venue in ("all", "away"):
                rec.add(m.away_goals, m.home_goals)
        return rec

    # ============================================================ dataset
    def dataset_info(self) -> str:
        d = self.data
        lines = ["Brazilian soccer knowledge base — loaded datasets:"]
        for src, n in d.raw_counts.items():
            loaded = d.loaded_counts.get(src, 0)
            skipped = d.skipped_counts.get(src, 0)
            lines.append(f"- {src}: {n} rows ({loaded} unique records kept, {skipped} skipped as unplayed/invalid)")
        lines.append(f"Unique matches after cross-file de-duplication: {len(d.matches)} "
                     f"({d.duplicates_merged} duplicate rows merged)")
        lines.append(f"Teams: {len(d.team_names)}; players: {len(d.players)}")
        lines.append("Coverage by competition:")
        for comp in COMPETITIONS:
            seasons = d.seasons(comp)
            n = sum(1 for m in d.matches if m.competition == comp)
            if seasons:
                lines.append(f"- {comp}: {n} matches, seasons {seasons[0]}-{seasons[-1]}")
        return "\n".join(lines)

    def find_team(self, query: str, limit: int = 10) -> str:
        norm = normalize_text(query or "")
        if not norm:
            raise QueryError("Provide part of a team name.")
        scored: dict[str, float] = {}
        for name, tid in self._name_index.items():
            if norm in name:
                scored[tid] = max(scored.get(tid, 0), 1.0 + len(self.data.by_team.get(tid, ())) / 1e5)
        if not scored:
            for name in difflib.get_close_matches(norm, list(self._name_index), n=limit, cutoff=0.6):
                scored.setdefault(self._name_index[name], 0.5)
        if not scored:
            return f"No team matching '{query}'."
        best = sorted(scored, key=lambda t: (-scored[t], -len(self.data.by_team.get(t, ()))))[:limit]
        lines = [f"Teams matching '{query}':"]
        for tid in best:
            ms = self.data.by_team.get(tid, [])
            comps = sorted({m.competition for m in ms})
            variants = sorted(self.data._raw_names.get(tid, {}))[:6]
            lines.append(f"- {self.name(tid)} [id: {tid}] — {len(ms)} matches ({', '.join(comps)}); "
                         f"spellings: {', '.join(variants)}")
        return "\n".join(lines)

    # ============================================================ matches
    def search_matches(self, team: str | None = None, opponent: str | None = None,
                       competition: str | None = None, season: int | None = None,
                       date_from: str | None = None, date_to: str | None = None,
                       venue: str | None = "all", stage: str | None = None, limit: int = 20) -> str:
        ms = self.filter_matches(team, opponent, competition, season, date_from, date_to, venue, stage)
        crit = []
        if team:
            crit.append(self.name(self.resolve_team(team)) + (f" ({venue})" if self._resolve_venue(venue) != "all"
                                                               else ""))
        if opponent:
            crit.append("vs " + self.name(self.resolve_team(opponent)))
        if competition:
            crit.append(self._resolve_comp(competition) or "all competitions")
        if season is not None:
            crit.append(f"season {season}")
        if stage:
            crit.append(f"stage {self._resolve_stage(stage)}")
        if date_from or date_to:
            crit.append(f"dates {date_from or '...'} to {date_to or '...'}")
        title = "Matches" + (f" — {', '.join(crit)}" if crit else "")
        if not ms:
            return f"{title}: no matches found in the dataset."
        lines = [f"{title}: {len(ms)} found (most recent first)"]
        comps = Counter(m.competition for m in ms)
        if len(comps) > 1:
            lines.append("By competition: " + ", ".join(f"{c} ({n})" for c, n in comps.most_common()))
        lines += [f"- {self.format_match(m)}" for m in ms[:max(1, limit)]]
        if len(ms) > limit:
            lines.append(f"- ... ({len(ms) - limit} more matches in dataset)")
        if team:
            tid = self.resolve_team(team)
            rec = self.record_for(ms, tid)
            lines.append(f"{self.name(tid)} in these matches: {rec.wins}W {rec.draws}D {rec.losses}L, "
                         f"GF {rec.goals_for} GA {rec.goals_against}")
        return "\n".join(lines)

    def head_to_head(self, team_a: str, team_b: str, competition: str | None = None,
                     season_from: int | None = None, season_to: int | None = None, limit: int = 15) -> str:
        a, b = self.resolve_team(team_a), self.resolve_team(team_b)
        if a == b:
            raise QueryError("Pick two different teams.")
        ms = [m for m in self.filter_matches(team_a, team_b, competition)
              if (season_from is None or m.season >= season_from) and (season_to is None or m.season <= season_to)]
        na, nb = self.name(a), self.name(b)
        derby = derby_name(a, b)
        title = f"{na} vs {nb}" + (f" ({derby} derby)" if derby else "")
        if not ms:
            return f"{title}: no meetings found in the dataset."
        ra = self.record_for(ms, a)
        lines = [f"{title}:"]
        lines += [f"- {self.format_match(m)}" for m in ms[:limit]]
        if len(ms) > limit:
            lines.append(f"- ... ({len(ms) - limit} more matches in dataset)")
        lines.append("")
        lines.append(f"Head-to-head in dataset ({len(ms)} matches): {na} {ra.wins} wins, {nb} {ra.losses} wins, "
                     f"{ra.draws} draws")
        lines.append(f"Goals: {na} {ra.goals_for}, {nb} {ra.goals_against}")
        by_comp = defaultdict(list)
        for m in ms:
            by_comp[m.competition].append(m)
        if len(by_comp) > 1:
            lines.append("By competition:")
            for comp, cms in sorted(by_comp.items()):
                r = self.record_for(cms, a)
                lines.append(f"- {comp}: {len(cms)} matches — {na} {r.wins}W, {nb} {r.losses}W, {r.draws} draws")
        home_a = self.record_for([m for m in ms if m.home_id == a], a)
        home_b = self.record_for([m for m in ms if m.home_id == b], b)
        lines.append(f"{na} at home: {home_a.wins}W {home_a.draws}D {home_a.losses}L; "
                     f"{nb} at home: {home_b.wins}W {home_b.draws}D {home_b.losses}L")
        lines.append(f"Most recent meeting: {self.format_match(ms[0])}")
        return "\n".join(lines)

    # ============================================================ teams
    def team_record(self, team: str, season: int | None = None, competition: str | None = None,
                    venue: str | None = "all") -> str:
        tid = self.resolve_team(team)
        v = self._resolve_venue(venue)
        comp = self._resolve_comp(competition)
        ms = self.filter_matches(team, competition=competition, season=season, venue=v)
        label = {"all": "record", "home": "home record", "away": "away record"}[v]
        scope = ", ".join(x for x in (str(season) if season is not None else "all seasons",
                                      comp or "all competitions") if x)
        title = f"{self.name(tid)} {label} ({scope})"
        if not ms:
            return f"{title}: no matches found."
        rec = self.record_for(ms, tid, v)
        lines = [f"{title}:",
                 f"- Matches: {rec.played}",
                 f"- Wins: {rec.wins}, Draws: {rec.draws}, Losses: {rec.losses}",
                 f"- Goals For: {rec.goals_for}, Goals Against: {rec.goals_against} "
                 f"(GD {_signed(rec.goal_difference)})",
                 f"- Win rate: {rec.win_rate:.1f}%",
                 f"- Points (3 per win): {rec.points} ({rec.points_per_match:.2f} per match)"]
        by_comp = defaultdict(list)
        for m in ms:
            by_comp[m.competition].append(m)
        if len(by_comp) > 1:
            lines.append("By competition:")
            for c, cms in sorted(by_comp.items()):
                lines.append(f"- {c}: {self.record_for(cms, tid, v).summary()}")
        if season is None:
            by_season = defaultdict(list)
            for m in ms:
                by_season[m.season].append(m)
            if len(by_season) > 1:
                best = max(by_season, key=lambda s: self.record_for(by_season[s], tid, v).win_rate)
                worst = min(by_season, key=lambda s: self.record_for(by_season[s], tid, v).win_rate)
                lines.append(f"Best season by win rate: {best} "
                             f"({self.record_for(by_season[best], tid, v).win_rate:.1f}%); "
                             f"worst: {worst} ({self.record_for(by_season[worst], tid, v).win_rate:.1f}%)")
        return "\n".join(lines)

    def team_overview(self, team: str) -> str:
        """Cross-file profile: competitions, records, league finishes, FIFA squad."""
        tid = self.resolve_team(team)
        ms = self.data.by_team.get(tid, [])
        club = CLUBS_BY_ID.get(tid)
        lines = [f"{self.name(tid)}" + (f" ({club.state})" if club else "") + " — team overview"]
        rec = self.record_for(ms, tid)
        lines.append(f"Matches in dataset: {rec.summary()}")
        lines.append("Competitions played:")
        by_comp = defaultdict(list)
        for m in ms:
            by_comp[m.competition].append(m)
        for comp in COMPETITIONS:
            cms = by_comp.get(comp)
            if not cms:
                continue
            seasons = sorted({m.season for m in cms})
            lines.append(f"- {comp}: {len(seasons)} seasons ({self._season_span(seasons)}); "
                         f"{self.record_for(cms, tid).summary()}")
        finishes = self._league_finishes(tid, SERIE_A)
        if finishes:
            titles = [s for s, row in finishes if row.position == 1]
            best = min(finishes, key=lambda x: (x[1].position, -x[0]))
            lines.append(f"Série A finishes (calculated): best {self._ordinal(best[1].position)} in {best[0]}"
                         + (f"; titles: {', '.join(map(str, titles))}" if titles else ""))
        derbies = sorted({name for pair, name in DERBIES.items() if tid in pair})
        if derbies:
            lines.append(f"Traditional derbies: {', '.join(derbies)}")
        recent = sorted(ms, key=lambda m: m.date or date.min, reverse=True)[:5]
        if recent:
            lines.append("Most recent matches:")
            lines += [f"- {self.format_match(m)}" for m in recent]
        lines.append(self._fifa_squad_summary(tid))
        return "\n".join(lines)

    @staticmethod
    def _season_span(seasons: list[int]) -> str:
        if not seasons:
            return ""
        spans, start, prev = [], seasons[0], seasons[0]
        for s in seasons[1:]:
            if s != prev + 1:
                spans.append(f"{start}" if start == prev else f"{start}-{prev}")
                start = s
            prev = s
        spans.append(f"{start}" if start == prev else f"{start}-{prev}")
        return ", ".join(spans)

    @staticmethod
    def _ordinal(n: int) -> str:
        suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix}"

    def _fifa_squad_summary(self, tid: str) -> str:
        club = TEAM_TO_FIFA_CLUB.get(tid)
        if not club:
            return (f"FIFA 19 player data: no squad for {self.name(tid)} (FIFA 19 only licensed "
                    f"{len(FIFA_CLUB_TO_TEAM)} Brazilian clubs).")
        squad = sorted((p for p in self.data.players if p.club == club), key=lambda p: -(p.overall or 0))
        avg = sum(p.overall or 0 for p in squad) / len(squad) if squad else 0
        top = ", ".join(f"{p.name} ({p.position}, {p.overall})" for p in squad[:5])
        return f"FIFA 19 squad ({club}): {len(squad)} players, avg overall {avg:.1f}; top: {top}"

    def _league_finishes(self, tid: str, competition: str) -> list[tuple[int, StandingRow]]:
        out = []
        for season in sorted({m.season for m in self.data.by_team.get(tid, []) if m.competition == competition}):
            for row in self.standings_table(competition, season):
                if row.team_id == tid:
                    out.append((season, row))
        return out

    def team_trend(self, team: str, competition: str | None = SERIE_A) -> str:
        tid = self.resolve_team(team)
        comp = self._resolve_comp(competition) or SERIE_A
        if comp not in LEAGUES:
            raise QueryError("team_trend works for league competitions (Série A/B/C).")
        finishes = self._league_finishes(tid, comp)
        if not finishes:
            return f"{self.name(tid)} has no {comp} matches in the dataset."
        lines = [f"{self.name(tid)} — {comp} season by season (calculated from matches):"]
        for season, row in finishes:
            r = row.record
            n_teams = len(self.standings_table(comp, season))
            lines.append(f"- {season}: {self._ordinal(row.position)} of {n_teams}, {r.points} pts "
                         f"({r.wins}W {r.draws}D {r.losses}L), GF {r.goals_for} GA {r.goals_against}"
                         + (f" — {row.note}" if row.note else ""))
        pts = [row.record.points_per_match for _, row in finishes]
        if len(pts) >= 2:
            trend = "improving" if pts[-1] > pts[0] else "declining" if pts[-1] < pts[0] else "flat"
            lines.append(f"Points per match: {pts[0]:.2f} in {finishes[0][0]} -> {pts[-1]:.2f} in "
                         f"{finishes[-1][0]} ({trend})")
        return "\n".join(lines)

    # ============================================================ competitions
    def standings_table(self, competition: str | None, season: int) -> list[StandingRow]:
        comp = self._resolve_comp(competition) or SERIE_A
        key = (comp, int(season))
        if key in self._standings_cache:
            return self._standings_cache[key]
        ms = [m for m in self.data.matches if m.competition == comp and m.season == int(season)]
        recs = self.team_records(ms)
        order = sorted(recs.items(), key=lambda kv: (-kv[1].points, -kv[1].wins, -kv[1].goal_difference,
                                                     -kv[1].goals_for, self.name(kv[0])))
        rows = [StandingRow(i + 1, tid, self.name(tid), rec) for i, (tid, rec) in enumerate(order)]
        # A double round robin has n*(n-1) matches; with missing matches the
        # final positions are not certain, so softer labels are used.
        complete = len(ms) >= len(rows) * (len(rows) - 1)
        if rows and comp in LEAGUES:
            rows[0].note = "Champion" if complete else "Leader"
            if comp in (SERIE_A, SERIE_B):
                n_releg = 2 if (comp == SERIE_A and season == 2003) else 4
                for row in rows[-n_releg:]:
                    row.note = "Relegated" if complete else "Relegation zone"
            if comp == SERIE_B:
                for row in rows[1:4]:
                    row.note = "Promoted" if complete else "Promotion zone"
                rows[0].note = "Champion (promoted)" if complete else "Leader"
        self._standings_cache[key] = rows
        return rows

    def standings(self, season: int, competition: str | None = SERIE_A, top: int | None = None) -> str:
        comp = self._resolve_comp(competition) or SERIE_A
        if comp not in LEAGUES:
            raise QueryError(f"Standings are only calculated for league competitions; for {comp} use "
                             f"knockout_results.")
        rows = self.standings_table(comp, season)
        if not rows:
            seasons = self.data.seasons(comp)
            return f"No {comp} matches for {season}. Seasons available: {self._season_span(seasons)}"
        n = sum(1 for m in self.data.matches if m.competition == comp and m.season == season)
        expected = len(rows) * (len(rows) - 1)
        title = f"{season} {comp} Final Standings (calculated from matches)"
        lines = [f"{title}:"]
        shown = rows if not top else rows[:top]
        for row in shown:
            r = row.record
            lines.append(f"{row.position}. {row.team} - {r.points} pts ({r.wins}W, {r.draws}D, {r.losses}L, "
                         f"GF {r.goals_for}, GA {r.goals_against}, GD {_signed(r.goal_difference)})"
                         + (f" - {row.note}" if row.note else ""))
        if top and top < len(rows):
            lines.append(f"... ({len(rows) - top} more teams)")
            for label in ("Relegated", "Relegation zone"):
                teams = [row.team for row in rows if row.note == label]
                if teams:
                    lines.append(f"{label}: {', '.join(teams)}")
        if n < expected:
            lines.append(f"Note: only {n} of {expected} matches are in the dataset, so the table is incomplete "
                         f"and the final positions may differ.")
        lines.append("Note: tables use 3 points per win and ignore off-field point deductions, so they can "
                     "differ from official tables in rare cases.")
        return "\n".join(lines)

    def team_rankings(self, metric: str = "points", competition: str | None = SERIE_A, season: int | None = None,
                      venue: str | None = "all", min_matches: int | None = None, limit: int = 10,
                      ascending: bool | None = None) -> str:
        key = normalize_text(metric or "points").replace(" ", "_")
        key = _METRIC_ALIASES.get(key.replace("_", " "), key)
        if key not in _RANK_METRICS:
            raise QueryError(f"Unknown metric '{metric}'. Options: {', '.join(_RANK_METRICS)}")
        fn, asc_default, label = _RANK_METRICS[key]
        asc = asc_default if ascending is None else ascending
        comp = self._resolve_comp(competition)
        v = self._resolve_venue(venue)
        ms = [m for m in self.data.matches
              if (comp is None or m.competition == comp) and (season is None or m.season == int(season))]
        if not ms:
            return "No matches for that selection."
        recs = self.team_records(ms, v)
        if min_matches is None:
            min_matches = 5 if season is not None else 30
        cands = [(tid, r) for tid, r in recs.items() if r.played >= min_matches]
        cands.sort(key=lambda kv: (fn(kv[1]) if asc else -fn(kv[1]), -kv[1].played, self.name(kv[0])))
        scope = ", ".join([comp or "all competitions", str(season) if season is not None else "all seasons"]
                          + ([f"{v} matches only"] if v != "all" else []))
        order = "lowest" if asc else "highest"
        lines = [f"Teams ranked by {label} ({order} first; {scope}; min {min_matches} matches):"]
        for i, (tid, r) in enumerate(cands[:limit], 1):
            val = fn(r)
            val_s = f"{val:.1f}%" if key == "win_rate" else f"{val:.2f}" if isinstance(val, float) else str(val)
            lines.append(f"{i}. {self.name(tid)} - {val_s} {'' if key == 'win_rate' else label} "
                         f"({r.played} matches, {r.wins}W {r.draws}D {r.losses}L, GF {r.goals_for} "
                         f"GA {r.goals_against})".replace("  ", " "))
        if not cands:
            lines.append("No team meets the minimum number of matches.")
        return "\n".join(lines)

    def knockout_results(self, competition: str = LIBERTADORES, season: int | None = None,
                         stage: str | None = None) -> str:
        comp = self._resolve_comp(competition) or LIBERTADORES
        if comp in LEAGUES:
            raise QueryError("knockout_results is for cup competitions (Copa do Brasil, Copa Libertadores).")
        st = self._resolve_stage(stage)
        if season is None and st is None:
            st = "final"
        ms = [m for m in self.data.matches if m.competition == comp
              and (season is None or m.season == int(season)) and (st is None or m.stage == st)]
        if season is not None and st is None:
            ms = [m for m in ms if m.stage != "group stage"]
        if not ms:
            return f"No {comp} knockout matches found for that selection (seasons: " \
                   f"{self._season_span(self.data.seasons(comp))})."
        title = f"{comp}" + (f" {season}" if season is not None else "") + \
                (f" — {st}" if st else " — knockout bracket")
        lines = [f"{title} (from match data):"]
        by_season_stage: dict[tuple[int, str], list[Match]] = defaultdict(list)
        for m in ms:
            by_season_stage[(m.season, m.stage or "stage unknown")].append(m)

        def stage_rank(s: str) -> int:
            return _STAGE_ORDER.index(s) if s in _STAGE_ORDER else -1

        for (s, stg) in sorted(by_season_stage, key=lambda k: (k[0], stage_rank(k[1]))):
            lines.append(f"{s} {stg}:")
            for tie in self._pair_ties(by_season_stage[(s, stg)], is_final=stg == "final"):
                lines.append(f"  - {tie}")
        return "\n".join(lines)

    def _pair_ties(self, matches: list[Match], is_final: bool = False) -> list[str]:
        ties: dict[frozenset, list[Match]] = defaultdict(list)
        for m in sorted(matches, key=lambda m: m.date or date.min):
            ties[frozenset({m.home_id, m.away_id})].append(m)
        out = []
        for legs in ties.values():
            a, b = legs[0].home_id, legs[0].away_id
            ga = sum(m.goals_for(a) for m in legs)
            gb = sum(m.goals_for(b) for m in legs)
            scores = "; ".join(f"{m.date.isoformat() if m.date else ''} {self.name(m.home_id)} "
                               f"{m.home_goals}-{m.away_goals} {self.name(m.away_id)}" for m in legs)
            if len(legs) == 1:
                w = legs[0].winner_id
                res = (f"{self.name(w)} {'champion' if is_final else 'win'}" if w
                       else "draw (decided by extra time/penalties, not in data)")
                out.append(f"{scores} — {res}")
            else:
                if ga != gb:
                    res = f"aggregate {self.name(a)} {ga}-{gb} {self.name(b)}, " \
                          f"{self.name(a if ga > gb else b)} {'champion' if is_final else 'advance'}"
                else:
                    res = f"aggregate {ga}-{gb} (decided by away goals/penalties, not in data)"
                out.append(f"{scores} — {res}")
        return out

    def derby_matches(self, season: int | None = None, team: str | None = None, competition: str | None = None,
                      derby: str | None = None, limit: int = 30) -> str:
        tid = self.resolve_team(team) if team else None
        comp = self._resolve_comp(competition)
        dnorm = normalize_text(derby) if derby else None
        ms = []
        for m in self.data.matches:
            name = derby_name(m.home_id, m.away_id)
            if not name:
                continue
            if season is not None and m.season != int(season):
                continue
            if comp and m.competition != comp:
                continue
            if tid and not m.involves(tid):
                continue
            if dnorm and dnorm not in normalize_text(name):
                continue
            ms.append((name, m))
        if not ms:
            return "No derby matches found for that selection."
        ms.sort(key=lambda x: x[1].date or date.min, reverse=True)
        counts = Counter(n for n, _ in ms)
        scope = ", ".join(x for x in (str(season) if season is not None else "", comp or "",
                                      self.name(tid) if tid else "") if x)
        lines = [f"Traditional derbies{f' ({scope})' if scope else ''}: {len(ms)} matches"]
        lines.append("By derby: " + ", ".join(f"{n} ({c})" for n, c in counts.most_common()))
        for name, m in ms[:limit]:
            lines.append(f"- [{name}] {self.format_match(m)}")
        if len(ms) > limit:
            lines.append(f"- ... ({len(ms) - limit} more)")
        return "\n".join(lines)

    # ============================================================ statistics
    def _stats_block(self, ms: list[Match]) -> list[str]:
        n = len(ms)
        goals = sum(m.total_goals for m in ms)
        hw = sum(1 for m in ms if m.home_goals > m.away_goals)
        aw = sum(1 for m in ms if m.away_goals > m.home_goals)
        dr = n - hw - aw
        lines = [f"- Matches: {n}, total goals: {goals}",
                 f"- Average goals per match: {goals / n:.2f} (home {sum(m.home_goals for m in ms) / n:.2f}, "
                 f"away {sum(m.away_goals for m in ms) / n:.2f})",
                 f"- Home win rate: {_pct(hw, n):.1f}%, draws: {_pct(dr, n):.1f}%, away wins: {_pct(aw, n):.1f}%"]
        common = Counter(f"{m.home_goals}-{m.away_goals}" for m in ms).most_common(3)
        lines.append("- Most common scores: " + ", ".join(f"{s} ({c})" for s, c in common))
        with_stats = [m for m in ms if m.stats and "home_corner" in m.stats and "away_corner" in m.stats]
        if with_stats:
            corners = sum(m.stats["home_corner"] + m.stats["away_corner"] for m in with_stats) / len(with_stats)
            shot_ms = [m for m in with_stats if "home_shots" in m.stats and "away_shots" in m.stats]
            extra = ""
            if shot_ms:
                shots = sum(m.stats["home_shots"] + m.stats["away_shots"] for m in shot_ms) / len(shot_ms)
                extra = f", shots per match: {shots:.1f}"
            lines.append(f"- Corners per match: {corners:.1f}{extra} (from {len(with_stats)} matches with "
                         f"extended stats)")
        return lines

    def competition_stats(self, competition: str | None = None, season: int | None = None,
                          team: str | None = None) -> str:
        comp = self._resolve_comp(competition)
        tid = self.resolve_team(team) if team else None
        pool = self.data.by_team.get(tid, []) if tid else self.data.matches
        ms = [m for m in pool if (comp is None or m.competition == comp)
              and (season is None or m.season == int(season))]
        if not ms:
            return "No matches for that selection."
        scope = ", ".join(x for x in (comp or "all competitions", str(season) if season is not None else "",
                                      f"matches involving {self.name(tid)}" if tid else "") if x)
        lines = [f"Statistics ({scope}):"] + self._stats_block(ms)
        if comp is None:
            lines.append("By competition:")
            for c in COMPETITIONS:
                cms = [m for m in ms if m.competition == c]
                if cms:
                    g = sum(m.total_goals for m in cms) / len(cms)
                    hw = _pct(sum(1 for m in cms if m.home_goals > m.away_goals), len(cms))
                    lines.append(f"- {c}: {len(cms)} matches, {g:.2f} goals/match, home win rate {hw:.1f}%")
        return "\n".join(lines)

    def compare_seasons(self, seasons: list[int], competition: str | None = SERIE_A) -> str:
        comp = self._resolve_comp(competition) or SERIE_A
        if not seasons:
            raise QueryError("Provide at least one season.")
        lines = [f"{comp} season comparison:"]
        for s in seasons:
            ms = [m for m in self.data.matches if m.competition == comp and m.season == int(s)]
            if not ms:
                lines.append(f"{s}: no data")
                continue
            lines.append(f"{s}:")
            lines += ["  " + x for x in self._stats_block(ms)]
            if comp in LEAGUES:
                table = self.standings_table(comp, s)
                champ = table[0]
                top_attack = max(table, key=lambda r: r.record.goals_for)
                best_def = min(table, key=lambda r: r.record.goals_against)
                lines.append(f"  - {champ.note} (calculated): {champ.team} with {champ.record.points} pts")
                lines.append(f"  - Best attack: {top_attack.team} ({top_attack.record.goals_for} goals); "
                             f"best defence: {best_def.team} ({best_def.record.goals_against} conceded)")
                relegated = [r.team for r in table if r.note.startswith("Relegat")]
                if relegated:
                    lines.append(f"  - {table[-1].note}: {', '.join(relegated)}")
            biggest = max(ms, key=lambda m: (m.margin, m.total_goals))
            lines.append(f"  - Biggest win: {self.format_match(biggest, with_competition=False)}")
        return "\n".join(lines)

    def biggest_wins(self, competition: str | None = None, season: int | None = None, team: str | None = None,
                     limit: int = 10) -> str:
        comp = self._resolve_comp(competition)
        tid = self.resolve_team(team) if team else None
        pool = self.data.by_team.get(tid, []) if tid else self.data.matches
        ms = [m for m in pool if (comp is None or m.competition == comp)
              and (season is None or m.season == int(season))]
        if tid:
            ms = [m for m in ms if m.winner_id == tid]
        if not ms:
            return "No matches for that selection."
        ms.sort(key=lambda m: (-m.margin, -max(m.home_goals, m.away_goals), m.date or date.min))
        scope = ", ".join(x for x in (comp or "all competitions", str(season) if season is not None else "",
                                      f"wins by {self.name(tid)}" if tid else "") if x)
        lines = [f"Biggest victories ({scope}):"]
        for i, m in enumerate(ms[:limit], 1):
            lines.append(f"{i}. {self.format_match(m)} — margin {m.margin}")
        if not tid:
            n = len(ms)
            lines.append("")
            lines.append(f"Average goals per match: {sum(m.total_goals for m in ms) / n:.2f}")
            lines.append(f"Home win rate: {_pct(sum(1 for m in ms if m.home_goals > m.away_goals), n):.1f}%")
        return "\n".join(lines)

    # ============================================================ players
    @staticmethod
    def _name_score(query_tokens: list[str], name_tokens: list[str]) -> float:
        """Fraction of query tokens found in the name.

        A query token matches a name token that is equal, starts with it, or
        is its initial ('lionel' ~ 'l' in 'L. Messi'); at least one token must
        match on more than an initial.
        """
        matched = strong = 0
        for q in query_tokens:
            if any(n == q or (len(q) >= 3 and n.startswith(q)) for n in name_tokens):
                matched += 1
                strong += 1
            elif any(len(n) == 1 and q[0] == n for n in name_tokens):
                matched += 1
        if not query_tokens or not strong:
            return 0.0
        return matched / len(query_tokens)

    def _club_filter(self, club: str) -> tuple[set[str] | None, str | None]:
        """Return (exact FIFA club names, normalized substring) for a club query."""
        norm = normalize_text(club)
        try:
            tid = self.resolve_team(club)
        except QueryError:
            tid = None
        if tid in TEAM_TO_FIFA_CLUB:
            return {TEAM_TO_FIFA_CLUB[tid]}, None
        if tid in CLUBS_BY_ID:
            # A Brazilian club that FIFA 19 does not include (e.g. Flamengo).
            return set(), None
        return None, norm

    def find_players(self, name: str | None = None, nationality: str | None = None, club: str | None = None,
                     position: str | None = None, min_overall: int | None = None, max_age: int | None = None,
                     brazilian_clubs_only: bool = False, sort_by: str = "overall") -> list[Player]:
        players = self.data.players
        if nationality:
            nat = normalize_text(nationality)
            nat = _NATIONALITY_WORDS.get(nat, nat)
            players = [p for p in players if p.nationality_norm == nat]
        if club:
            exact, sub = self._club_filter(club)
            if exact is not None:
                players = [p for p in players if p.club in exact]
            else:
                players = [p for p in players if sub and sub in p.club_norm]
        if brazilian_clubs_only:
            players = [p for p in players if p.club in FIFA_CLUB_TO_TEAM]
        if position:
            codes = self._position_codes(position)
            players = [p for p in players if p.position in codes]
        if min_overall is not None:
            players = [p for p in players if (p.overall or 0) >= min_overall]
        if max_age is not None:
            players = [p for p in players if p.age is not None and p.age <= max_age]
        if name:
            q = normalize_text(name).split()
            scored = [(self._name_score(q, p.name_norm.split()) + (0.5 if p.name_norm == " ".join(q) else 0), p)
                      for p in players]
            players = [p for s, p in sorted(scored, key=lambda x: (-x[0], -(x[1].overall or 0))) if s >= 1.0]
            return players
        return self._sort_players(players, sort_by)

    @staticmethod
    def _position_codes(position: str) -> set[str]:
        out: set[str] = set()
        for part in position.replace(",", " ").replace("/", " ").split():
            w = part.strip().lower()
            if w in _POSITION_WORDS:
                out |= _POSITION_GROUPS[_POSITION_WORDS[w]]
            elif w.upper() in {c for g in _POSITION_GROUPS.values() for c in g}:
                out.add(w.upper())
            else:
                raise QueryError(f"Unknown position '{part}'. Use a code like ST, CB, GK or a group: "
                                 f"goalkeeper, defender, midfielder, forward.")
        return out

    @staticmethod
    def _sort_players(players: list[Player], sort_by: str) -> list[Player]:
        key = (sort_by or "overall").strip()
        low = key.lower()
        if low == "overall":
            return sorted(players, key=lambda p: (-(p.overall or 0), -(p.potential or 0), p.name))
        if low == "potential":
            return sorted(players, key=lambda p: (-(p.potential or 0), -(p.overall or 0), p.name))
        if low == "age":
            return sorted(players, key=lambda p: (p.age or 99, -(p.overall or 0)))
        if low == "name":
            return sorted(players, key=lambda p: p.name_norm)
        attr = next((a for a in (players[0].attributes if players else {}) if a.lower() == low), None)
        if attr is None:
            raise QueryError(f"Unknown sort_by '{sort_by}'. Use overall, potential, age, name or a skill such as "
                             f"Finishing, Dribbling, Crossing.")
        return sorted(players, key=lambda p: (-p.attributes.get(attr, 0), -(p.overall or 0)))

    def _player_line(self, p: Player, extra: str = "") -> str:
        return (f"{p.name} - Overall: {p.overall}, Potential: {p.potential}, Position: {p.position or '?'}, "
                f"Club: {p.club or 'Free agent'}, Age: {p.age}, Nationality: {p.nationality}{extra}")

    def search_players(self, name: str | None = None, nationality: str | None = None, club: str | None = None,
                       position: str | None = None, min_overall: int | None = None, max_age: int | None = None,
                       brazilian_clubs_only: bool = False, sort_by: str = "overall", limit: int = 20) -> str:
        if not any([name, nationality, club, position, min_overall, max_age, brazilian_clubs_only]):
            raise QueryError("Provide at least one filter (name, nationality, club, position, ...).")
        players = self.find_players(name, nationality, club, position, min_overall, max_age,
                                    brazilian_clubs_only, sort_by)
        crit = [f"{k}={v}" for k, v in (("name", name), ("nationality", nationality), ("club", club),
                                         ("position", position), ("min_overall", min_overall),
                                         ("max_age", max_age)) if v]
        if brazilian_clubs_only:
            crit.append("Brazilian clubs only")
        if not players:
            msg = [f"No players found ({', '.join(crit)}) in the FIFA 19 dataset."]
            if club:
                exact, _ = self._club_filter(club)
                if exact == set():
                    msg.append(f"FIFA 19 has no squad for {self.name(self.resolve_team(club))}. Brazilian clubs "
                               f"available: {', '.join(sorted(FIFA_CLUB_TO_TEAM))}.")
            if name:
                msg.append(self._name_suggestions(name))
            return "\n".join(m for m in msg if m)
        if sort_by and sort_by.lower() not in ("overall",) and not name:
            header_sort = f", sorted by {sort_by}"
        else:
            header_sort = ""
        lines = [f"Players ({', '.join(crit)}{header_sort}): {len(players)} found"]
        attr = next((a for a in (players[0].attributes) if a.lower() == (sort_by or "").lower()), None)
        for i, p in enumerate(players[:limit], 1):
            extra = f", {attr}: {p.attributes.get(attr)}" if attr else ""
            lines.append(f"{i}. {self._player_line(p, extra)}")
        if len(players) > limit:
            lines.append(f"... ({len(players) - limit} more)")
        if len(players) > 1:
            avg = sum(p.overall or 0 for p in players) / len(players)
            lines.append(f"Average overall rating: {avg:.1f}")
        return "\n".join(lines)

    def _name_suggestions(self, name: str) -> str:
        q = normalize_text(name).split()
        partial = sorted(((self._name_score(q, p.name_norm.split()), p) for p in self.data.players),
                         key=lambda x: (-x[0], -(x[1].overall or 0)))
        partial = [p for s, p in partial if s >= 0.5][:8]
        close = difflib.get_close_matches(normalize_text(name), [p.name_norm for p in self.data.players], n=3,
                                          cutoff=0.7)
        names = list(dict.fromkeys([p.name for p in partial] +
                                   [p.name for p in self.data.players if p.name_norm in close]))
        return f"Closest names in dataset: {', '.join(names[:10])}" if names else ""

    def player_profile(self, name: str) -> str:
        if not name or not name.strip():
            raise QueryError("Provide a player name.")
        players = self.find_players(name=name)
        if not players:
            sugg = self._name_suggestions(name)
            return f"No player named '{name}' in the FIFA 19 dataset." + (f"\n{sugg}" if sugg else "")
        p = players[0]
        lines = [f"{p.name} (FIFA 19 data)",
                 f"- Age: {p.age}, Nationality: {p.nationality}",
                 f"- Club: {p.club or 'Free agent'}" + (f", shirt #{p.jersey_number}" if p.jersey_number else "")
                 + (f", contract until {p.contract_until}" if p.contract_until else ""),
                 f"- Position: {p.position}, Preferred foot: {p.preferred_foot}",
                 f"- Overall: {p.overall}, Potential: {p.potential}",
                 f"- Height: {p.height}, Weight: {p.weight}",
                 f"- Value: {p.value}, Wage: {p.wage}"]
        if p.attributes:
            skills = [(k, v) for k, v in p.attributes.items() if not k.startswith("GK") or p.position == "GK"]
            top = sorted(skills, key=lambda kv: -kv[1])[:6]
            lines.append("- Top attributes: " + ", ".join(f"{k} {v}" for k, v in top))
        if p.team_id:
            ms = self.data.by_team.get(p.team_id, [])
            if ms:
                rec = self.record_for(ms, p.team_id)
                last = max(ms, key=lambda m: m.date or date.min)
                lines.append(f"- Club in match data: {self.name(p.team_id)} — {rec.summary()}; "
                             f"latest: {self.format_match(last)}")
        if len(players) > 1:
            others = ", ".join(f"{o.name} ({o.club or 'free agent'}, {o.overall})" for o in players[1:6])
            lines.append(f"Other players matching '{name}': {others}")
        return "\n".join(lines)

    def player_club_summary(self, nationality: str | None = "Brazil", brazilian_clubs_only: bool = False,
                            top_players: int = 10, max_clubs: int = 20) -> str:
        players = self.find_players(nationality=nationality or None, brazilian_clubs_only=brazilian_clubs_only)
        if not players:
            return "No players for that selection."
        nat = nationality or "All"
        avg = sum(p.overall or 0 for p in players) / len(players)
        lines = [f"{nat} players in dataset" + (" at Brazilian clubs" if brazilian_clubs_only else "")
                 + f": {len(players)} (avg overall {avg:.1f})", "", "Top-rated:"]
        for i, p in enumerate(players[:top_players], 1):
            lines.append(f"{i}. {p.name} - Overall: {p.overall}, Position: {p.position}, Club: {p.club or 'Free agent'}")
        by_club: dict[str, list[Player]] = defaultdict(list)
        for p in players:
            if p.club:
                by_club[p.club].append(p)
        lines.append("")
        lines.append(f"{nat} players at Brazilian clubs:" if not brazilian_clubs_only else "By club:")
        br = {c: ps for c, ps in by_club.items() if c in FIFA_CLUB_TO_TEAM}
        for c, ps in sorted(br.items(), key=lambda kv: (-len(kv[1]), -sum(p.overall or 0 for p in kv[1]))):
            lines.append(f"- {c}: {len(ps)} players (avg rating: {sum(p.overall or 0 for p in ps) / len(ps):.0f})")
        if not br:
            lines.append("- none")
        if not brazilian_clubs_only:
            lines.append("")
            lines.append(f"Clubs with most {nat} players:")
            for c, ps in sorted(by_club.items(), key=lambda kv: -len(kv[1]))[:max_clubs]:
                lines.append(f"- {c}: {len(ps)} players (avg rating: "
                             f"{sum(p.overall or 0 for p in ps) / len(ps):.0f})")
        return "\n".join(lines)
