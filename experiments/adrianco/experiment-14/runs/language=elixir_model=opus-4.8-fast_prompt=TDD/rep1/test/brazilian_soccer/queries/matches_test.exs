defmodule BrazilianSoccer.Queries.MatchesTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.Queries.Matches

  setup do
    {:ok, dataset: BrazilianSoccer.Fixtures.dataset()}
  end

  describe "find/2" do
    test "filters by a single team (home or away)", %{dataset: ds} do
      results = Matches.find(ds, team: "Fluminense")
      assert length(results) == 3
      assert Enum.all?(results, &BrazilianSoccer.Match.involves?(&1, "fluminense"))
    end

    test "filters by two teams in any order", %{dataset: ds} do
      results = Matches.find(ds, teams: {"flamengo", "Fluminense-RJ"})
      assert length(results) == 3
    end

    test "filters by competition and season", %{dataset: ds} do
      results = Matches.find(ds, competition: "Copa do Brasil")
      assert length(results) == 1

      results = Matches.find(ds, season: 2022)
      assert length(results) == 1
    end

    test "filters by date range", %{dataset: ds} do
      results = Matches.find(ds, from: ~D[2023-06-01], to: ~D[2023-09-30])
      assert length(results) == 3
    end

    test "sorts most recent first", %{dataset: ds} do
      [first | _] = Matches.find(ds, team: "Flamengo")
      assert first.date == ~D[2023-10-20]
    end

    test "supports an explicit home filter", %{dataset: ds} do
      results = Matches.find(ds, home: "Flamengo", season: 2023)
      assert Enum.all?(results, &(&1.home_key == "flamengo"))
      assert length(results) == 3
    end
  end

  describe "head_to_head/3" do
    test "tallies wins, losses and draws from one team's perspective", %{dataset: ds} do
      h2h = Matches.head_to_head(ds, "Flamengo", "Fluminense")

      assert h2h.team_a == "Flamengo"
      assert h2h.team_b == "Fluminense"
      assert h2h.total == 3
      assert h2h.a_wins == 1
      assert h2h.b_wins == 1
      assert h2h.draws == 1
      assert h2h.a_goals == 3
      assert h2h.b_goals == 3
    end
  end
end
