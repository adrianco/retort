"""Answers to questions about Brazilian soccer, calculated from the loaded datasets.

Every public method returns a plain dictionary (the structured answer); formatting it as
text for people is done separately in answers.py.
"""
import math
from collections import defaultdict

from brazilian_soccer_mcp.names import (DOMESTIC, LEAGUES, competition_name, derby_name, nationality_key,
                                        position_codes, simplify, stage_name, team_key)

RELEGATION_PLACES = {("Brasileirão", 2003): 2}
DEFAULT_RELEGATION_PLACES = 4
SMALLEST_FULL_LEAGUE = 16
KNOCKOUT_ORDER = ["round 1", "round 2", "round 3", "round 4", "round 5", "round of 16", "quarterfinals",
                  "semifinals", "final"]
METRICS = {
    "win_rate": ("win rate", True), "points": ("points", True), "wins": ("wins", True),
    "goals_scored": ("goals scored", True), "goals_conceded": ("goals conceded", False),
    "goal_difference": ("goal difference", True), "losses": ("losses", False),
}


class QuestionError(Exception):
    """The question can't be answered as asked; the message says why, in plain words."""


class Tally:
    def __init__(self):
        self.matches = self.wins = self.draws = self.losses = self.goals_for = self.goals_against = 0

    def add(self, scored, conceded):
        self.matches += 1
        self.goals_for += scored
        self.goals_against += conceded
        if scored > conceded:
            self.wins += 1
        elif scored == conceded:
            self.draws += 1
        else:
            self.losses += 1

    @property
    def points(self):
        return self.wins * 3 + self.draws

    @property
    def win_rate(self):
        return round(100 * self.wins / self.matches, 1) if self.matches else 0.0

    def as_dict(self):
        return {"matches": self.matches, "wins": self.wins, "draws": self.draws, "losses": self.losses,
                "goals_for": self.goals_for, "goals_against": self.goals_against,
                "goal_difference": self.goals_for - self.goals_against, "points": self.points,
                "win_rate": self.win_rate}


def _int(value, what):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise QuestionError(f"'{value}' is not a valid {what}")


