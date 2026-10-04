"""DSL for the historical record the system answers from: matches and players.

Specs describe results the way a fan would ("Flamengo 2-1 Fluminense"); everything they
don't care about (date, round, which dataset it came from) gets a sensible default.
"""
import datetime
import re

from tests.acceptance.drivers.archive_driver import ArchivedMatch, ArchivedPlayer

DEFAULT_SOURCE_FOR_COMPETITION = {
    "Brasileirão": "brasileirao",
    "Copa do Brasil": "copa do brasil",
    "Copa Libertadores": "libertadores",
    "Série B": "extended statistics",
    "Série C": "extended statistics",
}

DEFAULT_COMPETITION_FOR_SOURCE = {
    "brasileirao": "Brasileirão",
    "historical brasileirao": "Brasileirão",
    "copa do brasil": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
    "extended statistics": "Brasileirão",
}

RESULT = re.compile(r"^(?P<home>.+?)\s+(?P<home_goals>\d+)-(?P<away_goals>\d+)\s+(?P<away>.+)$")


def parse_result(result):
    found = RESULT.match(result.strip())
    if not found:
        raise ValueError(f"Can't read the result '{result}' - write it like 'Flamengo 2-1 Fluminense'")
    return (found["home"], int(found["home_goals"]), int(found["away_goals"]), found["away"])


def parse_pair(text):
    if text is None:
        return None
    first, second = text.split("-")
    return int(first), int(second)


class Archive:
    def __init__(self, driver):
        self._driver = driver
        self._matches_recorded = 0
        self._league_rounds = {}

    def has_match(self, result, *, date=None, season=None, competition=None, source=None,
                  league_round=None, cup_round=None, stage=None, corners=None, shots=None):
        home, home_goals, away_goals, away = parse_result(result)
        competition = competition or DEFAULT_COMPETITION_FOR_SOURCE.get(source, "Brasileirão")
        source = source or DEFAULT_SOURCE_FOR_COMPETITION[competition]
        if date is None:
            date = self._next_date(season)
        if season is None:
            season = int(date[:4])
        self._matches_recorded += 1
        self._driver.record_match(ArchivedMatch(
            source=source, competition=competition, date=date, season=season,
            home=home, away=away, home_goals=home_goals, away_goals=away_goals,
            league_round=league_round or self._next_league_round(season),
            cup_round=cup_round or 1,
            stage=stage or "group stage",
            corners=parse_pair(corners), shots=parse_pair(shots)))

    def has_matches(self, *results, **details):
        for result in results:
            self.has_match(result, **details)

    def has_league_table(self, *, season, bottom_four, competition="Brasileirão"):
        """A full 20-club season in which the clubs finish in table order, ending with bottom_four."""
        clubs = [f"Clube {letter}" for letter in "ABCDEFGHIJKLMNOP"] + list(bottom_four)
        for higher, home in enumerate(clubs):
            for away in clubs[higher + 1:]:
                self.has_match(f"{home} 1-0 {away}", season=season, competition=competition)

    def has_player(self, name, *, nationality="Brazil", club="Santos", position="CM", overall=70,
                   potential=None, age=25, jersey_number=10):
        self._driver.record_player(ArchivedPlayer(
            name=name, nationality=nationality, club=club, position=position, overall=overall,
            potential=potential or overall, age=age, jersey_number=jersey_number))

    def _next_date(self, season):
        year = season or 2023
        day = datetime.date(year, 1, 15) + datetime.timedelta(days=self._matches_recorded)
        return day.isoformat()

    def _next_league_round(self, season):
        self._league_rounds[season] = self._league_rounds.get(season, 0) + 1
        return (self._league_rounds[season] - 1) % 38 + 1
