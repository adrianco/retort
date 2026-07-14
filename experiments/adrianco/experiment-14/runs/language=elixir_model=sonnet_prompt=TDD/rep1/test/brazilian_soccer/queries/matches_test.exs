defmodule BrazilianSoccer.Queries.MatchesTest do
  use ExUnit.Case, async: false

  alias BrazilianSoccer.Queries.Matches

  describe "search_by_team/1" do
    test "finds matches for a team as home or away" do
      results = Matches.search_by_team("Flamengo")
      assert length(results) > 0
      assert Enum.all?(results, fn m ->
        String.contains?(m.home_team, "Flamengo") or String.contains?(m.away_team, "Flamengo")
      end)
    end

    test "is case-insensitive" do
      results = Matches.search_by_team("flamengo")
      assert length(results) > 0
    end

    test "returns empty list for unknown team" do
      results = Matches.search_by_team("NonExistentTeamXYZ")
      assert results == []
    end
  end

  describe "search_by_teams/2" do
    test "finds head-to-head matches between two teams" do
      results = Matches.search_by_teams("Flamengo", "Fluminense")
      assert length(results) > 0
      assert Enum.all?(results, fn m ->
        (String.contains?(m.home_team, "Flamengo") and String.contains?(m.away_team, "Fluminense")) or
        (String.contains?(m.home_team, "Fluminense") and String.contains?(m.away_team, "Flamengo"))
      end)
    end
  end

  describe "search_by_competition/1" do
    test "finds matches in Brasileirão" do
      results = Matches.search_by_competition("Brasileirão")
      assert length(results) > 0
      assert Enum.all?(results, fn m -> m.competition == "Brasileirão" end)
    end

    test "finds matches in Copa do Brasil" do
      results = Matches.search_by_competition("Copa do Brasil")
      assert length(results) > 0
    end

    test "finds matches in Copa Libertadores" do
      results = Matches.search_by_competition("Copa Libertadores")
      assert length(results) > 0
    end

    test "case-insensitive partial match" do
      results = Matches.search_by_competition("libertadores")
      assert length(results) > 0
    end
  end

  describe "search_by_season/1" do
    test "finds matches in a specific season" do
      results = Matches.search_by_season(2019)
      assert length(results) > 0
      assert Enum.all?(results, fn m -> m.season == 2019 end)
    end

    test "returns empty for season with no data" do
      results = Matches.search_by_season(1800)
      assert results == []
    end
  end

  describe "search_by_team_and_season/2" do
    test "finds Palmeiras matches in 2023" do
      results = Matches.search_by_team_and_season("Palmeiras", 2023)
      assert length(results) > 0
      assert Enum.all?(results, fn m ->
        (String.contains?(m.home_team, "Palmeiras") or String.contains?(m.away_team, "Palmeiras")) and
        m.season == 2023
      end)
    end
  end

  describe "head_to_head_stats/2" do
    test "returns win/draw/loss record for two teams" do
      stats = Matches.head_to_head_stats("Flamengo", "Fluminense")
      assert is_map(stats)
      assert Map.has_key?(stats, :flamengo_wins)
      assert Map.has_key?(stats, :fluminense_wins)
      assert Map.has_key?(stats, :draws)
      assert Map.has_key?(stats, :total)
      assert stats.total == stats.flamengo_wins + stats.fluminense_wins + stats.draws
    end
  end

  describe "biggest_wins/2" do
    test "returns matches sorted by goal difference" do
      results = Matches.biggest_wins(5)
      assert length(results) == 5
      diffs = Enum.map(results, fn m -> abs(m.home_goal - m.away_goal) end)
      assert diffs == Enum.sort(diffs, :desc)
    end
  end

  describe "search_by_date_range/2" do
    test "finds matches within a date range" do
      results = Matches.search_by_date_range("2023-01-01", "2023-12-31")
      assert length(results) > 0
    end

    test "returns empty for out-of-range dates" do
      results = Matches.search_by_date_range("1800-01-01", "1800-12-31")
      assert results == []
    end
  end
end
