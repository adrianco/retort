"""BDD-style behaviour tests.

Each test follows the Given/When/Then structure from the TASK.md
acceptance scenarios. The `Given` step relies on the session-scoped
``queries`` fixture (data already loaded).
"""


class TestMatchQueries:
    """Feature: Match Queries."""

    def test_find_matches_between_two_teams(self, queries):
        # Given the match data is loaded (fixture)
        # When I search for matches between "Flamengo" and "Fluminense"
        result = queries.find_matches(team="Flamengo", opponent="Fluminense")
        # Then I should receive a list of matches
        assert isinstance(result, list)
        assert len(result) > 0
        # And each match should have date, scores, and competition
        for m in result:
            assert {"date", "competition", "home_team", "away_team", "home_goal", "away_goal"} <= m.keys()

    def test_find_matches_by_season(self, queries):
        # Given the match data is loaded
        # When I search for Palmeiras matches in 2019
        result = queries.find_matches(team="Palmeiras", season=2019, limit=200)
        # Then every returned match should be in 2019
        assert len(result) > 0
        assert all(m["season"] == 2019 for m in result if m["season"] is not None)

    def test_find_matches_by_competition(self, queries):
        # Given the data is loaded
        # When I search for Copa Libertadores matches
        result = queries.find_matches(competition="Libertadores", limit=20)
        # Then competition is Copa Libertadores
        assert len(result) > 0
        assert all("Libertadores" in m["competition"] for m in result)

    def test_find_matches_home_only(self, queries):
        result = queries.find_matches(team="Corinthians", season=2022, home_only=True, limit=200)
        assert len(result) > 0
        for m in result:
            assert "corinthians" in m["home_team"].lower()


class TestTeamQueries:
    """Feature: Team Queries."""

    def test_team_stats_returns_record(self, queries):
        # Given the match data is loaded
        # When I request statistics for Palmeiras in season 2019
        stats = queries.team_stats(team="Palmeiras", season=2019, competition="Brasileirão")
        # Then wins, losses, draws, and goals fields are present
        for key in ("wins", "draws", "losses", "goals_for", "goals_against", "points"):
            assert key in stats
        assert stats["matches_played"] == stats["wins"] + stats["draws"] + stats["losses"]

    def test_team_stats_full_season(self, queries):
        # In 2019 every Brasileirão team played 38 matches.
        stats = queries.team_stats(team="Flamengo", season=2019, competition="Brasileirão")
        assert stats["matches_played"] == 38

    def test_team_stats_home_only(self, queries):
        stats = queries.team_stats(team="Corinthians", season=2022, competition="Brasileirão", venue="home")
        # Corinthians 2022 home Brasileirão: 15 matches in the loaded data.
        assert stats["venue"] == "home"
        assert stats["matches_played"] > 0

    def test_head_to_head_symmetric(self, queries):
        a = queries.head_to_head("Flamengo", "Fluminense")
        b = queries.head_to_head("Fluminense", "Flamengo")
        assert a["total_matches"] == b["total_matches"]
        assert a["team_a_wins"] == b["team_b_wins"]


class TestPlayerQueries:
    """Feature: Player Queries."""

    def test_find_player_by_name(self, queries):
        result = queries.find_players(name="Neymar")
        assert any("Neymar" in (p.get("Name") or "") for p in result)

    def test_find_brazilian_players(self, queries):
        result = queries.find_players(nationality="Brazil", limit=5)
        assert len(result) == 5
        assert all(p["Nationality"] == "Brazil" for p in result)

    def test_top_brazilians_sorted_by_overall(self, queries):
        result = queries.top_brazilian_players(limit=10)
        overalls = [p["Overall"] for p in result if p.get("Overall") is not None]
        assert overalls == sorted(overalls, reverse=True)

    def test_filter_by_position(self, queries):
        result = queries.find_players(nationality="Brazil", position="GK", limit=5)
        for p in result:
            assert (p.get("Position") or "").upper() == "GK"


class TestCompetitionQueries:
    """Feature: Competition Queries."""

    def test_standings_2019_flamengo_champion(self, queries):
        # Flamengo won the 2019 Brasileirão with 90 points.
        table = queries.standings("Brasileirão", 2019)
        assert table[0]["points"] == 90
        # Their display name should include Flamengo somewhere.
        assert "Flamengo" in table[0]["team"]

    def test_standings_team_played_38_matches(self, queries):
        table = queries.standings("Brasileirão", 2019)
        assert all(t["played"] == 38 for t in table[:10])

    def test_list_competitions_includes_three_majors(self, queries):
        names = queries.list_competitions()
        joined = " ".join(names)
        assert "Brasileirão" in joined
        assert "Libertadores" in joined
        assert "Copa do Brasil" in joined

    def test_list_seasons_returns_sorted_unique(self, queries):
        seasons = queries.list_seasons("Brasileirão")
        assert seasons == sorted(set(seasons))
        assert 2019 in seasons


class TestStatisticalAnalysis:
    """Feature: Statistical Analysis."""

    def test_biggest_wins_sorted_by_margin(self, queries):
        wins = queries.biggest_wins(season=2019, limit=5)
        margins = [w["margin"] for w in wins]
        assert margins == sorted(margins, reverse=True)

    def test_average_goals_per_match_sane(self, queries):
        stats = queries.average_goals_per_match("Brasileirão", 2019)
        # Sanity: Brasileirão averages roughly 2-3 goals/match.
        assert stats["matches"] > 0
        assert 1.5 < stats["avg_goals"] < 4.0
        rate_sum = stats["home_win_rate"] + stats["away_win_rate"] + stats["draw_rate"]
        assert abs(rate_sum - 1.0) < 1e-3

    def test_summary_reports_totals(self, queries):
        s = queries.summary()
        assert s["total_matches"] > 10000
        assert s["total_players"] == 18207


class TestDataQuality:
    """Feature: Data Quality handling — name variants and encoding."""

    def test_team_name_with_state_suffix_matches_bare_name(self, queries):
        # Within a single competition the bare and suffixed forms should
        # return the same set of matches (e.g. Palmeiras = Palmeiras-SP).
        bare = queries.find_matches(team="Palmeiras", season=2019, competition="Brasileirão Serie A", limit=200)
        suffixed = queries.find_matches(team="Palmeiras-SP", season=2019, competition="Brasileirão Serie A", limit=200)
        assert len(bare) > 0
        assert len(bare) == len(suffixed)

    def test_handles_accents(self, queries):
        # "Gremio" (no accent) should still find Grêmio.
        result = queries.find_matches(team="Gremio", season=2019, limit=200)
        assert len(result) > 0

    def test_athletico_vs_atletico_dedup(self, queries):
        # 2019 Brasileirão: Atlético-PR played 38 games; the "Athletico" spelling
        # in another file shouldn't cause double-counting.
        stats = queries.team_stats("Atletico-PR", season=2019, competition="Brasileirão")
        assert stats["matches_played"] == 38
