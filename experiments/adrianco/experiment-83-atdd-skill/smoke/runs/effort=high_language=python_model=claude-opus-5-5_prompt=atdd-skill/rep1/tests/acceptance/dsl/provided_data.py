"""
DSL (layer 2): questions asked of the real, provided datasets.

Reuses the same domain vocabulary as the synthetic-data specs, so a sample
question reads the same whichever dataset it is asked of.
"""

from .competitions import Competitions
from .matches import Matches
from .players import Players
from .statistics import Statistics
from .teams import Teams


class ProvidedData:
    def __init__(self, driver):
        self._driver = driver
        self._matches = Matches(driver)
        self._teams = Teams(driver)
        self._players = Players(driver)
        self._competitions = Competitions(driver)
        self._statistics = Statistics(driver)

    def within_seconds(self, seconds):
        return _TimeLimited(self, self._driver, seconds)

    # questions
    def dataset_overview(self):
        self._driver.dataset_overview()

    def search_matches(self, **criteria):
        self._matches.search(**criteria)

    def team_record(self, team, **criteria):
        self._teams.record(team, **criteria)

    def head_to_head(self, team, other_team):
        self._teams.head_to_head(team, other_team)

    def competitions_played(self, team):
        self._teams.competitions_played(team)

    def search_players(self, **criteria):
        self._players.search(**criteria)

    def player_profile(self, name):
        self._players.profile(name)

    def summarise_by_brazilian_club(self, nationality=None):
        self._players.summarise_by_brazilian_club(nationality)

    def team_profile(self, team):
        self._players.team_profile(team)

    def standings(self, season):
        self._competitions.standings(season)

    def finals(self, competition, season=None):
        self._competitions.finals(competition, season)

    def knockout_bracket(self, season):
        self._competitions.knockout_bracket(season)

    def derbies(self, season=None):
        self._competitions.derbies(season)

    def competition_summary(self, competition=None, season=None):
        self._statistics.competition_summary(competition, season)

    def biggest_wins(self):
        self._statistics.biggest_wins()

    def rank_teams(self, by, **criteria):
        self._statistics.rank_teams(by, **criteria)

    def compare_seasons(self, season, other_season):
        self._statistics.compare_seasons(season, other_season)

    # confirmations
    def confirm_answered(self):
        self._driver.confirm_answered()

    def confirm_file_loaded(self, file_name, rows):
        self._driver.confirm_file_loaded(file_name, rows)

    def confirm_champion(self, team, **expected):
        self._competitions.confirm_champion(team, **expected)

    def confirm_relegated(self, *teams):
        self._competitions.confirm_relegated(*teams)

    def confirm_final(self, season, finalists, winner):
        self._competitions.confirm_final(season, finalists, winner)

    def confirm_players_start_with(self, *names):
        self._players.confirm_found_in_order(*names)


class _TimeLimited:
    """Asks the next question with a time limit on the answer."""

    def __init__(self, questions, driver, seconds):
        self._questions = questions
        self._driver = driver
        self._seconds = seconds

    def __getattr__(self, question):
        ask = getattr(self._questions, question)

        def timed(*args, **kwargs):
            with self._driver.time_limit(self._seconds):
                ask(*args, **kwargs)
        return timed
