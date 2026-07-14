defmodule BrazilianSoccer.Queries.CompetitionsTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.Queries.Competitions

  setup do
    {:ok, dataset: BrazilianSoccer.Fixtures.dataset()}
  end

  describe "standings/3" do
    test "computes points, ranks by points then goal difference", %{dataset: ds} do
      table = Competitions.standings(ds, "Brasileirão Série A", 2023)

      assert Enum.map(table, & &1.team) == ["Palmeiras", "Flamengo", "Fluminense"]

      [palmeiras, flamengo, _flu] = table
      assert palmeiras.position == 1
      assert palmeiras.points == 4
      assert palmeiras.goal_difference == 2
      assert flamengo.points == 4
      assert flamengo.goal_difference == -2
    end

    test "excludes other competitions and seasons", %{dataset: ds} do
      table = Competitions.standings(ds, "Brasileirão Série A", 2023)
      # The Copa do Brasil final and the 2022 match must not count.
      flamengo = Enum.find(table, &(&1.team == "Flamengo"))
      assert flamengo.played == 4
    end
  end

  describe "champion/3" do
    test "returns the top of the table", %{dataset: ds} do
      assert Competitions.champion(ds, "Brasileirão Série A", 2023).team == "Palmeiras"
    end
  end

  describe "seasons/2 and competitions/1" do
    test "lists available seasons for a competition", %{dataset: ds} do
      assert Competitions.seasons(ds, "Brasileirão Série A") == [2022, 2023]
    end

    test "lists distinct competitions", %{dataset: ds} do
      assert Competitions.competitions(ds) == ["Brasileirão Série A", "Copa do Brasil"]
    end
  end
end
