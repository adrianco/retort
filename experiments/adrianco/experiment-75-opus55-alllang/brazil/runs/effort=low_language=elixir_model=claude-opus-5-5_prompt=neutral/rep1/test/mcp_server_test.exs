defmodule BrSoccer.MCPServerTest do
  use ExUnit.Case, async: true
  alias BrSoccer.MCPServer

  test "initialize handshake" do
    resp = MCPServer.handle_json(~s({"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}))
    assert resp["result"]["serverInfo"]["name"] == "brazilian-soccer"
    assert resp["result"]["capabilities"]["tools"]
  end

  test "notifications get no response" do
    assert MCPServer.handle_json(~s({"jsonrpc":"2.0","method":"notifications/initialized"})) == nil
  end

  test "tools/list returns JSON-encodable tool schemas" do
    resp = MCPServer.handle_json(~s({"jsonrpc":"2.0","id":2,"method":"tools/list"}))
    names = Enum.map(resp["result"]["tools"], & &1["name"])
    assert "search_matches" in names and "search_players" in names and "standings" in names
    assert is_binary(JSON.encode!(resp))
  end

  test "tools/call returns text content" do
    req = ~s({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019,"limit":3}}})
    resp = MCPServer.handle_json(req)
    [%{"type" => "text", "text" => text}] = resp["result"]["content"]
    assert text =~ "Flamengo"
    assert resp["result"]["isError"] == false
  end

  test "errors" do
    assert MCPServer.handle_json("not json")["error"]["code"] == -32700
    assert MCPServer.handle_json(~s({"jsonrpc":"2.0","id":4,"method":"nope"}))["error"]["code"] == -32601
    resp = MCPServer.handle_json(~s({"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"bogus"}}))
    assert resp["result"]["isError"]
  end
end
