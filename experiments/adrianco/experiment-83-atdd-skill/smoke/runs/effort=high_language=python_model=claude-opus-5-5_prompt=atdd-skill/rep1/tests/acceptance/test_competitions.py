"""
Executable specification: competitions — standings, champions, relegation,
cup finals, knockout brackets and derbies.

Layer 1 of the four-layer acceptance test model. Standings are calculated
from match results; nothing here says how.
"""


class CompetitionSpec:
    def should_crown_the_team_with_most_points_champion(self, given, competitions):
        given.season_finishing_in_order(season=2019, teams=["Flamengo", "Santos", "Palmeiras", "Gremio"])

        competitions.standings(season=2019)

        competitions.confirm_champion("Flamengo", points=18)

    def should_separate_teams_level_on_points_by_goal_difference(self, given, competitions):
        given.brasileirao_match(home="Santos", away="Bahia", score="5-0", season=2018)
        given.brasileirao_match(home="Palmeiras", away="Bahia", score="1-0", season=2018)

        competitions.standings(season=2018)

        competitions.confirm_table_order("Santos", "Palmeiras", "Bahia")

    def should_identify_the_relegated_teams_as_the_bottom_four(self, given, competitions):
        given.season_finishing_in_order(
            season=2020, teams=["Flamengo", "Internacional", "Atletico-MG", "Vasco", "Goias", "Coritiba", "Botafogo"]
        )

        competitions.standings(season=2020)

        competitions.confirm_relegated("Vasco", "Goias", "Coritiba", "Botafogo")

    def should_find_the_copa_do_brasil_final_and_its_winner(self, given, competitions):
        given.copa_do_brasil_match(home="Gremio", away="Sao Paulo", score="1-0", season=2020, round=7)
        given.copa_do_brasil_match(home="Gremio", away="Palmeiras", score="0-1", season=2020, round=8)
        given.copa_do_brasil_match(home="Palmeiras", away="Gremio", score="2-0", season=2020, round=8)

        competitions.finals(competition="Copa do Brasil", season=2020)

        competitions.confirm_final(season=2020, finalists=("Gremio", "Palmeiras"), winner="Palmeiras")

    def should_leave_a_final_level_on_aggregate_undecided_rather_than_use_away_goals(self, given, competitions):
        given.copa_do_brasil_match(home="Santos", away="Palmeiras", score="1-0", season=2015, round=8)
        given.copa_do_brasil_match(home="Palmeiras", away="Santos", score="2-1", season=2015, round=8)

        competitions.finals(competition="Copa do Brasil", season=2015)

        competitions.confirm_final_undecided(season=2015)

    def should_show_the_libertadores_knockout_bracket(self, given, competitions):
        given.libertadores_match(home="Palmeiras", away="Bolivar", season=2018, stage="group stage")
        given.libertadores_match(home="River Plate", away="Gremio", score="0-1", season=2018, stage="semifinals")
        given.libertadores_match(home="Gremio", away="River Plate", score="1-2", season=2018, stage="semifinals")
        given.libertadores_match(home="Boca Juniors", away="River Plate", score="2-2", season=2018, stage="final")
        given.libertadores_match(home="River Plate", away="Boca Juniors", score="3-1", season=2018, stage="final")

        competitions.knockout_bracket(season=2018)

        competitions.confirm_tie(stage="semifinals", teams=("River Plate", "Gremio"), winner="River Plate")
        competitions.confirm_tie(stage="final", teams=("Boca Juniors", "River Plate"), winner="River Plate")

    def should_find_the_derbies_played_in_a_season(self, given, competitions):
        given.brasileirao_match(home="Flamengo", away="Fluminense", season=2023)
        given.brasileirao_match(home="Gremio", away="Internacional", season=2023)
        given.brasileirao_match(home="Flamengo", away="Bahia", season=2023)
        given.brasileirao_match(home="Flamengo", away="Fluminense", season=2022)

        competitions.derbies(season=2023)

        competitions.confirm_derbies("Fla-Flu", "Grenal")
