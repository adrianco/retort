"""Feature: Sample question coverage.

The spec requires that at least 20 sample questions can be answered.  Each
test maps one natural-language question to the tool call an LLM would make
and asserts a substantive answer comes back.
"""

import server


def answered(text: str) -> bool:
    """An answer is substantive when it is not an empty/no-data response."""
    return bool(text) and not text.startswith(("No matches", "No players",
                                               "No scored", "No teams",
                                               "No match data"))


class TestMatchQuestions:
    def test_q01_flamengo_vs_fluminense_matches(self):
        assert answered(server.search_matches(team="Flamengo",
                                              opponent="Fluminense"))

    def test_q02_palmeiras_matches_in_2023(self):
        assert answered(server.search_matches(team="Palmeiras", season=2023))

    def test_q03_copa_do_brasil_finals(self):
        text = server.search_matches(competition="copa do brasil",
                                     season=2019, limit=200)
        assert answered(text)
        assert "Final" in text                          # stage label shown

    def test_q04_when_did_flamengo_last_play_corinthians(self):
        text = server.search_matches(team="Flamengo", opponent="Corinthians",
                                     limit=1)
        assert answered(text)

    def test_q05_libertadores_matches_2018(self):
        assert answered(server.search_matches(competition="libertadores",
                                              season=2018))

    def test_q06_matches_in_date_range(self):
        assert answered(server.search_matches(team="Santos",
                                              date_from="2015-01-01",
                                              date_to="2015-12-31"))


class TestTeamQuestions:
    def test_q07_corinthians_home_record_2022(self):
        assert answered(server.team_statistics(team="Corinthians",
                                               season=2022, venue="home",
                                               competition="brasileirao"))

    def test_q08_compare_palmeiras_santos_head_to_head(self):
        assert answered(server.head_to_head(team1="Palmeiras",
                                            team2="Santos"))

    def test_q09_gremio_away_performance(self):
        assert answered(server.team_statistics(team="Grêmio", venue="away"))

    def test_q10_what_competitions_has_palmeiras_played(self):
        text = server.team_statistics(team="Palmeiras")
        assert "By competition" in text

    def test_q11_fla_flu_derby_record(self):
        text = server.head_to_head(team1="Flamengo", team2="Fluminense")
        assert "wins" in text and "draws" in text


class TestCompetitionQuestions:
    def test_q12_who_won_2019_brasileirao(self):
        text = server.competition_standings(season=2019)
        assert "1. Flamengo" in text and "Champion" in text

    def test_q13_2018_standings(self):
        text = server.competition_standings(season=2018)
        assert "1. Palmeiras" in text                   # 2018 champion

    def test_q14_serie_b_standings(self):
        assert answered(server.competition_standings(season=2020,
                                                     competition="serie b"))

    def test_q15_bottom_of_table_relegation_zone(self):
        text = server.competition_standings(season=2019)
        assert "20." in text                            # full 20-team table


class TestPlayerQuestions:
    def test_q16_find_all_brazilian_players(self):
        text = server.search_players(nationality="Brazil", limit=10)
        assert "Found 827 players" in text

    def test_q17_who_is_neymar(self):
        text = server.get_player(name="Neymar")
        assert "Neymar Jr" in text and "Overall: 92" in text

    def test_q18_highest_rated_players_at_cruzeiro(self):
        assert answered(server.search_players(club="Cruzeiro", limit=5))

    def test_q19_brazilian_goalkeepers(self):
        text = server.search_players(nationality="Brazil", position="GK",
                                     limit=5)
        assert "Alisson" in text

    def test_q20_brazilian_forwards_min_rating(self):
        assert answered(server.search_players(nationality="Brazil",
                                              position="forward",
                                              min_overall=80))


class TestAnalyticalQuestions:
    def test_q21_average_goals_per_match_brasileirao(self):
        text = server.goal_statistics(competition="brasileirao")
        assert "Average goals per match" in text

    def test_q22_which_team_has_best_away_record(self):
        assert answered(server.best_records(venue="away",
                                            competition="serie a",
                                            min_matches=100))

    def test_q23_biggest_wins_in_dataset(self):
        text = server.biggest_wins(limit=5)
        assert "9-1" in text

    def test_q24_compare_2018_and_2019_seasons(self):
        a = server.goal_statistics(competition="serie a", season=2018)
        b = server.goal_statistics(competition="serie a", season=2019)
        assert answered(a) and answered(b)

    def test_q25_dataset_coverage(self):
        assert answered(server.data_summary())
