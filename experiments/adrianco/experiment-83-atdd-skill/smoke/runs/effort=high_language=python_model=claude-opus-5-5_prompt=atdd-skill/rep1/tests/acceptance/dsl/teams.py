"""
DSL (layer 2): team records, head-to-heads and the competitions a team plays in.
"""


class Teams:
    def __init__(self, driver):
        self._driver = driver

    def record(self, team, season=None, competition=None, venue="all"):
        self._driver.team_record(team=team, season=season, competition=competition, venue=venue)

    def head_to_head(self, team, other_team, competition=None):
        self._driver.head_to_head(team, other_team, competition=competition)

    def competitions_played(self, team):
        self._driver.competitions_played(team)

    def confirm_record(self, **expected):
        self._driver.confirm_record(**expected)

    def confirm_head_to_head(self, matches, first_team_wins, second_team_wins, draws):
        self._driver.confirm_head_to_head(matches, first_team_wins, second_team_wins, draws)

    def confirm_competitions(self, *competitions):
        self._driver.confirm_competitions(competitions)

    def confirm_team_not_recognised(self, team):
        self._driver.confirm_team_not_recognised(team)
