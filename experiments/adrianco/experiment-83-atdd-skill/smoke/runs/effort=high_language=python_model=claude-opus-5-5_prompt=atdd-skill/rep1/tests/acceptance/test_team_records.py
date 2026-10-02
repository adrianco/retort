"""
Executable specification: team records, head-to-heads and team identity.

Layer 1 of the four-layer acceptance test model. Team names deliberately
vary between datasets ("Corinthians-SP", "Corinthians - SP", "Sport Club
Corinthians Paulista", "Sao Paulo" / "São Paulo"); these specs pin down
that the system still recognises one club.
"""


class TeamRecordSpec:
    def should_calculate_a_teams_home_record_for_a_season(self, given, teams):
        given.brasileirao_match(home="Corinthians", away="Santos", score="2-0", season=2022)
        given.brasileirao_match(home="Corinthians", away="Palmeiras", score="1-1", season=2022)
        given.brasileirao_match(home="Corinthians", away="Flamengo", score="0-3", season=2022)
        given.brasileirao_match(home="Santos", away="Corinthians", score="0-4", season=2022)

        teams.record(team="Corinthians", season=2022, venue="home")

        teams.confirm_record(matches=3, wins=1, draws=1, losses=1, goals_for=3, goals_against=4, win_rate="33.3%")

    def should_calculate_a_teams_away_record(self, given, teams):
        given.brasileirao_match(home="Santos", away="Corinthians", score="0-4")
        given.brasileirao_match(home="Corinthians", away="Santos", score="2-0")

        teams.record(team="Corinthians", venue="away")

        teams.confirm_record(matches=1, wins=1, goals_for=4, goals_against=0)

    def should_compare_two_teams_head_to_head(self, given, teams):
        given.brasileirao_match(home="Palmeiras", away="Santos", score="3-1", date="2020-02-01")
        given.brasileirao_match(home="Santos", away="Palmeiras", score="0-2", date="2020-09-01")
        given.copa_do_brasil_match(home="Santos", away="Palmeiras", score="1-1", date="2021-04-01")

        teams.head_to_head("Palmeiras", "Santos")

        teams.confirm_head_to_head(matches=3, first_team_wins=2, second_team_wins=0, draws=1)

    def should_recognise_a_team_however_a_dataset_names_it(self, given, teams):
        given.brasileirao_match(home="Corinthians-SP", away="Santos-SP")
        given.copa_do_brasil_match(home="Corinthians - SP", away="Bahia - BA")
        given.extended_stats_match(home="Sport Club Corinthians Paulista", away="Gremio")

        teams.record(team="Corinthians")

        teams.confirm_record(matches=3)

    def should_treat_accented_and_unaccented_names_as_the_same_team(self, given, teams):
        given.brasileirao_match(home="Sao Paulo-SP", away="Santos-SP", date="2015-05-01")
        given.historical_brasileirao_match(home="São Paulo", away="Grêmio", date="2008-05-01")

        teams.record(team="São Paulo")

        teams.confirm_record(matches=2)

    def should_keep_clubs_that_share_a_name_in_different_states_apart(self, given, teams):
        given.brasileirao_match(home="Atletico-MG", away="Cruzeiro-MG")
        given.brasileirao_match(home="Atletico-PR", away="Coritiba-PR")

        teams.record(team="Atletico-MG")

        teams.confirm_record(matches=1)

    def should_keep_a_foreign_club_apart_from_its_brazilian_namesake(self, given, teams):
        given.brasileirao_match(home="Guarani", away="Santos")
        given.libertadores_match(home="Guaraní (PAR)", away="Palmeiras")

        teams.record(team="Guarani")

        teams.confirm_record(matches=1)

    def should_list_the_competitions_a_team_has_played_in(self, given, teams):
        given.brasileirao_match(home="Palmeiras", away="Santos", season=2018)
        given.copa_do_brasil_match(home="Palmeiras", away="Bahia", season=2018)
        given.libertadores_match(home="Palmeiras", away="Boca Juniors", season=2018)

        teams.competitions_played(team="Palmeiras")

        teams.confirm_competitions("Brasileirão Série A", "Copa do Brasil", "Copa Libertadores")

    def should_explain_when_it_does_not_recognise_a_team(self, given, teams):
        given.brasileirao_match(home="Palmeiras", away="Santos")

        teams.record(team="Real Madrid")

        teams.confirm_team_not_recognised("Real Madrid")
