defmodule BrazilianSoccer.MCPTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.MCP.Server
  alias BrazilianSoccer.Tools

  setup_all do
    BrazilianSoccer.Data.get()
    :ok
  end

  defp rpc(method, params \\ %{}, id \\ 1) do
    Server.handle(%{"jsonrpc" => "2.0", "id" => id, "method" => method, "params" => params})
  end

  defp call(name, args) do
    %{"result" => %{"content" => [%{"type" => "text", "text" => text}], "isError" => err}} =
      rpc("tools/call", %{"name" => name, "arguments" => args})

    {err, text}
  end

  describe "Feature: MCP protocol" do
    test "Scenario: initialize handshake" do
      r =
        rpc("initialize", %{
          "protocolVersion" => "2024-11-05",
          "capabilities" => %{},
          "clientInfo" => %{"name" => "t", "version" => "0"}
        })

      assert r["jsonrpc"] == "2.0" and r["id"] == 1
      assert r["result"]["protocolVersion"] == "2024-11-05"
      assert r["result"]["serverInfo"]["name"] == "brazilian-soccer"
      assert Map.has_key?(r["result"]["capabilities"], "tools")

      # unknown versions are answered with one the server supports
      assert rpc("initialize", %{"protocolVersion" => "1999-01-01"})["result"]["protocolVersion"] ==
               "2025-06-18"
    end

    test "Scenario: notifications get no response, ping does" do
      assert Server.handle(%{"jsonrpc" => "2.0", "method" => "notifications/initialized"}) == nil
      assert rpc("ping")["result"] == %{}
    end

    test "Scenario: tools/list returns valid tool definitions" do
      tools = rpc("tools/list")["result"]["tools"]
      assert length(tools) == 15

      for t <- tools do
        assert is_binary(t["name"]) and is_binary(t["description"])
        assert t["inputSchema"]["type"] == "object"
        assert is_map(t["inputSchema"]["properties"])

        assert Enum.all?(
                 t["inputSchema"]["required"],
                 &Map.has_key?(t["inputSchema"]["properties"], &1)
               )
      end

      # the whole catalogue is JSON-encodable
      assert {:ok, _} = JSON.decode(JSON.encode!(tools))
    end

    test "Scenario: protocol errors" do
      assert rpc("resources/list")["error"]["code"] == -32601
      assert rpc("tools/call", %{"name" => "nope", "arguments" => %{}})["error"]["code"] == -32602
      assert JSON.decode!(Server.handle_line("{not json\n"))["error"]["code"] == -32700
      assert Server.handle_line("\n") == nil
    end

    test "Scenario: tool execution errors are reported in the result" do
      assert {true, text} = call("search_matches", %{"team" => "Nowhere United"})
      assert text =~ "Team not found"
      assert {true, text} = call("head_to_head", %{"team_a" => "Flamengo"})
      assert text =~ "team_b"
      assert {true, _} = call("standings", %{})
    end

    test "Scenario: a full stdio session with UTF-8 content" do
      requests =
        [
          %{
            "jsonrpc" => "2.0",
            "id" => 1,
            "method" => "initialize",
            "params" => %{"protocolVersion" => "2025-06-18"}
          },
          %{"jsonrpc" => "2.0", "method" => "notifications/initialized"},
          %{
            "jsonrpc" => "2.0",
            "id" => 2,
            "method" => "tools/call",
            "params" => %{
              "name" => "team_stats",
              "arguments" => %{
                "team" => "Grêmio",
                "season" => 2019,
                "competition" => "Brasileirão"
              }
            }
          }
        ]
        |> Enum.map_join("\n", &JSON.encode!/1)

      {:ok, input} = StringIO.open(requests <> "\n")
      {:ok, output} = StringIO.open("")
      assert Server.run(input, output) == :ok

      {_, written} = StringIO.contents(output)

      assert [init, stats] =
               written |> String.split("\n", trim: true) |> Enum.map(&JSON.decode!/1)

      assert init["id"] == 1
      assert stats["id"] == 2
      assert hd(stats["result"]["content"])["text"] =~ "Grêmio record (Brasileirão Série A, 2019)"
    end
  end

  describe "Feature: answering the sample questions through MCP tools" do
    # {question, tool, arguments, text expected in the answer}
    @questions [
      {"Show me all Flamengo vs Fluminense matches", "search_matches",
       %{"team" => "Flamengo", "opponent" => "Fluminense"},
       [
         "Flamengo vs Fluminense",
         "44 found",
         "Head-to-head in dataset (44 matches): Flamengo 18 wins, Fluminense 14 wins, 12 draws"
       ]},
      {"What matches did Palmeiras play in 2023?", "search_matches",
       %{"team" => "Palmeiras", "season" => 2023},
       ["Palmeiras, 2023", "2023-12-03: Palmeiras 1-0 Fluminense (Brasileirão Série A 2023)"]},
      {"Find all Copa do Brasil finals", "search_matches",
       %{"competition" => "Copa do Brasil", "stage" => "final", "limit" => 30},
       ["24 found", "2019-09-18: Internacional 1-2 Athletico-PR (Copa do Brasil 2019, final)"]},
      {"What is Corinthians' home record in 2022?", "team_stats",
       %{
         "team" => "Corinthians",
         "venue" => "home",
         "season" => 2022,
         "competition" => "Brasileirão"
       },
       [
         "Corinthians home record (Brasileirão Série A, 2022)",
         "Matches: 19",
         "Wins: 12, Draws: 4, Losses: 3",
         "Win rate: 63.2%"
       ]},
      {"Which team scored the most goals in Serie A 2023?", "team_rankings",
       %{"competition" => "Serie A", "season" => 2023, "metric" => "goals_for"},
       ["1. Grêmio - goals_for: 63"]},
      {"Compare Palmeiras and Santos head-to-head", "head_to_head",
       %{"team_a" => "Palmeiras", "team_b" => "Santos"},
       ["Palmeiras 17 wins, Santos 16 wins, 8 draws"]},
      {"Find all Brazilian players in the dataset", "search_players",
       %{"nationality" => "Brazil"},
       ["827 found", "1. Neymar Jr - Overall: 92", "Position: LW", "Club: Paris Saint-Germain"]},
      {"Who are the highest-rated players at Grêmio?", "search_players",
       %{"club" => "Gremio", "limit" => 5}, ["20 found", "Club: Grêmio"]},
      {"Show me all forwards from Santos", "search_players",
       %{"club" => "Santos", "position" => "forward"}, ["Position: ST", "Club: Santos"]},
      {"Which players play for Flamengo? (club not licensed in FIFA data)", "search_players",
       %{"club" => "Flamengo"}, ["0 found", "only licenses some Brazilian clubs"]},
      {"Brazilian players at Brazilian clubs", "brazilian_clubs_players",
       %{"nationality" => "Brazil"}, ["Grêmio: 20 players (avg rating: 73.3"]},
      {"Who won the 2019 Brasileirão?", "standings", %{"season" => 2019},
       ["1. Flamengo - 90 pts (28W, 6D, 4L)", "Champion", "2. Santos - 74 pts (22W, 8D, 8L)"]},
      {"Which teams were relegated in 2020?", "standings",
       %{"season" => 2020, "competition" => "Brasileirão"},
       ["17. Vasco - 41 pts", "20. Botafogo-RJ - 27 pts", "Relegated"]},
      {"Show the 2018 Copa Libertadores bracket", "knockout_bracket",
       %{"competition" => "Copa Libertadores", "season" => 2018},
       [
         "Semifinals (4 matches)",
         "2018-12-09: River Plate 3-1 Boca Juniors",
         "Champion (final won on aggregate): River Plate"
       ]},
      {"What's the average goals per match in the Brasileirão?", "competition_stats",
       %{"competition" => "Brasileirão"}, ["Average goals per match: 2.5", "Home wins:"]},
      {"Which team has the best away record?", "team_rankings",
       %{"venue" => "away", "competition" => "Brasileirão"},
       ["Team ranking by away win_rate", "1. "]},
      {"Which team has the best home record?", "team_rankings",
       %{"venue" => "home", "competition" => "Brasileirão"}, ["1. Grêmio - win_rate: 59.1"]},
      {"Show me the biggest wins in the dataset", "biggest_wins", %{},
       ["1. 2021-06-08: São Paulo 9-1 4 de Julho (Copa do Brasil 2021"]},
      {"When did Flamengo last play Corinthians?", "search_matches",
       %{"team" => "Flamengo", "opponent" => "Corinthians", "limit" => 1},
       ["- 2023-10-08: Corinthians 1-1 Flamengo"]},
      {"Who is Neymar?", "player_details", %{"name" => "Neymar"},
       [
         "Neymar Jr (FIFA id 190871)",
         "Club: Paris Saint-Germain, Position: LW, Jersey: 10",
         "Dribbling 96"
       ]},
      {"Who is Gabriel Barbosa? (not in dataset)", "player_details",
       %{"name" => "Gabriel Barbosa"}, ["No player matching"]},
      {"Show me all derbies in 2023", "derbies", %{"season" => 2023},
       ["37 found", "[Fla-Flu]", "[Grenal]"]},
      {"What competitions has Palmeiras played in?", "team_profile", %{"team" => "Palmeiras"},
       ["Brasileirão Série A (2004-2023)", "Copa Libertadores (", "Copa do Brasil ("]},
      {"Compare the 2018 and 2019 seasons", "competition_stats",
       %{"competition" => "Brasileirão", "seasons" => [2018, 2019]},
       [
         "Season 2018:",
         "Champion: Palmeiras (80 pts)",
         "Season 2019:",
         "Average goals per match: 2.31",
         "Champion: Flamengo (90 pts)"
       ]},
      {"Which Atlético is which?", "list_teams", %{"query" => "atletico"},
       ["Atlético-MG (MG)", "Athletico-PR (PR)", "Atlético-GO (GO)"]},
      {"What data is loaded?", "dataset_info", %{},
       [
         "Brasileirao_Matches.csv: 4180 rows",
         "fifa_data.csv",
         "Copa Libertadores: 1253 matches, seasons 2013-2022"
       ]}
    ]

    test "at least 20 sample questions are covered" do
      assert length(@questions) >= 20
      assert Enum.sort(Enum.uniq(Enum.map(@questions, &elem(&1, 1)))) == Enum.sort(Tools.names())
    end

    for {question, tool, args, expected} <- @questions do
      test "Scenario: #{question}" do
        {time, {is_error, text}} =
          :timer.tc(fn -> call(unquote(tool), unquote(Macro.escape(args))) end)

        refute is_error, text

        for fragment <- unquote(expected) do
          assert text =~ fragment, "expected #{inspect(fragment)} in:\n#{text}"
        end

        assert time < 2_000_000, "#{unquote(tool)} took #{div(time, 1000)} ms"
      end
    end
  end
end
