defmodule BrazilianSoccer.MCP.ServerTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.MCP.Server

  setup do
    {:ok, dataset: BrazilianSoccer.Fixtures.dataset()}
  end

  defp req(method, params \\ %{}, id \\ 1) do
    %{"jsonrpc" => "2.0", "id" => id, "method" => method, "params" => params}
  end

  describe "handle/2 initialize" do
    test "returns protocol version and server info", %{dataset: ds} do
      resp = Server.handle(req("initialize"), ds)

      assert resp["jsonrpc"] == "2.0"
      assert resp["id"] == 1
      assert is_binary(resp["result"]["protocolVersion"])
      assert resp["result"]["serverInfo"]["name"] =~ "brazilian"
      assert resp["result"]["capabilities"]["tools"] == %{}
    end
  end

  describe "handle/2 tools/list" do
    test "advertises tools with camelCase inputSchema", %{dataset: ds} do
      resp = Server.handle(req("tools/list"), ds)
      tools = resp["result"]["tools"]

      assert is_list(tools)
      first = hd(tools)
      assert Map.has_key?(first, "name")
      assert Map.has_key?(first, "inputSchema")
    end
  end

  describe "handle/2 tools/call" do
    test "wraps tool output in a text content block", %{dataset: ds} do
      resp =
        Server.handle(
          req("tools/call", %{"name" => "team_record", "arguments" => %{"team" => "Flamengo", "season" => 2023}}),
          ds
        )

      assert [%{"type" => "text", "text" => text}] = resp["result"]["content"]
      assert text =~ "Wins: 2"
      refute resp["result"]["isError"]
    end

    test "marks tool errors with isError", %{dataset: ds} do
      resp =
        Server.handle(
          req("tools/call", %{"name" => "team_record", "arguments" => %{}}),
          ds
        )

      assert resp["result"]["isError"] == true
    end

    test "returns a JSON-RPC error for an unknown method", %{dataset: ds} do
      resp = Server.handle(req("does/not/exist"), ds)
      assert resp["error"]["code"] == -32_601
    end
  end

  describe "handle/2 notifications" do
    test "returns nil for a notification (no id)", %{dataset: ds} do
      assert Server.handle(%{"jsonrpc" => "2.0", "method" => "notifications/initialized"}, ds) == nil
    end

    test "ping returns an empty result", %{dataset: ds} do
      resp = Server.handle(req("ping"), ds)
      assert resp["result"] == %{}
    end
  end
end
