defmodule BrazilianSoccer.Acceptance.ProtocolTest do
  @moduledoc """
  Acceptance tests for the MCP protocol surface itself: the handshake, tool
  discovery, and error handling that any MCP host relies on before it can ask
  domain questions.
  """
  use ExUnit.Case, async: true

  alias BrazilianSoccer.Test.MCPClient

  test "an MCP host can complete the initialize handshake" do
    resp = MCPClient.initialize()

    assert resp["jsonrpc"] == "2.0"
    assert get_in(resp, ["result", "protocolVersion"]) != nil
    assert get_in(resp, ["result", "serverInfo", "name"]) != nil
    assert get_in(resp, ["result", "capabilities", "tools"]) != nil
  end

  test "the server advertises tools covering every required query category" do
    names = MCPClient.list_tools() |> Enum.map(& &1["name"]) |> MapSet.new()

    for required <- ~w(find_matches head_to_head team_record search_players
                       get_player competition_standings competition_statistics
                       list_competitions) do
      assert MapSet.member?(names, required), "missing tool: #{required}"
    end
  end

  test "every advertised tool publishes a name, description and input schema" do
    for tool <- MCPClient.list_tools() do
      assert is_binary(tool["name"]) and tool["name"] != ""
      assert is_binary(tool["description"]) and tool["description"] != ""
      assert tool["inputSchema"]["type"] == "object"
    end
  end

  test "calling an unknown tool reports an error rather than crashing" do
    resp = MCPClient.call_raw("no_such_tool", %{})
    # Either a JSON-RPC error or a tool result flagged as an error is acceptable.
    assert resp["error"] != nil or get_in(resp, ["result", "isError"]) == true
  end

  test "an unknown JSON-RPC method yields a method-not-found error" do
    resp =
      MCPClient.request(%{
        "jsonrpc" => "2.0",
        "id" => 99,
        "method" => "does/not/exist",
        "params" => %{}
      })

    assert get_in(resp, ["error", "code"]) == -32601
    assert resp["id"] == 99
  end
end
