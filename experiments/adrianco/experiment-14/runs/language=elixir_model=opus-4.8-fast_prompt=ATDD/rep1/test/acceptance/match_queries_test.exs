defmodule BrazilianSoccer.Acceptance.MatchQueriesTest do
  @moduledoc """
  Category 1: Match Queries. Find matches by team, opponent, competition and
  season — exercised entirely through the `find_matches` MCP tool.
  """
  use ExUnit.Case, async: true

  alias BrazilianSoccer.Test.MCPClient

  test "find all matches between two teams (the Fla-Flu derby)" do
    result = MCPClient.call("find_matches", %{"team" => "Flamengo", "opponent" => "Fluminense"})

    assert result["count"] > 0

    Enum.each(result["matches"], fn m ->
      teams = [m["home_team"], m["away_team"]] |> Enum.map(&String.downcase/1)
      assert Enum.any?(teams, &String.contains?(&1, "flamengo"))
      assert Enum.any?(teams, &String.contains?(&1, "fluminense"))
    end)
  end

  test "find the matches a team played in a given season" do
    result = MCPClient.call("find_matches", %{"team" => "Palmeiras", "season" => 2023})

    assert result["count"] > 0

    Enum.each(result["matches"], fn m ->
      assert m["season"] == 2023
      teams = [m["home_team"], m["away_team"]] |> Enum.map(&String.downcase/1)
      assert Enum.any?(teams, &String.contains?(&1, "palmeiras"))
    end)
  end

  test "find matches filtered by competition" do
    result = MCPClient.call("find_matches", %{"team" => "Flamengo", "competition" => "Libertadores"})

    assert result["count"] > 0
    assert Enum.all?(result["matches"], &(&1["competition"] =~ "Libertadores"))
  end

  test "team name variations (state suffix) resolve to the same club" do
    # "Palmeiras" (query) must match rows stored as "Palmeiras-SP".
    result = MCPClient.call("find_matches", %{"team" => "Palmeiras", "season" => 2019})

    assert result["count"] > 0

    assert Enum.any?(result["matches"], fn m ->
             m["home_team"] =~ "Palmeiras" or m["away_team"] =~ "Palmeiras"
           end)
  end

  test "each returned match reports the score and the date" do
    result = MCPClient.call("find_matches", %{"team" => "Santos", "opponent" => "Palmeiras"})

    assert result["count"] > 0
    m = hd(result["matches"])
    assert is_integer(m["home_goal"])
    assert is_integer(m["away_goal"])
    assert m["date"] != nil
  end

  test "querying an unknown team returns no matches rather than an error" do
    result = MCPClient.call("find_matches", %{"team" => "Nonexistent United FC"})
    assert result["count"] == 0
    assert result["matches"] == []
  end
end
