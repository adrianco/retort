"""BDD specs for brazilian_soccer_mcp.queries.QueryEngine: match search,
team records, head-to-head, standings/champions, player search and
statistical analysis - the "20+ sample questions" required by TASK.md.
"""

import pytest

from brazilian_soccer_mcp.graph import TeamNotFoundError


class TestSearchMatches:
    def test_given_a_team_name_when_searching_matches_then_every_result_features_that_team(self, engine):
        # Given a request for all Palmeiras matches
        matches = engine.search_matches(team="Palmeiras")
        # When the results are inspected
        # Then Palmeiras appears as the home or away side in every match
        assert len(matches) > 0
        assert ((matches["home_team_key"] == "palmeiras") | (matches["away_team_key"] == "palmeiras")).all()

    def test_given_two_teams_when_searching_matches_between_them_then_only_their_meetings_are_returned(self, engine):
        # Given "Show me all Flamengo vs Fluminense matches"
        matches = engine.search_matches(team="Flamengo", opponent="Fluminense")
        # When the results are inspected
        # Then every match is specifically between those two teams
        assert len(matches) > 0
        home_away_pairs = set(zip(matches["home_team_key"], matches["away_team_key"]))
        assert home_away_pairs <= {("flamengo", "fluminense"), ("fluminense", "flamengo")}

    def test_given_a_team_and_season_when_searching_matches_then_only_that_seasons_matches_are_returned(self, engine):
        # Given "What matches did Palmeiras play in 2023?"
        matches = engine.search_matches(team="Palmeiras", season=2023)
        # When the results are inspected
        # Then every match is from the 2023 season
        assert len(matches) > 0
        assert (matches["season"] == 2023).all()

    def test_given_a_competition_filter_when_searching_matches_then_only_that_competition_is_returned(self, engine):
        # Given "Find all Copa do Brasil finals" (approximated here as: all
        # Copa do Brasil matches)
        matches = engine.search_matches(competition="Copa do Brasil")
        # When the results are inspected
        # Then every match belongs to the Copa do Brasil
        assert len(matches) > 0
        assert (matches["competition"] == "Copa do Brasil").all()

    def test_given_a_date_range_when_searching_matches_then_only_matches_inside_the_range_are_returned(self, engine):
        # Given a request scoped to a specific date range (October 2019, when
        # the Brasileirao, Copa Libertadores knockouts etc. are all in season)
        matches = engine.search_matches(date_from="2019-10-01", date_to="2019-10-31")
        # When the results are inspected
        # Then every match falls within October 2019
        assert len(matches) > 0
        assert (matches["datetime"] >= "2019-10-01").all()
        assert (matches["datetime"] <= "2019-10-31 23:59:59").all()

    def test_given_a_limit_when_searching_matches_then_no_more_than_the_limit_is_returned(self, engine):
        # Given a request for at most 5 matches
        matches = engine.search_matches(team="Santos", limit=5)
        # When the results are inspected
        # Then no more than 5 rows come back
        assert len(matches) == 5

    def test_given_matches_appearing_in_multiple_source_files_when_searched_then_duplicates_are_collapsed(
        self, engine
    ):
        # Given the same real-world match can appear in more than one source
        # CSV (e.g. both Brasileirao_Matches.csv and BR-Football-Dataset.csv)
        matches = engine.search_matches(team="Flamengo", opponent="Fluminense")
        # When the results are inspected
        dedup_columns = ["date", "home_team_key", "away_team_key", "home_goal", "away_goal"]
        # Then no two rows describe the exact same match
        assert not matches.duplicated(subset=dedup_columns).any()


class TestHeadToHead:
    def test_given_a_classic_rivalry_when_head_to_head_is_requested_then_the_win_counts_sum_to_the_total(
        self, engine
    ):
        # Given "Compare Palmeiras and Santos head-to-head"
        result = engine.head_to_head("Palmeiras", "Santos")
        # When the win/draw counts are inspected
        # Then they account for every match in the returned history
        assert result["wins_a"] + result["wins_b"] + result["draws"] == result["total"]
        assert result["total"] > 0

    def test_given_an_unknown_team_when_head_to_head_is_requested_then_team_not_found_error_is_raised(self, engine):
        # Given a nonsense team name
        # When requesting a head-to-head against a real team
        # Then a clear error is raised
        with pytest.raises(TeamNotFoundError):
            engine.head_to_head("Not A Real Club", "Palmeiras")


