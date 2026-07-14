defmodule BrasilSoccer.MCP.ServerTest do
  use ExUnit.Case, async: true

  alias BrasilSoccer.MCP.Server
  alias BrasilSoccer.Fixtures

  setup do
    {:ok, data: %{matches: Fixtures.matches(), players: Fixtures.players()}}
  end

  describe "process_line/2" do
    test "returns an encoded response for a request", %{data: data} do
      line = ~s({"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}})
      assert {:reply, json} = Server.process_line(line, data)
      assert {:ok, decoded} = JSON.decode(json)
      assert decoded["id"] == 1
      assert is_list(decoded["result"]["tools"])
    end

    test "returns :noreply for a notification", %{data: data} do
      line = ~s({"jsonrpc":"2.0","method":"notifications/initialized"})
      assert Server.process_line(line, data) == :noreply
    end

    test "blank lines are ignored", %{data: data} do
      assert Server.process_line("   ", data) == :noreply
    end

    test "invalid JSON yields a parse error", %{data: data} do
      assert {:reply, json} = Server.process_line("{not json", data)
      assert {:ok, decoded} = JSON.decode(json)
      assert decoded["error"]["code"] == -32700
    end

    test "a tools/call round-trips through JSON", %{data: data} do
      line =
        ~s({"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"dataset_info","arguments":{}}})

      assert {:reply, json} = Server.process_line(line, data)
      {:ok, decoded} = JSON.decode(json)
      [%{"text" => text}] = decoded["result"]["content"]
      assert text =~ "Matches:"
    end
  end
end
