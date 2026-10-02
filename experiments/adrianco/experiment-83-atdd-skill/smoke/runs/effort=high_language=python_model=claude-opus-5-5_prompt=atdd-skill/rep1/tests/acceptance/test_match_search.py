"""
Executable specification: finding matches.

Layer 1 of the four-layer acceptance test model (test cases). These specs
are written in the language of Brazilian football and say nothing about how
the system answers. Each one builds its own synthetic dataset ("given"),
asks one question ("when") and confirms one outcome ("then").
"""


class MatchSearchSpec:
    def should_find_every_meeting_between_two_teams(self, given, matches):
        given.brasileirao_match(home="Flamengo", away="Fluminense", score="2-1", date="2023-09-03", round=22)
        given.brasileirao_match(home="Fluminense", away="Flamengo", score="1-0", date="2023-05-28", round=8)
        given.brasileirao_match(home="Flamengo", away="Vasco da Gama", score="3-0", date="2023-06-10")

        matches.search(team="Flamengo", opponent="Fluminense")

        matches.confirm_found(count=2)

    def should_list_the_most_recent_meeting_first_with_its_score(self, given, matches):
        given.brasileirao_match(home="Corinthians", away="Flamengo", score="1-1", date="2021-07-04")
        given.brasileirao_match(home="Flamengo", away="Corinthians", score="2-0", date="2022-10-16")

        matches.search(team="Flamengo", opponent="Corinthians")

        matches.confirm_first(date="2022-10-16", home="Flamengo", away="Corinthians", score="2-0")

    def should_find_a_teams_matches_in_a_season(self, given, matches):
        given.brasileirao_match(home="Palmeiras", away="Santos", season=2023)
        given.copa_do_brasil_match(home="Bahia", away="Palmeiras", season=2023)
        given.brasileirao_match(home="Palmeiras", away="Santos", season=2022)

        matches.search(team="Palmeiras", season=2023)

        matches.confirm_found(count=2)

    def should_find_only_home_matches_when_asked(self, given, matches):
        given.brasileirao_match(home="Gremio", away="Santos", date="2019-05-01")
        given.brasileirao_match(home="Santos", away="Gremio", date="2019-09-01")

        matches.search(team="Gremio", venue="home")

        matches.confirm_found(count=1)

    def should_find_matches_within_a_date_range(self, given, matches):
        given.historical_brasileirao_match(home="Cruzeiro", away="Bahia", date="2010-05-01")
        given.brasileirao_match(home="Cruzeiro", away="Bahia", date="2013-08-11")
        given.brasileirao_match(home="Cruzeiro", away="Bahia", date="2016-08-11")

        matches.search(team="Cruzeiro", date_from="2010-01-01", date_to="2014-12-31")

        matches.confirm_found(count=2)

    def should_find_matches_by_competition(self, given, matches):
        given.libertadores_match(home="Flamengo", away="River Plate", season=2019, stage="final")
        given.brasileirao_match(home="Flamengo", away="Santos", season=2019)

        matches.search(team="Flamengo", competition="Libertadores")

        matches.confirm_found(count=1, competition="Copa Libertadores")

    def should_find_matches_from_every_provided_source(self, given, matches):
        given.brasileirao_match(home="Santos", away="Ceara", date="2015-06-01")
        given.historical_brasileirao_match(home="Santos", away="Goias", date="2008-06-01")
        given.copa_do_brasil_match(home="Santos", away="Vitoria", date="2016-04-01")
        given.libertadores_match(home="Santos", away="Bolivar", date="2012-04-01")
        given.extended_stats_match(home="Santos", away="Sport", date="2023-06-01")

        matches.search(team="Santos")

        matches.confirm_found(count=5)

    def should_not_count_a_match_twice_when_datasets_overlap(self, given, matches):
        given.brasileirao_match(home="Internacional", away="Gremio", score="1-0", date="2016-07-10")
        given.historical_brasileirao_match(home="Internacional", away="Gremio", score="1-0", date="2016-07-10")
        given.extended_stats_match(home="Internacional", away="Gremio", score="1-0", date="2016-07-10")

        matches.search(team="Internacional", opponent="Gremio")

        matches.confirm_found(count=1)

    def should_not_report_a_result_for_a_fixture_that_was_never_played(self, given, matches):
        given.brasileirao_match(home="Santos", away="Bahia", date="2016-12-11")
        given.brasileirao_fixture_without_result(home="Chapecoense", away="Atletico-MG", date="2016-12-11")
        given.historical_brasileirao_match(home="Chapecoense", away="Atletico-MG", score="0-0", date="2016-12-11")

        matches.search(team="Chapecoense")

        matches.confirm_found(count=0)

    def should_take_the_result_from_another_dataset_when_one_was_compiled_before_the_match(self, given, matches):
        given.brasileirao_match(home="Santos", away="Bahia", date="2022-10-06")
        given.brasileirao_fixture_without_result(home="Flamengo", away="Santos", date="2022-11-13")
        given.extended_stats_match(home="Flamengo", away="Santos", score="2-1", date="2022-11-13")

        matches.search(team="Flamengo")

        matches.confirm_first(date="2022-11-13", score="2-1")

    def should_ignore_a_match_wrongly_labelled_as_brasileirao(self, given, matches):
        given.brasileirao_match(home="Santos", away="Bahia", season=2016)
        given.extended_stats_match(home="Brasilia", away="CA Taguatinga", tournament="Serie A", date="2016-01-30")

        matches.search(competition="Brasileirão", season=2016)

        matches.confirm_found(count=1)

    def should_include_corner_and_shot_statistics_when_they_are_known(self, given, matches):
        given.extended_stats_match(home="Bahia", away="Vitoria", date="2023-04-02", corners="7-3", shots="15-6")

        matches.search(team="Bahia")

        matches.confirm_first(date="2023-04-02", corners="7-3", shots="15-6")
