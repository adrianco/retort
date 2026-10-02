"""
DSL (layer 2): players, squads and Brazilian clubs.
"""


class Players:
    def __init__(self, driver):
        self._driver = driver

    def profile(self, name):
        self._driver.player_profile(name)

    def search(self, name=None, nationality=None, club=None, position=None):
        self._driver.search_players(name=name, nationality=nationality, club=club, position=position)

    def summarise_by_brazilian_club(self, nationality=None):
        self._driver.brazilian_club_summary(nationality=nationality)

    def team_profile(self, team):
        self._driver.team_profile(team)

    def confirm_profile(self, **expected):
        self._driver.confirm_player_profile(**expected)

    def confirm_found(self, count):
        self._driver.confirm_player_count(count)

    def confirm_found_in_order(self, *names):
        self._driver.confirm_players_in_order(names)

    def confirm_club_summary(self, club, players, average_overall):
        self._driver.confirm_club_summary(club, players, average_overall)

    def confirm_club_not_in_summary(self, club):
        self._driver.confirm_club_not_in_summary(club)

    def confirm_team_profile(self, wins, squad_includes):
        self._driver.confirm_team_profile(wins, squad_includes)
