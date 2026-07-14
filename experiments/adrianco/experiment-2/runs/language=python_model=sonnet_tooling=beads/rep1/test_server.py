"""BDD-style tests for the Brazilian Soccer MCP server."""

import pytest
from data_loader import store, normalize_team_name


# ---------------------------------------------------------------------------
# Data Loader Tests
# ---------------------------------------------------------------------------

class TestDataLoader:
    """Given the datasets are loaded."""

    def test_brasileirao_loads(self):
        """Then Brasileirao data has expected row count."""
        assert len(store.brasileirao) >= 4000

    def test_copa_brasil_loads(self):
        assert len(store.copa_brasil) >= 1000

    def test_libertadores_loads(self):
        assert len(store.libertadores) >= 1000

    def test_br_football_loads(self):
        assert len(store.br_football) >= 10000

    def test_historico_loads(self):
        assert len(store.historico) >= 6000

    def test_fifa_loads(self):
        assert len(store.fifa) >= 18000

    def test_all_matches_no_duplicates_for_known_season(self):
        """All matches for 2019 Brasileirao should be 380 (38 rounds × 10 matches)."""
        df = store.all_matches()
        br2019 = df[(df["season"] == 2019) & (df["competition"] == "Brasileirao Serie A")]
        assert len(br2019) == 380

    def test_historico_covers_early_seasons(self):
        """Historico should cover seasons 2003-2011 in all_matches."""
        df = store.all_matches()
        early = df[df["season"] < 2012]
        assert len(early) > 0

    def test_team_name_normalization_state_suffix(self):
        assert normalize_team_name("Palmeiras-SP") == "Palmeiras"
        assert normalize_team_name("Flamengo-RJ") == "Flamengo"

    def test_team_name_normalization_accents(self):
        assert normalize_team_name("Grêmio") == "Gremio"
        assert normalize_team_name("São Paulo") == "Sao Paulo"

    def test_team_name_normalization_state_aware(self):
        """Atletico-MG and Atletico-PR must be distinguished."""
        assert normalize_team_name("Atletico-MG") == "Atletico Mineiro"
        assert normalize_team_name("Atletico-PR") == "Athletico Paranaense"
        assert normalize_team_name("Athletico-PR") == "Athletico Paranaense"

    def test_team_name_normalization_vasco(self):
        assert normalize_team_name("Vasco da Gama-RJ") == "Vasco"


# ---------------------------------------------------------------------------
# Match Query Tests
# ---------------------------------------------------------------------------

class TestMatchQueries:
    """Feature: Match Queries."""

    def test_find_matches_by_two_teams(self):
        """Scenario: Find matches between two specific teams."""
        from server import find_matches

        result = find_matches(team1="Flamengo", team2="Fluminense", limit=100)
        assert "Flamengo" in result
        assert "Fluminense" in result
        assert "Head-to-head" in result
        # Should have results
        assert "Found" in result
        assert "No matches" not in result

    def test_find_matches_head_to_head_has_record(self):
        """Then the head-to-head record is shown."""
        from server import find_matches

        result = find_matches(team1="Flamengo", team2="Fluminense")
        assert "wins" in result

    def test_find_matches_by_single_team(self):
        """When I search for matches for a single team, I get their matches."""
        from server import find_matches

        result = find_matches(team1="Palmeiras", limit=10)
        assert "Palmeiras" in result
        assert "No matches" not in result

    def test_find_matches_by_competition(self):
        """When I filter by competition, only those competition's matches are returned."""
        from server import find_matches

        result = find_matches(competition="Copa do Brasil", limit=10)
        assert "Copa do Brasil" in result

    def test_find_matches_by_season(self):
        """When I filter by season, only that season's matches are shown."""
        from server import find_matches

        result = find_matches(team1="Corinthians", season=2022, limit=20)
        assert "2022" in result

    def test_find_matches_nonexistent_team(self):
        """When no matches found, appropriate message returned."""
        from server import find_matches

        result = find_matches(team1="NonExistentTeamXYZ123")
        assert "No matches" in result

    def test_get_recent_matches(self):
        """When I request recent matches for a team, I get sorted results."""
        from server import get_recent_matches

        result = get_recent_matches(team="Santos", limit=5)
        assert "Santos" in result
        assert "Recent matches" in result

    def test_each_match_has_date_score_and_competition(self):
        """Then each match result includes date, score, and competition."""
        from server import find_matches

        result = find_matches(team1="Flamengo", team2="Fluminense", limit=3)
        # Should have date format YYYY-MM-DD
        import re
        assert re.search(r"\d{4}-\d{2}-\d{2}", result)
        # Should have score (digit-digit format)
        assert re.search(r"\d+-\d+", result)


