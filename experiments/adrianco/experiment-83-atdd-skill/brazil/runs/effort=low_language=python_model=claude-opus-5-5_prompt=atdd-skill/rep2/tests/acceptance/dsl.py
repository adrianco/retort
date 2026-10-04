"""DSL: domain vocabulary for the specs; delegates to a protocol driver."""


class SoccerKnowledgeDsl:
    def __init__(self, driver):
        self.driver = driver

    # --- questions -------------------------------------------------------
    def ask_for_matches(self, **criteria):
        self.driver.ask("search_matches", **criteria)

    def ask_for_last_meeting(self, team, opponent):
        self.driver.ask("last_meeting", team=team, opponent=opponent)

    def ask_for_team_record(self, team, season=None, venue="all", competition="Brasileirão"):
        self.driver.ask("team_record", team=team, season=season, venue=venue, competition=competition)

    def ask_for_head_to_head(self, team, opponent):
        self.driver.ask("head_to_head", team=team, opponent=opponent)

    def ask_for_competitions_of(self, team):
        self.driver.ask("team_competitions", team=team)

    def ask_for_players(self, limit=20, **criteria):
        self.driver.ask("search_players", limit=limit, **criteria)

    def ask_for_brazilian_club_squads(self):
        self.driver.ask("brazilian_club_squads")

    def ask_for_standings(self, season, sort_by="points"):
        self.driver.ask("standings", season=season, sort_by=sort_by)

    def ask_for_competition_statistics(self, competition, season=None):
        self.driver.ask("competition_stats", competition=competition, season=season)

    def ask_for_biggest_wins(self, limit=10, competition=None):
        self.driver.ask("biggest_wins", limit=limit, competition=competition)

    def ask_for_best_records(self, venue="all", limit=10, min_matches=19):
        self.driver.ask("best_records", venue=venue, limit=limit, min_matches=min_matches)

    def last_answer(self):
        return self.driver.last_answer

    # --- confirmations ---------------------------------------------------
    def confirm_matches_were_found(self):
        self.driver.confirm_matches_listed()

    def confirm_every_match_involves(self, *teams):
        self.driver.confirm_every_match_involves(teams)

    def confirm_every_match_is_in_season(self, season):
        self.driver.confirm_every_match_has(season=season)

    def confirm_every_match_is_in_competition(self, competition):
        self.driver.confirm_every_match_has(competition=competition)

    def confirm_head_to_head_summary_is_shown(self):
        self.driver.confirm_head_to_head()

    def confirm_a_score_is_reported(self):
        self.driver.confirm_matches_listed(exactly=1)

    def confirm_record_has(self, matches):
        self.driver.confirm_record(matches=matches)

    def confirm_answer_equals(self, previous):
        assert self.driver.last_answer == previous

    def confirm_answer_mentions(self, *phrases):
        self.driver.confirm_mentions(phrases)

    def confirm_first_listed_player_is(self, name):
        self.driver.confirm_first_ranked(name)

    def confirm_first_listed_team_is(self, name):
        self.driver.confirm_first_ranked(name)

    def confirm_players_were_found(self):
        self.driver.confirm_ranked_entries()

    def confirm_champion_is(self, team, points):
        self.driver.confirm_champion(team, points)

    def confirm_relegated_teams_are_shown(self, count):
        self.driver.confirm_relegated(count)

    def confirm_answered_within(self, seconds, question, **criteria):
        self.driver.confirm_answer_time(seconds, question, **criteria)
