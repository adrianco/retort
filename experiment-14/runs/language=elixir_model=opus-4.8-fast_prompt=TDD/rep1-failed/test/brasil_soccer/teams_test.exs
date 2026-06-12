defmodule BrasilSoccer.TeamsTest do
  use ExUnit.Case, async: true

  alias BrasilSoccer.Teams
  alias BrasilSoccer.Fixtures

  setup do
    {:ok, matches: Fixtures.matches()}
  end

  describe "record/3" do
    test "tallies wins, draws, losses, and goals for a team", %{matches: ms} do
      rec = Teams.record(ms, "Flamengo")
      assert rec.team == "Flamengo"
      assert rec.played == 5
      assert rec.wins == 2
      assert rec.draws == 1
      assert rec.losses == 2
      assert rec.goals_for == 2 + 0 + 2 + 0 + 1
      assert rec.goals_against == 1 + 1 + 0 + 3 + 1
    end

    test "win_rate is wins over games played as a percentage", %{matches: ms} do
      rec = Teams.record(ms, "Flamengo")
      assert_in_delta rec.win_rate, 40.0, 0.001
    end

    test "can be scoped to home games only", %{matches: ms} do
      rec = Teams.record(ms, "Flamengo", home: "Flamengo")
      assert rec.played == 3
      assert rec.wins == 2
    end

    test "can be scoped by season", %{matches: ms} do
      rec = Teams.record(ms, "Flamengo", season: 2022)
      assert rec.played == 1
      assert rec.losses == 1
    end

    test "an unknown team yields an empty record", %{matches: ms} do
      rec = Teams.record(ms, "Chapecoense")
      assert rec.played == 0
      assert rec.win_rate == 0.0
    end
  end

  describe "compare/3" do
    test "returns the head-to-head plus each team's record", %{matches: ms} do
      cmp = Teams.compare(ms, "Flamengo", "Fluminense")
      assert cmp.head_to_head.a_wins == 2
      assert cmp.record_a.team == "Flamengo"
      assert cmp.record_b.team == "Fluminense"
    end
  end
end
