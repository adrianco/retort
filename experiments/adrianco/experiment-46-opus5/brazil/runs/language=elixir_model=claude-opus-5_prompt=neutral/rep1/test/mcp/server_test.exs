defmodule BrazilianSoccer.MCP.ServerTest do
  @moduledoc """
  Feature: MCP protocol

  Scenario: An MCP client talks to the server
    Given a JSON-RPC request
    When the server handles it
    Then it answers with a JSON-RPC response the client can use
  """

  use BrazilianSoccer.GraphCase, async: true

  alias BrazilianSoccer.MCP.{Server, Tools}

  defp request(method, params \\ %{}, id \\ 1) do
    Server.handle(%{"jsonrpc" => "2.0", "id" => id, "method" => method, "params" => params})
  end

  describe "Scenario: initialize" do
    test "Given an initialize request Then capabilities and server info come back" do
      response = request("initialize", %{"protocolVersion" => "2025-06-18"})

      assert response["jsonrpc"] == "2.0"
      assert response["id"] == 1
      assert response["result"]["protocolVersion"] == "2025-06-18"
      assert response["result"]["serverInfo"]["name"] == "brazilian-soccer"
      assert response["result"]["capabilities"]["tools"]
      assert response["result"]["capabilities"]["resources"]
      assert response["result"]["instructions"] =~ "Knowledge graph"
    end

    test "Given an older protocol version Then the server speaks it" do
      response = request("initialize", %{"protocolVersion" => "2024-11-05"})
      assert response["result"]["protocolVersion"] == "2024-11-05"
    end

    test "Given an unknown protocol version Then the server offers its latest" do
      response = request("initialize", %{"protocolVersion" => "1999-01-01"})
      assert response["result"]["protocolVersion"] == "2025-06-18"
    end
  end

  describe "Scenario: notifications and ping" do
    test "Given a notification Then there is no response" do
      assert Server.handle(%{"jsonrpc" => "2.0", "method" => "notifications/initialized"}) == nil
    end

    test "Given a request with no id Then there is no response" do
      assert Server.handle(%{"jsonrpc" => "2.0", "method" => "tools/list"}) == nil
    end

    test "Given a ping Then an empty result comes back" do
      assert request("ping")["result"] == %{}
    end

    test "Given a request with an id but no method Then an invalid request error comes back" do
      response = Server.handle(%{"jsonrpc" => "2.0", "id" => 9})

      assert response["id"] == 9
      assert response["error"]["code"] == -32_600
    end

    test "Given an unknown method Then a JSON-RPC error comes back" do
      response = request("does/not/exist")

      assert response["error"]["code"] == -32_601
      assert response["error"]["message"] =~ "does/not/exist"
    end
  end

  describe "Scenario: tools/list" do
    test "Given a tools/list request Then every tool is described with a schema" do
      tools = request("tools/list")["result"]["tools"]

      assert length(tools) == length(Tools.all())
      assert length(tools) >= 20

      for tool <- tools do
        assert is_binary(tool["name"])
        assert String.length(tool["description"]) > 20
        assert tool["inputSchema"]["type"] == "object"
        assert is_map(tool["inputSchema"]["properties"])
      end

      names = Enum.map(tools, & &1["name"])
      assert "search_matches" in names
      assert "head_to_head" in names
      assert "league_standings" in names
      assert "search_players" in names
    end
  end

  describe "Scenario: tools/call" do
    test "Given a tool call Then text and structured content come back" do
      response =
        request("tools/call", %{
          "name" => "head_to_head",
          "arguments" => %{"team_a" => "Flamengo", "team_b" => "Fluminense"}
        })

      result = response["result"]
      assert result["isError"] == false
      assert [%{"type" => "text", "text" => text}] = result["content"]
      assert text =~ "Flamengo"
      assert text =~ "Head-to-head"

      structured = result["structuredContent"]
      assert structured["team_a"]["name"] == "Flamengo"
      assert structured["summary"]["matches"] > 0
      assert is_list(structured["matches"])
    end

    test "Given structured content Then it is JSON encodable" do
      response =
        request("tools/call", %{"name" => "search_matches", "arguments" => %{"limit" => 3}})

      assert {:ok, json} = Jason.encode(response)
      assert {:ok, decoded} = Jason.decode(json)
      assert length(decoded["result"]["structuredContent"]["matches"]) == 3

      match = hd(decoded["result"]["structuredContent"]["matches"])
      assert is_binary(match["date"])
      assert is_binary(match["competition"])
      assert is_boolean(match["played"])
    end

    test "Given a failing tool Then the failure is reported inside the result" do
      response =
        request("tools/call", %{
          "name" => "team_stats",
          "arguments" => %{"team" => "Manchester United"}
        })

      assert response["result"]["isError"] == true
      assert hd(response["result"]["content"])["text"] =~ "No team called"
      refute Map.has_key?(response, "error")
    end

    test "Given an unknown tool Then the error names it" do
      response = request("tools/call", %{"name" => "teleport", "arguments" => %{}})

      assert response["result"]["isError"] == true
      assert hd(response["result"]["content"])["text"] =~ "Unknown tool: teleport"
    end

    test "Given a call with no tool name Then it is an invalid params error" do
      response = request("tools/call", %{"arguments" => %{}})
      assert response["error"]["code"] == -32_602
    end

    test "Given arguments as a JSON object Then strings are coerced" do
      response =
        request("tools/call", %{
          "name" => "league_standings",
          "arguments" => %{"competition" => "brasileirao", "season" => "2019"}
        })

      assert hd(response["result"]["content"])["text"] =~ "Flamengo"
    end
  end

  describe "Scenario: resources" do
    test "Given resources/list Then the datasets and helpers are offered" do
      resources = request("resources/list")["result"]["resources"]
      uris = Enum.map(resources, & &1["uri"])

      assert "brazilian-soccer://datasets" in uris
      assert "brazilian-soccer://competitions" in uris
      assert "brazilian-soccer://teams" in uris
      assert "brazilian-soccer://sample-questions" in uris
    end

    test "Given resources/read Then the content comes back as text" do
      for uri <- [
            "brazilian-soccer://datasets",
            "brazilian-soccer://competitions",
            "brazilian-soccer://teams",
            "brazilian-soccer://sample-questions"
          ] do
        response = request("resources/read", %{"uri" => uri})
        [content] = response["result"]["contents"]

        assert content["uri"] == uri
        assert String.length(content["text"]) > 50
      end
    end

    test "Given an unknown resource Then an error comes back" do
      response = request("resources/read", %{"uri" => "brazilian-soccer://nope"})
      assert response["error"]["code"] == -32_602
    end
  end

  describe "Scenario: batches" do
    test "Given a batch of requests Then a batch of responses comes back" do
      responses =
        Server.handle([
          %{"jsonrpc" => "2.0", "id" => 1, "method" => "ping"},
          %{"jsonrpc" => "2.0", "method" => "notifications/initialized"},
          %{"jsonrpc" => "2.0", "id" => 2, "method" => "tools/list"}
        ])

      assert length(responses) == 2
      assert Enum.map(responses, & &1["id"]) == [1, 2]
    end
  end

  describe "Scenario: every tool answers" do
    test "Given each tool with plausible arguments Then it returns text or an explained error" do
      arguments = %{
        "list_datasets" => %{},
        "search_matches" => %{"team" => "Flamengo", "limit" => 3},
        "head_to_head" => %{"team_a" => "Flamengo", "team_b" => "Vasco"},
        "last_meeting" => %{"team_a" => "Santos", "team_b" => "Corinthians"},
        "find_derbies" => %{"season" => 2019},
        "team_stats" => %{"team" => "Cruzeiro", "season" => 2019},
        "team_profile" => %{"team" => "Bahia"},
        "compare_teams" => %{"team_a" => "Grêmio", "team_b" => "Internacional"},
        "team_rankings" => %{"metric" => "home", "limit" => 3},
        "search_players" => %{"nationality" => "Brazil", "limit" => 3},
        "player_profile" => %{"name" => "Alisson"},
        "club_squad" => %{"club" => "Cruzeiro"},
        "players_by_nationality" => %{"nationality" => "Brazil", "limit" => 3},
        "list_competitions" => %{},
        "league_standings" => %{"season" => 2019},
        "competition_champion" => %{"season" => 2019},
        "cup_bracket" => %{"competition" => "Libertadores", "season" => 2019},
        "competition_summary" => %{"season" => 2019},
        "match_statistics" => %{"competition" => "Serie B"},
        "biggest_wins" => %{"limit" => 3},
        "highest_scoring_matches" => %{"limit" => 3},
        "compare_seasons" => %{"seasons" => [2018, 2019]},
        "home_advantage" => %{},
        "resolve_team_name" => %{"name" => "Botafogo"}
      }

      for tool <- Tools.all() do
        args = Map.fetch!(arguments, tool.name)
        assert {:ok, %{text: text, data: data}} = Tools.call(tool.name, args)
        assert String.length(text) > 10, "#{tool.name} produced no answer"
        assert is_map(data)
        assert {:ok, _} = Jason.encode(data)
      end
    end
  end
end
