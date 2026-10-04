"""DSL layer: domain vocabulary for asking questions about Brazilian soccer.

Named parameters with defaults so specs only state what they care about.
Delegates to a protocol driver at the same level of abstraction.
"""


class SoccerDsl:
    def __init__(self, driver):
        self.driver = driver

    # questions
    def ask_for_matches_between(self, team, opponent, **criteria):
        self.driver.ask("search_matches", team=team, opponent=opponent, limit=500, **criteria)

    def ask_for_matches(self, team=None, competition=None, season=None, stage=None,
                        date_from=None, date_to=None):
        self.driver.ask("search_matches", team=team, competition=competition, season=season,
                        stage=stage, date_from=date_from, date_to=date_to, limit=500)

    def ask_when_teams_last_met(self, team, opponent):
        self.driver.ask("last_meeting", team_a=team, team_b=opponent)

    def ask_for_team_record(self, team, season=None, competition=None, venue="all"):
        self.driver.ask("team_record", team=team, season=season, competition=competition, venue=venue)

    def ask_for_head_to_head(self, team, opponent):
        self.driver.ask("head_to_head", team_a=team, team_b=opponent)

    def ask_which_competitions(self, team):
        self.driver.ask("team_competitions", team=team)

    def ask_for_top_scoring_team(self, season, competition="Brasileirão"):
        self.driver.ask("top_scoring_team", season=season, competition=competition)

    def ask_for_standings(self, season, competition="Brasileirão"):
        self.driver.ask("standings", season=season, competition=competition)

    def ask_for_relegated_teams(self, season):
        self.driver.ask("relegated_teams", season=season)

    def ask_for_bracket(self, season):
        self.driver.ask("libertadores_bracket", season=season)

    def ask_about_player(self, name):
        self.driver.ask("search_players", name=name)

    def ask_for_players(self, nationality=None, club=None, position=None, limit=20):
        self.driver.ask("search_players", nationality=nationality, club=club, position=position, limit=limit)

    def ask_for_brazilian_club_summary(self):
        self.driver.ask("brazilian_clubs_players_summary")

    def ask_for_competition_statistics(self, competition=None, season=None):
        self.driver.ask("competition_statistics", competition=competition, season=season)

    def ask_for_biggest_wins(self, competition=None, season=None, limit=10):
        self.driver.ask("biggest_wins", competition=competition, season=season, limit=limit)

    def ask_for_best_record(self, venue="all", competition=None, season=None):
        self.driver.ask("best_record", venue=venue, competition=competition, season=season)

    def ask_to_compare_seasons(self, season_a, season_b, competition="Brasileirão"):
        self.driver.ask("compare_seasons", season_a=season_a, season_b=season_b, competition=competition)

    def ask_for_derbies(self, season=None):
        self.driver.ask("derbies", season=season)

    def ask_for_club_profile(self, club):
        self.driver.ask("club_profile", club=club)

    def ask_for_dataset_overview(self):
        self.driver.ask("dataset_overview")

    # checks
    def last_answer(self):
        return self.driver.last_answer

    def confirm_answer_equals(self, expected):
        self.driver.confirm_answer_equals(expected)

    def confirm_answer_mentions(self, *phrases):
        self.driver.confirm_answer_mentions(*phrases)

    def confirm_match_listed(self, date, home, home_goals, away, away_goals):
        self.driver.confirm_match_listed(date, home, home_goals, away, away_goals)

    def confirm_match_count(self, count):
        self.driver.confirm_match_count(count)

    def confirm_record(self, matches):
        self.driver.confirm_record(matches)

    def confirm_champion(self, team, points=None):
        self.driver.confirm_champion(team, points)

    def confirm_first_player(self, name):
        self.driver.confirm_first_player(name)

    def confirm_every_player_has_position(self, position):
        self.driver.confirm_every_player_has_position(position)

    def confirm_answer_line_count_at_least(self, n):
        self.driver.confirm_answer_line_count_at_least(n)

    def confirm_answered_within(self, seconds):
        self.driver.confirm_answered_within(seconds)