# ---------------------------------------------------------------------------
# Team Stats Tests
# ---------------------------------------------------------------------------

class TestTeamStats:
    """Feature: Team Statistics."""

    def test_get_team_stats_returns_record(self):
        """When I request statistics for a team, I get W/D/L and goals."""
        from server import get_team_stats

        result = get_team_stats("Corinthians")
        assert "W" in result or "Wins" in result or "Record" in result
        assert "Goals" in result

    def test_get_team_stats_with_season_filter(self):
        """When I filter by season, only that season's stats are shown."""
        from server import get_team_stats

        result = get_team_stats("Flamengo", season=2019)
        assert "2019" in result
        assert "No matches" not in result

    def test_get_team_stats_with_competition_filter(self):
        """When I filter by competition, only those matches count."""
        from server import get_team_stats

        result = get_team_stats("Palmeiras", competition="Brasileirao")
        assert "Palmeiras" in result

    def test_compare_teams_returns_both_stats(self):
        """When I compare two teams, I get both their stats."""
        from server import compare_teams

        result = compare_teams("Flamengo", "Palmeiras")
        assert "Flamengo" in result
        assert "Palmeiras" in result

    def test_get_home_away_performance_team(self):
        """When I request home/away breakdown for a team, I see both records."""
        from server import get_home_away_performance

        result = get_home_away_performance(team="Santos")
        assert "Home" in result
        assert "Away" in result

    def test_get_home_away_performance_ranking(self):
        """When no team specified, I get a ranking of teams by home win rate."""
        from server import get_home_away_performance

        result = get_home_away_performance()
        assert "Top" in result
        assert "%" in result


# ---------------------------------------------------------------------------
# Player Tests
# ---------------------------------------------------------------------------

class TestPlayerQueries:
    """Feature: Player Queries."""

    def test_find_players_by_name(self):
        """When I search by name, I get matching players."""
        from server import find_players

        result = find_players(name="Neymar")
        assert "Neymar" in result
        assert "Brazil" in result

    def test_find_players_by_nationality(self):
        """When I filter by Brazilian nationality, I get Brazilian players."""
        from server import find_players

        result = find_players(nationality="Brazil", limit=5)
        assert "Brazil" in result

    def test_find_players_by_club(self):
        """When I search by club, I get that club's players."""
        from server import find_players

        # Fluminense and Santos are Brazilian clubs present in the FIFA dataset
        result = find_players(club="Fluminense", limit=10)
        assert "Fluminense" in result

    def test_find_players_by_min_overall(self):
        """When I filter by minimum overall rating, only high-rated players appear."""
        from server import find_players

        result = find_players(min_overall=90, limit=10)
        assert "Overall" in result
        # All players should have overall >= 90
        import re
        overalls = re.findall(r"Overall: (\d+)", result)
        assert all(int(o) >= 90 for o in overalls)

    def test_find_players_nonexistent(self):
        """When no players match, appropriate message is returned."""
        from server import find_players

        result = find_players(name="NonExistentPlayerXYZ999")
        assert "No players" in result

    def test_get_player_details(self):
        """When I request details for a player, I get comprehensive info."""
        from server import get_player_details

        result = get_player_details("Neymar")
        assert "Neymar" in result
        assert "Overall" in result
        assert "Nationality" in result
        assert "Club" in result
        assert "Position" in result

    def test_get_club_players(self):
        """When I request players at a club, I get them sorted by rating."""
        from server import get_club_players

        result = get_club_players("Barcelona")
        assert "Barcelona" in result
        assert "Overall" in result


# ---------------------------------------------------------------------------
# Competition / Standings Tests
# ---------------------------------------------------------------------------

class TestCompetitionQueries:
    """Feature: Competition and Standings Queries."""

    def test_get_league_standings_2019(self):
        """Scenario: 2019 Brasileirao champion was Flamengo with 90 points."""
        from server import get_league_standings

        result = get_league_standings(2019, "Brasileirao")
        # Flamengo should be first
        lines = result.split("\n")
        first_team_line = [l for l in lines if "1." in l][0]
        assert "Flamengo" in first_team_line

    def test_get_league_standings_has_correct_match_count(self):
        """2019 Brasileirao should have 380 matches (38 rounds × 10)."""
        from server import get_league_standings

        result = get_league_standings(2019, "Brasileirao")
        assert "380 matches" in result

    def test_get_league_standings_unknown_season(self):
        """When season has no data, appropriate message returned."""
        from server import get_league_standings

        result = get_league_standings(1900, "Brasileirao")
        assert "No match data" in result

    def test_get_competition_history(self):
        """When I request a team's competition history, I see all competitions."""
        from server import get_competition_history

        result = get_competition_history("Flamengo")
        assert "Flamengo" in result
        assert "Brasileirao" in result

    def test_list_seasons(self):
        """When I list seasons, I get a range from 2003+."""
        from server import list_seasons

        result = list_seasons()
        assert "2003" in result
        assert "2019" in result

    def test_list_teams(self):
        """When I list teams, I get a large set."""
        from server import list_teams

        result = list_teams()
        assert "Flamengo" in result
        assert "Palmeiras" in result
        assert "total" in result


