"""BDD scenarios for the query layer, checked against the real Kaggle data."""

from datetime import date

import pytest

from soccer_mcp.queries import QueryError


def test_scenario_find_flamengo_vs_fluminense_matches(queries):
    # Given the match data is loaded
    # When I search for matches between "Flamengo" and "Fluminense"
    matches = queries.find_matches(team="Flamengo", opponent="Fluminense")
    # Then I receive a list of matches, newest first
    assert matches
    assert matches == sorted(matches, key=lambda m: m.date, reverse=True)
    # And each match has a date, a score and a competition
    for m in matches:
        assert m.date and isinstance(m.home_goals, int) and m.competition


def test_scenario_matches_respect_team_and_opponent_both_ways(queries):
    # Given a head-to-head search
    # When it is run in either order
    forward = queries.find_matches(team="Flamengo", opponent="Fluminense")
    reverse = queries.find_matches(team="Fluminense", opponent="Flamengo")
    # Then the same games come back
    assert {(m.date, m.home.base, m.away.base) for m in forward} == \
        {(m.date, m.home.base, m.away.base) for m in reverse}


def test_scenario_venue_filter_limits_to_home_games(queries):
    # Given Corinthians' 2022 matches
    # When I ask for home matches only
    home = queries.find_matches(team="Corinthians", season=2022, venue="home")
    # Then every match was played at home
    assert home and all(m.home.base == "corinthians" for m in home)


def test_scenario_date_range_is_inclusive(queries):
    # Given a date range
    # When I search for matches in it
    matches = queries.find_matches(start="2019-01-01", end="2019-03-31")
    # Then every match falls inside the range
    assert matches and all(date(2019, 1, 1) <= m.date <= date(2019, 3, 31) for m in matches)


def test_scenario_unknown_competition_is_an_error(queries):
    # Given a competition name that is not in the data
    # When matches are searched for it
    # Then a query error is raised
    with pytest.raises(QueryError):
        queries.find_matches(competition="Premier League")


def test_scenario_team_and_opponent_must_differ(queries):
    # Given the same club as team and opponent
    # When a head-to-head search is run
    # Then it is rejected
    with pytest.raises(QueryError):
        queries.find_matches(team="Flamengo", opponent="Flamengo-RJ")


def test_scenario_head_to_head_counts_add_up(queries):
    # Given a head-to-head between Palmeiras and Santos
    # When the summary is produced
    h = queries.head_to_head("Palmeiras", "Santos")
    # Then wins for each side plus draws equals the number of meetings
    assert h["wins_a"] + h["wins_b"] + h["draws"] == len(h["matches"]) > 0
    # And the last meeting is the first match listed
    assert h["last_meeting"] == h["matches"][0]


def test_scenario_team_record_for_season_and_venue(queries):
    # Given Corinthians' 2022 home matches
    # When the record is requested
    record = queries.team_record("Corinthians", season=2022, competition="brasileirao",
                                 venue="home")["record"]
    # Then wins, draws and losses account for every match and goals are totalled
    assert record.wins + record.draws + record.losses == record.played > 0
    assert record.goals_for >= 0 and record.goals_against >= 0
    assert 0 <= record.win_rate <= 100


def test_scenario_standings_are_calculated_from_results(queries):
    # Given the 2019 Brasileirão results
    # When the table is calculated
    table = queries.standings(2019)
    # Then there are 20 clubs, each with 38 games
    assert len(table) == 20
    assert all(row["played"] == 38 for row in table)
    # And points are 3 per win plus 1 per draw, sorted highest first
    assert all(row["points"] == 3 * row["won"] + row["drawn"] for row in table)
    assert [row["points"] for row in table] == sorted((r["points"] for r in table), reverse=True)


def test_scenario_2019_champion_matches_the_spec_example(queries):
    # Given the 2019 Brasileirão table
    # When the leader is read
    leader = queries.standings(2019)[0]
    # Then it is Flamengo on 90 points (28W, 6D, 4L)
    assert leader["team"].startswith("Flamengo")
    assert (leader["points"], leader["won"], leader["drawn"], leader["lost"]) == (90, 28, 6, 4)


def test_scenario_league_stats_percentages_add_up(queries):
    # Given the Brasileirão Série A matches
    # When the statistics are computed
    stats = queries.league_stats(competition="Brasileirão Série A")
    # Then home, draw and away rates sum to about 100% and goals per match is plausible
    total = stats["home_win_pct"] + stats["draw_pct"] + stats["away_win_pct"]
    assert abs(total - 100) < 0.5
    assert 2 < stats["goals_per_match"] < 3.5


def test_scenario_biggest_wins_are_ordered_by_margin(queries):
    # Given the dataset
    # When the biggest wins are requested
    wins = queries.biggest_wins(limit=5)
    # Then they are not draws and are ordered by winning margin, largest first
    margins = [m.goal_margin for m in wins]
    assert margins == sorted(margins, reverse=True) and min(margins) >= 1


def test_scenario_venue_leaderboard_requires_home_or_away(queries):
    # Given a request for an 'either' leaderboard
    # When it is run
    # Then it is refused
    with pytest.raises(QueryError):
        queries.venue_leaderboard("either")


def test_scenario_best_away_record_is_ranked_by_win_rate(queries):
    # Given the Brasileirão away records with a minimum of 50 games
    rows = queries.venue_leaderboard("away", competition="brasileirao", min_matches=50)
    # Then teams are ordered by away win rate and meet the minimum
    rates = [r["win_rate"] for r in rows]
    assert rates == sorted(rates, reverse=True) and rows
    assert all(r["record"].played >= 50 for r in rows)


def test_scenario_search_brazilian_players_by_nationality(queries):
    # Given the FIFA player data
    # When Brazilian players are searched for, best rated first
    players = queries.search_players(nationality="Brazilian", limit=3)
    # Then they are Brazilian and sorted by overall rating
    assert players and all(p.nationality == "Brazil" for p in players)
    assert [p.overall for p in players] == sorted((p.overall for p in players), reverse=True)


def test_scenario_forwards_are_found_by_position_group(queries):
    # Given the FIFA player data
    # When I ask for forwards
    forwards = queries.search_players(position="forwards", limit=50)
    # Then every returned player plays in a forward position
    allowed = {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"}
    assert forwards and all(p.position in allowed for p in forwards)


def test_scenario_player_search_by_club_and_name(queries):
    # Given a club name and a partial player name
    # When I search for players at Real Madrid
    club = queries.search_players(club="Real Madrid", limit=50)
    # Then they all play for that club
    assert club and all("real madrid" in p.club.lower() for p in club)
    # And a name search is case and accent insensitive
    assert queries.search_players(name="neymar")


def test_scenario_unknown_sort_is_rejected(queries):
    # Given an unsupported sort field
    # When players are searched
    # Then a query error is raised
    with pytest.raises(QueryError):
        queries.search_players(sort_by="speed")


def test_scenario_brazilian_players_grouped_by_brazilian_club(queries):
    # Given Brazilian players and the clubs that play in Brazilian league matches
    rows = queries.brazilian_players_by_club(limit=50)
    # Then clubs are ordered by number of Brazilian players
    counts = [r["players"] for r in rows]
    assert rows and counts == sorted(counts, reverse=True)


def test_scenario_search_teams_lists_spellings_for_disambiguation(queries):
    # Given a partial club name
    # When I search the match data for it
    rows = queries.search_teams("palmeiras")
    # Then the spellings are returned with their match counts
    assert rows and all("palmeiras" in r["team"].lower() for r in rows)
