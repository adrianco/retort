defmodule BrazilianSoccer.Acceptance.TeamQueriesTest do
  @moduledoc """
  Category 2: Team Queries. Win/loss/draw records, goals for/against, and
  head-to-head comparison via the `team_record` and `head_to_head` MCP tools.
  """
  use ExUnit.Case, async: true

  alias BrazilianSoccer.Test.MCPClient

  test "a team's home record for a season is internally consistent" do
    result =
      MCPClient.call("team_record", %{
        "team" => "Corinthians",
        "season" => 2019,
        "competition" => "Brasileirão",
        "venue" => "home"
      })

    assert result["matches"] == result["wins"] + result["draws"] + result["losses"]
    assert result["matches"] > 0
    assert result["wins"] >= 0 and result["draws"] >= 0 and result["losses"] >= 0
    assert result["goals_for"] >= 0 and result["goals_against"] >= 0
    assert_in_delta result["win_rate"], result["wins"] / result["matches"] * 100, 0.1
  end

  test "a full-season record equals home plus away records" do
    args = %{"team" => "Flamengo", "season" => 2019, "competition" => "Brasileirão"}
    home = MCPClient.call("team_record", Map.put(args, "venue", "home"))
    away = MCPClient.call("team_record", Map.put(args, "venue", "away"))
    all = MCPClient.call("team_record", Map.put(args, "venue", "all"))

    assert all["matches"] == home["matches"] + away["matches"]
    assert all["wins"] == home["wins"] + away["wins"]
    assert all["goals_for"] == home["goals_for"] + away["goals_for"]
  end

  test "compare two teams head-to-head" do
    result = MCPClient.call("head_to_head", %{"team1" => "Palmeiras", "team2" => "Santos"})

    assert result["total_matches"] > 0
    assert result["total_matches"] ==
             result["team1_wins"] + result["team2_wins"] + result["draws"]

    # The two clubs named back must be the ones reported.
    assert String.downcase(result["team1"]) =~ "palmeiras"
    assert String.downcase(result["team2"]) =~ "santos"
  end

  test "head-to-head is symmetric when the teams are swapped" do
    ab = MCPClient.call("head_to_head", %{"team1" => "Flamengo", "team2" => "Fluminense"})
    ba = MCPClient.call("head_to_head", %{"team1" => "Fluminense", "team2" => "Flamengo"})

    assert ab["total_matches"] == ba["total_matches"]
    assert ab["draws"] == ba["draws"]
    assert ab["team1_wins"] == ba["team2_wins"]
    assert ab["team2_wins"] == ba["team1_wins"]
  end
end
