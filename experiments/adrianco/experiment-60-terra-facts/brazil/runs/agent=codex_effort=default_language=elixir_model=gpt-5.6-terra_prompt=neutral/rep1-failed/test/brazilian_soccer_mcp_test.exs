defmodule BrazilianSoccerMcpTest do
  use ExUnit.Case, async: true
  alias BrazilianSoccerMcp.{CSV, Catalog, JSON, MCP, Query}

  # BDD: Given a normalized soccer catalog, when a team variant is searched,
  # then the state suffix and accent differences resolve to the same team.
  test "finds matches across normalized team-name variants" do
    catalog = catalog()
    matches = Query.matches(catalog, %{"team" => "São Paulo-SP"})
    assert length(matches) == 3
    assert Enum.any?(matches, &(&1.home == "Sao Paulo"))
  end

  # BDD: Given results for a team, when its home record is requested,
  # then wins, draws, losses, and goals are calculated from its home matches only.
  test "calculates a team home record" do
    stats = Query.team_statistics(catalog(), "Sao Paulo", %{"venue" => "home"})

    assert stats == %{
             team: "Sao Paulo",
             matches: 1,
             wins: 1,
             draws: 0,
             losses: 0,
             goals_for: 2,
             goals_against: 0,
             points: 3,
             win_rate: 100.0
           }
  end

  # BDD: Given two teams, when head-to-head is requested, then both directions are included.
  test "compares teams head to head" do
    result = Query.head_to_head(catalog(), "Sao Paulo", "Flamengo")
    assert length(result.matches) == 3
    assert result.first.wins == 2
    assert result.second.wins == 1
    assert result.draws == 0
  end

  # BDD: Given player records, when nationality and position are filtered,
  # then only matching players are returned in rating order.
  test "searches and sorts players" do
    [player] = Query.players(catalog(), %{"nationality" => "Brazil", "position" => "ST"})
    assert player.name == "Gabriel"
  end

  test "calculates standings and aggregate competition statistics" do
    standings = Query.standings(catalog(), 2023, "Brasileirão")
    assert [%{team: "Sao Paulo", rank: 1, points: 6} | _] = standings

    assert %{matches: 3, average_goals: 2.67, home_wins: 2, away_wins: 1} =
             Query.competition_statistics(catalog(), %{"competition" => "Brasileirão"})
  end

  test "CSV reader accepts quoted commas and JSON round-trips MCP-shaped values" do
    assert CSV.parse("name,club\n\"João, Jr.\",Flamengo\n") == [
             ["name", "club"],
             ["João, Jr.", "Flamengo"]
           ]

    payload = %{"jsonrpc" => "2.0", "id" => 1, "params" => %{"team" => "São Paulo"}}
    assert {:ok, ^payload} = payload |> JSON.encode() |> JSON.decode()
  end

  test "MCP advertises its soccer tools after initialization" do
    assert %{"result" => %{"protocolVersion" => "2024-11-05"}} =
             MCP.handle(%{"method" => "initialize", "id" => 1})

    assert %{"result" => %{"tools" => tools}} = MCP.handle(%{"method" => "tools/list", "id" => 2})
    assert Enum.any?(tools, &(&1["name"] == "search_matches"))
    assert Enum.any?(tools, &(&1["name"] == "search_players"))
  end

  test "loads all six supplied Kaggle CSV datasets" do
    assert {:ok, loaded} = Catalog.load(Path.expand("data/kaggle", File.cwd!()))
    assert length(loaded.players) == 18_207
    assert length(loaded.matches) == 23_954
    assert loaded.matches |> Enum.map(& &1.source) |> Enum.uniq() |> length() == 5
  end

  defp catalog do
    %Catalog{
      matches: [
        match("2023-09-24", "Sao Paulo", "Flamengo", 2, 0),
        match("2023-05-10", "Flamengo-RJ", "São Paulo-SP", 1, 2),
        match("2023-04-10", "Flamengo-RJ", "São Paulo-SP", 2, 1)
      ],
      players: [
        %{
          id: "1",
          name: "Gabriel",
          name_key: "gabriel",
          nationality: "Brazil",
          club: "Flamengo",
          club_key: "flamengo",
          position: "ST",
          overall: 80,
          potential: 84,
          age: 25
        },
        %{
          id: "2",
          name: "Other",
          name_key: "other",
          nationality: "Brazil",
          club: "Flamengo",
          club_key: "flamengo",
          position: "GK",
          overall: 90,
          potential: 90,
          age: 30
        }
      ]
    }
  end

  defp match(date, home, away, home_goals, away_goals),
    do: %{
      date: date,
      home: home,
      away: away,
      home_key: Catalog.team_key(home),
      away_key: Catalog.team_key(away),
      home_goals: home_goals,
      away_goals: away_goals,
      season: 2023,
      competition: "Brasileirão",
      round: nil,
      stage: nil,
      source: "test",
      extras: %{}
    }
end
