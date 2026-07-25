defmodule BrazilianSoccerMcp.ServerTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccerMcp.Server

  defp request(method, params, id) do
    JSON.encode!(%{jsonrpc: "2.0", id: id, method: method, params: params})
  end

  defp roundtrip(method, params, id \\ 1) do
    {:reply, json} = Server.handle_line(request(method, params, id))
    {:ok, decoded} = JSON.decode(json)
    decoded
  end

  describe "Given an MCP client, when it initializes the connection" do
    test "then the server replies with protocol version, capabilities, and identity" do
      response =
        roundtrip("initialize", %{
          protocolVersion: "2025-06-18",
          capabilities: %{},
          clientInfo: %{name: "test", version: "0"}
        })

      assert response["jsonrpc"] == "2.0"
      assert response["id"] == 1
      assert response["result"]["protocolVersion"] == "2025-06-18"
      assert response["result"]["capabilities"]["tools"] == %{}
      assert response["result"]["serverInfo"]["name"] == "brazilian-soccer-mcp"
    end

    test "then an unknown requested protocol version falls back to a supported one" do
      response = roundtrip("initialize", %{protocolVersion: "1999-01-01"})
      assert response["result"]["protocolVersion"] in ["2025-06-18", "2025-03-26", "2024-11-05"]
    end

    test "then the initialized notification gets no response" do
      line = JSON.encode!(%{jsonrpc: "2.0", method: "notifications/initialized"})
      assert Server.handle_line(line) == :noreply
    end

    test "then ping is answered" do
      assert roundtrip("ping", %{})["result"] == %{}
    end
  end

  describe "Given an initialized session, when the client lists tools" do
    test "then all tools are advertised with JSON Schemas" do
      response = roundtrip("tools/list", %{})
      tools = response["result"]["tools"]

      names = Enum.map(tools, & &1["name"])

      for expected <- [
            "search_matches",
            "head_to_head",
            "team_stats",
            "league_standings",
            "search_players",
            "top_players",
            "biggest_wins",
            "competition_stats",
            "list_teams"
          ] do
        assert expected in names
      end

      for tool <- tools do
        assert is_binary(tool["description"]) and tool["description"] != ""
        assert tool["inputSchema"]["type"] == "object"
        assert is_map(tool["inputSchema"]["properties"])
      end
    end
  end

  describe "Given the tool list, when the client calls a tool" do
    test "then a text content result is returned" do
      response =
        roundtrip("tools/call", %{
          name: "head_to_head",
          arguments: %{team1: "Flamengo", team2: "Fluminense"}
        })

      assert response["result"]["isError"] == false
      assert [%{"type" => "text", "text" => text}] = response["result"]["content"]
      assert text =~ "Flamengo"
      assert text =~ "Head-to-head"
    end

    test "then invalid tool arguments produce an isError result, not a crash" do
      response =
        roundtrip("tools/call", %{name: "head_to_head", arguments: %{team1: "Flamengo"}})

      assert response["result"]["isError"] == true
      assert [%{"type" => "text", "text" => text}] = response["result"]["content"]
      assert text =~ "team2"
    end

    test "then an unknown tool name is a JSON-RPC invalid-params error" do
      response = roundtrip("tools/call", %{name: "no_such_tool", arguments: %{}})
      assert response["error"]["code"] == -32602
    end
  end

  describe "Given malformed input, when the server parses it" do
    test "then invalid JSON produces a -32700 parse error" do
      {:reply, json} = Server.handle_line("{not json")
      {:ok, response} = JSON.decode(json)
      assert response["error"]["code"] == -32700
    end

    test "then an unknown method produces -32601" do
      response = roundtrip("resources/list", %{})
      assert response["error"]["code"] == -32601
    end

    test "then blank lines are ignored" do
      assert Server.handle_line("\n") == :noreply
      assert Server.handle_line("   \n") == :noreply
    end
  end
end
