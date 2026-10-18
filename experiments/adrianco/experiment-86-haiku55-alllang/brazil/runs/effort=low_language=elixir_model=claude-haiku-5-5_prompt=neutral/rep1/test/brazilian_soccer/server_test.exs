defmodule BrazilianSoccer.ServerTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.{Data, Server}

  @fixtures Path.expand("../fixtures/kaggle", __DIR__)

  setup_all do
    %{data: Data.load(@fixtures)}
  end

  defp call_tool(data, name, arguments) do
    request = %{
      "jsonrpc" => "2.0",
      "id" => 1,
      "method" => "tools/call",
      "params" => %{"name" => name, "arguments" => arguments}
    }

    %{result: result} = Server.handle(request, data)
    result
  end

  defp text(result), do: result.content |> hd() |> Map.fetch!(:text)

  describe "Scenario: MCP handshake" do
    test "Given an initialize request, then the server reports tool support", %{data: data} do
      response =
        Server.handle(
          %{"jsonrpc" => "2.0", "id" => 1, "method" => "initialize", "params" => %{}},
          data
        )

      assert response.id == 1
      assert response.result.protocolVersion == "2024-11-05"
      assert Map.has_key?(response.result.capabilities, :tools)
      assert response.result.serverInfo.name == "brazilian-soccer"
    end

    test "Given the initialized notification, then no response is sent", %{data: data} do
      assert Server.handle(%{"jsonrpc" => "2.0", "method" => "notifications/initialized"}, data) ==
               nil
    end

    test "Given tools/list, then all eight tools are advertised with schemas", %{data: data} do
      %{result: %{tools: tools}} =
        Server.handle(%{"jsonrpc" => "2.0", "id" => 2, "method" => "tools/list"}, data)

      names = Enum.map(tools, & &1.name)

      assert names == [
               "search_matches",
               "team_record",
               "head_to_head",
               "standings",
               "league_stats",
               "biggest_wins",
               "team_ranking",
               "search_players"
             ]

      assert Enum.all?(tools, &(&1.inputSchema.type == "object"))
    end
  end

  describe "Scenario: protocol errors" do
    test "Given malformed JSON, then a parse error is returned", %{data: data} do
      assert %{error: %{code: -32_700}} = Server.handle_line("{nope", data)
    end

    test "Given an unknown method, then method-not-found is returned", %{data: data} do
      assert %{id: 3, error: %{code: -32_601}} =
               Server.handle(%{"jsonrpc" => "2.0", "id" => 3, "method" => "resources/list"}, data)
    end

    test "Given tools/call without a name, then invalid params is returned", %{data: data} do
      assert %{error: %{code: -32_602}} =
               Server.handle(
                 %{"jsonrpc" => "2.0", "id" => 4, "method" => "tools/call", "params" => %{}},
                 data
               )
    end
  end

  describe "Scenario: tool calls return readable text" do
    test "Given Flamengo vs Fluminense, then the match list is formatted", %{data: data} do
      result =
        call_tool(data, "search_matches", %{"team" => "Flamengo", "opponent" => "Fluminense"})

      refute result.isError
      assert text(result) =~ "Found 2 matches (showing 2):"
      assert text(result) =~ "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 22)"
    end

    test "Given a Copa do Brasil final, then the stage name appears", %{data: data} do
      result =
        call_tool(data, "search_matches", %{"competition" => "Copa do Brasil", "season" => 2023})

      assert text(result) =~ "Copa do Brasil, final"
    end

    test "Given Corinthians 2022, then the record block is formatted as specified", %{data: data} do
      result =
        call_tool(data, "team_record", %{
          "team" => "Corinthians",
          "season" => 2022,
          "competition" => "Brasileirão Série A"
        })

      assert text(result) == """
             Corinthians record (Brasileirão Série A, 2022):
             - Matches: 3
             - Wins: 1, Draws: 1, Losses: 1
             - Goals For: 3, Goals Against: 4
             - Win rate: 33.3%\
             """
    end

    test "Given the 2022 table, then positions are numbered", %{data: data} do
      result = call_tool(data, "standings", %{"season" => 2022})
      assert text(result) =~ "1. Palmeiras - 7 pts"
    end

    test "Given Brazilian players, then names and clubs are formatted", %{data: data} do
      result = call_tool(data, "search_players", %{"nationality" => "Brazil", "limit" => 1})
      assert text(result) =~ "Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain"
    end

    test "Given a ranking metric, then rate metrics show a percent sign", %{data: data} do
      result =
        call_tool(data, "team_ranking", %{
          "metric" => "home_win_rate",
          "min_matches" => 1,
          "competition" => "Série A"
        })

      assert text(result) =~ "1. "
      assert text(result) =~ "%"
    end

    test "Given an unknown tool, then the result is flagged as an error, not a protocol error", %{
      data: data
    } do
      result = call_tool(data, "make_coffee", %{})
      assert result.isError
      assert text(result) == "unknown tool: make_coffee"
    end

    test "Given a missing required argument, then the error names it", %{data: data} do
      result = call_tool(data, "team_record", %{})
      assert result.isError
      assert text(result) == "missing required argument: team"
    end

    test "Given an invalid date, then the error explains it", %{data: data} do
      result = call_tool(data, "search_matches", %{"date_from" => "yesterday"})
      assert result.isError
      assert text(result) =~ "date_from is not a recognised date"
    end

    test "Given a bad side value, then the error lists the allowed values", %{data: data} do
      result = call_tool(data, "search_matches", %{"side" => "middle"})
      assert result.isError
      assert text(result) == "side must be one of: home, away, either"
    end
  end
end
