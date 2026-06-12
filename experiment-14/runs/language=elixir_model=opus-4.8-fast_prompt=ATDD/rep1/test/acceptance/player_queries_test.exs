defmodule BrazilianSoccer.Acceptance.PlayerQueriesTest do
  @moduledoc """
  Category 3: Player Queries. Search by name, nationality, club and position
  through the `search_players` and `get_player` MCP tools.
  """
  use ExUnit.Case, async: true

  alias BrazilianSoccer.Test.MCPClient

  test "look up a single player by name" do
    result = MCPClient.call("get_player", %{"name" => "Neymar"})

    assert result["found"] == true
    assert result["player"]["name"] =~ "Neymar"
    assert result["player"]["nationality"] == "Brazil"
    assert is_integer(result["player"]["overall"])
  end

  test "find all Brazilian players in the dataset" do
    result = MCPClient.call("search_players", %{"nationality" => "Brazil", "limit" => 5000})

    assert result["count"] > 100
    assert Enum.all?(result["players"], &(&1["nationality"] == "Brazil"))
  end

  test "find the highest-rated players, sorted by overall rating" do
    result =
      MCPClient.call("search_players", %{"nationality" => "Brazil", "limit" => 10})

    overalls = Enum.map(result["players"], & &1["overall"])
    assert overalls == Enum.sort(overalls, :desc)
    # The top Brazilian in this FIFA dataset is Neymar.
    assert hd(result["players"])["name"] =~ "Neymar"
  end

  test "filter players by club" do
    result = MCPClient.call("search_players", %{"club" => "Santos", "limit" => 100})

    assert result["count"] > 0
    assert Enum.all?(result["players"], &String.contains?(&1["club"], "Santos"))
  end

  test "filter players by position" do
    result =
      MCPClient.call("search_players", %{
        "club" => "Santos",
        "position" => "GK",
        "limit" => 100
      })

    assert result["count"] > 0
    assert Enum.all?(result["players"], &(&1["position"] == "GK"))
  end

  test "a minimum-rating filter excludes lower-rated players" do
    result = MCPClient.call("search_players", %{"min_overall" => 88, "limit" => 100})

    assert result["count"] > 0
    assert Enum.all?(result["players"], &(&1["overall"] >= 88))
  end

  test "looking up a player who is not in the dataset reports not found" do
    result = MCPClient.call("get_player", %{"name" => "Some Unknown Person 12345"})
    assert result["found"] == false
  end
end
