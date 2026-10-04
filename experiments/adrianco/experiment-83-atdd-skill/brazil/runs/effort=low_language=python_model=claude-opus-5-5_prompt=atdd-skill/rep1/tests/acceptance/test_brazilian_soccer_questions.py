"""Executable specifications: questions a fan can ask about Brazilian soccer.

Written in the language of the problem domain; the DSL (`soccer`) hides how
the questions reach the system.
"""


# --- Match queries -------------------------------------------------------

def test_should_find_matches_between_two_rivals(soccer):
    soccer.ask_for_matches_between("Flamengo", "Fluminense")
    soccer.confirm_match_listed(date="2019-10-20", home="Flamengo", home_goals=2, away="Fluminense", away_goals=0)


def test_should_find_a_teams_matches_in_a_season(soccer):
    soccer.ask_for_matches(team="Palmeiras", season=2022, competition="Brasileirão")
    soccer.confirm_match_count(38)


def test_should_find_cup_finals(soccer):
    soccer.ask_for_matches(competition="Copa do Brasil", stage="final")
    soccer.confirm_answer_mentions("Copa do Brasil")


def test_should_find_matches_in_a_date_range(soccer):
    soccer.ask_for_matches(team="Corinthians", date_from="2019-01-01", date_to="2019-12-31", competition="Brasileirão")
    soccer.confirm_match_count(38)


def test_should_find_when_two_teams_last_met(soccer):
    soccer.ask_when_teams_last_met("Flamengo", "Corinthians")
    soccer.confirm_answer_mentions("Flamengo", "Corinthians")


def test_should_find_libertadores_matches(soccer):
    soccer.ask_for_matches(team="Palmeiras", competition="Libertadores", season=2021, stage="semifinals")
    soccer.confirm_answer_mentions("Palmeiras", "Atlético-MG")


# --- Team name variations ------------------------------------------------

def test_should_treat_team_name_variations_as_the_same_team(soccer):
    soccer.ask_for_matches(team="Palmeiras-SP", season=2022, competition="Brasileirão")
    soccer.confirm_match_count(38)


def test_should_understand_accented_and_unaccented_names(soccer):
    soccer.ask_for_team_record("Grêmio", season=2019, competition="Brasileirão")
    first = soccer.last_answer()
    soccer.ask_for_team_record("Gremio", season=2019, competition="Brasileirão")
    soccer.confirm_answer_equals(first)


def test_should_distinguish_teams_sharing_a_name(soccer):
    soccer.ask_for_team_record("Atletico-MG", season=2019, competition="Brasileirão")
    soccer.confirm_record(matches=38)


# --- Team queries --------------------------------------------------------

def test_should_report_a_teams_home_record(soccer):
    soccer.ask_for_team_record("Corinthians", season=2022, competition="Brasileirão", venue="home")
    soccer.confirm_record(matches=19)


def test_should_compare_two_teams_head_to_head(soccer):
    soccer.ask_for_head_to_head("Palmeiras", "Santos")
    soccer.confirm_answer_mentions("Palmeiras", "Santos", "wins", "draws")


def test_should_list_competitions_a_team_has_played_in(soccer):
    soccer.ask_which_competitions("Palmeiras")
    soccer.confirm_answer_mentions("Brasileirão", "Copa do Brasil", "Libertadores")


def test_should_find_top_scoring_team_of_a_season(soccer):
    soccer.ask_for_top_scoring_team(season=2019)
    soccer.confirm_answer_mentions("Flamengo")


# --- Competition queries -------------------------------------------------

def test_should_name_the_champion_of_a_season(soccer):
    soccer.ask_for_standings(season=2019)
    soccer.confirm_champion("Flamengo", points=90)


def test_should_list_relegated_teams(soccer):
    soccer.ask_for_relegated_teams(season=2019)
    soccer.confirm_answer_mentions("Avai", "Cruzeiro", "Chapecoense", "Csa")


def test_should_calculate_standings_from_historical_seasons(soccer):
    soccer.ask_for_standings(season=2005)
    soccer.confirm_champion("Corinthians")


def test_should_show_libertadores_knockout_bracket(soccer):
    soccer.ask_for_bracket(season=2018)
    soccer.confirm_answer_mentions("final", "River Plate")


# --- Player queries ------------------------------------------------------

def test_should_find_a_player_by_name(soccer):
    soccer.ask_about_player("Neymar")
    soccer.confirm_answer_mentions("Neymar Jr", "Paris Saint-Germain", "92")


def test_should_rank_top_brazilian_players(soccer):
    soccer.ask_for_players(nationality="Brazil")
    soccer.confirm_first_player("Neymar Jr")


def test_should_find_players_at_a_brazilian_club(soccer):
    soccer.ask_for_players(club="Santos")
    soccer.confirm_answer_mentions("Santos")


def test_should_filter_players_by_position(soccer):
    soccer.ask_for_players(club="Grêmio", position="ST")
    soccer.confirm_every_player_has_position("ST")


def test_should_summarise_brazilian_players_at_brazilian_clubs(soccer):
    soccer.ask_for_brazilian_club_summary()
    soccer.confirm_answer_mentions("Santos", "avg rating")


# --- Statistics ----------------------------------------------------------

def test_should_report_average_goals_per_match(soccer):
    soccer.ask_for_competition_statistics(competition="Brasileirão")
    soccer.confirm_answer_mentions("Average goals per match", "Home win rate")


def test_should_list_biggest_wins(soccer):
    soccer.ask_for_biggest_wins(competition="Brasileirão", limit=5)
    soccer.confirm_answer_line_count_at_least(5)


def test_should_find_best_home_record(soccer):
    soccer.ask_for_best_record(venue="home", competition="Brasileirão")
    soccer.confirm_answer_mentions("win rate")


def test_should_compare_two_seasons(soccer):
    soccer.ask_to_compare_seasons(2018, 2019)
    soccer.confirm_answer_mentions("2018", "2019", "goals per match")


def test_should_find_derbies_in_a_season(soccer):
    soccer.ask_for_derbies(season=2019)
    soccer.confirm_answer_mentions("Flamengo", "Fluminense")


def test_should_report_extended_match_statistics(soccer):
    soccer.ask_for_matches(team="Flamengo", competition="Copa do Brasil", season=2023)
    soccer.confirm_answer_mentions("corners")


def test_should_combine_player_and_match_data_for_a_club(soccer):
    soccer.ask_for_club_profile("Santos")
    soccer.confirm_answer_mentions("players", "Brasileirão")


# --- Coverage & performance ---------------------------------------------

def test_should_load_every_provided_dataset(soccer):
    soccer.ask_for_dataset_overview()
    soccer.confirm_answer_mentions(
        "Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv",
        "BR-Football-Dataset.csv", "novo_campeonato_brasileiro.csv", "fifa_data.csv")


def test_should_answer_aggregate_questions_quickly(soccer):
    soccer.ask_for_best_record(venue="away")
    soccer.confirm_answered_within(seconds=5)


def test_should_answer_lookups_quickly(soccer):
    soccer.ask_about_player("Casemiro")
    soccer.confirm_answered_within(seconds=2)
