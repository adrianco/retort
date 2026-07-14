defmodule BrazilianSoccer.Acceptance.StatisticsTest do
  @moduledoc """
  Category 5: Statistical Analysis. Goals-per-match averages, home/away win
  rates and the biggest victories, via the `competition_statistics` tool.
  """
  use ExUnit.Case, async: true

  alias BrazilianSoccer.Test.MCPClient

  test "average goals per match for a season is a plausible football figure" do
    result =
      MCPClient.call("competition_statistics", %{
        "competition" => "Brasileirão",
        "season" => 2019
      })

    assert result["matches"] == 380
    assert result["avg_goals_per_match"] > 1.5 and result["avg_goals_per_match"] < 4.0

    assert_in_delta result["avg_goals_per_match"],
                    result["total_goals"] / result["matches"],
                    0.01
  end

  test "win-rate proportions add up to one" do
    result =
      MCPClient.call("competition_statistics", %{
        "competition" => "Brasileirão",
        "season" => 2019
      })

    total =
      result["home_win_rate"] + result["away_win_rate"] + result["draw_rate"]

    assert_in_delta total, 1.0, 0.001
    assert result["home_win_rate"] > result["away_win_rate"]
  end

  test "the biggest wins are ordered by goal margin" do
    result =
      MCPClient.call("competition_statistics", %{
        "competition" => "Brasileirão",
        "season" => 2019,
        "biggest_wins_limit" => 5
      })

    wins = result["biggest_wins"]
    assert length(wins) == 5

    margins = Enum.map(wins, &abs(&1["home_goal"] - &1["away_goal"]))
    assert margins == Enum.sort(margins, :desc)
    # The single most lopsided result of the season had at least a 4-goal margin.
    assert hd(margins) >= 4
  end

  test "statistics can be aggregated across a whole competition (all seasons)" do
    result = MCPClient.call("competition_statistics", %{"competition" => "Brasileirão"})

    assert result["matches"] > 380
    assert result["avg_goals_per_match"] > 1.5 and result["avg_goals_per_match"] < 4.0
  end
end
