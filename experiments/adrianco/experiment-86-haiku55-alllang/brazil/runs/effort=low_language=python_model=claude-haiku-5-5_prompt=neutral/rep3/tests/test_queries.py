"""Feature: natural-language-backed queries answered from the real datasets."""

from datetime import date

import pytest

from brazsoccer_mcp.loaders import BRASILEIRAO, COPA_DO_BRASIL
from brazsoccer_mcp.store import QueryError, SoccerData
from conftest import make_match


class TestMatchQueries:
    def test_given_two_teams_when_searched_then_matches_include_both_sides(self, data):
        # Given the full data set
        # When I search for Flamengo against Fluminense
        matches = data.find_matches(team="Flamengo", opponent="Fluminense", limit=None)
        # Then I get many meetings, each involving both teams
        assert len(matches) > 40
        for m in matches:
            assert {m.home_key, m.away_key} == {"flamengo", "fluminense"}

    def test_given_results_then_they_are_newest_first(self, data):
        dates = [m.date for m in data.find_matches(team="Palmeiras", limit=50)]
        assert dates == sorted(dates, reverse=True)

    def test_given_venue_home_then_only_home_games_return(self, data):
        matches = data.find_matches(team="Corinthians", venue="home", season=2022, limit=None)
        assert matches and all(m.home_key == "corinthians" for m in matches)

    def test_given_competition_and_season_then_both_filters_apply(self, data):
        matches = data.find_matches(
            team="Palmeiras", competition="Brasileirão", season=2023, limit=None,
        )
        # The 2023 rows in the provided files give 37 Palmeiras league games
        assert len(matches) == 37
        assert {m.competition for m in matches} == {BRASILEIRAO}

    def test_given_copa_do_brasil_when_searched_then_only_cup_matches_return(self, data):
        matches = data.find_matches(competition="copa do brasil", limit=None)
        assert matches and {m.competition for m in matches} == {COPA_DO_BRASIL}

    def test_given_date_range_then_matches_fall_inside_it(self, data):
        matches = data.find_matches(
            team="Santos", start=date(2019, 1, 1), end=date(2019, 6, 30), limit=None,
        )
        assert matches
        assert all(date(2019, 1, 1) <= m.date <= date(2019, 6, 30) for m in matches)


class TestTeamResolution:
    @pytest.mark.parametrize("text", ["Flamengo", "Flamengo-RJ", "flamengo", "Flamengo RJ"])
    def test_given_name_variants_then_same_team_key_resolves(self, data, text):
        assert data.resolve_team(text) == "flamengo"

    def test_given_unknown_team_then_helpful_error(self, data):
        with pytest.raises(QueryError, match="no team matches"):
            data.resolve_team("Time Inexistente")

    def test_given_ambiguous_fragment_then_candidates_are_listed(self):
        # Given two clubs whose names both contain "vila"
        d = SoccerData([
            make_match("2020-01-01", "Vila Nova", "X", 1, 0),
            make_match("2020-01-02", "Vila Rica", "X", 1, 0),
        ], [])
        # When the fragment is resolved
        # Then the error lists both candidates instead of guessing
        with pytest.raises(QueryError, match="ambiguous.*Vila Nova.*Vila Rica"):
            d.resolve_team("Vila")


class TestHeadToHead:
    def test_given_two_teams_then_wins_draws_and_goals_add_up(self, data):
        # Given Flamengo and Fluminense
        h2h = data.head_to_head("Flamengo", "Fluminense")
        # When the head-to-head is computed
        # Then the outcome counts equal the number of meetings
        assert h2h.a_wins + h2h.b_wins + h2h.draws == len(h2h.matches)
        dates = [m.date for m in h2h.matches]
        assert dates == sorted(dates, reverse=True)

    def test_given_synthetic_meetings_then_scores_are_counted_per_team(self):
        # Given three fixtures between A and B with known results
        matches = [
            make_match("2020-01-01", "A", "B", 2, 0),
            make_match("2020-02-01", "B", "A", 1, 1),
            make_match("2020-03-01", "A", "B", 0, 3),
        ]
        d = SoccerData(matches, [])
        # When head-to-head is computed
        h2h = d.head_to_head("A", "B")
        # Then A won one, B won one, one draw, goals are 3 for A and 4 for B
        assert (h2h.a_wins, h2h.b_wins, h2h.draws) == (1, 1, 1)
        assert (h2h.a_goals, h2h.b_goals) == (3, 4)


