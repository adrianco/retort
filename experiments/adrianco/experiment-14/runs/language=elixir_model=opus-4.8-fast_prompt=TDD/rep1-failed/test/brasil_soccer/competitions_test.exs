defmodule BrasilSoccer.CompetitionsTest do
  use ExUnit.Case, async: true

  alias BrasilSoccer.Competitions
  alias BrasilSoccer.Fixtures

  setup do
    {:ok, matches: Fixtures.mini_season()}
  end

  describe "standings/3" do
    test "computes points (3/1/0) and orders the table", %{matches: ms} do
      table = Competitions.standings(ms, "Brasileirão", 2019)
      assert Enum.map(table, & &1.team) == ["Flamengo", "Palmeiras", "Santos"]
    end

    test "tracks each team's full line", %{matches: ms} do
      table = Competitions.standings(ms, "Brasileirão", 2019)
      flamengo = hd(table)
      assert flamengo.points == 12
      assert flamengo.played == 4
      assert flamengo.wins == 4
      assert flamengo.goals_for == 8
      assert flamengo.goals_against == 0
      assert flamengo.position == 1
    end

    test "ties break on goal difference then goals for", %{matches: ms} do
      table = Competitions.standings(ms, "Brasileirão", 2019)
      [_, palmeiras, santos] = table
      assert palmeiras.points == 4
      assert santos.points == 1
      assert palmeiras.goal_difference > santos.goal_difference
    end
  end

  describe "champion/3" do
    test "returns the top team of the computed table", %{matches: ms} do
      assert Competitions.champion(ms, "Brasileirão", 2019).team == "Flamengo"
    end
  end

  describe "seasons/2" do
    test "lists the distinct seasons present for a competition", %{matches: ms} do
      assert Competitions.seasons(ms, "Brasileirão") == [2019]
    end
  end
end
