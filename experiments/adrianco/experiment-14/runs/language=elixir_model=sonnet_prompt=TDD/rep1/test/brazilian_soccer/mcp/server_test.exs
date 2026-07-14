defmodule BrazilianSoccer.MCP.ServerTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.MCP.Server

  describe "handle_request/1 - initialize" do
    test "responds to initialize request" do
      request = %{
        "jsonrpc" => "2.0",
        "id" => 1,
        "method" => "initialize",
        "params" => %{
          "protocolVersion" => "2024-11-05",
          "capabilities" => %{},
          "clientInfo" => %{"name" => "test", "version" => "1.0"}
        }
      }

      response = Server.handle_request(request)
      assert response["jsonrpc"] == "2.0"
      assert response["id"] == 1
      result = response["result"]
      assert result["protocolVersion"] == "2024-11-05"
      assert Map.has_key?(result, "capabilities")
      assert Map.has_key?(result, "serverInfo")
    end
  end

  describe "handle_request/1 - tools/list" do
    test "returns list of available tools" do
      request = %{"jsonrpc" => "2.0", "id" => 2, "method" => "tools/list", "params" => %{}}
      response = Server.handle_request(request)
      assert response["jsonrpc"] == "2.0"
      tools = response["result"]["tools"]
      assert is_list(tools)
      assert length(tools) >= 6
      tool_names = Enum.map(tools, & &1["name"])
      assert "search_matches" in tool_names
      assert "get_team_stats" in tool_names
      assert "search_players" in tool_names
      assert "get_standings" in tool_names
      assert "head_to_head" in tool_names
      assert "biggest_wins" in tool_names
    end
  end

  describe "handle_request/1 - tools/call" do
    test "search_matches by team returns results" do
      request = %{
        "jsonrpc" => "2.0",
        "id" => 3,
        "method" => "tools/call",
        "params" => %{
          "name" => "search_matches",
          "arguments" => %{"team" => "Flamengo", "limit" => 5}
        }
      }
      response = Server.handle_request(request)
      assert response["jsonrpc"] == "2.0"
      result = response["result"]
      assert is_list(result["content"])
      content = hd(result["content"])
      assert content["type"] == "text"
      assert String.contains?(content["text"], "Flamengo")
    end

    test "search_players by name returns results" do
      request = %{
        "jsonrpc" => "2.0",
        "id" => 4,
        "method" => "tools/call",
        "params" => %{
          "name" => "search_players",
          "arguments" => %{"name" => "Neymar"}
        }
      }
      response = Server.handle_request(request)
      result = response["result"]
      assert is_list(result["content"])
      content = hd(result["content"])
      assert content["type"] == "text"
      assert String.contains?(content["text"], "Neymar")
    end

    test "get_team_stats returns team record" do
      request = %{
        "jsonrpc" => "2.0",
        "id" => 5,
        "method" => "tools/call",
        "params" => %{
          "name" => "get_team_stats",
          "arguments" => %{"team" => "Corinthians"}
        }
      }
      response = Server.handle_request(request)
      result = response["result"]
      content = hd(result["content"])
      assert String.contains?(content["text"], "Corinthians")
      assert String.contains?(content["text"], "wins") or String.contains?(content["text"], "Wins")
    end

    test "get_standings returns competition standings" do
      request = %{
        "jsonrpc" => "2.0",
        "id" => 6,
        "method" => "tools/call",
        "params" => %{
          "name" => "get_standings",
          "arguments" => %{"season" => 2019, "competition" => "Brasileirão"}
        }
      }
      response = Server.handle_request(request)
      result = response["result"]
      content = hd(result["content"])
      assert String.contains?(content["text"], "Flamengo")
    end

    test "head_to_head returns stats for two teams" do
      request = %{
        "jsonrpc" => "2.0",
        "id" => 7,
        "method" => "tools/call",
        "params" => %{
          "name" => "head_to_head",
          "arguments" => %{"team1" => "Flamengo", "team2" => "Fluminense"}
        }
      }
      response = Server.handle_request(request)
      result = response["result"]
      content = hd(result["content"])
      assert String.contains?(content["text"], "Flamengo")
      assert String.contains?(content["text"], "Fluminense")
    end

    test "biggest_wins returns sorted wins" do
      request = %{
        "jsonrpc" => "2.0",
        "id" => 8,
        "method" => "tools/call",
        "params" => %{
          "name" => "biggest_wins",
          "arguments" => %{"limit" => 5}
        }
      }
      response = Server.handle_request(request)
      result = response["result"]
      content = hd(result["content"])
      assert content["type"] == "text"
      assert String.length(content["text"]) > 0
    end

    test "unknown tool returns error" do
      request = %{
        "jsonrpc" => "2.0",
        "id" => 9,
        "method" => "tools/call",
        "params" => %{
          "name" => "nonexistent_tool",
          "arguments" => %{}
        }
      }
      response = Server.handle_request(request)
      assert Map.has_key?(response, "error")
    end

    test "unknown method returns error" do
      request = %{"jsonrpc" => "2.0", "id" => 10, "method" => "unknown/method", "params" => %{}}
      response = Server.handle_request(request)
      assert Map.has_key?(response, "error")
    end
  end

  describe "encode/decode" do
    test "encodes response to JSON string" do
      request = %{"jsonrpc" => "2.0", "id" => 1, "method" => "tools/list", "params" => %{}}
      response = Server.handle_request(request)
      encoded = Jason.encode!(response)
      decoded = Jason.decode!(encoded)
      assert decoded["jsonrpc"] == "2.0"
    end
  end
end
