defmodule BrazilianSoccer.Queries.StatsTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.Queries.Stats

  setup do
    {:ok, dataset: BrazilianSoccer.Fixtures.dataset()}
  end

  describe "summary/2" do
    test "computes averages and outcome rates", %{dataset: ds} do
      s = Stats.summary(ds)

      assert s.matches == 6
      assert_in_delta s.avg_goals_per_match, 2.0, 0.001
      assert_in_delta s.home_win_rate, 4 / 6, 0.001
      assert_in_delta s.draw_rate, 2 / 6, 0.001
      assert_in_delta s.away_win_rate, 0.0, 0.001
    end

    test "can be scoped to a competition", %{dataset: ds} do
      s = Stats.summary(ds, competition: "Copa do Brasil")
      assert s.matches == 1
    end
  end

  describe "biggest_wins/2" do
    test "ranks matches by goal margin", %{dataset: ds} do
      [top | _] = Stats.biggest_wins(ds, limit: 1)
      assert top.home_team == "Palmeiras"
      assert top.home_goals - top.away_goals == 2
    end
  end

  describe "best_record/3" do
    test "ranks teams by win rate with a minimum-match threshold", %{dataset: ds} do
      [best | _] = Stats.best_record(ds, :home, min_matches: 2)
      assert best.team == "Flamengo"
      assert best.played == 4
    end
  end
end
