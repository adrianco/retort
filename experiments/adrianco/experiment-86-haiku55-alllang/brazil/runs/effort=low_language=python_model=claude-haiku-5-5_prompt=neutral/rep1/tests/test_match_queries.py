# Context: Behaviour scenarios for match, team, head-to-head, standings and statistics queries,
# run against the small hand-checked dataset in conftest.py. Expected numbers are worked out by
# hand from those fixture rows, so a failure means the query logic changed.

from datetime import date

import pytest

from brazilian_soccer_mcp.data import load_matches


# ---- match search -------------------------------------------------------

def test_given_match_data_when_searching_a_fixture_then_only_that_pairing_is_returned(sample_kb):
    # Given the match data is loaded
    # When I search for matches between "Flamengo" and "Fluminense"
    matches = sample_kb.find_matches(team="Flamengo", opponent="Fluminense")
    # Then I receive that single fixture, with date, scores and competition
    assert len(matches) == 1
    assert matches[0].played_on == date(2023, 5, 1)
    assert (matches[0].home_goals, matches[0].away_goals) == (2, 1)
    assert matches[0].competition == "Brasileirão Série A"


def test_given_match_data_when_searching_by_season_then_every_match_of_that_team_is_returned(sample_kb):
    # Given the match data is loaded
    # When I ask for Palmeiras matches in 2023
    matches = sample_kb.find_matches(team="Palmeiras", season=2023)
    # Then all four 2023 Palmeiras matches are returned, newest first
    assert len(matches) == 4
    assert matches[0].played_on > matches[-1].played_on


def test_given_a_venue_filter_when_searching_then_only_home_matches_are_returned(sample_kb):
    # Given the match data is loaded
    # When I ask for Palmeiras home matches in 2023
    matches = sample_kb.find_matches(team="Palmeiras", season=2023, venue="home")
    # Then only the matches Palmeiras hosted are returned
    assert {m.home.key for m in matches} == {"palmeiras"}
    assert len(matches) == 2


def test_given_a_date_range_when_searching_then_only_matches_inside_it_are_returned(sample_kb):
    # Given the match data is loaded
    # When I search a ten-day window in May 2023
    matches = sample_kb.find_matches(start=date(2023, 5, 10), end=date(2023, 5, 20))
    # Then only the match inside the window is returned
    assert [m.played_on for m in matches] == [date(2023, 5, 15)]


def test_given_a_competition_when_searching_then_only_that_competition_is_returned(sample_kb):
    # Given the match data is loaded, including a Copa do Brasil match
    # When I search for Copa do Brasil matches
    matches = sample_kb.find_matches(competition="copa do brasil")
    # Then I receive only the cup fixture
    assert len(matches) == 1
    assert matches[0].home.name == "Flamengo"


def test_given_a_team_with_state_when_searching_then_only_that_club_is_returned(sample_kb):
    # Given Atlético-MG and Atlético-PR both appear in the data
    # When I search for "Atletico-MG"
    matches = sample_kb.find_matches(team="Atletico-MG")
    # Then only the Minas Gerais club's match is returned
    assert len(matches) == 1
    assert matches[0].home.state == "MG"


# ---- team records -------------------------------------------------------

def test_given_home_matches_when_asking_corinthians_home_record_2022_then_wins_draws_losses_and_goals_are_correct(sample_kb):
    # Given the 2022 Corinthians results in the data
    # When I request their home record for 2022
    record = sample_kb.team_record("Corinthians", season=2022, venue="home")
    # Then 2 wins and 1 loss from 3 home games, with 4 scored and 3 conceded
    assert (record.played, record.wins, record.draws, record.losses) == (3, 2, 0, 1)
    assert (record.goals_for, record.goals_against) == (4, 3)
    assert record.win_rate == pytest.approx(2 / 3)


def test_given_a_season_when_requesting_palmeiras_record_then_statistics_are_correct(sample_kb):
    # Given Palmeiras' 2023 matches
    # When I request their 2023 record
    record = sample_kb.team_record("Palmeiras", season=2023)
    # Then 2 wins, 2 draws, no losses, 6 scored and 2 conceded
    assert (record.played, record.wins, record.draws, record.losses) == (4, 2, 2, 0)
    assert (record.goals_for, record.goals_against) == (6, 2)


def test_given_states_when_comparing_teams_head_to_head_then_both_sides_are_counted(sample_kb):
    # Given Corinthians and Palmeiras met three times in the data
    # When I compare the two clubs head-to-head
    h2h = sample_kb.head_to_head("Corinthians", "Palmeiras")
    # Then the win and draw counts are split correctly
    assert len(h2h.matches) == 3
    assert (h2h.a_wins, h2h.b_wins, h2h.draws) == (1, 1, 1)


# ---- standings ----------------------------------------------------------

