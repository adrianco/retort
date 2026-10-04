"""Competition queries: standings, champions, relegation and knockout brackets."""


def test_should_crown_the_champion_from_the_calculated_standings(archive, competitions):
    archive.has_matches("Flamengo 3-0 Santos", "Santos 1-0 Palmeiras", "Palmeiras 1-1 Flamengo",
                        season=2019)

    competitions.request_standings(season=2019)

    competitions.confirm_champion("Flamengo", points=4)


def test_should_order_the_table_by_points(archive, competitions):
    archive.has_matches("Flamengo 3-0 Santos", "Santos 1-0 Palmeiras", "Palmeiras 1-1 Flamengo",
                        season=2019)

    competitions.request_standings(season=2019)

    competitions.confirm_table_order("Flamengo", "Santos", "Palmeiras")


def test_should_separate_teams_level_on_points_by_wins_then_goal_difference(archive, competitions):
    archive.has_matches("Bahia 1-0 Vitória", "Ceará 2-0 Bahia", "Sport 0-0 Bahia",
                        "Sport 2-2 Vitória", "Vitória 0-0 Sport", "Sport 0-0 Ceará",
                        season=2010)

    competitions.request_standings(season=2010)

    competitions.confirm_table_order("Ceará", "Bahia", "Sport", "Vitória")


def test_should_identify_the_relegated_teams(archive, competitions):
    archive.has_league_table(season=2020, bottom_four=["Vasco", "Goiás", "Coritiba", "Botafogo"])

    competitions.request_standings(season=2020)

    competitions.confirm_relegated("Vasco", "Goiás", "Coritiba", "Botafogo")


def test_should_show_a_knockout_bracket_with_aggregate_scores(archive, competitions):
    archive.has_match("Boca Juniors 2-2 River Plate", competition="Copa Libertadores", season=2018, stage="final")
    archive.has_match("River Plate 3-1 Boca Juniors", competition="Copa Libertadores", season=2018, stage="final")

    competitions.request_bracket("Copa Libertadores", season=2018)

    competitions.confirm_tie("final", winner="River Plate", aggregate="5-3")
