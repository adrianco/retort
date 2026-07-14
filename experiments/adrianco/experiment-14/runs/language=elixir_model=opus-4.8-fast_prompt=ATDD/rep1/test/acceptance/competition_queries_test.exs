defmodule BrazilianSoccer.Acceptance.CompetitionQueriesTest do
  @moduledoc """
  Category 4: Competition Queries. League standings calculated from match
  results, and the list of competitions a club has appeared in.
  """
  use ExUnit.Case, async: true

  alias BrazilianSoccer.Test.MCPClient

  test "the 2019 Brasileirão standings crown Flamengo as champion" do
    result =
      MCPClient.call("competition_standings", %{
        "competition" => "Brasileirão",
        "season" => 2019
      })

    standings = result["standings"]
    # A 20-team double round-robin: 20 teams, 38 games each.
    assert length(standings) == 20

    champion = hd(standings)
    assert champion["position"] == 1
    assert champion["team"] =~ "Flamengo"
    assert champion["points"] == 90
    assert champion["played"] == 38

    # Points must be ordered descending down the table.
    points = Enum.map(standings, & &1["points"])
    assert points == Enum.sort(points, :desc)

    # Each row is internally consistent.
    Enum.each(standings, fn row ->
      assert row["played"] == row["wins"] + row["draws"] + row["losses"]
      assert row["points"] == row["wins"] * 3 + row["draws"]
      assert row["goal_difference"] == row["goals_for"] - row["goals_against"]
    end)
  end

  test "standings positions are dense and start at 1" do
    result =
      MCPClient.call("competition_standings", %{
        "competition" => "Brasileirão",
        "season" => 2018
      })

    positions = Enum.map(result["standings"], & &1["position"])
    assert positions == Enum.to_list(1..length(positions))
  end

  test "list the competitions a club has played in" do
    result = MCPClient.call("list_competitions", %{"team" => "Palmeiras"})

    comps = result["competitions"]
    assert "Brasileirão" in comps
    assert "Copa Libertadores" in comps
  end

  test "list all competitions known to the server" do
    result = MCPClient.call("list_competitions", %{})

    assert "Brasileirão" in result["competitions"]
    assert "Copa do Brasil" in result["competitions"]
    assert "Copa Libertadores" in result["competitions"]
  end
end
