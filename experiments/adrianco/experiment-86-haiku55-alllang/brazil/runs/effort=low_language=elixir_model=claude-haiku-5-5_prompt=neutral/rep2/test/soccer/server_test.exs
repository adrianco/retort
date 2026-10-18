defmodule SoccerMcp.ServerTest do
  # Feature: JSON-RPC handshake and tool calls over the MCP stdio protocol
  use ExUnit.Case, async: true

  import ExUnit.CaptureIO

  alias SoccerMcp.{Server, Store}

  @fixtures Path.expand("../fixtures", __DIR__)

  setup_all do
    capture_io(:stderr, fn -> send(self(), {:store, Store.load(@fixtures)}) end)
    assert_received {:store, store}
    {:ok, store: store}
  end

  defp request(store, message) do
    store |> then(fn s -> Server.handle_line(Jason.encode!(message), s) end) |> Jason.decode!()
  end

  describe "Feature: MCP handshake" do
    test "Scenario: initialize reports protocol and server info", %{store: store} do
      # Given a client starting a session
      # When it sends initialize
      response = request(store, %{jsonrpc: "2.0", id: 1, method: "initialize", params: %{}})

      # Then the server replies with its protocol version and tool capability
      assert response["id"] == 1
      assert response["result"]["protocolVersion"] == "2024-11-05"
      assert response["result"]["capabilities"]["tools"] == %{}
      assert response["result"]["serverInfo"]["name"] == "brazilian-soccer-mcp"
    end

    test "Scenario: notifications get no response", %{store: store} do
      # Given the client's initialized notification (no id)
      # When it is handled
      # Then no response line is produced
      assert Server.handle_line(~s({"jsonrpc":"2.0","method":"notifications/initialized"}), store) ==
               nil
    end

    test "Scenario: ping answers with an empty result", %{store: store} do
      assert %{"result" => %{}} = request(store, %{jsonrpc: "2.0", id: 9, method: "ping"})
    end
  end

  describe "Feature: tool discovery and calls" do
    test "Scenario: tools/list advertises the six tools", %{store: store} do
      # Given a connected client
      # When it lists tools
      %{"result" => %{"tools" => tools}} =
        request(store, %{jsonrpc: "2.0", id: 2, method: "tools/list"})

      # Then each tool has a name and a JSON schema
      assert length(tools) == 6
      assert Enum.all?(tools, &(is_binary(&1["name"]) and is_map(&1["inputSchema"])))
    end

    test "Scenario: tools/call returns text content", %{store: store} do
      # Given a question about a team
      # When the client calls search_matches
      response =
        request(store, %{
          jsonrpc: "2.0",
          id: 3,
          method: "tools/call",
          params: %{name: "search_matches", arguments: %{team: "Palmeiras", opponent: "Santos"}}
        })

      # Then the answer is text content and not flagged as an error
      assert %{
               "result" => %{
                 "isError" => false,
                 "content" => [%{"type" => "text", "text" => text}]
               }
             } = response

      assert text =~ "Head-to-head in dataset"
    end

    test "Scenario: a failing tool is reported inside the result", %{store: store} do
      # Given a tool call with a bad argument
      response =
        request(store, %{
          jsonrpc: "2.0",
          id: 4,
          method: "tools/call",
          params: %{name: "team_stats", arguments: %{}}
        })

      # Then the protocol succeeds but the content is marked as an error
      assert %{"result" => %{"isError" => true, "content" => [%{"text" => text}]}} = response
      assert text == "missing required argument team"
    end
  end

  describe "Feature: protocol errors" do
    test "Scenario: an unknown method", %{store: store} do
      # Given a method the server does not implement
      response = request(store, %{jsonrpc: "2.0", id: 5, method: "resources/list"})

      # Then the standard method-not-found code is returned
      assert response["error"]["code"] == -32_601
    end

    test "Scenario: malformed JSON", %{store: store} do
      # Given a line that is not JSON
      response = Server.handle_line("{not json", store) |> Jason.decode!()

      # Then a parse error is returned with a null id
      assert response["error"]["code"] == -32_700
      assert response["id"] == nil
    end

    test "Scenario: tools/call without a name", %{store: store} do
      response = request(store, %{jsonrpc: "2.0", id: 6, method: "tools/call", params: %{}})
      assert response["error"]["code"] == -32_602
    end
  end
end