def test_given_a_season_when_building_standings_then_points_and_order_are_calculated_from_results(sample_kb):
    # Given the 2023 Brasileirão results (duplicated in the BR-Football file with a different date)
    # When I calculate the 2023 table
    rows = sample_kb.standings(2023)
    # Then teams are ordered by points and the duplicate fixture is not counted twice
    assert [(r.team, r.points) for r in rows] == [
        ("Palmeiras (SP)", 8),
        ("Flamengo (RJ)", 4),
        ("Corinthians (SP)", 1),
        ("Fluminense (RJ)", 0),
    ]


def test_given_a_calculated_table_when_formatting_then_leader_is_champion_and_last_place_is_relegated(sample_kb):
    # Given a calculated 2023 table
    from brazilian_soccer_mcp.formatting import format_standings

    # When I format it with one relegation place
    lines = format_standings("2023 standings:", sample_kb.standings(2023), relegation_places=1).splitlines()
    # Then the leader line carries the champion marker and the last place is marked relegated
    assert lines[1] == "1. Palmeiras (SP) - 8 pts (2W, 2D, 0L, GD +4) - Champion"
    assert lines[-1].endswith("- Relegated")


# ---- statistics ---------------------------------------------------------

def test_given_a_season_when_computing_statistics_then_goals_per_match_and_venue_rates_are_correct(sample_kb):
    # Given the 2023 Brasileirão matches
    # When I compute statistics for the season
    stats = sample_kb.season_stats(season=2023, competition="Brasileirão Série A")
    # Then averages and rates are computed over the five matches
    assert stats.matches == 5
    assert stats.goals_per_match == pytest.approx(2.2)
    assert stats.home_win_rate == pytest.approx(0.4)
    assert stats.draw_rate == pytest.approx(0.4)
    assert stats.away_win_rate == pytest.approx(0.2)


def test_given_home_records_when_ranking_by_home_win_rate_then_the_best_home_side_comes_first(sample_kb):
    # Given the 2022 league results
    # When I rank teams by home win rate
    ranking = sample_kb.venue_ranking("home", season=2022, min_matches=1)
    # Then Corinthians (2 wins from 3 home games) leads
    assert ranking[0].team == "Corinthians (SP)"
    assert ranking[0].win_rate == pytest.approx(2 / 3)


def test_given_a_season_when_listing_biggest_wins_then_largest_margin_comes_first(sample_kb):
    # Given the 2022 league results, including Flamengo's 4-0 win away at Atlético-MG
    # When I list the biggest wins of 2022
    wins = sample_kb.biggest_wins(season=2022, limit=1)
    # Then the 4-goal margin match is first
    assert wins[0].goal_margin == 4
    assert wins[0].played_on == date(2022, 6, 22)


# ---- data loading rules -------------------------------------------------

def test_given_a_season_in_several_files_when_loading_then_only_the_preferred_source_is_used(sample_kb):
    # Given the 2023 Serie A fixture appears in the league file and the BR-Football file
    # When I count 2023 Serie A matches
    count = len(sample_kb.find_matches(competition="Serie A", season=2023))
    # Then the league file is used and the BR-Football copy is ignored
    assert count == 5


def test_given_a_season_only_in_one_file_when_loading_then_it_is_kept(sample_kb):
    # Given a 2021 Serie A fixture exists only in the BR-Football file
    # When I search 2021
    matches = sample_kb.find_matches(season=2021)
    # Then it is loaded
    assert len(matches) == 1
    assert matches[0].home.name == "Santos"


def test_given_rows_with_missing_scores_or_dates_when_loading_then_those_rows_are_skipped(sample_kb):
    # Given the Libertadores and historical files contain 'NA' dates and scores
    # When I load all matches
    # Then the usable Libertadores fixture is kept and the unusable rows are not
    libertadores = sample_kb.find_matches(competition="libertadores")
    assert [(m.home.name, m.home_goals, m.away_goals) for m in libertadores] == [("Nacional", 2, 2)]
    assert [m.played_on for m in sample_kb.find_matches(team="Santos", season=2010)] == [date(2010, 3, 15)]


def test_given_historical_dates_in_brazilian_format_when_loading_then_they_are_parsed(sample_kb):
    # Given a 2010 fixture recorded as DD/MM/YYYY
    # When I find it
    matches = sample_kb.find_matches(team="Palmeiras", season=2010)
    # Then its date is parsed correctly
    assert [m.played_on for m in matches] == [date(2010, 3, 15)]


def test_given_the_loader_when_called_directly_then_it_returns_matches(sample_dir):
    # Given the sample dataset directory
    # When the match loader runs
    matches = load_matches(sample_dir)
    # Then it returns a non-empty, date-ordered list
    assert matches
    assert [m.played_on for m in matches] == sorted(m.played_on for m in matches)
