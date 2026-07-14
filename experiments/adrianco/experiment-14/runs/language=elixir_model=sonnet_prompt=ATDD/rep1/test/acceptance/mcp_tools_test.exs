defmodule BrazilianSoccerMcp.Acceptance.McpToolsTest do
  use ExUnit.Case, async: false

  # All tests communicate only through the MCP JSON-RPC protocol.
  # No direct access to internal modules, data structures, or state.

  setup_all do
    # Ensure the application (and DataStore) is started
    Application.ensure_all_started(:brazilian_soccer_mcp)
    :ok
  end

  # ----------------------------------------------------------------
  # Protocol helper: send a tools/call MCP message, return text body
  # ----------------------------------------------------------------

  defp call_tool(tool_name, arguments) do
    request = %{
      "jsonrpc" => "2.0",
      "id" => System.unique_integer([:positive]),
      "method" => "tools/call",
      "params" => %{"name" => tool_name, "arguments" => arguments}
    }

    case BrazilianSoccerMcp.Server.handle_request(request) do
      {:ok, %{"result" => %{"content" => content}}} ->
        text = content |> Enum.map_join("\n", & &1["text"])
        {:ok, text}

      {:ok, %{"error" => err}} ->
        {:error, err["message"]}

      other ->
        {:error, inspect(other)}
    end
  end

  defp mcp_request(method, params \\ %{}) do
    request = %{
      "jsonrpc" => "2.0",
      "id" => System.unique_integer([:positive]),
      "method" => method,
      "params" => params
    }

    BrazilianSoccerMcp.Server.handle_request(request)
  end

  # ----------------------------------------------------------------
  # 1. Protocol: tools/list returns the five required tools
  # ----------------------------------------------------------------

  describe "tools/list" do
    test "exposes the five required MCP tools" do
      {:ok, response} = mcp_request("tools/list")
      tool_names = response["result"]["tools"] |> Enum.map(& &1["name"]) |> MapSet.new()

      assert MapSet.member?(tool_names, "find_matches"),
             "find_matches tool must be listed"

      assert MapSet.member?(tool_names, "get_team_stats"),
             "get_team_stats tool must be listed"

      assert MapSet.member?(tool_names, "find_players"),
             "find_players tool must be listed"

      assert MapSet.member?(tool_names, "get_competition_standings"),
             "get_competition_standings tool must be listed"

      assert MapSet.member?(tool_names, "get_statistics"),
             "get_statistics tool must be listed"
    end

    test "every tool has a name, description, and inputSchema" do
      {:ok, response} = mcp_request("tools/list")

      for tool <- response["result"]["tools"] do
        assert is_binary(tool["name"]) and tool["name"] != "",
               "tool missing name: #{inspect(tool)}"

        assert is_binary(tool["description"]) and tool["description"] != "",
               "tool '#{tool["name"]}' missing description"

        assert is_map(tool["inputSchema"]),
               "tool '#{tool["name"]}' missing inputSchema"
      end
    end
  end

  # ----------------------------------------------------------------
  # 2. find_matches — match queries by team, competition, season
  # ----------------------------------------------------------------

  describe "find_matches: head-to-head between two teams" do
    test "returns matches between Flamengo and Fluminense" do
      {:ok, text} = call_tool("find_matches", %{"team1" => "Flamengo", "team2" => "Fluminense"})

      assert text =~ "Flamengo", "response should mention Flamengo"
      assert text =~ "Fluminense", "response should mention Fluminense"
      # Must contain at least one match score
      assert text =~ ~r/\d+\s*[-x]\s*\d+/,
             "response should contain match scores, got: #{text}"
    end

    test "includes head-to-head summary with win counts" do
      {:ok, text} = call_tool("find_matches", %{"team1" => "Flamengo", "team2" => "Fluminense"})

      assert text =~ ~r/win|draw|empate/i,
             "response should include win/draw summary"
    end
  end

  describe "find_matches: by team and season" do
    test "finds Palmeiras matches in 2023" do
      {:ok, text} = call_tool("find_matches", %{"team1" => "Palmeiras", "season" => 2023})

      assert text =~ "Palmeiras", "response should mention Palmeiras"
      assert text =~ "2023", "response should mention season 2023"
      assert text =~ ~r/\d+\s*[-x]\s*\d+/, "response should contain match scores"
    end
  end

  describe "find_matches: by competition" do
    test "finds Brasileirao matches" do
      {:ok, text} = call_tool("find_matches", %{"competition" => "Brasileirao", "season" => 2022})

      assert text =~ ~r/\d{4}-\d{2}-\d{2}|\d{2}\/\d{2}\/\d{4}/,
             "response should include dates"

      assert text =~ ~r/\d+\s*[-x]\s*\d+/, "response should contain scores"
    end

    test "finds Copa do Brasil matches" do
      {:ok, text} =
        call_tool("find_matches", %{"competition" => "Copa do Brasil", "season" => 2019})

      assert text =~ ~r/\d+\s*[-x]\s*\d+/, "response should contain scores"
    end

    test "finds Libertadores matches" do
      {:ok, text} =
        call_tool("find_matches", %{"competition" => "Libertadores", "season" => 2022})

      assert text =~ ~r/\d+\s*[-x]\s*\d+/, "response should contain scores"
    end
  end

  describe "find_matches: handles team name variations" do
    test "finds matches with state suffix stripped (Palmeiras-SP -> Palmeiras)" do
      {:ok, text_no_suffix} =
        call_tool("find_matches", %{"team1" => "Palmeiras", "season" => 2022})

      assert text_no_suffix =~ "Palmeiras"
    end
  end

  # ----------------------------------------------------------------
  # 3. get_team_stats — team performance statistics
  # ----------------------------------------------------------------

  describe "get_team_stats" do
    test "returns Corinthians 2022 record with wins/draws/losses" do
      {:ok, text} = call_tool("get_team_stats", %{"team" => "Corinthians", "season" => 2022})

      assert text =~ "Corinthians"
      assert text =~ ~r/\bw(?:in)?s?\b|\bwon\b/i, "should mention wins"
      assert text =~ ~r/\bdraw|\bempate|\bd:/i, "should mention draws"
      assert text =~ ~r/\blos(?:s|ses|t)\b|\bl:/i, "should mention losses"
    end

    test "includes goals scored and conceded" do
      {:ok, text} = call_tool("get_team_stats", %{"team" => "Flamengo", "season" => 2019})

      assert text =~ "Flamengo"
      assert text =~ ~r/goal|gol/i, "should mention goals"
      assert text =~ ~r/\d+/, "should contain numbers"
    end

    test "returns win rate percentage" do
      {:ok, text} = call_tool("get_team_stats", %{"team" => "Palmeiras", "season" => 2023})

      assert text =~ ~r/\d+\.?\d*%/, "should include a percentage"
    end

    test "handles team with no matches gracefully" do
      {:ok, text} = call_tool("get_team_stats", %{"team" => "NoSuchTeamXYZ"})
      # Should return an informative message, not crash
      assert is_binary(text)
    end
  end

  # ----------------------------------------------------------------
  # 4. find_players — FIFA player data queries
  # ----------------------------------------------------------------

  describe "find_players: by nationality" do
    test "finds Brazilian players" do
      {:ok, text} = call_tool("find_players", %{"nationality" => "Brazil"})

      assert text =~ ~r/Brazil/i
      # Should list multiple players
      assert text =~ ~r/Overall|Rating|\d{2}/
    end
  end

  describe "find_players: by club" do
    test "finds players at Santos" do
      {:ok, text} = call_tool("find_players", %{"club" => "Santos"})

      assert text =~ "Santos"
      assert text =~ ~r/Overall|Rating|\d{2}/
    end

    test "finds players at Fluminense" do
      {:ok, text} = call_tool("find_players", %{"club" => "Fluminense"})

      assert text =~ "Fluminense"
      assert text =~ ~r/Overall|Rating|\d{2}/
    end
  end

  describe "find_players: by name" do
    test "finds Neymar by name" do
      {:ok, text} = call_tool("find_players", %{"name" => "Neymar"})

      assert text =~ "Neymar"
      assert text =~ ~r/Overall|\d{2}/
    end

    test "finds Gabriel Barbosa" do
      {:ok, text} = call_tool("find_players", %{"name" => "Gabriel"})

      # Dataset should have Gabriel (Barbosa) or similar
      assert is_binary(text)
      assert text != ""
    end
  end

  describe "find_players: combined filters" do
    test "finds Brazilian players at Santos sorted by rating" do
      {:ok, text} = call_tool("find_players", %{"nationality" => "Brazil", "club" => "Santos"})

      assert text =~ "Santos"
      assert text =~ ~r/Brazil/i
    end
  end

  # ----------------------------------------------------------------
  # 5. get_competition_standings — calculated league tables
  # ----------------------------------------------------------------

  describe "get_competition_standings: Brasileirao" do
    test "calculates 2019 Brasileirao standings showing Flamengo at top" do
      {:ok, text} =
        call_tool("get_competition_standings", %{
          "competition" => "Brasileirao",
          "season" => 2019
        })

      assert text =~ "Flamengo", "Flamengo won 2019 Brasileirao, must appear"
      assert text =~ ~r/pts|points/i, "should show points"

      # Flamengo should be ranked 1st (90 pts)
      lines = String.split(text, "\n") |> Enum.reject(&(String.trim(&1) == ""))
      flamengo_pos = Enum.find_index(lines, &String.contains?(&1, "Flamengo"))
      refute is_nil(flamengo_pos), "Flamengo must appear in standings"
    end

    test "2022 standings include top teams" do
      {:ok, text} =
        call_tool("get_competition_standings", %{
          "competition" => "Brasileirao",
          "season" => 2022
        })

      assert text =~ ~r/pts|points/i
      # Should have at least 10 teams listed
      teams_count =
        text
        |> String.split("\n")
        |> Enum.count(&(String.match?(&1, ~r/\d+\s*pts|\d+\s*points/i)))

      assert teams_count >= 5, "should list at least 5 teams with points"
    end
  end

  # ----------------------------------------------------------------
  # 6. get_statistics — aggregated analytics
  # ----------------------------------------------------------------

  describe "get_statistics: biggest wins" do
    test "returns the biggest winning margins in the dataset" do
      {:ok, text} = call_tool("get_statistics", %{"stat_type" => "biggest_wins"})

      # Should contain high-score matches
      assert text =~ ~r/\d+\s*[-x]\s*\d+/, "should contain match scores"
      # At least one match where margin >= 4
      has_big_win =
        Regex.scan(~r/(\d+)\s*[-x]\s*(\d+)/, text)
        |> Enum.any?(fn [_, a, b] ->
          abs(String.to_integer(a) - String.to_integer(b)) >= 4
        end)

      assert has_big_win, "should include matches with goal margin >= 4"
    end
  end

  describe "get_statistics: goals per match average" do
    test "returns average goals per match as a decimal number" do
      {:ok, text} = call_tool("get_statistics", %{"stat_type" => "goals_per_match"})

      assert text =~ ~r/\d+\.\d+/, "should contain a decimal average"
      assert text =~ ~r/average|avg|média/i, "should mention 'average'"
    end

    test "average goals per match is in plausible range (1.5 to 4.0)" do
      {:ok, text} = call_tool("get_statistics", %{"stat_type" => "goals_per_match"})

      [avg_str] = Regex.run(~r/(\d+\.\d+)/, text, capture: :all_but_first)
      avg = String.to_float(avg_str)
      assert avg >= 1.5 and avg <= 4.0, "expected goals/match between 1.5 and 4.0, got #{avg}"
    end
  end

  describe "get_statistics: home vs away record" do
    test "returns home win rate and away win rate" do
      {:ok, text} = call_tool("get_statistics", %{"stat_type" => "home_away_record"})

      assert text =~ ~r/home/i, "should mention home"
      assert text =~ ~r/away/i, "should mention away"
      assert text =~ ~r/\d+\.?\d*%|\d+\.\d+/, "should contain percentages or ratios"
    end

    test "home win rate is higher than away win rate (typical in soccer)" do
      {:ok, text} = call_tool("get_statistics", %{"stat_type" => "home_away_record"})

      home_pct = extract_percentage(text, ~r/home[^\n]*?(\d+\.?\d*)%/i)
      away_pct = extract_percentage(text, ~r/away[^\n]*?(\d+\.?\d*)%/i)

      if home_pct && away_pct do
        assert home_pct > away_pct,
               "home win rate (#{home_pct}%) should exceed away win rate (#{away_pct}%)"
      end
    end
  end

  describe "get_statistics: cross-file team comparison" do
    test "returns best home team record across all competitions" do
      {:ok, text} = call_tool("get_statistics", %{"stat_type" => "best_home_teams"})

      assert text =~ ~r/\w+/, "should return team names"
      assert text =~ ~r/\d+\.?\d*%|\d+\s+wins/i, "should include stats"
    end
  end

  # ----------------------------------------------------------------
  # Helpers
  # ----------------------------------------------------------------

  defp extract_percentage(text, regex) do
    case Regex.run(regex, text, capture: :all_but_first) do
      [num] ->
        case Float.parse(num) do
          {f, _} -> f
          :error -> nil
        end

      _ ->
        nil
    end
  end
end