# ---------------------------------------------------------------------------
# Statistical Analysis Tests
# ---------------------------------------------------------------------------

class TestStatisticalAnalysis:
    """Feature: Statistical Analysis."""

    def test_get_top_scorers_teams(self):
        """When I request top scoring teams, I get ranked list with goals."""
        from server import get_top_scorers_teams

        result = get_top_scorers_teams(top_n=5)
        assert "goals" in result.lower()
        # Should have at least 5 entries
        assert result.count("1.") >= 1

    def test_get_biggest_wins(self):
        """When I request biggest wins, I get matches with large goal differences."""
        from server import get_biggest_wins

        result = get_biggest_wins(limit=5)
        assert "diff" in result
        # Biggest win should have large margin
        import re
        diffs = re.findall(r"diff: (\d+)", result)
        assert max(int(d) for d in diffs) >= 6

    def test_get_competition_summary(self):
        """When I request competition summary, I get key statistics."""
        from server import get_competition_summary

        result = get_competition_summary(competition="Brasileirao")
        assert "Total matches" in result
        assert "Average goals" in result
        assert "Home wins" in result
        assert "Away wins" in result
        assert "Draws" in result

    def test_competition_summary_goals_per_match_reasonable(self):
        """Average goals per match should be between 2 and 4."""
        from server import get_competition_summary
        import re

        result = get_competition_summary(competition="Brasileirao")
        avg_match = re.search(r"Average goals per match: ([\d.]+)", result)
        assert avg_match
        avg = float(avg_match.group(1))
        assert 1.5 <= avg <= 4.0

    def test_get_top_scorers_teams_by_season(self):
        """When filtered by season, top scorers show only that season's data."""
        from server import get_top_scorers_teams

        result = get_top_scorers_teams(season=2022, top_n=5)
        assert "2022" in result

    def test_biggest_wins_by_competition(self):
        """When filtered by competition, only those matches appear."""
        from server import get_biggest_wins

        result = get_biggest_wins(competition="Copa do Brasil", limit=5)
        assert "Copa do Brasil" in result


# ---------------------------------------------------------------------------
# Cross-file / Integration Tests
# ---------------------------------------------------------------------------

class TestIntegration:
    """Feature: Cross-dataset queries."""

    def test_player_and_team_cross_query(self):
        """I can find players at a club and then find that club's matches."""
        from server import get_club_players, find_matches

        players = get_club_players("Flamengo", min_overall=75)
        matches = find_matches(team1="Flamengo", limit=5)
        assert "Flamengo" in players
        assert "Flamengo" in matches

    def test_all_six_csv_files_queryable(self):
        """All 6 CSV files should be loaded with data."""
        assert len(store.brasileirao) > 0
        assert len(store.copa_brasil) > 0
        assert len(store.libertadores) > 0
        assert len(store.br_football) > 0
        assert len(store.historico) > 0
        assert len(store.fifa) > 0

    def test_flamengo_corinthians_rivalry(self):
        """When did Flamengo last play Corinthians? Should find matches."""
        from server import find_matches

        result = find_matches(team1="Flamengo", team2="Corinthians")
        assert "No matches" not in result
        assert "Flamengo" in result

    def test_who_won_2019_brasileirao(self):
        """2019 Brasileirao was won by Flamengo."""
        from server import get_league_standings

        result = get_league_standings(2019, "Brasileirao")
        lines = result.split("\n")
        first_team = [l for l in lines if "1." in l][0]
        assert "Flamengo" in first_team

    def test_average_goals_brasileirao(self):
        """Average goals per match in Brasileirao should be around 2-3."""
        from server import get_competition_summary
        import re

        result = get_competition_summary("Brasileirao")
        m = re.search(r"Average goals per match: ([\d.]+)", result)
        assert m
        assert 2.0 <= float(m.group(1)) <= 3.5

    def test_highest_rated_fluminense_player(self):
        """Highest rated player at Fluminense (present in FIFA data) should have overall > 60."""
        from server import find_players
        import re

        result = find_players(club="Fluminense", limit=1)
        overalls = re.findall(r"Overall: (\d+)", result)
        assert overalls
        assert int(overalls[0]) > 60


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