class TestTeamRecord:
    def test_given_a_team_and_season_when_record_is_requested_then_played_equals_wins_plus_draws_plus_losses(
        self, engine
    ):
        # Given "What is Corinthians' home record in 2022?"
        record = engine.team_record("Corinthians", season=2022, competition="Brasileirao", venue="home")
        # When the record is inspected
        # Then matches played is exactly the sum of the outcome counts
        assert record["played"] == record["wins"] + record["draws"] + record["losses"]
        assert record["played"] > 0

    def test_given_a_teams_home_only_record_when_requested_then_every_included_match_was_played_at_home(
        self, engine, graph
    ):
        # Given a home-only record request
        record = engine.team_record("Corinthians", season=2022, competition="Brasileirao", venue="home")
        node = graph.resolve_team("Corinthians")
        home_matches = graph.matches.iloc[node.match_indices]
        home_matches = home_matches[
            (home_matches["season"] == 2022)
            & (home_matches["competition"] == "Brasileirao Serie A")
            & (home_matches["home_team_key"] == node.key)
        ].dropna(subset=["home_goal", "away_goal"])
        # When the reported win/draw/loss totals are compared against a
        # direct count of home matches for that season
        # Then they match exactly
        assert record["played"] == len(home_matches)

    def test_given_an_unknown_team_when_record_is_requested_then_team_not_found_error_is_raised(self, engine):
        # Given a nonsense team name
        # When requesting its record
        # Then a clear error is raised
        with pytest.raises(TeamNotFoundError):
            engine.team_record("Not A Real Club")


class TestCompareTeams:
    def test_given_two_teams_when_compared_then_result_includes_both_records_and_head_to_head(self, engine):
        # Given "Compare Palmeiras and Santos head-to-head"
        result = engine.compare_teams("Palmeiras", "Santos")
        # When the comparison result is inspected
        # Then it bundles both teams' overall records and their h2h history
        assert result["team_a"]["team"] == "Palmeiras"
        assert result["team_b"]["team"] == "Santos"
        assert "wins_a" in result["head_to_head"]


class TestTopScoringTeams:
    def test_given_a_season_when_top_scoring_teams_are_requested_then_results_are_sorted_descending(self, engine):
        # Given "Which team scored the most goals in Serie A 2023?"
        table = engine.top_scoring_teams(competition="Brasileirao", season=2023, n=5)
        # When the ranking is inspected
        # Then goals are in strictly non-increasing order
        goals = table["goals"].tolist()
        assert goals == sorted(goals, reverse=True)
        assert len(table) == 5


class TestSearchPlayers:
    def test_given_a_player_name_when_searched_then_matching_players_are_returned(self, engine):
        # Given "Who is Neymar Jr?"
        players = engine.search_players(name="Neymar")
        # When the search results are inspected
        # Then at least one matching player is found
        assert len(players) > 0
        assert players["name"].str.contains("Neymar").any()

    def test_given_nationality_brazil_when_searched_then_every_result_is_brazilian(self, engine):
        # Given "Find all Brazilian players in the dataset"
        players = engine.search_players(nationality="Brazil", limit=None)
        # When the results are inspected
        # Then every player's nationality is Brazil
        assert len(players) > 0
        assert (players["nationality"] == "Brazil").all()

    def test_given_a_club_filter_when_searched_then_every_result_plays_for_that_club(self, engine):
        # Given "Which players play for Santos?"
        players = engine.search_players(club="Santos")
        # When the results are inspected
        # Then every player's club_key matches Santos
        assert len(players) > 0
        assert (players["club_key"] == "santos").all()

    def test_given_a_position_group_when_searched_then_every_result_is_in_that_group(self, engine):
        # Given "Show me all forwards from ..." (position expressed as a group, not a raw FIFA code)
        players = engine.search_players(position="forward", limit=None)
        # When the results are inspected
        # Then every player's position code is a forward position
        assert len(players) > 0
        assert set(players["position"].unique()) <= {"LW", "RW", "LF", "CF", "RF", "LS", "ST", "RS"}

    def test_given_a_minimum_overall_rating_when_searched_then_every_result_meets_the_threshold(self, engine):
        # Given "Who are the highest-rated players at Flamengo?" style filtering by rating
        players = engine.search_players(min_overall=90)
        # When the results are inspected
        # Then every player's overall rating is at least 90
        assert len(players) > 0
        assert (players["overall"] >= 90).all()

    def test_given_a_result_limit_when_searched_then_results_are_sorted_by_overall_descending(self, engine):
        # Given a request for the top 3 rated players overall
        players = engine.search_players(limit=3)
        # When the results are inspected
        # Then they are the 3 highest overall ratings, in descending order
        assert len(players) == 3
        assert players["overall"].tolist() == sorted(players["overall"].tolist(), reverse=True)


class TestTopRatedAtClub:
    def test_given_a_club_when_top_rated_players_are_requested_then_results_are_sorted_descending(self, engine):
        # Given "Who are the highest-rated players at Flamengo?" (using a club
        # that does have a FIFA roster in this dataset)
        players = engine.top_rated_at_club("Santos", n=5)
        # When the results are inspected
        # Then they are sorted from highest to lowest overall rating
        ratings = players["overall"].tolist()
        assert ratings == sorted(ratings, reverse=True)
        assert len(players) <= 5


