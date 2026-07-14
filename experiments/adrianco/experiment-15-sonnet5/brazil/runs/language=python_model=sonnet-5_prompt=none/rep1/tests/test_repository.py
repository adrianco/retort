def test_find_matches_by_team(repo):
    matches = repo.find_matches(team="Flamengo-RJ", limit=None)
    assert len(matches) > 0
    assert all(m.involves("flamengo") for m in matches)


def test_find_matches_handles_team_name_variants(repo):
    a = repo.find_matches(team="Flamengo", limit=None)
    b = repo.find_matches(team="Flamengo-RJ", limit=None)
    assert len(a) == len(b)


def test_find_matches_by_opponent(repo):
    matches = repo.find_matches(team="Flamengo", opponent="Fluminense", limit=None)
    assert len(matches) > 0
    for m in matches:
        keys = {m.home_team_key, m.away_team_key}
        assert keys == {"flamengo", "fluminense"}


def test_find_matches_by_season_and_competition(repo):
    matches = repo.find_matches(
        team="Palmeiras", competition="Brasileirao Serie A", season=2023, limit=None
    )
    assert all(m.season == 2023 and m.competition == "Brasileirao Serie A" for m in matches)
    assert len(matches) > 0


def test_find_matches_venue_filter(repo):
    home_only = repo.find_matches(team="Corinthians", venue="home", limit=None)
    assert all(m.home_team_key == "corinthians" for m in home_only)


def test_find_matches_date_range(repo):
    matches = repo.find_matches(
        team="Flamengo", date_from="2023-01-01", date_to="2023-12-31", limit=None
    )
    assert all(m.match_date.year == 2023 for m in matches)


def test_head_to_head_symmetry(repo):
    ab = repo.head_to_head("Flamengo", "Fluminense")
    ba = repo.head_to_head("Fluminense", "Flamengo")
    assert ab["matches_found"] == ba["matches_found"]
    assert ab["wins_a"] == ba["wins_b"]
    assert ab["wins_b"] == ba["wins_a"]
    assert ab["matches_found"] > 0


def test_team_record_no_double_counts_home_and_away(repo):
    record = repo.team_record("Flamengo", competition="Brasileirao Serie A", season=2019)
    home = repo.team_record(
        "Flamengo", competition="Brasileirao Serie A", season=2019, venue="home"
    )
    away = repo.team_record(
        "Flamengo", competition="Brasileirao Serie A", season=2019, venue="away"
    )
    assert record.matches == home.matches + away.matches
    assert record.wins == home.wins + away.wins


def test_2019_brasileirao_standings_matches_known_result(repo):
    # Real-world result: Flamengo won the 2019 Brasileirao with 90 points
    # (28W-6D-4L) from 38 matches. Also a regression guard against
    # double-counting matches that exist in more than one source dataset.
    table = repo.standings("Brasileirao Serie A", 2019, min_matches=30)
    assert table[0].team == "Flamengo"
    assert table[0].matches == 38
    assert table[0].wins == 28
    assert table[0].draws == 6
    assert table[0].losses == 4
    assert table[0].points == 90


def test_standings_no_team_exceeds_one_match_per_matchday(repo):
    # 20-team single round-robin => 38 matches per team. If overlapping
    # source datasets were double-counted this would be 76 or 114.
    table = repo.standings("Brasileirao Serie A", 2019, min_matches=30)
    assert all(row.matches == 38 for row in table)


def test_biggest_wins_sorted_by_goal_difference(repo):
    wins = repo.biggest_wins(n=10)
    diffs = [m.goal_difference for m in wins]
    assert diffs == sorted(diffs, reverse=True)


def test_average_goals_is_reasonable(repo):
    stats = repo.average_goals(competition="Brasileirao Serie A")
    assert stats["matches"] > 5000
    assert 1.5 < stats["average_goals_per_match"] < 4.0
    assert 0.3 < stats["home_win_rate"] < 0.7


def test_best_record_respects_min_matches(repo):
    rows = repo.best_record(
        competition="Brasileirao Serie A", season=2019, venue="home", min_matches=5, n=25
    )
    assert all(row.matches >= 5 for row in rows)
    assert rows[0].win_rate >= rows[-1].win_rate


def test_search_players_by_name(repo):
    players = repo.search_players(name="Neymar")
    assert any("Neymar" in p.name for p in players)


def test_search_players_by_nationality(repo):
    players = repo.search_players(nationality="Brazil", limit=1000)
    assert len(players) > 500
    assert all(p.nationality == "Brazil" for p in players)


def test_top_players_sorted_by_overall(repo):
    players = repo.top_players(nationality="Brazil", n=10)
    ratings = [p.overall for p in players]
    assert ratings == sorted(ratings, reverse=True)


def test_list_competitions_and_seasons(repo):
    competitions = repo.list_competitions()
    assert "Brasileirao Serie A" in competitions
    assert "Copa do Brasil" in competitions
    assert "Copa Libertadores" in competitions
    seasons = repo.list_seasons("Brasileirao Serie A")
    assert 2019 in seasons
