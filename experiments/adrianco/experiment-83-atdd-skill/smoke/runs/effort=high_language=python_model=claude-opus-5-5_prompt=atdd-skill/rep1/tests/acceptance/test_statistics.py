"""
Executable specification: aggregated statistics — goal averages, result
rates, rankings, biggest wins and season comparisons.

Layer 1 of the four-layer acceptance test model.
"""


class StatisticsSpec:
    def should_calculate_average_goals_per_match(self, given, statistics):
        given.brasileirao_match(home="Santos", away="Bahia", score="2-1")
        given.brasileirao_match(home="Bahia", away="Gremio", score="0-0")
        given.brasileirao_match(home="Gremio", away="Santos", score="3-3")

        statistics.competition_summary(competition="Brasileirão")

        statistics.confirm_summary(matches=3, average_goals=3.0, home_win_rate="33.3%")

    def should_rank_the_biggest_wins_first(self, given, statistics):
        given.brasileirao_match(home="Palmeiras", away="Sao Paulo", score="6-0", date="2015-09-13")
        given.libertadores_match(home="Santos", away="Bolivar", score="8-0", date="2012-05-27")
        given.brasileirao_match(home="Flamengo", away="Gremio", score="5-0", date="2019-10-27")
        given.brasileirao_match(home="Bahia", away="Vitoria", score="2-1", date="2019-10-28")

        statistics.biggest_wins()

        statistics.confirm_ranking("Santos", "Palmeiras", "Flamengo")

    def should_find_the_team_with_the_best_home_record(self, given, statistics):
        given.brasileirao_match(home="Santos", away="Bahia", score="2-0")
        given.brasileirao_match(home="Santos", away="Gremio", score="1-1")
        given.brasileirao_match(home="Bahia", away="Gremio", score="1-0")
        given.brasileirao_match(home="Bahia", away="Santos", score="1-0")

        statistics.rank_teams(by="win rate", venue="home")

        statistics.confirm_ranking("Bahia", "Santos")

    def should_find_the_team_with_the_best_away_record(self, given, statistics):
        given.brasileirao_match(home="Santos", away="Bahia", score="0-2")
        given.brasileirao_match(home="Gremio", away="Santos", score="0-1")
        given.brasileirao_match(home="Bahia", away="Santos", score="1-0")

        statistics.rank_teams(by="win rate", venue="away")

        statistics.confirm_ranking("Bahia", "Santos")

    def should_find_the_team_that_scored_most_goals_in_a_season(self, given, statistics):
        given.brasileirao_match(home="Palmeiras", away="Santos", score="3-2", season=2023)
        given.brasileirao_match(home="Botafogo", away="Palmeiras", score="4-0", season=2023)
        given.brasileirao_match(home="Santos", away="Botafogo", score="5-0", season=2022)

        statistics.rank_teams(by="goals scored", competition="Brasileirão", season=2023)

        statistics.confirm_ranking("Botafogo", "Palmeiras", "Santos")

    def should_compare_two_seasons(self, given, statistics):
        given.brasileirao_match(home="Santos", away="Bahia", score="1-0", season=2018)
        given.brasileirao_match(home="Santos", away="Bahia", score="3-2", season=2019)
        given.brasileirao_match(home="Bahia", away="Santos", score="2-2", season=2019)

        statistics.compare_seasons(2018, 2019)

        statistics.confirm_season_average_goals(season=2018, average_goals=1.0)
        statistics.confirm_season_average_goals(season=2019, average_goals=4.5)
