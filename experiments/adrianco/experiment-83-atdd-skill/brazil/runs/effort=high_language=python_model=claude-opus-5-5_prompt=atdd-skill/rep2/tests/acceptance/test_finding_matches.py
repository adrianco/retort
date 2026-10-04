"""
Executable specifications: finding matches.

Capability: a fan (via an LLM) can find matches by team, opponent, venue,
competition, season, stage and date range, across every match dataset.

Layer: test case (layer 1 of Dave Farley's four-layer model). These specs speak
only the language of Brazilian football; how the answers are produced is
hidden behind the DSL in tests/acceptance/dsl.
"""


def test_should_find_every_meeting_between_two_teams(soccer):
    soccer.given.match("Flamengo 2-1 Fluminense", date="2023-09-03")
    soccer.given.match("Fluminense 1-0 Flamengo", date="2023-05-28")
    soccer.given.match("Flamengo 3-0 Vasco da Gama")

    soccer.matches.confirm_meetings("Flamengo", "Fluminense", count=2)


def test_should_list_meetings_most_recent_first_with_their_scores(soccer):
    soccer.given.match("Fluminense 1-0 Flamengo", date="2023-05-28", round=8)
    soccer.given.match("Flamengo 2-1 Fluminense", date="2023-09-03", round=22)

    soccer.matches.confirm_meetings(
        "Flamengo", "Fluminense",
        listed=[
            "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 22)",
            "2023-05-28: Fluminense 1-0 Flamengo (Brasileirão Série A, Round 8)",
        ],
    )


def test_should_find_the_matches_a_team_played_in_a_season(soccer):
    soccer.given.match("Palmeiras 2-0 Santos", season=2023)
    soccer.given.match("Corinthians 1-1 Palmeiras", season=2023)
    soccer.given.match("Palmeiras 3-1 Santos", season=2022)

    soccer.matches.confirm_team_played("Palmeiras", season=2023, count=2)


def test_should_find_only_home_or_only_away_matches(soccer):
    soccer.given.match("Palmeiras 2-0 Santos")
    soccer.given.match("Corinthians 1-1 Palmeiras")
    soccer.given.match("Palmeiras 1-0 Grêmio")

    soccer.matches.confirm_team_played("Palmeiras", venue="away", count=1)


def test_should_find_matches_in_one_competition(soccer):
    soccer.given.match("Palmeiras 2-0 Santos", competition="Brasileirão")
    soccer.given.match("Palmeiras 1-0 Ceará", competition="Copa do Brasil")
    soccer.given.match("Palmeiras 3-0 Bolívar", competition="Libertadores")

    soccer.matches.confirm_team_played("Palmeiras", competition="Copa do Brasil", count=1)


def test_should_find_cup_finals(soccer):
    soccer.given.match("Flamengo 2-0 Atlético-GO", competition="Copa do Brasil", season=2022, stage="semifinals")
    soccer.given.match("Corinthians 0-0 Flamengo", competition="Copa do Brasil", season=2022, stage="final")
    soccer.given.match("Flamengo 1-1 Corinthians", competition="Copa do Brasil", season=2022, stage="final")

    soccer.matches.confirm_found(competition="Copa do Brasil", stage="final", count=2)


def test_should_find_matches_in_a_date_range_whatever_date_format_the_source_uses(soccer):
    soccer.given.match("Guarani 4-2 Vasco", source="historical brasileirão", date="2003-03-29")
    soccer.given.match("Flamengo 1-0 Vasco", source="brasileirão", date="2012-05-19")
    soccer.given.match("Vasco 2-2 Bahia", source="extended statistics", date="2023-09-24")

    soccer.matches.confirm_found(team="Vasco", date_from="2003-01-01", date_to="2012-12-31", count=2)


def test_should_accept_dates_written_the_brazilian_way(soccer):
    soccer.given.match("Guarani 4-2 Vasco", date="2003-03-29")
    soccer.given.match("Vasco 1-0 Bahia", date="2003-04-05")

    soccer.matches.confirm_found(team="Vasco", date_from="01/04/2003", date_to="30/04/2003", count=1)


def test_should_count_a_match_once_when_several_datasets_record_it(soccer):
    soccer.given.match("Palmeiras-SP 6-0 Sao Paulo-SP", source="brasileirão", date="2015-09-13", season=2015)
    soccer.given.match("Palmeiras 6-0 São Paulo", source="historical brasileirão", date="2015-09-13", season=2015)
    soccer.given.match("Palmeiras 6-0 Sao Paulo", source="extended statistics", date="2015-09-13")

    soccer.matches.confirm_meetings("Palmeiras", "São Paulo", count=1)


def test_should_report_match_statistics_where_a_dataset_provides_them(soccer):
    soccer.given.match("Sao Paulo 1-1 Flamengo", source="extended statistics", competition="Copa do Brasil",
                       date="2023-09-24", corners="2-4", shots="8-13")

    soccer.matches.confirm_statistics("São Paulo", "Flamengo", corners="2-4", shots="8-13")


def test_should_report_when_two_teams_last_met(soccer):
    soccer.given.match("Flamengo 2-0 Corinthians", date="2022-04-10")
    soccer.given.match("Corinthians 1-1 Flamengo", date="2023-08-10")
    soccer.given.match("Flamengo 3-0 Bahia", date="2023-11-01")

    soccer.matches.confirm_last_meeting("Flamengo", "Corinthians", "2023-08-10: Corinthians 1-1 Flamengo")


def test_should_ignore_fixtures_that_were_never_played(soccer):
    soccer.given.match("Santos 2-0 Juazeirense", competition="Copa do Brasil", date="2021-07-20")
    soccer.given.unplayed_fixture("Juazeirense vs Santos", competition="Copa do Brasil", date="2021-08-04")

    soccer.matches.confirm_team_played("Santos", count=1)
