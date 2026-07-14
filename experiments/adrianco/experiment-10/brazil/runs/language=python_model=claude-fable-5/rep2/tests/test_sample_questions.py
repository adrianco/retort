"""BDD scenarios: the 20+ sample questions from TASK.md.

Feature: Sample question coverage
  Success criterion: "At least 20 sample questions can be answered".
  Each test maps one natural-language question to the tool call an LLM
  client would make, and asserts a non-empty, well-formed answer.
"""

from team_normalizer import team_matches


class TestSimpleLookups:
    def test_q01_show_all_flamengo_vs_fluminense_matches(self, kb):
        assert kb.find_matches(team="Flamengo", opponent="Fluminense", limit=0)

    def test_q02_what_matches_did_palmeiras_play_in_2023(self, kb):
        assert kb.find_matches(team="Palmeiras", season=2023, limit=0)

    def test_q03_find_all_copa_do_brasil_finals(self, kb):
        assert kb.cup_finals("Copa do Brasil")["finals_by_season"]

    def test_q04_when_did_flamengo_last_play_corinthians(self, kb):
        latest = kb.find_matches(team="Flamengo", opponent="Corinthians", limit=1)
        assert latest and latest[0].date is not None

    def test_q05_what_was_the_score(self, kb):
        latest = kb.find_matches(team="Flamengo", opponent="Corinthians", limit=1)[0]
        assert isinstance(latest.home_goal, int) and isinstance(latest.away_goal, int)

    def test_q06_who_is_a_given_player(self, kb):
        players = kb.search_players(name="Casemiro")
        assert players and players[0].overall is not None


class TestRelationshipQueries:
    def test_q07_which_players_play_for_a_club(self, kb):
        assert kb.search_players(club="Grêmio", limit=0)

    def test_q08_show_me_derbies_in_a_season(self, kb):
        # Traditional rivalry: the Choque-Rei (Palmeiras vs São Paulo) in 2019
        derby = kb.find_matches(team="Palmeiras", opponent="São Paulo",
                                season=2019, limit=0)
        assert derby

    def test_q09_what_competitions_has_palmeiras_played_in(self, kb):
        comps = kb.list_team_competitions("Palmeiras")["competitions"]
        assert len(comps) >= 3

    def test_q10_corinthians_home_record_2022(self, kb):
        stats = kb.team_statistics("Corinthians", season=2022,
                                   competition="Brasileirão", venue="home")
        assert stats["matches"] == 19

    def test_q11_which_team_scored_most_goals_serie_a_2019(self, kb):
        rows = kb.standings(2019)["standings"]
        most = max(rows, key=lambda r: r["goals_for"])
        assert team_matches("Flamengo", most["team"])  # 86 goals in 2019

    def test_q12_compare_palmeiras_and_santos_head_to_head(self, kb):
        assert kb.head_to_head("Palmeiras", "Santos")["total_matches"] > 0


class TestPlayerQuestions:
    def test_q13_find_all_brazilian_players(self, kb):
        assert len(kb.search_players(nationality="Brazil", limit=0)) > 800

    def test_q14_highest_rated_players_at_a_club(self, kb):
        players = kb.search_players(club="Internacional", limit=5)
        assert players
        assert players[0].overall == max(p.overall for p in players)

    def test_q15_forwards_at_a_club(self, kb):
        strikers = kb.search_players(club="Santos", position="ST", limit=0)
        assert all(p.position == "ST" for p in strikers)

    def test_q16_top_brazilian_players(self, kb):
        top = kb.search_players(nationality="Brazil", limit=3)
        assert [p.name for p in top][0] == "Neymar Jr"


class TestAnalyticalQuestions:
    def test_q17_who_won_the_2019_brasileirao(self, kb):
        assert team_matches("Flamengo", kb.standings(2019)["champion"])

    def test_q18_show_the_2018_libertadores_bracket(self, kb):
        assert kb.libertadores_stage_results(2018)["stages"]

    def test_q19_which_teams_were_relegated_in_2020(self, kb):
        assert len(kb.standings(2020)["relegated"]) == 4

    def test_q20_average_goals_per_match_brasileirao(self, kb):
        assert kb.average_goals("Brasileirão")["avg_goals_per_match"] > 0

    def test_q21_which_team_has_best_home_record(self, kb):
        teams = kb.best_record(venue="home", min_matches=100)["teams"]
        assert teams and teams[0]["win_rate"] >= teams[-1]["win_rate"]

    def test_q22_biggest_wins_in_the_dataset(self, kb):
        assert kb.biggest_wins(limit=5)[0]["margin"] >= 7

    def test_q23_compare_2018_and_2019_seasons(self, kb):
        s18 = kb.average_goals(competition="Serie A", season=2018)
        s19 = kb.average_goals(competition="Serie A", season=2019)
        assert s18["matches"] == s19["matches"] == 380
        assert s18["avg_goals_per_match"] != s19["avg_goals_per_match"]
