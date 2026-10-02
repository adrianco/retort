"""
DSL (layer 2): the "Given" vocabulary for building a synthetic dataset.

Each method describes a fact about Brazilian football in domain terms and
supplies sensible defaults, so a spec states only what it cares about.
Dates are generated from a test-scoped sequence so that matches a spec
doesn't date explicitly never collide with each other.
"""

import datetime
import itertools


class Dataset:
    def __init__(self, data_source):
        self._data = data_source
        self._day = itertools.count()

    def brasileirao_match(self, home, away, score="1-0", season=None, date=None, round=1):
        date, season = self._when(date, season)
        self._data.add_brasileirao_match(home, away, *_goals(score), date, season, round)

    def brasileirao_fixture_without_result(self, home, away, season=None, date=None, round=1):
        date, season = self._when(date, season)
        self._data.add_brasileirao_match(home, away, None, None, date, season, round)

    def historical_brasileirao_match(self, home, away, score="1-0", season=None, date=None, round=1):
        date, season = self._when(date, season)
        self._data.add_historical_brasileirao_match(home, away, *_goals(score), date, season, round)

    def copa_do_brasil_match(self, home, away, score="1-0", season=None, date=None, round=1):
        date, season = self._when(date, season)
        self._data.add_copa_do_brasil_match(home, away, *_goals(score), date, season, round)

    def libertadores_match(self, home, away, score="1-0", season=None, date=None, stage="group stage"):
        date, season = self._when(date, season)
        self._data.add_libertadores_match(home, away, *_goals(score), date, season, stage)

    def extended_stats_match(self, home, away, score="1-0", date=None, season=None, tournament="Serie A",
                             corners="5-5", shots="10-10"):
        date, season = self._when(date, season)
        self._data.add_extended_stats_match(home, away, *_goals(score), date, tournament,
                                            _goals(corners), _goals(shots))

    def fifa_player(self, name, nationality="Brazil", club="Santos", overall=70, position="ST", age=25):
        self._data.add_fifa_player(name, nationality, club, overall, position, age)

    def season_finishing_in_order(self, season, teams):
        """A double round-robin where every team beats everyone listed below it."""
        for better, worse in itertools.combinations(teams, 2):
            self.brasileirao_match(home=better, away=worse, score="1-0", season=season)
            self.brasileirao_match(home=worse, away=better, score="0-1", season=season)

    def _when(self, date, season):
        if date is not None:
            return date, season or int(date[:4])
        season = season or 2023
        day = datetime.date(season, 4, 1) + datetime.timedelta(days=next(self._day))
        return day.isoformat(), season


def _goals(score):
    home, away = score.split("-")
    return int(home), int(away)
