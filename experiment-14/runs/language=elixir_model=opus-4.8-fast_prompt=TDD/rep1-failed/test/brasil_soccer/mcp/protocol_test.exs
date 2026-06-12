defmodule BrasilSoccer.MCP.ProtocolTest do
  use ExUnit.Case, async: true

  alias BrasilSoccer.MCP.Protocol
  alias BrasilSoccer.Fixtures

  setup do
    {:ok, data: %{matches: Fixtures.matches(), players: Fixtures.players()}}
  end

  describe "initialize" do
    test "echoes the protocol version and advertises tool capability", %{data: data} do
      req = %{"jsonrpc" => "2.0", "id" => 1, "method" => "initialize", "params" => %{}}
      resp = Protocol.handle(req, data)

      assert resp["id"] == 1
      assert resp["jsonrpc"] == "2.0"
      assert resp["result"]["serverInfo"]["name"] =~ "brazil"
      assert is_map(resp["result"]["capabilities"]["tools"])
    end
  end

  describe "notifications" do
    test "initialized notification produces no response", %{data: data} do
      req = %{"jsonrpc" => "2.0", "method" => "notifications/initialized"}
      assert Protocol.handle(req, data) == nil
    end
  end

  describe "tools/list" do
    test "returns the tool catalogue", %{data: data} do
      req = %{"jsonrpc" => "2.0", "id" => 2, "method" => "tools/list", "params" => %{}}
      resp = Protocol.handle(req, data)
      tools = resp["result"]["tools"]
      assert is_list(tools)
      assert Enum.any?(tools, &(&1.name == "find_matches"))
    end
  end

  describe "tools/call" do
    test "runs a tool and returns text content", %{data: data} do
      req = %{
        "jsonrpc" => "2.0",
        "id" => 3,
        "method" => "tools/call",
        "params" => %{"name" => "team_record", "arguments" => %{"team" => "Flamengo"}}
      }

      resp = Protocol.handle(req, data)
      assert [%{"type" => "text", "text" => text}] = resp["result"]["content"]
      assert text =~ "Win rate"
      refute resp["result"]["isError"]
    end

    test "reports tool errors via isError", %{data: data} do
      req = %{
        "jsonrpc" => "2.0",
        "id" => 4,
        "method" => "tools/call",
        "params" => %{"name" => "team_record", "arguments" => %{}}
      }

      resp = Protocol.handle(req, data)
      assert resp["result"]["isError"] == true
      assert [%{"text" => text}] = resp["result"]["content"]
      assert text =~ "Missing"
    end
  end

  describe "unknown method" do
    test "returns a JSON-RPC method-not-found error", %{data: data} do
      req = %{"jsonrpc" => "2.0", "id" => 5, "method" => "frobnicate", "params" => %{}}
      resp = Protocol.handle(req, data)
      assert resp["error"]["code"] == -32601
    end
  end
end
