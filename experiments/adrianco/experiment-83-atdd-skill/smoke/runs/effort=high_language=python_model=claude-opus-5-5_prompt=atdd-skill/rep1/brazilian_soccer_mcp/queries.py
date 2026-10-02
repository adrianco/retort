"""
Answers questions about Brazilian football from a loaded `SoccerData`.

Each public method takes plain arguments (as an MCP tool call supplies
them) and returns a JSON-serialisable dict. Problems the user can fix —
an unknown team, competition or player — raise `QueryError`, which the
server reports as a tool error with an explanation.
"""

import datetime
import math
from collections import defaultdict

from .data import (COMPETITIONS, COPA_DO_BRASIL, LEAGUES, LIBERTADORES, SERIE_A, SERIE_B, SERIE_C,
                   Match)
from .teams import fold, identify

DERBIES = [
    ("Fla-Flu", "Flamengo", "Fluminense"),
    ("Clássico dos Milhões", "Flamengo", "Vasco da Gama"),
    ("Clássico da Rivalidade", "Flamengo", "Botafogo"),
    ("Clássico dos Gigantes", "Fluminense", "Vasco da Gama"),
    ("Clássico Vovô", "Botafogo", "Fluminense"),
    ("Clássico da Amizade", "Botafogo", "Vasco da Gama"),
    ("Derby Paulista", "Corinthians", "Palmeiras"),
    ("Choque-Rei", "Palmeiras", "São Paulo"),
    ("Majestoso", "Corinthians", "São Paulo"),
    ("San-São", "Santos", "São Paulo"),
    ("Clássico Alvinegro", "Corinthians", "Santos"),
    ("Clássico da Saudade", "Palmeiras", "Santos"),
    ("Grenal", "Grêmio", "Internacional"),
    ("Clássico Mineiro", "Atlético Mineiro", "Cruzeiro"),
    ("Ba-Vi", "Bahia", "Vitória"),
    ("Atletiba", "Athletico Paranaense", "Coritiba"),
    ("Clássico-Rei", "Ceará", "Fortaleza"),
    ("Clássico dos Clássicos", "Náutico", "Sport Recife"),
]

