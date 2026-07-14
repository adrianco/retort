defmodule BrazilianSoccer.Queries.TeamsTest do
  use ExUnit.Case, async: false

  alias BrazilianSoccer.Queries.Teams

  describe "team_record/1" do
    test "returns win/draw/loss record for a team" do
      stats = Teams.team_record("Corinthians")
      assert is_map(stats)
      assert Map.has_key?(stats, :wins)
      assert Map.has_key?(stats, :draws)
      assert Map.has_key?(stats, :losses)
      assert Map.has_key?(stats, :goals_for)
      assert Map.has_key?(stats, :goals_against)
      assert Map.has_key?(stats, :matches)
      assert stats.matches == stats.wins + stats.draws + stats.losses
    end

    test "home record only" do
      stats = Teams.team_record("Corinthians", home_only: true)
      assert stats.matches >= 0
    end

    test "record for a specific season and competition" do
      stats = Teams.team_record("Corinthians", season: 2022, competition: "Brasileirão")
      assert stats.matches >= 0
    end
  end

  describe "top_scorers_team/2" do
    test "returns team that scored most goals in a season" do
      results = Teams.top_scoring_teams(2019, "Brasileirão", 5)
      assert length(results) <= 5
      assert Enum.all?(results, fn {_team, goals} -> is_integer(goals) and goals > 0 end)
      goals_list = Enum.map(results, fn {_team, goals} -> goals end)
      assert goals_list == Enum.sort(goals_list, :desc)
    end
  end

  describe "competition_standings/2" do
    test "calculates standings from match results" do
      standings = Teams.competition_standings(2019, "Brasileirão")
      assert length(standings) > 0
      # Each entry has team, points, wins, draws, losses
      first = hd(standings)
      assert Map.has_key?(first, :team)
      assert Map.has_key?(first, :points)
      assert Map.has_key?(first, :wins)
      assert Map.has_key?(first, :draws)
      assert Map.has_key?(first, :losses)
      # Sorted by points descending
      points = Enum.map(standings, & &1.points)
      assert points == Enum.sort(points, :desc)
    end

    test "2019 Brasileirão champion should be Flamengo" do
      standings = Teams.competition_standings(2019, "Brasileirão")
      champion = hd(standings)
      assert String.contains?(champion.team, "Flamengo")
    end
  end

  describe "average_goals_per_match/1" do
    test "calculates average goals per match for a competition" do
      avg = Teams.average_goals_per_match("Brasileirão")
      assert is_float(avg)
      assert avg > 0.0
      assert avg < 10.0
    end
  end

  describe "home_win_rate/0" do
    test "calculates home win rate across all matches" do
      rate = Teams.home_win_rate()
      assert is_float(rate)
      assert rate > 0.0
      assert rate <= 1.0
    end
  end

  describe "best_away_teams/2" do
    test "returns teams with best away records" do
      results = Teams.best_away_teams(5)
      assert length(results) <= 5
    end
  end
end
