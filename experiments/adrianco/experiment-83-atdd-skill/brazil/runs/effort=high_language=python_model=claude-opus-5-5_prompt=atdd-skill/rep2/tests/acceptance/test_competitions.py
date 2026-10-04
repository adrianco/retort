"""
Executable specifications: competitions, standings and knockout brackets.

Capability: league tables calculated from match results, champions,
relegation, the season's top-scoring teams, and cup knockout brackets.

Layer: test case (layer 1 of the four-layer model).
"""


def test_should_crown_the_team_with_most_points_as_champion(soccer):
    soccer.given.season_finished(2019, in_order=["Flamengo", "Santos", "Palmeiras", "Grêmio"])

    soccer.competitions.confirm_champion(2019, "Flamengo")


def test_should_calculate_points_and_record_for_each_team_in_the_table(soccer):
    soccer.given.match("Flamengo 2-0 Santos", season=2019)
    soccer.given.match("Santos 1-1 Palmeiras", season=2019)
    soccer.given.match("Palmeiras 0-3 Flamengo", season=2019)

    soccer.competitions.confirm_standing(2019, position=1, team="Flamengo", points=6, won=2, drawn=0, lost=0)
    soccer.competitions.confirm_standing(2019, position=2, team="Santos", points=1, won=0, drawn=1, lost=1)


def test_should_rank_level_teams_on_wins_then_goal_difference(soccer):
    soccer.given.match("Grêmio 2-0 Bahia", season=2018)
    soccer.given.match("Internacional 4-3 Bahia", season=2018)
    soccer.given.match("Grêmio 0-0 Internacional", season=2018)

    soccer.competitions.confirm_standing(2018, position=1, team="Grêmio")
    soccer.competitions.confirm_standing(2018, position=2, team="Internacional")


def test_should_relegate_the_bottom_four_teams(soccer):
    soccer.given.season_finished(2020, in_order=["Flamengo", "Internacional", "Atlético-MG", "São Paulo",
                                                 "Vasco", "Goiás", "Coritiba", "Botafogo"])

    soccer.competitions.confirm_relegated(2020, ["Vasco", "Goiás", "Coritiba", "Botafogo"])


def test_should_find_the_seasons_top_scoring_team(soccer):
    soccer.given.match("Palmeiras 4-0 Santos", season=2023)
    soccer.given.match("Botafogo 2-2 Palmeiras", season=2023)
    soccer.given.match("Botafogo 3-1 Santos", season=2023)

    soccer.competitions.confirm_top_scoring_team(2023, "Palmeiras", goals=6)


def test_should_show_a_cup_knockout_bracket_stage_by_stage(soccer):
    soccer.given.match("River Plate 2-0 Grêmio", competition="Libertadores", season=2018, stage="semifinals")
    soccer.given.match("Boca Juniors 2-2 Palmeiras", competition="Libertadores", season=2018, stage="semifinals")
    soccer.given.match("Boca Juniors 2-2 River Plate", competition="Libertadores", season=2018, stage="final")
    soccer.given.match("Palmeiras 2-0 Junior de Barranquilla", competition="Libertadores", season=2018,
                       stage="group stage")

    soccer.competitions.confirm_bracket(
        "Libertadores", 2018,
        stages={"semifinals": ["River Plate vs Grêmio", "Boca Juniors vs Palmeiras"],
                "final": ["Boca Juniors vs River Plate"]},
    )


def test_should_count_a_league_pairing_once_per_season_when_a_dataset_mislabels_a_cup_tie(soccer):
    soccer.given.match("Atlético-MG 2-0 Santos", source="brasileirão", season=2014, date="2014-06-01")
    soccer.given.match("Atlético-MG 2-0 Santos", source="extended statistics", date="2014-06-01")
    soccer.given.match("Atlético-MG 3-2 Santos", source="extended statistics", date="2014-09-24")

    soccer.competitions.confirm_standing(2014, position=1, team="Atlético-MG", played=1, won=1)


def test_should_leave_teams_with_only_stray_results_out_of_the_table(soccer):
    soccer.given.season_finished(2015, in_order=["Corinthians", "Atlético-MG", "Grêmio", "São Paulo",
                                                 "Avaí", "Vasco", "Goiás", "Joinville"])
    soccer.given.match("Brasília 1-1 CA Taguatinga", source="extended statistics", date="2016-01-30")

    soccer.competitions.confirm_relegated(2015, ["Avaí", "Vasco", "Goiás", "Joinville"])
