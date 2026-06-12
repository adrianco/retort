defmodule BrazilianSoccer.Queries.PlayersTest do
  use ExUnit.Case, async: false

  alias BrazilianSoccer.Queries.Players

  describe "search_by_name/1" do
    test "finds players by partial name match" do
      results = Players.search_by_name("Neymar")
      assert length(results) > 0
      assert Enum.any?(results, fn p -> String.contains?(p.name, "Neymar") end)
    end

    test "is case-insensitive" do
      results = Players.search_by_name("neymar")
      assert length(results) > 0
    end

    test "returns empty for unknown player" do
      results = Players.search_by_name("ZXYUnknownPlayerABC")
      assert results == []
    end
  end

  describe "search_by_nationality/1" do
    test "finds Brazilian players" do
      results = Players.search_by_nationality("Brazil")
      assert length(results) > 0
      assert Enum.all?(results, fn p -> String.contains?(p.nationality, "Brazil") end)
    end

    test "case-insensitive search" do
      results = Players.search_by_nationality("brazil")
      assert length(results) > 0
    end
  end

  describe "search_by_club/1" do
    test "finds players by club name" do
      results = Players.search_by_club("Santos")
      assert length(results) > 0
      assert Enum.all?(results, fn p -> String.contains?(p.club, "Santos") end)
    end

    test "returns empty for unknown club" do
      results = Players.search_by_club("NonExistentClubXYZ")
      assert results == []
    end
  end

  describe "search_by_position/1" do
    test "finds strikers by position" do
      results = Players.search_by_position("ST")
      assert length(results) > 0
      assert Enum.all?(results, fn p -> p.position == "ST" end)
    end
  end

  describe "top_rated/2" do
    test "returns top N players sorted by overall rating" do
      results = Players.top_rated(10)
      assert length(results) == 10
      ratings = Enum.map(results, & &1.overall)
      assert ratings == Enum.sort(ratings, :desc)
    end

    test "filters by nationality" do
      results = Players.top_rated(10, nationality: "Brazil")
      assert length(results) <= 10
      assert Enum.all?(results, fn p -> String.contains?(p.nationality, "Brazil") end)
    end

    test "filters by club" do
      results = Players.top_rated(10, club: "Santos")
      assert length(results) <= 10
      assert Enum.all?(results, fn p -> String.contains?(p.club, "Santos") end)
    end
  end

  describe "players_by_club_with_nationality/2" do
    test "finds Brazilian players at Santos" do
      results = Players.players_by_club_with_nationality("Santos", "Brazil")
      assert Enum.all?(results, fn p ->
        String.contains?(p.club, "Santos") and String.contains?(p.nationality, "Brazil")
      end)
    end
  end
end
