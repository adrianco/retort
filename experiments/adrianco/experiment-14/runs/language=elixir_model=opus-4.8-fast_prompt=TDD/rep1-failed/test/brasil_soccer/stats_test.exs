defmodule BrasilSoccer.StatsTest do
  use ExUnit.Case, async: true

  alias BrasilSoccer.Stats
  alias BrasilSoccer.Fixtures

  setup do
    {:ok, matches: Fixtures.matches()}
  end

  describe "summary/2" do
    test "computes counts, average goals, and outcome rates", %{matches: ms} do
      s = Stats.summary(ms)
      assert s.matches == 7
      assert s.total_goals == 17
      assert_in_delta s.avg_goals, 2.43, 0.01
      assert s.home_wins == 4
      assert s.away_wins == 1
      assert s.draws == 2
      assert_in_delta s.home_win_rate, 57.1, 0.1
    end

    test "can be scoped by competition", %{matches: ms} do
      s = Stats.summary(ms, competition: "Copa do Brasil")
      assert s.matches == 1
    end
  end

  describe "biggest_wins/2" do
    test "returns matches ordered by goal margin descending", %{matches: ms} do
      [top | _] = Stats.biggest_wins(ms, limit: 3)
      assert top.home_team == "Palmeiras"
      assert top.home_goal - top.away_goal == 4
    end

    test "respects the limit", %{matches: ms} do
      assert Stats.biggest_wins(ms, limit: 2) |> length() == 2
    end
  end

  describe "top_scoring_teams/2" do
    test "ranks teams by goals scored", %{matches: ms} do
      [leader | _] = Stats.top_scoring_teams(ms, limit: 3)
      assert leader.goals_for >= Enum.at(Stats.top_scoring_teams(ms), 1).goals_for
    end
  end
end
