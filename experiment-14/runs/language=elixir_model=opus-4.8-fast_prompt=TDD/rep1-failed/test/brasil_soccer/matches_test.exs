defmodule BrasilSoccer.MatchesTest do
  use ExUnit.Case, async: true

  alias BrasilSoccer.Matches
  alias BrasilSoccer.Fixtures

  setup do
    {:ok, matches: Fixtures.matches()}
  end

  describe "find/2" do
    test "filters by a single team on either side", %{matches: ms} do
      found = Matches.find(ms, team: "Flamengo")
      assert length(found) == 5
      assert Enum.all?(found, &BrasilSoccer.Match.involves?(&1, "Flamengo"))
    end

    test "filters by two teams (head-to-head pairing)", %{matches: ms} do
      found = Matches.find(ms, team: "Flamengo", opponent: "Fluminense")
      assert length(found) == 3
    end

    test "filters by competition", %{matches: ms} do
      found = Matches.find(ms, competition: "Copa do Brasil")
      assert length(found) == 1
    end

    test "filters by season", %{matches: ms} do
      assert Matches.find(ms, season: 2022) |> length() == 1
    end

    test "filters by date range", %{matches: ms} do
      found = Matches.find(ms, from: ~D[2023-05-01], to: ~D[2023-06-30])
      assert Enum.all?(found, &(Date.compare(&1.date, ~D[2023-05-01]) != :lt))
      assert Enum.all?(found, &(Date.compare(&1.date, ~D[2023-06-30]) != :gt))
    end

    test "filters by home side only", %{matches: ms} do
      found = Matches.find(ms, home: "Flamengo")
      assert Enum.all?(found, &(&1.home_team == "Flamengo"))
      assert length(found) == 3
    end

    test "sorts results most-recent first and respects a limit", %{matches: ms} do
      found = Matches.find(ms, team: "Flamengo", limit: 2)
      assert length(found) == 2
      dates = Enum.map(found, & &1.date)
      assert dates == Enum.sort(dates, {:desc, Date})
    end
  end

  describe "head_to_head/3" do
    test "summarises wins, draws, and the matches", %{matches: ms} do
      h2h = Matches.head_to_head(ms, "Flamengo", "Fluminense")
      assert h2h.team_a == "Flamengo"
      assert h2h.team_b == "Fluminense"
      assert h2h.a_wins == 2
      assert h2h.b_wins == 1
      assert h2h.draws == 0
      assert length(h2h.matches) == 3
    end
  end
end
