defmodule BrazilianSoccer.Queries.PlayersTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.Queries.Players

  setup do
    {:ok, dataset: BrazilianSoccer.Fixtures.dataset()}
  end

  describe "search/2" do
    test "matches by name substring, accent-insensitive", %{dataset: ds} do
      assert [p] = Players.search(ds, name: "neymar")
      assert p.name == "Neymar Jr"
    end

    test "filters Brazilian players and sorts by overall desc", %{dataset: ds} do
      results = Players.search(ds, brazilian: true)
      assert Enum.map(results, & &1.name) == ["Neymar Jr", "Gabriel Barbosa", "Pedro", "Endrick"]
    end

    test "filters by club using normalized names", %{dataset: ds} do
      results = Players.search(ds, club: "Flamengo")
      assert length(results) == 2
      assert Enum.all?(results, &(&1.club == "Flamengo"))
    end

    test "filters by position and nationality", %{dataset: ds} do
      results = Players.search(ds, position: "ST", nationality: "Brazil")
      assert Enum.map(results, & &1.name) == ["Gabriel Barbosa", "Pedro", "Endrick"]
    end

    test "applies min_overall and limit", %{dataset: ds} do
      results = Players.search(ds, min_overall: 85, limit: 1)
      assert length(results) == 1
      assert hd(results).name == "Lionel Messi"
    end
  end

  describe "by_club/2" do
    test "summarizes player count and average rating", %{dataset: ds} do
      summary = Players.by_club(ds, "Flamengo")
      assert summary.club == "Flamengo"
      assert summary.count == 2
      assert_in_delta summary.avg_overall, 82.0, 0.001
      assert length(summary.players) == 2
    end
  end
end
