"""
DSL (layer 2): aggregate statistics, rankings and season comparisons.
"""

METRICS = {"win rate": "win_rate", "goals scored": "goals_scored", "goals conceded": "goals_conceded",
           "points": "points", "wins": "wins"}


class Statistics:
    def __init__(self, driver):
        self._driver = driver

    def competition_summary(self, competition=None, season=None):
        self._driver.competition_summary(competition=competition, season=season)

    def biggest_wins(self, competition=None, season=None):
        self._driver.biggest_wins(competition=competition, season=season)

    def rank_teams(self, by, venue="all", competition=None, season=None):
        self._driver.rank_teams(metric=METRICS[by], venue=venue, competition=competition, season=season)

    def compare_seasons(self, season, other_season, competition="Brasileirão"):
        self._driver.compare_seasons(season, other_season, competition=competition)

    def confirm_summary(self, **expected):
        self._driver.confirm_summary(**expected)

    def confirm_ranking(self, *teams):
        self._driver.confirm_ranking(teams)

    def confirm_season_average_goals(self, season, average_goals):
        self._driver.confirm_season_average_goals(season, average_goals)
