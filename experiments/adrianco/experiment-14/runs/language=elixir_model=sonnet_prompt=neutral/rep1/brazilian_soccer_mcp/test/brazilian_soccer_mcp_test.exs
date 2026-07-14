defmodule BrazilianSoccerMcpTest do
  use ExUnit.Case

  alias BrazilianSoccerMcp.TeamNormalizer
  alias BrazilianSoccerMcp.QueryEngine
  alias BrazilianSoccerMcp.Tools

  # ─── TeamNormalizer Tests ────────────────────────────────────────────────────

  describe "TeamNormalizer.normalize/1" do
    test "removes state suffix with dash" do
      assert TeamNormalizer.normalize("Palmeiras-SP") == "Palmeiras"
      assert TeamNormalizer.normalize("Flamengo-RJ") == "Flamengo"
      assert TeamNormalizer.normalize("Sport-PE") == "Sport"
    end

    test "removes state suffix with space-dash" do
      assert TeamNormalizer.normalize("América - MG") == "América"
      assert TeamNormalizer.normalize("Grêmio - RS") == "Grêmio"
    end

    test "removes parenthetical notes" do
      name = "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
      assert TeamNormalizer.normalize(name) == "Boavista Sport Club"
    end

    test "handles plain names without suffix" do
      assert TeamNormalizer.normalize("Flamengo") == "Flamengo"
      assert TeamNormalizer.normalize("Corinthians") == "Corinthians"
    end

    test "trims whitespace" do
      assert TeamNormalizer.normalize("  Palmeiras  ") == "Palmeiras"
    end
  end

  describe "TeamNormalizer.matches?/2" do
    test "matches exact name" do
      assert TeamNormalizer.matches?("Flamengo-RJ", "Flamengo")
    end

    test "matches partial name" do
      assert TeamNormalizer.matches?("Atletico Mineiro", "Atletico")
    end

    test "is case insensitive" do
      assert TeamNormalizer.matches?("Palmeiras-SP", "palmeiras")
      assert TeamNormalizer.matches?("Flamengo-RJ", "FLAMENGO")
    end

    test "matches with accents" do
      assert TeamNormalizer.matches?("Grêmio", "Gremio")
    end

    test "does not match wrong team" do
      refute TeamNormalizer.matches?("Flamengo-RJ", "Palmeiras")
    end
  end

  # ─── QueryEngine Tests (require DataStore to be running) ─────────────────────

  describe "QueryEngine.search_matches/1" do
    test "returns results for Flamengo" do
      result = QueryEngine.search_matches(%{"team" => "Flamengo", "limit" => 5})
      assert is_binary(result)
      assert String.contains?(result, "Flamengo") or String.contains?(result, "No matches")
    end

    test "filters by season" do
      result = QueryEngine.search_matches(%{"competition" => "brasileirao", "season" => 2023})
      assert is_binary(result)
    end

    test "filters by competition" do
      result = QueryEngine.search_matches(%{"competition" => "libertadores", "limit" => 5})
      assert is_binary(result)
      refute result == ""
    end

    test "returns no matches for unknown team" do
      result = QueryEngine.search_matches(%{"team" => "XYZ_NONEXISTENT_CLUB_999"})
      assert String.contains?(result, "No matches found")
    end

    test "head to head search" do
      result = QueryEngine.search_matches(%{
        "home_team" => "Flamengo",
        "away_team" => "Fluminense"
      })
      assert is_binary(result)
    end
  end

  describe "QueryEngine.get_team_stats/1" do
    test "returns stats for Flamengo" do
      result = QueryEngine.get_team_stats(%{"team" => "Flamengo"})
      assert is_binary(result)
      assert String.contains?(result, "Flamengo")
      assert String.contains?(result, "Matches played")
    end

    test "returns stats for Palmeiras" do
      result = QueryEngine.get_team_stats(%{"team" => "Palmeiras"})
      assert is_binary(result)
      assert String.contains?(result, "Palmeiras")
    end

    test "filters by competition and season" do
      result = QueryEngine.get_team_stats(%{
        "team" => "Corinthians",
        "competition" => "brasileirao",
        "season" => 2022
      })
      assert is_binary(result)
    end

    test "returns error without team" do
      result = QueryEngine.get_team_stats(%{})
      assert String.contains?(result, "Error")
    end

    test "returns not found for unknown team" do
      result = QueryEngine.get_team_stats(%{"team" => "XYZ_NONEXISTENT_999"})
      assert String.contains?(result, "No matches found")
    end
  end

  describe "QueryEngine.head_to_head/1" do
    test "returns h2h record for Flamengo vs Fluminense" do
      result = QueryEngine.head_to_head(%{"team1" => "Flamengo", "team2" => "Fluminense"})
      assert is_binary(result)
      assert String.contains?(result, "Flamengo") or String.contains?(result, "No matches")
    end

    test "returns error without teams" do
      result = QueryEngine.head_to_head(%{})
      assert String.contains?(result, "Error")
    end

    test "returns h2h for Palmeiras vs Santos" do
      result = QueryEngine.head_to_head(%{"team1" => "Palmeiras", "team2" => "Santos"})
      assert is_binary(result)
    end
  end

  describe "QueryEngine.search_players/1" do
    test "finds players by nationality Brazil" do
      result = QueryEngine.search_players(%{"nationality" => "Brazil", "limit" => 5})
      assert is_binary(result)
      assert String.contains?(result, "Brazil") or String.contains?(result, "players")
    end

    test "finds players by name" do
      result = QueryEngine.search_players(%{"name" => "Neymar"})
      assert is_binary(result)
      assert String.contains?(result, "Neymar") or String.contains?(result, "No players")
    end

    test "finds players by club" do
      result = QueryEngine.search_players(%{"club" => "Flamengo", "limit" => 5})
      assert is_binary(result)
    end

    test "finds goalkeepers" do
      result = QueryEngine.search_players(%{"position" => "GK", "limit" => 5})
      assert is_binary(result)
    end

    test "returns no players for nonsense search" do
      result = QueryEngine.search_players(%{"name" => "XYZ_NOBODY_999"})
      assert String.contains?(result, "No players found")
    end
  end

  describe "QueryEngine.get_standings/1" do
    test "calculates 2019 Brasileirão standings" do
      result = QueryEngine.get_standings(%{"season" => 2019, "competition" => "brasileirao"})
      assert is_binary(result)
      assert String.contains?(result, "2019") or String.contains?(result, "No match data")
    end

    test "calculates 2023 standings" do
      result = QueryEngine.get_standings(%{"season" => 2023})
      assert is_binary(result)
    end

    test "returns error without season" do
      result = QueryEngine.get_standings(%{})
      assert String.contains?(result, "Error")
    end
  end

  describe "QueryEngine.get_biggest_wins/1" do
    test "returns biggest wins overall" do
      result = QueryEngine.get_biggest_wins(%{})
      assert is_binary(result)
      assert String.contains?(result, "Biggest wins")
    end

    test "returns biggest wins in brasileirao" do
      result = QueryEngine.get_biggest_wins(%{"competition" => "brasileirao", "limit" => 5})
      assert is_binary(result)
    end
  end

  describe "QueryEngine.get_summary_stats/1" do
    test "returns overall stats" do
      result = QueryEngine.get_summary_stats(%{})
      assert is_binary(result)
      assert String.contains?(result, "Total matches")
      assert String.contains?(result, "Average goals")
    end

    test "returns stats filtered by competition" do
      result = QueryEngine.get_summary_stats(%{"competition" => "brasileirao"})
      assert is_binary(result)
      assert String.contains?(result, "Total matches")
    end
  end

  # ─── Tools Tests ─────────────────────────────────────────────────────────────

  describe "Tools.list_tools/0" do
    test "returns all 7 tools" do
      tools = Tools.list_tools()
      assert length(tools) == 7
    end

    test "all tools have required fields" do
      tools = Tools.list_tools()
      for tool <- tools do
        assert Map.has_key?(tool, :name)
        assert Map.has_key?(tool, :description)
        assert Map.has_key?(tool, :inputSchema)
      end
    end

    test "tool names match expected set" do
      names = Tools.list_tools() |> Enum.map(& &1.name) |> MapSet.new()
      expected = MapSet.new([
        "search_matches", "get_team_stats", "head_to_head",
        "search_players", "get_standings", "get_biggest_wins", "get_summary_stats"
      ])
      assert names == expected
    end
  end

  describe "Tools.call_tool/2" do
    test "dispatches search_matches" do
      result = Tools.call_tool("search_matches", %{"team" => "Flamengo", "limit" => 3})
      assert is_binary(result)
    end

    test "dispatches search_players" do
      result = Tools.call_tool("search_players", %{"nationality" => "Brazil", "limit" => 3})
      assert is_binary(result)
    end

    test "returns error for unknown tool" do
      result = Tools.call_tool("nonexistent_tool", %{})
      assert {:error, _} = result
    end
  end

  # ─── Data Loading Tests ──────────────────────────────────────────────────────

  describe "DataStore" do
    test "brasileirao matches are loaded" do
      matches = BrazilianSoccerMcp.DataStore.get_brasileirao()
      assert length(matches) > 0
      [first | _] = matches
      assert first.competition == :brasileirao
      assert is_binary(first.home_team)
      assert is_binary(first.away_team)
    end

    test "copa brasil matches are loaded" do
      matches = BrazilianSoccerMcp.DataStore.get_copa_brasil()
      assert length(matches) > 0
      assert Enum.all?(matches, &(&1.competition == :copa_brasil))
    end

    test "libertadores matches are loaded" do
      matches = BrazilianSoccerMcp.DataStore.get_libertadores()
      assert length(matches) > 0
      assert Enum.all?(matches, &(&1.competition == :libertadores))
    end

    test "extended matches are loaded" do
      matches = BrazilianSoccerMcp.DataStore.get_extended()
      assert length(matches) > 0
      assert Enum.all?(matches, &(&1.competition == :extended))
    end

    test "historical matches are loaded" do
      matches = BrazilianSoccerMcp.DataStore.get_historical()
      assert length(matches) > 0
      assert Enum.all?(matches, &(&1.competition == :historical))
    end

    test "players are loaded" do
      players = BrazilianSoccerMcp.DataStore.get_players()
      assert length(players) > 0
      [first | _] = players
      assert is_binary(first.name)
      assert is_binary(first.nationality)
    end

    test "all_matches combines all competitions" do
      all = BrazilianSoccerMcp.DataStore.get_all_matches()
      brasileirao = BrazilianSoccerMcp.DataStore.get_brasileirao()
      copa = BrazilianSoccerMcp.DataStore.get_copa_brasil()
      assert length(all) >= length(brasileirao) + length(copa)
    end

    test "match data has valid scores" do
      matches = BrazilianSoccerMcp.DataStore.get_brasileirao()
      valid = Enum.reject(matches, &(is_nil(&1.home_goal) or is_nil(&1.away_goal)))
      assert length(valid) > 0
      assert Enum.all?(valid, &(&1.home_goal >= 0 and &1.away_goal >= 0))
    end

    test "dates are parsed to ISO format" do
      matches = BrazilianSoccerMcp.DataStore.get_brasileirao()
      dates = matches |> Enum.map(& &1.datetime) |> Enum.reject(&is_nil/1) |> Enum.take(5)
      for date <- dates do
        assert Regex.match?(~r/^\d{4}-\d{2}-\d{2}/, date)
      end
    end
  end
end
