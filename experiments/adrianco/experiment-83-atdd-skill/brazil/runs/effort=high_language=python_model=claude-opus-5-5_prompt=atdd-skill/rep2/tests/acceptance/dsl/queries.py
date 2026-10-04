"""
DSL (layer 2): asking questions about Brazilian football and confirming answers.

Decomposed by domain area (matches, teams, competitions, statistics, players)
so specs read naturally and no one class becomes a dumping ground. Each method
keeps the same level of abstraction as the spec that calls it, adds defaults,
and delegates to the protocol driver, which is where the assertions live.

Query methods (no "confirm_" prefix) return the answer so specs about
responsiveness can time them; "confirm_" methods pass or fail.
"""

BRASILEIRAO = "Brasileirão"


class Matches:
    def __init__(self, driver):
        self._driver = driver

    def meetings(self, team, opponent, competition=None):
        return self._driver.find_matches(team=team, opponent=opponent, competition=competition)

    def confirm_meetings(self, team, opponent, count=None, listed=None, from_competitions=None, at_least=None):
        self._driver.confirm_meetings(team, opponent, count=count, listed=listed,
                                      from_competitions=from_competitions, at_least=at_least)

    def team_played(self, team, season=None, competition=None, venue="any"):
        return self._driver.find_matches(team=team, season=season, competition=competition, venue=venue)

    def confirm_team_played(self, team, count, season=None, competition=None, venue="any"):
        self._driver.confirm_matches_found(dict(team=team, season=season, competition=competition, venue=venue),
                                           count=count)

    def find(self, **criteria):
        return self._driver.find_matches(**criteria)

    def confirm_found(self, count, **criteria):
        self._driver.confirm_matches_found(criteria, count=count)

    def confirm_statistics(self, team, opponent, **statistics):
        self._driver.confirm_match_statistics(team, opponent, statistics)

    def last_meeting(self, team, opponent):
        return self._driver.head_to_head(team, opponent)

    def confirm_last_meeting(self, team, opponent, meeting):
        self._driver.confirm_last_meeting(team, opponent, meeting)


class Teams:
    def __init__(self, driver):
        self._driver = driver

    def record(self, team, season=None, competition=None, venue="all"):
        return self._driver.team_record(team, season=season, competition=competition, venue=venue)

    def confirm_record(self, team, season=None, competition=None, venue="all", **expected):
        self._driver.confirm_team_record(team, dict(season=season, competition=competition, venue=venue), expected)

    def confirm_unknown(self, team, suggesting=None):
        self._driver.confirm_unknown_team(team, suggesting)

    def head_to_head(self, team, opponent):
        return self._driver.head_to_head(team, opponent)

    def confirm_head_to_head(self, team, opponent, wins, draws):
        self._driver.confirm_head_to_head(team, opponent, wins=wins, draws=draws)

    def competitions(self, team):
        return self._driver.team_competitions(team)

    def confirm_competitions(self, team, competitions):
        self._driver.confirm_team_competitions(team, competitions)

    def club_profile(self, team):
        return self._driver.club_profile(team)

    def confirm_club_profile(self, team, **expected):
        self._driver.confirm_club_profile(team, expected)


class Competitions:
    def __init__(self, driver):
        self._driver = driver

    def table(self, season, competition=BRASILEIRAO):
        return self._driver.league_table(season, competition)

    def confirm_champion(self, season, team, competition=BRASILEIRAO):
        self._driver.confirm_champion(season, competition, team)

    def confirm_standing(self, season, position, team, competition=BRASILEIRAO, **expected):
        self._driver.confirm_standing(season, competition, position, team, expected)

    def confirm_relegated(self, season, teams, competition=BRASILEIRAO):
        self._driver.confirm_relegated(season, competition, teams)

    def top_scoring_teams(self, season, competition=BRASILEIRAO):
        return self._driver.top_scoring_teams(season, competition)

    def confirm_top_scoring_team(self, season, team, goals, competition=BRASILEIRAO):
        self._driver.confirm_top_scoring_team(season, competition, team, goals)

    def bracket(self, competition, season):
        return self._driver.knockout_bracket(competition, season)

    def confirm_bracket(self, competition, season, stages):
        self._driver.confirm_bracket(competition, season, stages)


class Statistics:
    def __init__(self, driver):
        self._driver = driver

    def summary(self, competition=None, season=None):
        return self._driver.competition_summary(competition, season)

    def confirm_summary(self, competition=None, season=None, **expected):
        self._driver.confirm_competition_summary(competition, season, expected)

    def biggest_wins(self, competition=None, season=None):
        return self._driver.biggest_wins(competition, season)

    def confirm_biggest_wins(self, listed, competition=None, season=None):
        self._driver.confirm_biggest_wins(competition, season, listed)

    def best_records(self, venue="all", competition=None, season=None):
        return self._driver.best_records(venue, competition, season)

    def confirm_best_record(self, venue, team, competition=None, season=None):
        self._driver.confirm_best_record(venue, competition, season, team)

    def compare_seasons(self, season, other_season, competition=BRASILEIRAO):
        return self._driver.compare_seasons(season, other_season, competition)

    def confirm_season_comparison(self, season, other_season, average_goals, competition=BRASILEIRAO):
        self._driver.confirm_season_comparison(season, other_season, competition, average_goals)

    def derbies(self, season=None):
        return self._driver.derbies(season)

    def confirm_derbies(self, season, rivalries):
        self._driver.confirm_derbies(season, rivalries)


class Players:
    def __init__(self, driver):
        self._driver = driver

    def profile(self, name):
        return self._driver.player_profile(name)

    def confirm_profile(self, name, **expected):
        self._driver.confirm_player_profile(name, expected)

    def confirm_not_found(self, name, suggesting):
        self._driver.confirm_player_not_found(name, suggesting)

    def top(self, nationality=None, club=None, position=None):
        return self._driver.search_players(dict(nationality=nationality, club=club, position=position))

    def confirm_top_players(self, ranked, nationality=None, club=None, position=None, in_any_order=False):
        self._driver.confirm_top_players(dict(nationality=nationality, club=club, position=position),
                                         ranked, in_any_order)

    def brazilians_at_brazilian_clubs(self):
        return self._driver.brazilians_at_brazilian_clubs()

    def confirm_brazilians_at_brazilian_clubs(self, clubs):
        self._driver.confirm_brazilians_at_brazilian_clubs(clubs)
