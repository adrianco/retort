"""
DSL (layer 2): establishing what the football datasets record.

Specs describe results in football language ("Flamengo 2-1 Fluminense") and
only mention what they care about. This class supplies sensible defaults
(competition, date, season, which dataset records the match) and hands each
fact to the datasets driver, which writes it in that dataset's native format.

Defaults:
  - competition: Brasileirão (Série A)
  - source: the dataset that normally records that competition
  - date: a test-scoped sequence of dates (one week apart) within the season
  - season: the year of the date
"""
import datetime
import itertools
import re

RESULT = re.compile(r"^\s*(?P<home>.*\S)\s+(?P<home_goals>\d+)-(?P<away_goals>\d+)\s+(?P<away>\S.*?)\s*$")
FIXTURE = re.compile(r"^\s*(?P<home>.*\S)\s+vs\s+(?P<away>\S.*?)\s*$")

DEFAULT_SOURCE_FOR_COMPETITION = {
    "brasileirão": "brasileirão",
    "série a": "brasileirão",
    "copa do brasil": "copa do brasil",
    "libertadores": "libertadores",
    "série b": "extended statistics",
    "série c": "extended statistics",
}


class Given:
    def __init__(self, datasets):
        self._datasets = datasets
        self._week = itertools.count()
        self._player_ids = itertools.count(100001)

    def match(self, result, competition="Brasileirão", source=None, date=None, season=None,
              round=None, stage=None, corners=None, shots=None):
        found = RESULT.match(result)
        assert found, f"A result should read like 'Flamengo 2-1 Fluminense', not {result!r}"
        date, season = self._when(date, season)
        self._datasets.record_match(
            source=source or DEFAULT_SOURCE_FOR_COMPETITION[competition.lower()],
            competition=competition, date=date, season=season, round=round, stage=stage,
            home=found["home"], away=found["away"],
            home_goals=int(found["home_goals"]), away_goals=int(found["away_goals"]),
            corners=_pair(corners), shots=_pair(shots),
        )

    def unplayed_fixture(self, fixture, competition="Brasileirão", source=None, date=None, season=None):
        found = FIXTURE.match(fixture)
        assert found, f"A fixture should read like 'Santos vs Juazeirense', not {fixture!r}"
        date, season = self._when(date, season)
        self._datasets.record_match(
            source=source or DEFAULT_SOURCE_FOR_COMPETITION[competition.lower()],
            competition=competition, date=date, season=season, round=None, stage=None,
            home=found["home"], away=found["away"], home_goals=None, away_goals=None,
        )

    def season_finished(self, season, in_order, competition="Brasileirão"):
        """Every team plays every other once; a team higher in the order always wins."""
        for higher, lower in itertools.combinations(in_order, 2):
            self.match(f"{higher} 1-0 {lower}", competition=competition, season=season)

    def player(self, name, club="", nationality="Brazil", overall=70, potential=None, position="CM", age=25):
        self._datasets.record_player(
            player_id=next(self._player_ids), name=name, club=club, nationality=nationality,
            overall=overall, potential=potential or overall, position=position, age=age,
        )

    def _when(self, date, season):
        if date:
            day = datetime.date.fromisoformat(date)
            return day, season or day.year
        year = season or 2023
        return datetime.date(year, 4, 15) + datetime.timedelta(weeks=next(self._week) % 30), year


def _pair(score):
    if score is None:
        return None
    home, away = score.split("-")
    return int(home), int(away)
