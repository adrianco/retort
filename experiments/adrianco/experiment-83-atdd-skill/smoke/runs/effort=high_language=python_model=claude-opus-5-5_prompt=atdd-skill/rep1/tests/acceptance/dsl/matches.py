"""
DSL (layer 2): finding matches.
"""


class Matches:
    def __init__(self, driver):
        self._driver = driver

    def search(self, team=None, opponent=None, venue=None, competition=None, season=None,
               date_from=None, date_to=None):
        self._driver.search_matches(team=team, opponent=opponent, venue=venue, competition=competition,
                                    season=season, date_from=date_from, date_to=date_to)

    def confirm_found(self, count, competition=None):
        self._driver.confirm_match_count(count)
        if competition:
            self._driver.confirm_all_matches_in(competition)

    def confirm_first(self, **expected):
        self._driver.confirm_first_match(**expected)