class TestBrazilianPlayersByClub:
    def test_given_the_full_dataset_when_grouped_by_club_then_every_row_is_a_real_match_dataset_club(self, engine, graph):
        # Given "Brazilian players at Brazilian clubs" style aggregation
        table = engine.brazilian_players_by_club()
        # When the results are inspected
        # Then every listed club is one that actually appears in the match data
        assert len(table) > 0
        assert set(table["club"]) <= {graph.team_display(k) for k in graph.all_team_keys()}


class TestStandings:
    def test_given_a_known_season_when_standings_are_requested_then_flamengo_is_the_2019_champion(self, engine):
        # Given "Who won the 2019 Brasileirao?" - a season whose real-world
        # result (Flamengo, 90 points) is well documented
        table = engine.standings("Brasileirao", 2019)
        # When the top of the table is inspected
        # Then Flamengo is in first place with 90 points
        champion_row = table.iloc[0]
        assert champion_row["team"] == "Flamengo"
        assert champion_row["points"] == 90

    def test_given_a_standings_table_when_inspected_then_every_team_played_the_same_number_of_matches(self, engine):
        # Given a completed Brasileirao season
        table = engine.standings("Brasileirao", 2019)
        # When each team's match count is inspected
        # Then every team played the same number of matches (a round-robin league)
        assert table["played"].nunique() == 1

    def test_given_an_unplayed_season_when_standings_are_requested_then_a_clear_error_is_raised(self, engine):
        # Given a season with no data at all for a competition
        # When standings are requested
        # Then a clear error is raised instead of an empty/misleading table
        with pytest.raises(ValueError):
            engine.standings("Copa Libertadores", 1950)


class TestChampion:
    def test_given_a_league_season_when_champion_is_requested_then_it_matches_the_standings_leader(self, engine):
        # Given the 2019 Brasileirao season
        champion = engine.champion("Brasileirao", 2019)
        # When the champion result is inspected
        # Then it names Flamengo, consistent with the standings table
        assert champion["champion"] == "Flamengo"

    def test_given_a_cup_competition_when_champion_is_requested_then_the_final_aggregate_winner_is_returned(
        self, engine
    ):
        # Given "Who won the 2019 Copa do Brasil?" - a knockout cup, not a league table
        champion = engine.champion("Copa do Brasil", 2019)
        # When the champion result is inspected
        # Then a definite winner is returned, backed by the final's aggregate score
        assert champion["champion"] is not None
        assert len(champion["aggregate"]) >= 1


class TestRelegatedTeams:
    def test_given_a_season_when_relegated_teams_are_requested_then_they_are_the_bottom_of_the_table(self, engine):
        # Given "Which teams were relegated in 2020?" (approximated as bottom 4)
        full_table = engine.standings("Brasileirao", 2020)
        relegated = engine.relegated_teams("Brasileirao", 2020, n=4)
        # When the relegated teams are inspected
        # Then they are exactly the bottom 4 positions of the full standings
        assert list(relegated["team"]) == list(full_table.tail(4)["team"])


class TestStatisticalAnalysis:
    def test_given_the_brasileirao_dataset_when_average_goals_is_computed_then_it_is_a_plausible_football_value(
        self, engine
    ):
        # Given "What's the average goals per match in the Brasileirao?"
        average = engine.average_goals_per_match(competition="Brasileirao")
        # When the value is inspected
        # Then it falls within a plausible real-world range for football
        assert 1.5 < average < 4.0

    def test_given_the_brasileirao_dataset_when_home_win_rate_is_computed_then_it_is_a_plausible_percentage(
        self, engine
    ):
        # Given "home advantage" is a well-known real phenomenon in football
        home_rate = engine.home_win_rate(competition="Brasileirao")
        # When the home win rate is computed
        # Then it's a plausible percentage, and higher than a fair coin flip
        assert 33.0 < home_rate < 70.0

    def test_given_a_minimum_matches_threshold_when_best_away_record_is_requested_then_every_team_meets_it(
        self, engine
    ):
        # Given "Which team has the best away record?"
        table = engine.best_away_record(competition="Brasileirao", min_matches=10, n=5)
        # When the results are inspected
        # Then every listed team played at least the minimum number of away matches
        assert len(table) > 0
        assert (table["played"] >= 10).all()

    def test_given_the_full_dataset_when_biggest_wins_are_requested_then_they_are_sorted_by_margin_descending(
        self, engine
    ):
        # Given "Show me the biggest wins in the dataset"
        table = engine.biggest_wins(n=10)
        # When the results are inspected
        # Then goal margins are in non-increasing order
        margins = table["margin"].tolist()
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 5
