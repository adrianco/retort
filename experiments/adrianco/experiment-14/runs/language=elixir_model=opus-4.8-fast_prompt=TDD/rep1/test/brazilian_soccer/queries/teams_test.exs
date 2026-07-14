defmodule BrazilianSoccer.Queries.TeamsTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.Queries.Teams

  setup do
    {:ok, dataset: BrazilianSoccer.Fixtures.dataset()}
  end

  describe "record/3" do
    test "computes an overall season record", %{dataset: ds} do
      r = Teams.record(ds, "Flamengo", season: 2023)

      assert r.team == "Flamengo"
      assert r.played == 5
      assert r.wins == 2
      assert r.draws == 1
      assert r.losses == 2
      assert r.goals_for == 5
      assert r.goals_against == 5
      assert r.goal_difference == 0
      assert_in_delta r.win_rate, 0.40, 0.001
    end

    test "filters by venue", %{dataset: ds} do
      r = Teams.record(ds, "Flamengo", season: 2023, venue: :home)

      assert r.played == 3
      assert r.wins == 2
      assert r.draws == 1
      assert r.losses == 0
      assert r.goals_for == 4
      assert r.goals_against == 1
    end

    test "filters by competition", %{dataset: ds} do
      r = Teams.record(ds, "Flamengo", season: 2023, competition: "Brasileirão")
      assert r.played == 4
      assert r.wins == 1
    end
  end

  describe "compare/3" do
    test "returns records for both teams and their head-to-head", %{dataset: ds} do
      cmp = Teams.compare(ds, "Flamengo", "Fluminense")

      assert cmp.team_a.team == "Flamengo"
      assert cmp.team_b.team == "Fluminense"
      assert cmp.head_to_head.total == 3
    end
  end
end