class SoccerKnowledge:
    def __init__(self, data):
        self.data = data
        self._domestic_clubs = {key for match in data.matches if match.competition in DOMESTIC
                                for key in (match.home_key, match.away_key)}
        self._match_clubs = {key for match in data.matches for key in (match.home_key, match.away_key)}

    # -- understanding the question ----------------------------------------------------------

    def resolve_team(self, text):
        """The club a user means, or None when no club in the data matches."""
        if not text or not str(text).strip():
            return None
        key = self.data.canonical(team_key(str(text)))
        if key in self._match_clubs:
            return key
        wanted = simplify(text)
        same_base = [club for club in self._match_clubs if club.rsplit("-", 1)[0] == key]
        if len(same_base) == 1:
            return same_base[0]
        containing = [club for club in self._match_clubs
                      if wanted and (simplify(self.data.name_of(club)).startswith(wanted + " ")
                                     or simplify(self.data.name_of(club)) == wanted)]
        if len(containing) == 1:
            return containing[0]
        return None

    def _team(self, text, *, required=True):
        if text is None or str(text).strip() == "":
            if required:
                raise QuestionError("Please say which team you mean")
            return None
        key = self.resolve_team(text)
        if key is None:
            raise QuestionError(f"No matches found for team '{text}'")
        return key

    @staticmethod
    def _competition(text):
        if text is None or str(text).strip() == "":
            return None
        name = competition_name(text)
        if name is None:
            raise QuestionError(f"Unknown competition '{text}'. Try Brasileirão, Série B, Série C, "
                                "Copa do Brasil or Copa Libertadores")
        return name

    def _filter(self, *, team=None, opponent=None, venue="any", competition=None, season=None,
                date_from=None, date_to=None, stage=None):
        venue = (venue or "any").lower()
        if venue not in ("any", "home", "away"):
            raise QuestionError("venue must be 'home', 'away' or 'any'")
        stage = stage_name(stage)
        for match in self.data.matches:
            if competition and match.competition != competition:
                continue
            if season is not None and match.season != season:
                continue
            if date_from and (not match.date or match.date < date_from):
                continue
            if date_to and (not match.date or match.date > date_to):
                continue
            if stage and match.stage != stage:
                continue
            if team:
                if venue == "home" and match.home_key != team:
                    continue
                if venue == "away" and match.away_key != team:
                    continue
                if team not in (match.home_key, match.away_key):
                    continue
                if opponent and opponent not in (match.home_key, match.away_key):
                    continue
            yield match

    # -- describing matches ------------------------------------------------------------------

    def describe_match(self, match):
        described = {
            "date": match.date, "competition": match.competition, "season": match.season,
            "round": match.round, "stage": match.stage,
            "home": self.data.name_of(match.home_key), "away": self.data.name_of(match.away_key),
            "home_goals": match.home_goals, "away_goals": match.away_goals,
            "statistics": match.statistics, "arena": match.arena, "sources": list(match.sources),
        }
        derby = derby_name(match.home_key, match.away_key)
        if derby:
            described["derby"] = derby
        return described

    def _criteria(self, arguments):
        return {
            "competition": self._competition(arguments.get("competition")),
            "season": _int(arguments.get("season"), "season"),
            "date_from": arguments.get("date_from") or None,
            "date_to": arguments.get("date_to") or None,
        }

    # -- matches -----------------------------------------------------------------------------

    def search_matches(self, team=None, opponent=None, venue="any", competition=None, season=None,
                       date_from=None, date_to=None, stage=None, limit=20):
        club = self._team(team, required=False)
        rival = self._team(opponent, required=False)
        if rival and not club:
            club, rival = rival, None
        criteria = self._criteria(locals())
        found = list(self._filter(team=club, opponent=rival, venue=venue, stage=stage, **criteria))
        limit = _int(limit, "limit") or 20
        answer = {
            "team": self.data.name_of(club) if club else None,
            "opponent": self.data.name_of(rival) if rival else None,
            "total": len(found),
            "matches": [self.describe_match(match) for match in found[:limit]],
        }
        if club and rival:
            answer["derby"] = derby_name(club, rival)
            answer["head_to_head"] = self._head_to_head_summary(club, rival, found)
        return answer

    def _head_to_head_summary(self, team, opponent, matches):
        mine, theirs = Tally(), Tally()
        for match in matches:
            scored, conceded = ((match.home_goals, match.away_goals) if match.home_key == team
                                else (match.away_goals, match.home_goals))
            mine.add(scored, conceded)
            theirs.add(conceded, scored)
        return {
            "team": {"name": self.data.name_of(team), "wins": mine.wins, "goals": mine.goals_for},
            "opponent": {"name": self.data.name_of(opponent), "wins": theirs.wins, "goals": theirs.goals_for},
            "draws": mine.draws, "matches": mine.matches,
        }

    def head_to_head(self, team, opponent, competition=None, season=None, limit=20):
        club, rival = self._team(team), self._team(opponent)
        criteria = self._criteria(locals())
        found = list(self._filter(team=club, opponent=rival, **criteria))
        summary = self._head_to_head_summary(club, rival, found)
        summary.update({
            "derby": derby_name(club, rival),
            "competition": criteria["competition"], "season": criteria["season"],
            "recent_matches": [self.describe_match(match) for match in found[:_int(limit, "limit") or 20]],
        })
        return summary

    def find_derbies(self, season=None, competition=None, team=None, limit=50):
        club = self._team(team, required=False)
        criteria = self._criteria(locals())
        found = [match for match in self._filter(team=club, **criteria)
                 if derby_name(match.home_key, match.away_key)]
        return {"season": criteria["season"], "competition": criteria["competition"], "total": len(found),
                "matches": [self.describe_match(match) for match in found[:_int(limit, "limit") or 50]]}

    # -- teams -------------------------------------------------------------------------------

    def _tally(self, team, matches):
        tally = Tally()
        for match in matches:
            if match.home_key == team:
                tally.add(match.home_goals, match.away_goals)
            else:
                tally.add(match.away_goals, match.home_goals)
        return tally

    def team_record(self, team, season=None, competition=None, venue="any", opponent=None):
        club = self._team(team)
        rival = self._team(opponent, required=False)
        criteria = self._criteria(locals())
        found = list(self._filter(team=club, opponent=rival, venue=venue, **criteria))
        record = {"team": self.data.name_of(club), "venue": (venue or "any").lower(),
                  "competition": criteria["competition"], "season": criteria["season"],
                  "opponent": self.data.name_of(rival) if rival else None}
        record.update(self._tally(club, found).as_dict())
        return record

    def team_overview(self, team):
        club = self._team(team)
        matches = list(self._filter(team=club))
        by_competition = defaultdict(list)
        for match in matches:
            by_competition[match.competition].append(match)
        competitions = []
        for competition, competition_matches in sorted(by_competition.items(), key=lambda item: -len(item[1])):
            seasons = sorted({match.season for match in competition_matches if match.season})
            entry = {"competition": competition, "seasons": seasons}
            entry.update(self._tally(club, competition_matches).as_dict())
            competitions.append(entry)
        squad = sorted((player for player in self.data.players if player.club_key == club),
                       key=lambda player: (-player.overall, player.name))
        rivals = sorted({self.data.name_of(other) for match in matches
                         for other in (match.home_key, match.away_key)
                         if other != club and derby_name(club, other)})
        return {
            "team": self.data.name_of(club),
            "record": self._tally(club, matches).as_dict(),
            "competitions": competitions,
            "recent_matches": [self.describe_match(match) for match in matches[:5]],
            "rivals": rivals,
            "squad": {"players": [self.describe_player(player) for player in squad[:15]],
                      "count": len(squad),
                      "average_overall": round(sum(p.overall for p in squad) / len(squad), 1) if squad else None},
        }

    # -- competitions ------------------------------------------------------------------------

    def _table(self, competition, season):
        tallies = defaultdict(Tally)
        for match in self._filter(competition=competition, season=season):
            tallies[match.home_key].add(match.home_goals, match.away_goals)
            tallies[match.away_key].add(match.away_goals, match.home_goals)
        ordered = sorted(tallies.items(), key=lambda item: (
            -item[1].points, -item[1].wins, -(item[1].goals_for - item[1].goals_against), -item[1].goals_for,
            self.data.name_of(item[0])))
        return [(key, tally) for key, tally in ordered]

    def standings(self, season, competition="Brasileirão"):
        competition = self._competition(competition) or "Brasileirão"
        season = _int(season, "season")
        if season is None:
            raise QuestionError("Please say which season")
        if competition not in LEAGUES:
            raise QuestionError(f"{competition} is a knockout competition - ask for its bracket instead")
        table = self._table(competition, season)
        if not table:
            raise QuestionError(f"No {competition} matches found for {season}")
        relegation = 0
        if competition == "Brasileirão" and len(table) >= SMALLEST_FULL_LEAGUE:
            relegation = RELEGATION_PLACES.get((competition, season), DEFAULT_RELEGATION_PLACES)
        rows = []
        for position, (key, tally) in enumerate(table, start=1):
            row = {"position": position, "team": self.data.name_of(key), "status": None}
            row.update(tally.as_dict())
            if position == 1:
                row["status"] = "champion"
            elif relegation and position > len(table) - relegation:
                row["status"] = "relegated"
            rows.append(row)
        return {"competition": competition, "season": season, "champion": rows[0]["team"],
                "relegated": [row["team"] for row in rows if row["status"] == "relegated"],
                "matches": sum(tally.matches for _, tally in table) // 2, "table": rows}

    def knockout_bracket(self, competition, season):
        competition = self._competition(competition)
        season = _int(season, "season")
        if competition not in ("Copa do Brasil", "Copa Libertadores"):
            raise QuestionError("Brackets are available for Copa do Brasil and Copa Libertadores")
        ties = defaultdict(dict)
        for match in sorted(self._filter(competition=competition, season=season),
                            key=lambda match: match.date or ""):
            if not match.stage or match.stage == "group stage":
                continue
            pair = frozenset({match.home_key, match.away_key})
            tie = ties[match.stage].setdefault(pair, {
                "team": match.home_key, "opponent": match.away_key, "team_goals": 0, "opponent_goals": 0,
                "legs": []})
            home_is_team = match.home_key == tie["team"]
            tie["team_goals"] += match.home_goals if home_is_team else match.away_goals
            tie["opponent_goals"] += match.away_goals if home_is_team else match.home_goals
            tie["legs"].append(self.describe_match(match))
        if not ties:
            raise QuestionError(f"No knockout matches found for {competition} {season}")
        stages = []
        for stage in sorted(ties, key=lambda name: (KNOCKOUT_ORDER.index(name) if name in KNOCKOUT_ORDER
                                                    else -1, name)):
            stage_ties = []
            for tie in ties[stage].values():
                winner = (tie["team"] if tie["team_goals"] > tie["opponent_goals"]
                          else tie["opponent"] if tie["opponent_goals"] > tie["team_goals"] else None)
                stage_ties.append({**tie, "team": self.data.name_of(tie["team"]),
                                   "opponent": self.data.name_of(tie["opponent"]),
                                   "winner": self.data.name_of(winner) if winner else None})
            stages.append({"stage": stage, "ties": stage_ties})
        return {"competition": competition, "season": season, "stages": stages}

    # -- statistics --------------------------------------------------------------------------

    def _summary(self, matches):
        total = len(matches)
        goals = sum(match.home_goals + match.away_goals for match in matches)
        home_wins = sum(1 for match in matches if match.home_goals > match.away_goals)
        away_wins = sum(1 for match in matches if match.home_goals < match.away_goals)
        draws = total - home_wins - away_wins

        def rate(count):
            return round(100 * count / total, 1) if total else 0.0

        return {"matches": total, "goals": goals, "average_goals": round(goals / total, 2) if total else 0.0,
                "home_wins": home_wins, "away_wins": away_wins, "draws": draws,
                "home_win_rate": rate(home_wins), "away_win_rate": rate(away_wins), "draw_rate": rate(draws)}

    def competition_stats(self, competition=None, season=None, team=None):
        club = self._team(team, required=False)
        criteria = self._criteria(locals())
        matches = list(self._filter(team=club, **criteria))
        summary = {"competition": criteria["competition"], "season": criteria["season"],
                   "team": self.data.name_of(club) if club else None}
        summary.update(self._summary(matches))
        summary["seasons"] = sorted({match.season for match in matches if match.season})
        return summary

    def compare_seasons(self, seasons, competition="Brasileirão"):
        competition = self._competition(competition) or "Brasileirão"
        if isinstance(seasons, (str, int)):
            seasons = [part for part in str(seasons).replace(",", " ").split()]
        compared = []
        for season in [_int(season, "season") for season in seasons]:
            matches = list(self._filter(competition=competition, season=season))
            entry = {"season": season}
            entry.update(self._summary(matches))
            table = self._table(competition, season) if competition in LEAGUES else []
            entry["champion"] = self.data.name_of(table[0][0]) if table else None
            if table:
                best_attack = max(table, key=lambda item: item[1].goals_for)
                entry["top_scoring_team"] = {"team": self.data.name_of(best_attack[0]),
                                             "goals": best_attack[1].goals_for}
            compared.append(entry)
        return {"competition": competition, "seasons": compared}

    def biggest_wins(self, competition=None, season=None, team=None, limit=10):
        club = self._team(team, required=False)
        criteria = self._criteria(locals())
        found = [match for match in self._filter(team=club, **criteria) if match.home_goals != match.away_goals]
        found.sort(key=lambda match: (-abs(match.home_goals - match.away_goals),
                                      -max(match.home_goals, match.away_goals), match.date or ""))
        return {"competition": criteria["competition"], "season": criteria["season"],
                "matches": [dict(self.describe_match(match), margin=abs(match.home_goals - match.away_goals))
                            for match in found[:_int(limit, "limit") or 10]]}

    def rank_teams(self, metric="win_rate", venue="any", competition=None, season=None, min_matches=None,
                   limit=10):
        if metric not in METRICS:
            raise QuestionError(f"Unknown measure '{metric}'. Choose from {', '.join(METRICS)}")
        venue = (venue or "any").lower()
        criteria = self._criteria(locals())
        tallies = defaultdict(Tally)
        for match in self._filter(**criteria):
            if venue in ("any", "home"):
                tallies[match.home_key].add(match.home_goals, match.away_goals)
            if venue in ("any", "away"):
                tallies[match.away_key].add(match.away_goals, match.home_goals)
        if not tallies:
            raise QuestionError("No matches found for that selection")
        most_played = max(tally.matches for tally in tallies.values())
        minimum = _int(min_matches, "minimum number of matches") or max(1, math.ceil(most_played / 4))
        _, higher_is_better = METRICS[metric]

        def value(tally):
            return tally.as_dict()[{"goals_scored": "goals_for", "goals_conceded": "goals_against"}.get(metric, metric)]

        eligible = [(key, tally) for key, tally in tallies.items() if tally.matches >= minimum]
        eligible.sort(key=lambda item: ((-value(item[1]) if higher_is_better else value(item[1])),
                                        -item[1].matches, self.data.name_of(item[0])))
        rankings = [dict(team=self.data.name_of(key), value=value(tally), **tally.as_dict())
                    for key, tally in eligible[:_int(limit, "limit") or 10]]
        return {"metric": metric, "venue": venue, "competition": criteria["competition"],
                "season": criteria["season"], "min_matches": minimum, "rankings": rankings}

    # -- players -----------------------------------------------------------------------------

    @staticmethod
    def describe_player(player, *, detailed=False):
        described = {"name": player.name, "age": player.age, "nationality": player.nationality,
                     "club": player.club, "position": player.position, "overall": player.overall,
                     "potential": player.potential, "jersey_number": player.jersey_number}
        if detailed:
            described.update({"height": player.height, "weight": player.weight,
                              "preferred_foot": player.preferred_foot, "value": player.value,
                              "wage": player.wage, "skills": player.skills})
        return described

    def _club_matches(self, club):
        wanted_key = self.data.canonical(team_key(club))
        wanted = simplify(club)
        by_key = [player for player in self.data.players if player.club_key == wanted_key]
        if by_key:
            return by_key
        return [player for player in self.data.players if wanted and wanted in simplify(player.club)]

    def search_players(self, name=None, nationality=None, club=None, position=None, min_overall=None, limit=20):
        found = self._club_matches(club) if club else self.data.players
        if name:
            words = simplify(name).split()
            found = [player for player in found if all(word in simplify(player.name).split()
                                                       or word in simplify(player.name) for word in words)]
        if nationality:
            wanted = nationality_key(nationality)
            found = [player for player in found if simplify(player.nationality) == wanted]
        if position:
            codes = position_codes(position)
            found = [player for player in found if player.position in codes]
        minimum = _int(min_overall, "rating")
        if minimum:
            found = [player for player in found if player.overall >= minimum]
        found = sorted(found, key=lambda player: (-player.overall, -player.potential, player.name))
        return {"total": len(found),
                "players": [self.describe_player(player) for player in found[:_int(limit, "limit") or 20]]}

    def get_player(self, name):
        if not name or not str(name).strip():
            raise QuestionError("Please say which player you mean")
        wanted = simplify(name)
        exact = [player for player in self.data.players if simplify(player.name) == wanted]
        found = exact or self.search_players(name=name, limit=10_000)["players"]
        if not found:
            raise QuestionError(f"No player called '{name}' in the FIFA dataset" + self._similar_players(wanted))
        if exact:
            found = sorted(exact, key=lambda player: -player.overall)
            best, others = found[0], found[1:]
        else:
            best = next(player for player in self.data.players if player.name == found[0]["name"])
            others = found[1:]
        others = [other["name"] if isinstance(other, dict) else other.name for other in others][:5]
        return {"player": self.describe_player(best, detailed=True), "other_matches": others}

    def _similar_players(self, wanted):
        words = {word for word in wanted.split() if len(word) > 2}
        similar = sorted((player for player in self.data.players if words & set(simplify(player.name).split())),
                         key=lambda player: (-len(words & set(simplify(player.name).split())), -player.overall))
        return (". Similar names: " + ", ".join(player.name for player in similar[:8])) if similar else ""

    def club_squads(self, nationality=None, brazilian_clubs_only=True, club=None, limit=30):
        if isinstance(brazilian_clubs_only, str):
            brazilian_clubs_only = brazilian_clubs_only.lower() not in ("false", "no", "0")
        players = self._club_matches(club) if club else self.data.players
        if nationality:
            wanted = nationality_key(nationality)
            players = [player for player in players if simplify(player.nationality) == wanted]
        clubs = defaultdict(list)
        for player in players:
            if not player.club:
                continue
            if brazilian_clubs_only and player.club_key not in self._domestic_clubs:
                continue
            clubs[player.club_key if player.club_key in self._match_clubs else player.club].append(player)
        summary = []
        for key, members in clubs.items():
            members.sort(key=lambda player: -player.overall)
            summary.append({"club": self.data.name_of(key) if key in self._match_clubs else key,
                            "players": len(members),
                            "average_overall": round(sum(p.overall for p in members) / len(members), 1),
                            "best_player": members[0].name, "best_overall": members[0].overall})
        summary.sort(key=lambda club: (-club["players"], -club["average_overall"], club["club"]))
        return {"nationality": nationality, "brazilian_clubs_only": brazilian_clubs_only,
                "clubs": summary[:_int(limit, "limit") or 30]}

    # -- the data itself ---------------------------------------------------------------------

    def dataset_summary(self):
        competitions = defaultdict(list)
        for match in self.data.matches:
            competitions[match.competition].append(match)
        return {
            "datasets": [{"file": dataset.file, "description": dataset.description, "records": dataset.records,
                          "skipped": dataset.skipped} for dataset in self.data.datasets],
            "competitions": [{"competition": name, "matches": len(matches),
                              "seasons": sorted({match.season for match in matches if match.season})}
                             for name, matches in sorted(competitions.items())],
            "matches": len(self.data.matches), "teams": len(self._match_clubs), "players": len(self.data.players),
        }