POSITION_GROUPS = {
    "forward": {"ST", "CF", "LS", "RS", "LW", "RW", "LF", "RF"},
    "midfielder": {"CAM", "CM", "CDM", "LM", "RM", "LCM", "RCM", "LAM", "RAM", "LDM", "RDM"},
    "defender": {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
    "goalkeeper": {"GK"},
}
POSITION_WORDS = {
    "forward": "forward", "forwards": "forward", "striker": "forward", "strikers": "forward",
    "attacker": "forward", "attackers": "forward", "winger": "forward", "wingers": "forward",
    "midfielder": "midfielder", "midfielders": "midfielder", "midfield": "midfielder",
    "defender": "defender", "defenders": "defender", "defence": "defender", "defense": "defender",
    "goalkeeper": "goalkeeper", "goalkeepers": "goalkeeper", "keeper": "goalkeeper", "gk": "goalkeeper",
}
NATIONALITY_WORDS = {"brazilian": "brazil", "argentinian": "argentina", "argentine": "argentina",
                     "uruguayan": "uruguay", "colombian": "colombia", "chilean": "chile",
                     "paraguayan": "paraguay", "portuguese": "portugal"}

LIBERTADORES_STAGE_ORDER = ["round of 16", "quarterfinals", "semifinals", "final"]

METRICS = {
    "win_rate": ("Win rate", True),
    "goals_scored": ("Goals scored", True),
    "goals_conceded": ("Goals conceded", False),
    "points": ("Points", True),
    "wins": ("Wins", True),
    "goals_per_match": ("Goals scored per match", True),
}


class QueryError(Exception):
    def __init__(self, code, message, **details):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def resolve_competition(name):
    """Map a user's way of naming a competition to its canonical name (None means all)."""
    if name is None or not str(name).strip() or fold(name) in {"all", "any"}:
        return None
    text = fold(name)
    if "libertadores" in text:
        return LIBERTADORES
    if "copa do brasil" in text or "cup" in text or "copa" in text:
        return COPA_DO_BRASIL
    if "serie b" in text or text == "b":
        return SERIE_B
    if "serie c" in text or text == "c":
        return SERIE_C
    if any(word in text for word in ("brasileir", "serie a", "brazilian league", "campeonato brasileiro")) \
            or text == "a":
        return SERIE_A
    for competition in COMPETITIONS:
        if fold(competition) == text:
            return competition
    raise QueryError("unknown_competition", f"Competition not recognised: '{name}'. "
                     f"Known competitions: {', '.join(COMPETITIONS)}.", query=name, competitions=COMPETITIONS)


def _season(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise QueryError("invalid_season", f"Season must be a year, got '{value}'.", query=value)


def _date(value, field):
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except ValueError:
        from .data import parse_date
        parsed = parse_date(str(value))
        if parsed is None:
            raise QueryError("invalid_date", f"{field} must be a date like 2023-09-24 or 24/09/2023, "
                                             f"got '{value}'.", query=value)
        return parsed


def _venue(value):
    venue = fold(value or "all")
    if venue in {"all", "any", "both", "either"}:
        return "all"
    if venue in {"home", "away"}:
        return venue
    raise QueryError("invalid_venue", f"Venue must be 'home', 'away' or 'all', got '{value}'.", query=value)


def _rate(part, whole):
    return round(100.0 * part / whole, 1) if whole else 0.0


class Record:
    """Win/draw/loss and goals tally for one team over some matches."""

    def __init__(self):
        self.matches = self.wins = self.draws = self.losses = self.goals_for = self.goals_against = 0

    def add(self, scored, conceded):
        self.matches += 1
        self.goals_for += scored
        self.goals_against += conceded
        if scored > conceded:
            self.wins += 1
        elif scored < conceded:
            self.losses += 1
        else:
            self.draws += 1

    @property
    def points(self):
        return 3 * self.wins + self.draws

    def as_dict(self):
        return {
            "matches": self.matches, "wins": self.wins, "draws": self.draws, "losses": self.losses,
            "goals_for": self.goals_for, "goals_against": self.goals_against,
            "goal_difference": self.goals_for - self.goals_against, "points": self.points,
            "win_rate": _rate(self.wins, self.matches),
        }


def _tally(matches, team, venue="all"):
    record = Record()
    for match in matches:
        if match.home == team and venue in ("all", "home"):
            record.add(match.home_goals, match.away_goals)
        elif match.away == team and venue in ("all", "away"):
            record.add(match.away_goals, match.home_goals)
    return record


class SoccerQueries:
    def __init__(self, data):
        self.data = data
        self._appearances = defaultdict(int)
        for match in data.matches:
            self._appearances[match.home] += 1
            self._appearances[match.away] += 1
        self._player_clubs = {player.club_key for player in data.players}

    # -- helpers -----------------------------------------------------------

    def team(self, name, argument="team"):
        if not name or not str(name).strip():
            raise QueryError("missing_team", f"Please name a team for '{argument}'.")
        key = self.data.teams.resolve(name, among=self._appearances)
        if key is None:
            suggestions = self.data.teams.suggestions(name)
            hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
            raise QueryError("unknown_team", f"Team not recognised: '{name}'. No team by that name appears in "
                                             f"the match data.{hint}", query=name, suggestions=suggestions)
        return key

    def name(self, key):
        return self.data.teams.display(key)

    def match_dict(self, match: Match):
        result = {
            "date": match.date.isoformat() if match.date else None,
            "home": self.name(match.home), "away": self.name(match.away),
            "home_goals": match.home_goals, "away_goals": match.away_goals,
            "competition": match.competition, "season": match.season,
            "round": match.round, "stage": match.stage, "source": match.source,
        }
        if match.arena:
            result["arena"] = match.arena
        if match.stats:
            result["stats"] = dict(match.stats)
        return result

    def select(self, team=None, opponent=None, venue="all", competition=None, season=None,
               date_from=None, date_to=None, stage=None):
        team_key = self.team(team) if team else None
        opponent_key = self.team(opponent, "opponent") if opponent else None
        venue = _venue(venue)
        competition = resolve_competition(competition)
        season = _season(season)
        start, end = _date(date_from, "date_from"), _date(date_to, "date_to")
        stage = fold(stage) if stage else None
        selected = []
        for match in self.data.matches:
            if competition and match.competition != competition:
                continue
            if season is not None and match.season != season:
                continue
            if start and (match.date is None or match.date < start):
                continue
            if end and (match.date is None or match.date > end):
                continue
            if stage and stage not in fold(match.stage or "") and stage != fold(match.round or ""):
                continue
            if team_key:
                if venue == "home" and match.home != team_key:
                    continue
                if venue == "away" and match.away != team_key:
                    continue
                if not match.involves(team_key):
                    continue
            if opponent_key and not match.involves(opponent_key):
                continue
            selected.append(match)
        return selected, team_key, opponent_key

    @staticmethod
    def _recent_first(matches):
        return sorted(matches, key=lambda m: (m.date or datetime.date.min, m.kickoff or ""), reverse=True)

    # -- matches -----------------------------------------------------------

    def find_matches(self, team=None, opponent=None, venue="all", competition=None, season=None,
                     date_from=None, date_to=None, stage=None, limit=20):
        selected, team_key, opponent_key = self.select(team, opponent, venue, competition, season,
                                                       date_from, date_to, stage)
        ordered = self._recent_first(selected)
        result = {
            "criteria": {k: v for k, v in dict(team=team, opponent=opponent, venue=venue,
                                               competition=competition, season=season, date_from=date_from,
                                               date_to=date_to, stage=stage).items() if v not in (None, "all")},
            "total": len(ordered),
            "matches": [self.match_dict(m) for m in ordered[:max(1, int(limit))]],
        }
        if team_key and opponent_key:
            result["head_to_head"] = self._head_to_head_summary(selected, team_key, opponent_key)
        return result

    def head_to_head(self, team_a, team_b, competition=None, season=None, limit=10):
        selected, a, b = self.select(team_a, team_b, "all", competition, season)
        summary = self._head_to_head_summary(selected, a, b)
        summary["recent"] = [self.match_dict(m) for m in self._recent_first(selected)[:max(1, int(limit))]]
        return summary

    def _head_to_head_summary(self, matches, a, b):
        record = _tally(matches, a)
        return {
            "team_a": self.name(a), "team_b": self.name(b), "matches": record.matches,
            "team_a_wins": record.wins, "team_b_wins": record.losses, "draws": record.draws,
            "team_a_goals": record.goals_for, "team_b_goals": record.goals_against,
        }

    def find_derbies(self, season=None, competition=None, team=None, derby=None, limit=50):
        team_key = self.team(team) if team else None
        pairs = {}
        for name, first, second in DERBIES:
            if derby and fold(derby) not in fold(name):
                continue
            a, b = self.data.teams.resolve(first), self.data.teams.resolve(second)
            if a and b and fold(self.name(a)) == fold(first) and fold(self.name(b)) == fold(second):
                pairs[frozenset((a, b))] = name
        selected, _, _ = self.select(competition=competition, season=season)
        derbies = []
        for match in self._recent_first(selected):
            name = pairs.get(frozenset((match.home, match.away)))
            if name and (team_key is None or match.involves(team_key)):
                derbies.append(dict(self.match_dict(match), derby=name))
        counts = defaultdict(int)
        for match in derbies:
            counts[match["derby"]] += 1
        return {"total": len(derbies), "by_derby": dict(counts), "matches": derbies[:max(1, int(limit))]}

    # -- teams -------------------------------------------------------------

    def team_record(self, team, season=None, competition=None, venue="all"):
        venue = _venue(venue)
        selected, key, _ = self.select(team, None, venue, competition, season)
        record = _tally(selected, key, venue)
        return dict({"team": self.name(key), "venue": venue, "season": _season(season),
                     "competition": resolve_competition(competition)}, **record.as_dict())

    def team_competitions(self, team):
        key = self.team(team)
        by_competition = defaultdict(list)
        for match in self.data.matches:
            if match.involves(key):
                by_competition[match.competition].append(match)
        return {
            "team": self.name(key),
            "competitions": [
                {"competition": competition, "matches": len(matches),
                 "seasons": sorted({m.season for m in matches}),
                 **{k: v for k, v in _tally(matches, key).as_dict().items() if k in ("wins", "draws", "losses")}}
                for competition, matches in sorted(by_competition.items(), key=lambda kv: COMPETITIONS.index(kv[0]))
            ],
        }

    def team_profile(self, team, squad_size=15):
        key = self.team(team)
        competitions = self.team_competitions(team)["competitions"]
        mine = [m for m in self.data.matches if m.involves(key)]
        squad = sorted((p for p in self.data.players if p.club_key == key), key=lambda p: -p.overall)
        return {
            "team": self.name(key),
            "record": _tally(mine, key).as_dict(),
            "home_record": _tally(mine, key, "home").as_dict(),
            "away_record": _tally(mine, key, "away").as_dict(),
            "competitions": competitions,
            "recent_matches": [self.match_dict(m) for m in self._recent_first(mine)[:5]],
            "squad_size": len(squad),
            "squad": [self.player_dict(p) for p in squad[:squad_size]],
        }

    # -- competitions ------------------------------------------------------

    def standings(self, season, competition=SERIE_A):
        competition = resolve_competition(competition) or SERIE_A
        season = _season(season)
        if season is None:
            raise QueryError("missing_season", "Please give the season (year) for the standings.")
        selected = [m for m in self.data.matches if m.competition == competition and m.season == season]
        if not selected:
            seasons = sorted({m.season for m in self.data.matches if m.competition == competition})
            raise QueryError("no_data", f"No {competition} matches for {season} in the data. "
                                        f"Seasons available: {_season_ranges(seasons)}.", seasons=seasons)
        records = defaultdict(Record)
        for match in selected:
            records[match.home].add(match.home_goals, match.away_goals)
            records[match.away].add(match.away_goals, match.home_goals)
        ordered = sorted(records.items(), key=lambda kv: (-kv[1].points, -kv[1].wins,
                                                          -(kv[1].goals_for - kv[1].goals_against),
                                                          -kv[1].goals_for, self.name(kv[0])))
        table = [dict({"position": i, "team": self.name(key)}, **record.as_dict())
                 for i, (key, record) in enumerate(ordered, start=1)]
        for row in table:
            row["played"] = row.pop("matches")
        relegated = [row["team"] for row in table[-4:]] if competition in LEAGUES and len(table) > 4 else []
        expected = len(table) * (len(table) - 1) if competition in LEAGUES else None
        return {
            "competition": competition, "season": season, "table": table,
            "champion": table[0]["team"], "relegated": relegated, "matches": len(selected),
            "complete": expected is None or len(selected) >= expected,
        }

    def cup_finals(self, competition=COPA_DO_BRASIL, season=None):
        competition = resolve_competition(competition) or COPA_DO_BRASIL
        if competition in LEAGUES:
            raise QueryError("not_a_cup", f"{competition} is a league, it has no final. Try the standings.")
        season = _season(season)
        by_season = defaultdict(list)
        for match in self.data.matches:
            if match.competition == competition and (season is None or match.season == season):
                by_season[match.season].append(match)
        finals = []
        for year in sorted(by_season):
            legs = self._final_legs(by_season[year], competition)
            if legs:
                finals.append(dict({"season": year}, **self._tie(legs, away_goals_rule=False)))
        if season is not None and not finals:
            raise QueryError("no_data", f"No {competition} final for {season} in the data.")
        return {"competition": competition, "finals": finals}

    def _final_legs(self, matches, competition):
        if competition == LIBERTADORES:
            legs = [m for m in matches if fold(m.stage or "") == "final"]
            if legs:
                return legs
        rounds = [int(m.round) for m in matches if (m.round or "").isdigit()]
        if rounds:
            legs = [m for m in matches if m.round == str(max(rounds))]
            if len({t for m in legs for t in (m.home, m.away)}) == 2:
                last = max(m.date for m in matches if m.date)
                if all(m.date and (last - m.date).days <= 30 for m in legs):
                    return legs
        dated = [m for m in matches if m.date]
        if not dated:
            return []
        last = max(dated, key=lambda m: m.date)
        pair = {last.home, last.away}
        return [m for m in dated if {m.home, m.away} == pair and (last.date - m.date).days <= 30]

    def _tie(self, legs, away_goals_rule=True):
        """Aggregate a (one- or two-legged) tie. Away goals break a level aggregate only before the
        final; a final level on aggregate went to extra time or penalties, which the data lacks."""
        legs = sorted(legs, key=lambda m: m.date or datetime.date.min)
        first, second = legs[0].home, legs[0].away
        goals = {first: 0, second: 0}
        away_goals = {first: 0, second: 0}
        for leg in legs:
            goals[leg.home] += leg.home_goals
            goals[leg.away] += leg.away_goals
            away_goals[leg.away] += leg.away_goals
        winner, decided_by = None, None
        if goals[first] != goals[second]:
            winner = max(goals, key=goals.get)
            decided_by = "aggregate" if len(legs) > 1 else "score"
        elif away_goals_rule and len(legs) == 2 and away_goals[first] != away_goals[second]:
            winner = max(away_goals, key=away_goals.get)
            decided_by = "away goals"
        return {
            "teams": [self.name(first), self.name(second)],
            "finalists": [self.name(first), self.name(second)],
            "aggregate": f"{goals[first]}-{goals[second]}",
            "winner": self.name(winner) if winner else None,
            "decided_by": decided_by or "level (penalties or extra time, not in data)",
            "legs": [self.match_dict(m) for m in legs],
        }

    def knockout_bracket(self, season, competition=LIBERTADORES):
        competition = resolve_competition(competition) or LIBERTADORES
        season = _season(season)
        if season is None:
            raise QueryError("missing_season", "Please give the season (year) for the bracket.")
        matches = [m for m in self.data.matches if m.competition == competition and m.season == season]
        if competition == LIBERTADORES:
            def stage_of(m):
                return fold(m.stage or "")
            knockout = [m for m in matches if stage_of(m) and stage_of(m) != "group stage"]
        elif competition == COPA_DO_BRASIL:
            def stage_of(m):
                return f"round {m.round}" if m.round else "unknown round"
            knockout = matches
        else:
            raise QueryError("not_a_cup", f"{competition} is a league; it has no knockout bracket.")
        if not knockout:
            raise QueryError("no_data", f"No {competition} knockout matches for {season} in the data.")
        stages = defaultdict(lambda: defaultdict(list))
        for match in knockout:
            stages[stage_of(match)][frozenset((match.home, match.away))].append(match)

        def order(stage):
            if stage in LIBERTADORES_STAGE_ORDER:
                return (1, LIBERTADORES_STAGE_ORDER.index(stage), stage)
            digits = "".join(ch for ch in stage if ch.isdigit())
            return (0 if not digits else 1, int(digits) if digits else 0, stage)

        ordered = sorted(stages, key=order)

        def is_final(stage):
            return stage == "final" or (competition == COPA_DO_BRASIL and stage == ordered[-1]
                                        and len(stages[stage]) == 1)
        return {
            "competition": competition, "season": season,
            "stages": [{"stage": stage, "ties": [self._tie(legs, away_goals_rule=not is_final(stage))
                                                 for legs in stages[stage].values()]}
                       for stage in ordered],
        }

    # -- statistics --------------------------------------------------------

    def competition_stats(self, competition=None, season=None, team=None):
        selected, team_key, _ = self.select(team=team, competition=competition, season=season)
        if not selected:
            raise QueryError("no_data", "No matches found for those criteria.")
        return dict({"competition": resolve_competition(competition) or "All competitions",
                     "season": _season(season), "team": self.name(team_key) if team_key else None},
                    **_summary(selected))

    def biggest_wins(self, competition=None, season=None, team=None, limit=10):
        selected, team_key, _ = self.select(team=team, competition=competition, season=season)
        wins = [m for m in selected if m.winner and (team_key is None or m.winner == team_key)]
        wins.sort(key=lambda m: (-abs(m.home_goals - m.away_goals), -max(m.home_goals, m.away_goals),
                                 m.date or datetime.date.min))
        return {"matches": [dict(self.match_dict(m), winner=self.name(m.winner),
                                 margin=abs(m.home_goals - m.away_goals)) for m in wins[:max(1, int(limit))]]}

    def rank_teams(self, metric="win_rate", venue="all", competition=None, season=None, min_matches=None,
                   limit=10):
        if metric not in METRICS:
            raise QueryError("invalid_metric", f"Metric must be one of {', '.join(METRICS)}, got '{metric}'.")
        venue = _venue(venue)
        selected, _, _ = self.select(competition=competition, season=season)
        records = defaultdict(Record)
        for match in selected:
            if venue in ("all", "home"):
                records[match.home].add(match.home_goals, match.away_goals)
            if venue in ("all", "away"):
                records[match.away].add(match.away_goals, match.home_goals)
        if not records:
            raise QueryError("no_data", "No matches found for those criteria.")
        most = max(r.matches for r in records.values())
        threshold = int(min_matches) if min_matches is not None else max(1, math.ceil(0.2 * most))
        label, descending = METRICS[metric]

        def value(record):
            if metric == "goals_scored":
                return record.goals_for
            if metric == "goals_conceded":
                return record.goals_against
            if metric == "goals_per_match":
                return round(record.goals_for / record.matches, 2)
            if metric == "win_rate":
                return _rate(record.wins, record.matches)
            return getattr(record, metric)

        eligible = [(key, record) for key, record in records.items() if record.matches >= threshold]
        sign = -1 if descending else 1
        eligible.sort(key=lambda kv: (sign * value(kv[1]), -kv[1].matches, self.name(kv[0])))
        return {
            "metric": metric, "metric_label": label, "venue": venue,
            "competition": resolve_competition(competition) or "All competitions", "season": _season(season),
            "min_matches": threshold,
            "ranking": [dict({"rank": i, "team": self.name(key), "value": value(record)}, **record.as_dict())
                        for i, (key, record) in enumerate(eligible[:max(1, int(limit))], start=1)],
        }

    def compare_seasons(self, seasons, competition=SERIE_A):
        competition = resolve_competition(competition) or SERIE_A
        if not seasons:
            raise QueryError("missing_season", "Please give at least one season to compare.")
        results = []
        for season in seasons:
            season = _season(season)
            selected = [m for m in self.data.matches if m.competition == competition and m.season == season]
            if not selected:
                results.append({"season": season, "matches": 0, "note": "no matches in the data"})
                continue
            entry = dict({"season": season}, **_summary(selected))
            if competition in LEAGUES:
                table = self.standings(season, competition)
                entry["champion"] = table["champion"]
                entry["champion_points"] = table["table"][0]["points"]
                entry["relegated"] = table["relegated"]
            top = self.rank_teams("goals_scored", competition=competition, season=season, limit=1)["ranking"][0]
            entry["top_scoring_team"] = {"team": top["team"], "goals": top["value"]}
            results.append(entry)
        return {"competition": competition, "seasons": results}

    # -- players -----------------------------------------------------------

    def player_dict(self, player, detailed=False):
        result = {
            "name": player.name, "age": player.age, "nationality": player.nationality,
            "overall": player.overall, "potential": player.potential, "club": player.club or None,
            "position": player.position or None, "jersey_number": player.jersey_number,
        }
        if detailed:
            result.update(height=player.height, weight=player.weight, preferred_foot=player.preferred_foot,
                          value=player.value, wage=player.wage, skills=player.skills)
        return result

    def _player_filter(self, name=None, nationality=None, club=None, position=None, min_overall=None):
        name_words = fold(name).split() if name else []
        nationality = fold(nationality) if nationality else None
        nationality = NATIONALITY_WORDS.get(nationality, nationality)
        club_keys = self._club_keys(club) if club else None
        club_words = fold(club) if club else None
        positions = None
        if position:
            word = fold(position)
            group = POSITION_WORDS.get(word, word)
            positions = POSITION_GROUPS.get(group, {position.strip().upper()})
        for player in self.data.players:
            if name_words and not all(w in fold(player.name) for w in name_words):
                continue
            if nationality and fold(player.nationality) != nationality:
                continue
            if club and not (player.club_key in club_keys if club_keys else club_words in fold(player.club)):
                continue
            if positions and player.position not in positions:
                continue
            if min_overall is not None and player.overall < int(min_overall):
                continue
            yield player

    def _club_keys(self, club):
        """Exact club identities for a club name, if any player plays for them; else None (use substring)."""
        keys = {identify(club)[0], self.data.teams.resolve(club, among=self._appearances)}
        keys = {key for key in keys if key and key in self._player_clubs}
        return keys or None

    def search_players(self, name=None, nationality=None, club=None, position=None, min_overall=None,
                       sort_by="overall", limit=20):
        found = list(self._player_filter(name, nationality, club, position, min_overall))
        sort_by = sort_by if sort_by in ("overall", "potential", "age", "name") else "overall"
        if sort_by == "name":
            found.sort(key=lambda p: fold(p.name))
        elif sort_by == "age":
            found.sort(key=lambda p: (p.age or 0, -p.overall))
        else:
            found.sort(key=lambda p: (-(getattr(p, sort_by) or 0), fold(p.name)))
        return {"total": len(found), "players": [self.player_dict(p) for p in found[:max(1, int(limit))]]}

    def player_profile(self, name):
        if not name or not str(name).strip():
            raise QueryError("missing_player", "Please give a player name.")
        candidates = list(self._player_filter(name=name))
        if not candidates:
            words = [w for w in fold(name).split() if len(w) >= 3]
            similar = sorted((p for p in self.data.players if any(w in fold(p.name) for w in words)),
                             key=lambda p: -p.overall)[:8]
            hint = f" Similar names: {', '.join(p.name for p in similar)}." if similar else ""
            raise QueryError("unknown_player", f"No player matching '{name}' in the FIFA player data.{hint}",
                             query=name, suggestions=[p.name for p in similar])
        exact = [p for p in candidates if fold(p.name) == fold(name)]
        best = max(exact or candidates, key=lambda p: p.overall)
        others = [p.name for p in sorted(candidates, key=lambda p: -p.overall) if p is not best][:10]
        return {"player": self.player_dict(best, detailed=True), "other_matches": others}

    def brazilian_club_players(self, nationality=None, limit=30):
        nationality = fold(nationality) if nationality else None
        nationality = NATIONALITY_WORDS.get(nationality, nationality)
        clubs = defaultdict(list)
        for player in self.data.players:
            if player.club_key in self.data.brazilian_clubs and \
                    (nationality is None or fold(player.nationality) == nationality):
                clubs[player.club_key].append(player)
        summary = []
        for key, squad in clubs.items():
            best = max(squad, key=lambda p: p.overall)
            summary.append({"club": self.name(key), "fifa_club_name": best.club, "players": len(squad),
                            "average_overall": round(sum(p.overall for p in squad) / len(squad), 1),
                            "top_player": {"name": best.name, "overall": best.overall, "position": best.position}})
        summary.sort(key=lambda c: (-c["players"], -c["average_overall"], c["club"]))
        return {"nationality": nationality, "total_players": sum(c["players"] for c in summary),
                "clubs": summary[:max(1, int(limit))]}

    # -- dataset -----------------------------------------------------------

    def dataset_info(self):
        by_competition = defaultdict(lambda: {"matches": 0, "seasons": set()})
        for match in self.data.matches:
            by_competition[match.competition]["matches"] += 1
            by_competition[match.competition]["seasons"].add(match.season)
        return {
            "data_dir": str(self.data.data_dir),
            "files": [{"file": r.file, "rows": r.rows, "loaded": r.loaded, "skipped": r.skipped,
                       "duplicates_merged": r.duplicates, "error": r.error} for r in self.data.files.values()],
            "matches": len(self.data.matches), "players": len(self.data.players),
            "teams": len(self.data.teams.keys()),
            "competitions": [{"competition": c, "matches": by_competition[c]["matches"],
                              "seasons": _season_ranges(sorted(by_competition[c]["seasons"]))}
                             for c in COMPETITIONS if c in by_competition],
        }


def _summary(matches):
    total = len(matches)
    goals = sum(m.total_goals for m in matches)
    home = sum(1 for m in matches if m.home_goals > m.away_goals)
    away = sum(1 for m in matches if m.away_goals > m.home_goals)
    draws = total - home - away
    return {
        "matches": total, "goals": goals, "average_goals": round(goals / total, 2) if total else 0.0,
        "home_wins": home, "draws": draws, "away_wins": away,
        "home_win_rate": _rate(home, total), "draw_rate": _rate(draws, total), "away_win_rate": _rate(away, total),
    }


def _season_ranges(seasons):
    if not seasons:
        return "none"
    ranges, start, previous = [], seasons[0], seasons[0]
    for season in seasons[1:] + [None]:
        if season is not None and season == previous + 1:
            previous = season
            continue
        ranges.append(str(start) if start == previous else f"{start}-{previous}")
        if season is not None:
            start = previous = season
    return ", ".join(ranges)
