defmodule BrSoccer.MCPTest do
  use ExUnit.Case, async: false

  alias BrSoccer.{Fixtures, Repo}
  alias BrSoccer.MCP.{Server, Tools}

  setup do
    Repo.put_data(Fixtures.data())
    :ok
  end

  describe "Tools" do
    test "every advertised tool has a name, description and input schema" do
      for tool <- Tools.list() do
        assert is_binary(tool.name)
        assert is_binary(tool.description)
        assert tool.inputSchema.type == "object"
      end

      assert length(Tools.list()) >= 14
    end

    test "search_matches renders match lines" do
      {:ok, text} = Tools.call("search_matches", %{"team" => "Alpha", "competition" => "brasileirao", "season" => 2020})
      assert text =~ "Alpha"
      assert text =~ "Beta"
    end

    test "head_to_head reports the record" do
      {:ok, text} = Tools.call("head_to_head", %{"team_a" => "Alpha", "team_b" => "Beta"})
      assert text =~ "Alpha 3 wins"
    end

    test "league_standings renders a table with the champion" do
      {:ok, text} = Tools.call("league_standings", %{"competition" => "brasileirao", "season" => 2020})
      assert text =~ "1. Alpha"
      assert text =~ "Champion"
    end

    test "search_players renders ranked players" do
      {:ok, text} = Tools.call("search_players", %{"nationality" => "Brazil"})
      assert text =~ "1. Neymar Jr"
    end

    test "missing required arguments produce an error result, not a crash" do
      assert {:error, _} = Tools.call("head_to_head", %{"team_a" => "Alpha"})
    end

    test "unknown tool is reported" do
      assert {:error, msg} = Tools.call("does_not_exist", %{})
      assert msg =~ "Unknown tool"
    end
  end

  describe "Server (JSON-RPC)" do
    test "initialize returns protocol version and server info" do
      msg = ~s({"jsonrpc":"2.0","id":1,"method":"initialize","params":{}})
      assert {:reply, resp} = Server.handle_message(msg)
      assert resp.id == 1
      assert resp.result.protocolVersion == "2024-11-05"
      assert resp.result.serverInfo.name == "br-soccer"
    end

    test "tools/list returns the catalogue" do
      msg = ~s({"jsonrpc":"2.0","id":2,"method":"tools/list"})
      assert {:reply, resp} = Server.handle_message(msg)
      assert is_list(resp.result.tools)
    end

    test "tools/call executes a tool and wraps the text content" do
      msg =
        Jason.encode!(%{
          jsonrpc: "2.0",
          id: 3,
          method: "tools/call",
          params: %{name: "league_standings", arguments: %{competition: "brasileirao", season: 2020}}
        })

      assert {:reply, resp} = Server.handle_message(msg)
      assert resp.result.isError == false
      assert [%{type: "text", text: text}] = resp.result.content
      assert text =~ "Alpha"
    end

    test "notifications produce no reply" do
      msg = ~s({"jsonrpc":"2.0","method":"notifications/initialized"})
      assert :noreply = Server.handle_message(msg)
    end

    test "unknown method on a request returns a JSON-RPC error" do
      msg = ~s({"jsonrpc":"2.0","id":9,"method":"no/such/method"})
      assert {:reply, %{error: %{code: -32601}}} = Server.handle_message(msg)
    end

    test "malformed JSON is ignored" do
      assert :noreply = Server.handle_message("{not json")
    end

    test "the full response envelope is JSON-encodable" do
      msg = ~s({"jsonrpc":"2.0","id":1,"method":"tools/list"})
      {:reply, resp} = Server.handle_message(msg)
      assert {:ok, _} = Jason.encode(resp)
    end
  end
end
