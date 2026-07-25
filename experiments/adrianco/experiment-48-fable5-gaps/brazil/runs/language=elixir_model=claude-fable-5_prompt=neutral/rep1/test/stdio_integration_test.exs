defmodule BrazilianSoccerMcp.StdioIntegrationTest do
  @moduledoc """
  Transport-level test: drives the real server process over stdio, verifying
  the full JSON-RPC round trip including UTF-8 handling (multi-byte
  characters such as "Brasileirão" must survive stdin/stdout intact).
  """

  use ExUnit.Case, async: false

  @moduletag :integration
  @moduletag timeout: 120_000

  test "Given a running server process, when a client session runs over stdio, then responses are valid UTF-8 JSON-RPC" do
    requests =
      [
        %{jsonrpc: "2.0", id: 1, method: "initialize", params: %{protocolVersion: "2025-06-18"}},
        %{jsonrpc: "2.0", method: "notifications/initialized"},
        %{
          jsonrpc: "2.0",
          id: 2,
          method: "tools/call",
          params: %{name: "competition_stats", arguments: %{competition: "Brasileirão"}}
        },
        %{
          jsonrpc: "2.0",
          id: 3,
          method: "tools/call",
          params: %{name: "search_players", arguments: %{club: "Grêmio", limit: 2}}
        }
      ]
      |> Enum.map_join("\n", &JSON.encode!/1)

    {output, 0} =
      System.cmd("sh", ["-c", "printf '%s\\n' \"$REQUESTS\" | mix mcp.server 2>/dev/null"],
        env: [{"REQUESTS", requests}, {"MIX_ENV", "test"}]
      )

    responses =
      output
      |> String.split("\n", trim: true)
      |> Enum.map(fn line ->
        assert {:ok, decoded} = JSON.decode(line)
        decoded
      end)

    assert [init, stats, players] = responses
    assert init["result"]["serverInfo"]["name"] == "brazilian-soccer-mcp"

    assert [%{"text" => stats_text}] = stats["result"]["content"]
    assert stats_text =~ "Average goals per match"

    assert [%{"text" => players_text}] = players["result"]["content"]
    assert players_text =~ "Grêmio"
  end
end
