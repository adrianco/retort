defmodule BrazilianSoccer.MCP.CLITest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.MCP.CLI

  setup do
    {:ok, dataset: BrazilianSoccer.Fixtures.dataset()}
  end

  describe "process_line/2" do
    test "decodes a request, handles it, and encodes the response", %{dataset: ds} do
      line = JSON.encode!(%{"jsonrpc" => "2.0", "id" => 7, "method" => "tools/list"})
      assert {:reply, json} = CLI.process_line(line, ds)

      decoded = JSON.decode!(json)
      assert decoded["id"] == 7
      assert is_list(decoded["result"]["tools"])
    end

    test "returns :noreply for a notification", %{dataset: ds} do
      line = JSON.encode!(%{"jsonrpc" => "2.0", "method" => "notifications/initialized"})
      assert CLI.process_line(line, ds) == :noreply
    end

    test "returns a parse error for invalid JSON", %{dataset: ds} do
      assert {:reply, json} = CLI.process_line("{not json", ds)
      assert JSON.decode!(json)["error"]["code"] == -32_700
    end

    test "round-trips a tools/call", %{dataset: ds} do
      line =
        JSON.encode!(%{
          "jsonrpc" => "2.0",
          "id" => 1,
          "method" => "tools/call",
          "params" => %{"name" => "match_stats", "arguments" => %{}}
        })

      assert {:reply, json} = CLI.process_line(line, ds)
      [%{"text" => text}] = JSON.decode!(json)["result"]["content"]
      assert text =~ "Average goals per match"
    end
  end
end