class TestTeamStatistics:
    def test_given_known_season_then_record_matches_the_2019_champion(self, data):
        # Given the 2019 Brasileirão, where Flamengo were champions with 90 points
        # When Flamengo's record is requested
        record = data.team_record("Flamengo", competition="Brasileirão", season=2019)
        # Then it is 28W 6D 4L, consistent with the spec's example table
        assert (record.wins, record.draws, record.losses) == (28, 6, 4)
        assert record.played == 38

    def test_given_standings_2019_then_flamengo_top_with_90_points(self, data):
        table = data.standings(2019)
        assert table[0].team == "Flamengo"
        assert table[0].points == 90
        assert len(table) == 20

    def test_given_standings_then_points_are_sorted_descending(self, data):
        points = [row.points for row in data.standings(2023)]
        assert points == sorted(points, reverse=True)

    def test_given_home_record_request_then_win_rate_is_percentage(self):
        d = SoccerData([make_match("2022-01-01", "X", "Y", 1, 0)], [])
        record = d.team_record("X", venue="home")
        assert record.win_rate == 100.0

    def test_given_no_matches_for_team_then_empty_record(self):
        d = SoccerData([make_match("2022-01-01", "X", "Y", 1, 0)], [])
        assert d.team_record("X", season=1999).played == 0


class TestAggregates:
    def test_given_brasileirao_then_average_goals_is_plausible(self, data):
        avg = data.goals_per_match(competition="Brasileirão")
        assert 2.0 < avg < 3.5

    def test_given_home_win_rate_then_it_is_a_percentage(self, data):
        rate = data.home_win_rate(competition="Brasileirão", season=2019)
        assert 0 < rate < 100

    def test_given_biggest_wins_then_margins_are_descending(self, data):
        margins = [m.margin for m in data.biggest_wins(5)]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 5

    def test_given_min_matches_then_teams_below_threshold_are_excluded(self, data):
        rows = data.best_away_records(season=2022, min_matches=15)
        assert rows and all(rec.played >= 15 for _name, rec in rows)

    def test_given_unknown_competition_then_query_error(self, data):
        with pytest.raises(QueryError, match="unknown competition"):
            data.goals_per_match(competition="Campeonato Imaginário")


class TestPlayers:
    def test_given_nationality_filter_then_only_brazilians_return(self, data):
        players = data.find_players(nationality="Brazil", limit=None)
        assert players and all(p.nationality == "Brazil" for p in players)

    def test_given_name_search_then_accents_are_ignored(self, data):
        names = [p.name for p in data.find_players(name="neymar", limit=5)]
        assert any("Neymar" in n for n in names)

    def test_given_position_group_then_forwards_only(self, data):
        players = data.find_players(position="forwards", limit=50)
        assert players and all(p.position in {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"}
                               for p in players)

    def test_given_min_overall_then_ratings_meet_threshold_and_sort_descending(self, data):
        players = data.find_players(min_overall=88, limit=None)
        assert players and all(p.overall >= 88 for p in players)
        ratings = [p.overall for p in players]
        assert ratings == sorted(ratings, reverse=True)

    def test_given_brazilian_clubs_then_counts_and_averages_are_reported(self, data):
        rows = data.brazilian_players_by_club(limit=5)
        assert rows
        for club, count, avg in rows:
            assert count >= 1 and 0 < avg <= 100, club
