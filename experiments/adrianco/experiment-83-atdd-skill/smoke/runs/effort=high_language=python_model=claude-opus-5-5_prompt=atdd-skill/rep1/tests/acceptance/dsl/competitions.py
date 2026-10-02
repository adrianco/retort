"""
DSL (layer 2): standings, finals, knockout brackets and derbies.
"""

BRASILEIRAO = "Brasileirão"


class Competitions:
    def __init__(self, driver):
        self._driver = driver

    def standings(self, season, competition=BRASILEIRAO):
        self._driver.standings(season=season, competition=competition)

    def finals(self, competition, season=None):
        self._driver.finals(competition=competition, season=season)

    def knockout_bracket(self, season, competition="Libertadores"):
        self._driver.knockout_bracket(season=season, competition=competition)

    def derbies(self, season=None):
        self._driver.derbies(season=season)

    def confirm_champion(self, team, **expected):
        self._driver.confirm_champion(team, **expected)

    def confirm_table_order(self, *teams):
        self._driver.confirm_table_order(teams)

    def confirm_relegated(self, *teams):
        self._driver.confirm_relegated(teams)

    def confirm_final(self, season, finalists, winner):
        self._driver.confirm_final(season, finalists, winner)

    def confirm_final_undecided(self, season):
        self._driver.confirm_final_undecided(season)

    def confirm_tie(self, stage, teams, winner):
        self._driver.confirm_tie(stage, teams, winner)

    def confirm_derbies(self, *derby_names):
        self._driver.confirm_derbies(derby_names)
