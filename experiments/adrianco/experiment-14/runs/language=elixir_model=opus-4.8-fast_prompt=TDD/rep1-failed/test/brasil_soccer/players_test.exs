defmodule BrasilSoccer.PlayersTest do
  use ExUnit.Case, async: true

  alias BrasilSoccer.Players
  alias BrasilSoccer.Fixtures

  setup do
    {:ok, players: Fixtures.players()}
  end

  describe "search/2" do
    test "matches by partial, case-insensitive name", %{players: ps} do
      assert [%{name: "Gabriel Barbosa"}] = Players.search(ps, name: "barbosa")
    end

    test "filters by nationality", %{players: ps} do
      brazilians = Players.search(ps, nationality: "Brazil")
      assert length(brazilians) == 4
      assert Enum.all?(brazilians, &(&1.nationality == "Brazil"))
    end

    test "filters by club (fuzzy)", %{players: ps} do
      assert Players.search(ps, club: "Flamengo") |> length() == 2
    end

    test "filters by position", %{players: ps} do
      assert Players.search(ps, position: "LW") |> length() == 3
    end

    test "results are sorted by overall rating descending", %{players: ps} do
      ratings = Players.search(ps, nationality: "Brazil") |> Enum.map(& &1.overall)
      assert ratings == Enum.sort(ratings, :desc)
    end

    test "respects a limit", %{players: ps} do
      assert Players.search(ps, nationality: "Brazil", limit: 2) |> length() == 2
    end
  end

  describe "by_club_summary/2" do
    test "counts players and averages ratings per club for a nationality", %{players: ps} do
      summary = Players.by_club_summary(ps, nationality: "Brazil")
      flamengo = Enum.find(summary, &(&1.club == "Flamengo"))
      assert flamengo.count == 2
      assert_in_delta flamengo.avg_overall, 80.0, 0.001
    end
  end
end
