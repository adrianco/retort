defmodule BrazilianSoccerMcpTest do
  use ExUnit.Case, async: false
  alias BrazilianSoccerMcp.Query

  setup_all do
    BrazilianSoccerMcp.load()
    :ok
  end

  test "loads all datasets and normalizes state suffixes and accents" do
    assert length(BrazilianSoccerMcp.matches()) > 16_000
    assert BrazilianSoccerMcp.matches(%{team: "Flamengo"}) != []
    assert Query.normalize("São Paulo-SP") == Query.normalize("Sao Paulo")
  end

  test "searches players and sorts them by rating" do
    players = BrazilianSoccerMcp.players(%{nationality: "Brazil"})
    assert players != []
    assert Enum.all?(players, &(&1.nationality == "Brazil"))
    assert Enum.sort_by(players, & &1.overall, :desc) == players
  end

  test "calculates a team's record and aggregated statistics" do
    record = BrazilianSoccerMcp.team_stats("Flamengo", %{season: 2023})
    assert record.matches > 0
    assert record.matches == record.wins + record.draws + record.losses
    assert BrazilianSoccerMcp.aggregate(%{competition: "Brasileirao"}).average_goals > 0
  end

  test "returns head to head and standings" do
    comparison = BrazilianSoccerMcp.head_to_head("Flamengo", "Fluminense")
    assert length(comparison.matches) > 0

    assert comparison.record.first_wins + comparison.record.second_wins + comparison.record.draws ==
             length(comparison.matches)

    assert BrazilianSoccerMcp.standings(2019) != []
  end

  test "declares an executable MCP server entrypoint" do
    assert BrazilianSoccerMcp.MixProject.project()[:escript] ==
             [main_module: BrazilianSoccerMcp.Server]
  end
end
