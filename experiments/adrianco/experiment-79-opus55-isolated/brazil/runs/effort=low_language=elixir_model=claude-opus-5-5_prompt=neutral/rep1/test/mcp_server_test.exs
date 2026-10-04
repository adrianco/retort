defmodule BrazilianSoccer.MCPServerTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.MCP.{Server, Tools}

  defp rpc(method, params \\ %{}, id \\ 1) do
    Server.handle(%{"jsonrpc" => "2.0", "id" => id, "method" => method, "params" => params})
  end

  defp ask(tool, args) do
    %{"result" => %{"content" => [%{"type" => "text", "text" => text}], "isError" => false}} =
      rpc("tools/call", %{"name" => tool, "arguments" => args})

    text
  end

  describe "Feature: MCP protocol" do
    test "initialize negotiates the protocol and advertises tools" do
      %{"jsonrpc" => "2.0", "id" => 7, "result" => r} =
        rpc("initialize", %{"protocolVersion" => "2025-03-26", "capabilities" => %{}}, 7)

      assert r["protocolVersion"] == "2025-03-26"
      assert r["capabilities"]["tools"]
      assert r["serverInfo"]["name"] == "brazilian-soccer-mcp"

      assert rpc("initialize", %{"protocolVersion" => "1999-01-01"})["result"]["protocolVersion"] ==
               "2024-11-05"
    end

    test "notifications get no response; ping does" do
      assert Server.handle(%{"jsonrpc" => "2.0", "method" => "notifications/initialized"}) == nil
      assert rpc("ping")["result"] == %{}
    end

    test "tools/list returns valid tool definitions" do
      tools = rpc("tools/list")["result"]["tools"]
      assert length(tools) >= 12

      for t <- tools do
        assert is_binary(t["name"]) and is_binary(t["description"])
        assert t["inputSchema"]["type"] == "object"
        assert is_map(t["inputSchema"]["properties"])
      end

      assert JSON.decode!(JSON.encode!(tools)) == tools
    end

    test "errors: unknown method, unknown tool, missing arguments, bad JSON" do
      assert rpc("resources/list")["error"]["code"] == -32601
      assert Server.handle(%{"id" => 1})["error"]["code"] == -32600

      assert %{"isError" => true} =
               rpc("tools/call", %{"name" => "nope", "arguments" => %{}})["result"]

      assert %{"isError" => true, "content" => [%{"text" => text}]} =
               rpc("tools/call", %{
                 "name" => "head_to_head",
                 "arguments" => %{"team_a" => "Santos"}
               })["result"]

      assert text =~ "team_b"
      assert JSON.decode!(Server.handle_line("{not json\n"))["error"]["code"] == -32700
      assert Server.handle_line("\n") == nil
    end

    test "the stdio loop answers newline-delimited requests" do
      requests =
        [
          %{"jsonrpc" => "2.0", "id" => 1, "method" => "initialize", "params" => %{}},
          %{"jsonrpc" => "2.0", "method" => "notifications/initialized"},
          %{
            "jsonrpc" => "2.0",
            "id" => 2,
            "method" => "tools/call",
            "params" => %{"name" => "standings", "arguments" => %{"season" => 2019}}
          }
        ]
        |> Enum.map_join("\n", &JSON.encode!/1)

      {:ok, input} = StringIO.open(requests <> "\n")
      {:ok, output} = StringIO.open("")
      assert Server.run(input, output) == :ok

      {_, written} = StringIO.contents(output)
      [init, standings] = written |> String.split("\n", trim: true) |> Enum.map(&JSON.decode!/1)
      assert init["id"] == 1
      assert standings["id"] == 2
      assert hd(standings["result"]["content"])["text"] =~ "1. Flamengo - 90 pts (28W, 6D, 4L)"
    end
  end

  # The sample questions from the specification, each answered through the
  # MCP tools/call interface.
  describe "Feature: sample questions" do
    test "1. Show me all Flamengo vs Fluminense matches" do
      text =
        ask("search_matches", %{"team" => "Flamengo", "opponent" => "Fluminense", "limit" => 5})

      assert text =~
               ~r/- \d{4}-\d{2}-\d{2}: (Flamengo|Fluminense) \d+-\d+ (Flamengo|Fluminense) \(/

      assert text =~ "more in dataset"

      assert text =~
               ~r/Head-to-head in dataset: Flamengo \d+ wins, Fluminense \d+ wins, \d+ draws/
    end

    test "2. What matches did Palmeiras play in 2023?" do
      text = ask("search_matches", %{"team" => "Palmeiras", "season" => 2023})
      assert text =~ "Palmeiras" and text =~ "2023-"
    end

    test "3. Find all Copa do Brasil finals" do
      text =
        ask("search_matches", %{
          "competition" => "Copa do Brasil",
          "stage" => "final",
          "limit" => 50
        })

      assert text =~ "2015-12-02: Palmeiras 2-1 Santos (Copa do Brasil 2015, final)"
    end

    test "4. What is Corinthians' home record in 2022?" do
      text =
        ask("team_stats", %{
          "team" => "Corinthians",
          "season" => 2022,
          "competition" => "Brasileirão",
          "venue" => "home"
        })

      assert text =~ "Home record:"
      assert text =~ "- Matches: 19"
      assert text =~ ~r/- Wins: \d+, Draws: \d+, Losses: \d+/
      assert text =~ ~r/- Win rate: \d+\.\d%/
    end

    test "5. Which team scored the most goals in Serie A 2019?" do
      text =
        ask("team_rankings", %{
          "sort_by" => "goals_for",
          "season" => 2019,
          "competition" => "Serie A"
        })

      assert text =~ "1. Flamengo"
    end

    test "6. Compare Palmeiras and Santos head-to-head" do
      text = ask("head_to_head", %{"team_a" => "Palmeiras", "team_b" => "Santos"})
      assert text =~ "Palmeiras vs Santos (Clássico da Saudade)"
      assert text =~ "Head-to-head in dataset: Palmeiras"
    end

    test "7. Find all Brazilian players in the dataset" do
      text = ask("search_players", %{"nationality" => "Brazil", "limit" => 3})
      assert text =~ "1. Neymar Jr - Overall: 92"
      assert text =~ "Club: Paris Saint-Germain"
    end

    test "8. Who are the highest-rated players at Grêmio? / Which players play for Flamengo?" do
      assert ask("search_players", %{"club" => "Grêmio"}) =~ "Club: Grêmio"
      # Flamengo is not licensed in the FIFA dataset: a clear answer, not an error.
      assert ask("search_players", %{"club" => "Flamengo"}) =~ "No players found"
    end

    test "9. Show me all forwards from Santos" do
      text = ask("search_players", %{"club" => "Santos", "position" => "forwards"})
      assert text =~ ~r/Position: (ST|LS|RS|CF|LW|RW|LF|RF)/
      refute text =~ "Position: GK"
    end

    test "10. Who won the 2019 Brasileirão?" do
      text = ask("standings", %{"season" => 2019})
      assert text =~ "2019 Brasileirão Série A Final Standings (calculated from matches):"
      assert text =~ "1. Flamengo - 90 pts (28W, 6D, 4L), GF 86, GA 37, GD +49 - Champion"
      assert text =~ "2. Santos - 74 pts (22W, 8D, 8L)"
    end

    test "11. Show the 2018 Copa Libertadores knockout matches" do
      text =
        ask("search_matches", %{
          "competition" => "Libertadores",
          "season" => 2018,
          "stage" => "semifinals"
        })

      assert text =~ "4 found"
      assert text =~ "Grêmio" and text =~ "River Plate"
    end

    test "12. Which teams were relegated in 2020?" do
      text = ask("standings", %{"season" => "2020", "competition" => "Brasileirão"})

      for t <- ["Vasco da Gama", "Goiás", "Coritiba", "Botafogo"],
          do: assert(text =~ ~r/#{t} .* - Relegated/)
    end

    test "13. What's the average goals per match in the Brasileirão?" do
      text = ask("competition_stats", %{"competition" => "Brasileirão"})
      assert text =~ ~r/Average goals per match: 2\.\d\d/
      assert text =~ ~r/Home wins: \d+ \(\d+\.\d%\)/
    end

    test "14. Which team has the best away record? / best home record?" do
      assert ask("team_rankings", %{"venue" => "away", "min_matches" => 50}) =~
               "Teams ranked by away win rate"

      assert ask("team_rankings", %{"venue" => "home", "min_matches" => 50}) =~
               ~r/1\. .+ - \d+ matches/
    end

    test "15. Show me the biggest wins in the dataset" do
      text = ask("biggest_wins", %{"limit" => 5})
      assert text =~ "Biggest victories (all data):"
      assert length(String.split(text, "\n")) == 6

      assert ask("biggest_wins", %{"by" => "total_goals", "competition" => "Libertadores"}) =~
               "Highest-scoring"
    end

    test "16. When did Flamengo last play Corinthians, and what was the score?" do
      text =
        ask("search_matches", %{"team" => "Flamengo", "opponent" => "Corinthians", "limit" => 1})

      [_, first | _] = String.split(text, "\n")

      assert first =~
               ~r/^- 2023-\d\d-\d\d: (Flamengo \d+-\d+ Corinthians|Corinthians \d+-\d+ Flamengo)/
    end

    test "17. Who is Neymar? (player lookup)" do
      text = ask("player_details", %{"name" => "Neymar"})
      assert text =~ "Neymar Jr"
      assert text =~ "- Nationality: Brazil"
      assert text =~ "- Overall: 92, Potential: 93"
      assert ask("player_details", %{"name" => "Gabriel Barbosa"}) =~ "No player found"
    end

    test "18. Show me all derbies in 2023" do
      text = ask("derbies", %{"season" => 2023, "limit" => 100})
      assert text =~ "[Fla-Flu]"
      assert text =~ "[Gre-Nal]"
    end

    test "19. What competitions has Palmeiras played in? (cross-file profile)" do
      text = ask("team_profile", %{"team" => "Palmeiras"})
      # Palmeiras spent 2003 in Série B, so its Série A data starts in 2004.
      assert text =~ "- Brasileirão Série A (2004-2023)"
      assert text =~ "- Copa do Brasil"
      assert text =~ "- Copa Libertadores"

      # match data and player data joined for a club present in both
      text = ask("team_profile", %{"team" => "Gremio"})
      assert text =~ "Grêmio (RS)"
      assert text =~ "FIFA player data: 20 players"
    end

    test "20. Who are the top Brazilian players / Brazilian players at Brazilian clubs?" do
      text = ask("players_by_club", %{"nationality" => "Brazil", "brazilian_clubs_only" => true})
      assert text =~ ~r/- Grêmio: \d+ players \(avg rating: \d+\.\d/
    end

    test "21. Compare the 2018 and 2019 seasons" do
      text = ask("compare_seasons", %{"season_a" => 2018, "season_b" => 2019})
      assert text =~ "2018 Brasileirão Série A:"
      assert text =~ "- Top 4: Palmeiras (80 pts)"
      assert text =~ "- Top 4: Flamengo (90 pts)"
    end

    test "22. What data is available?" do
      text = ask("dataset_info", %{})

      for f <-
            ~w(Brasileirao_Matches.csv Brazilian_Cup_Matches.csv Libertadores_Matches.csv BR-Football-Dataset.csv novo_campeonato_brasileiro.csv fifa_data.csv) do
        assert text =~ f
      end
    end

    test "empty results are reported, not errors" do
      assert ask("search_matches", %{"team" => "Nonexistent United"}) =~ "0 found"
      assert ask("team_stats", %{"team" => "Nonexistent United"}) =~ "No played matches"
      assert ask("standings", %{"season" => 1950}) =~ "No played matches"
    end

    test "every tool responds to a call with its minimal arguments" do
      samples = %{
        "team" => "Santos",
        "team_a" => "Santos",
        "team_b" => "Bahia",
        "season" => 2018,
        "season_a" => 2017,
        "season_b" => 2018,
        "name" => "Silva"
      }

      for tool <- Tools.list() do
        args = Map.take(samples, tool["inputSchema"]["required"] || [])
        assert {:ok, text} = Tools.call(tool["name"], args)
        assert String.length(text) > 0
      end
    end
  end
end
