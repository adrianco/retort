"""Executable specifications for the Brazilian Soccer knowledge server.

Written in the language of the problem domain. They say nothing about how
the server works; the DSL and protocol driver handle that.
"""


class TestMatchQueries:
    def test_should_find_matches_between_two_rivals(self, soccer):
        soccer.ask_for_matches(team="Flamengo", opponent="Fluminense")
        soccer.confirm_every_match_involves("Flamengo", "Fluminense")
        soccer.confirm_head_to_head_summary_is_shown()

    def test_should_find_a_teams_matches_in_a_season(self, soccer):
        soccer.ask_for_matches(team="Palmeiras", season=2022)
        soccer.confirm_every_match_involves("Palmeiras")
        soccer.confirm_every_match_is_in_season(2022)

    def test_should_find_copa_do_brasil_finals(self, soccer):
        soccer.ask_for_matches(competition="Copa do Brasil", stage="final")
        soccer.confirm_matches_were_found()
        soccer.confirm_every_match_is_in_competition("Copa do Brasil")

    def test_should_find_matches_in_a_date_range(self, soccer):
        soccer.ask_for_matches(team="Corinthians", date_from="2019-01-01", date_to="2019-12-31")
        soccer.confirm_every_match_is_in_season(2019)

    def test_should_find_the_most_recent_meeting(self, soccer):
        soccer.ask_for_last_meeting("Flamengo", "Corinthians")
        soccer.confirm_a_score_is_reported()

    def test_should_search_every_match_source(self, soccer):
        for competition in ["Brasileirão", "Copa do Brasil", "Libertadores", "Serie B", "Serie C"]:
            soccer.ask_for_matches(competition=competition)
            soccer.confirm_matches_were_found()


class TestTeamQueries:
    def test_should_report_a_home_record_for_a_season(self, soccer):
        soccer.ask_for_team_record("Corinthians", season=2019, venue="home")
        soccer.confirm_record_has(matches=19)

    def test_should_treat_team_name_variations_as_the_same_team(self, soccer):
        soccer.ask_for_team_record("Palmeiras-SP", season=2019)
        first = soccer.last_answer()
        soccer.ask_for_team_record("palmeiras", season=2019)
        soccer.confirm_answer_equals(first)

    def test_should_handle_accented_names(self, soccer):
        soccer.ask_for_team_record("Grêmio", season=2018)
        soccer.confirm_record_has(matches=38)
        soccer.ask_for_team_record("Gremio", season=2018)
        soccer.confirm_record_has(matches=38)

    def test_should_compare_two_teams_head_to_head(self, soccer):
        soccer.ask_for_head_to_head("Palmeiras", "Santos")
        soccer.confirm_head_to_head_summary_is_shown()

    def test_should_list_competitions_a_team_played_in(self, soccer):
        soccer.ask_for_competitions_of("Palmeiras")
        soccer.confirm_answer_mentions("Brasileirão", "Copa do Brasil", "Libertadores")


class TestPlayerQueries:
    def test_should_find_a_player_by_name(self, soccer):
        soccer.ask_for_players(name="Neymar")
        soccer.confirm_answer_mentions("Neymar Jr", "Brazil")

    def test_should_rank_top_brazilian_players(self, soccer):
        soccer.ask_for_players(nationality="Brazil", limit=3)
        soccer.confirm_first_listed_player_is("Neymar Jr")

    def test_should_find_players_at_a_club(self, soccer):
        soccer.ask_for_players(club="Grêmio")
        soccer.confirm_answer_mentions("Grêmio")
        soccer.confirm_players_were_found()

    def test_should_find_players_by_position(self, soccer):
        soccer.ask_for_players(club="Santos", position="ST")
        soccer.confirm_players_were_found()

    def test_should_summarise_brazilian_players_by_club(self, soccer):
        soccer.ask_for_brazilian_club_squads()
        soccer.confirm_answer_mentions("Grêmio", "avg rating")


class TestCompetitionQueries:
    def test_should_crown_the_2019_brasileirao_champion(self, soccer):
        soccer.ask_for_standings(season=2019)
        soccer.confirm_champion_is("Flamengo", points=90)

    def test_should_identify_relegated_teams(self, soccer):
        soccer.ask_for_standings(season=2020)
        soccer.confirm_relegated_teams_are_shown(count=4)

    def test_should_show_libertadores_knockout_bracket(self, soccer):
        soccer.ask_for_matches(competition="Libertadores", season=2018, stage="final")
        soccer.confirm_matches_were_found()

    def test_should_report_the_top_scoring_team_of_a_season(self, soccer):
        soccer.ask_for_standings(season=2019, sort_by="goals_for")
        soccer.confirm_first_listed_team_is("Flamengo")


class TestStatistics:
    def test_should_report_average_goals_per_match(self, soccer):
        soccer.ask_for_competition_statistics("Brasileirão")
        soccer.confirm_answer_mentions("Average goals per match", "Home win rate")

    def test_should_compare_two_seasons(self, soccer):
        soccer.ask_for_competition_statistics("Brasileirão", season=2018)
        soccer.ask_for_competition_statistics("Brasileirão", season=2019)
        soccer.confirm_answer_mentions("2019")

    def test_should_list_the_biggest_wins(self, soccer):
        soccer.ask_for_biggest_wins(limit=5)
        soccer.confirm_matches_were_found()

    def test_should_rank_the_best_away_teams(self, soccer):
        soccer.ask_for_best_records(venue="away", limit=5)
        soccer.confirm_answer_mentions("Win rate")


class TestServiceQuality:
    def test_should_answer_aggregate_questions_promptly(self, soccer):
        soccer.confirm_answered_within(seconds=5, question="standings", season=2015)

    def test_should_answer_lookups_promptly(self, soccer):
        soccer.confirm_answered_within(seconds=2, question="players", name="Casemiro")
