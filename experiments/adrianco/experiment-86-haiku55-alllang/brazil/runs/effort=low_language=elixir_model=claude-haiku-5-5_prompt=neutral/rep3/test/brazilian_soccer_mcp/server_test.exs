defmodule BrazilianSoccerMcp.ServerTest do
  use ExUnit.Case, async: true

  import BrazilianSoccerMcp.Fixtures

  alias BrazilianSoccerMcp.Server

  @data data()

  defp request(method, params \\ %{}, id \\ 1) do
    %{"jsonrpc" => "2.0", "id" => id, "method" => method, "params" => params}
  end

  defp call_line(message),
    do: message |> Jason.encode!() |> Server.handle_line(@data) |> Jason.decode!()

  describe "Given a client starts a session" do
    test "When initialize is sent Then the server reports its protocol version and tool capability" do
      response = call_line(request("initialize", %{"protocolVersion" => "2024-11-05"}))

      assert response["id"] == 1
      assert response["result"]["protocolVersion"] == "2024-11-05"
      assert response["result"]["capabilities"] == %{"tools" => %{}}
      assert response["result"]["serverInfo"]["name"] == "brazilian-soccer-mcp"
    end

    test "When the initialized notification arrives Then no response is sent" do
      notification = %{"jsonrpc" => "2.0", "method" => "notifications/initialized"}

      assert Server.handle_line(Jason.encode!(notification), @data) == nil
    end

    test "When ping is sent Then an empty result is returned" do
      assert call_line(request("ping"))["result"] == %{}
    end
  end

  describe "Given a client lists tools" do
    test "When tools/list is sent Then all ten query tools are returned" do
      names = call_line(request("tools/list"))["result"]["tools"] |> Enum.map(& &1["name"])

      assert "search_matches" in names
      assert "team_overview" in names
      assert length(names) == 10
    end
  end

  describe "Given a client calls a tool" do
    test "When a valid call is made Then the text content is returned as a success result" do
      result =
        call_line(
          request("tools/call", %{"name" => "team_record", "arguments" => %{"team" => "Alpha"}})
        )["result"]

      assert result["isError"] == false
      assert [%{"type" => "text", "text" => text}] = result["content"]
      assert text =~ "Alpha (all competitions):"
    end

    test "When the arguments are invalid Then the result is flagged as an error, not a JSON-RPC error" do
      response = call_line(request("tools/call", %{"name" => "team_record", "arguments" => %{}}))

      assert response["result"]["isError"] == true
      refute Map.has_key?(response, "error")
    end

    test "When no arguments object is given Then the call still runs with empty arguments" do
      response = call_line(request("tools/call", %{"name" => "league_stats"}))

      assert response["result"]["isError"] == false
    end
  end

  describe "Given malformed or unsupported requests" do
    test "When the JSON is invalid Then a parse error is returned with a null id" do
      response = "{not json" |> Server.handle_line(@data) |> Jason.decode!()

      assert response["error"]["code"] == -32700
      assert response["id"] == nil
    end

    test "When the method is unknown Then method-not-found is returned" do
      response = call_line(request("resources/list"))

      assert response["error"]["code"] == -32601
      assert response["error"]["message"] == "Method not found: resources/list"
    end

    test "When a message has no method Then an invalid request error is returned" do
      response = "[1, 2]" |> Server.handle_line(@data) |> Jason.decode!()

      assert response["error"]["code"] == -32600
    end

    test "When the line is blank Then nothing is sent back" do
      assert Server.handle_line("   \n", @data) == nil
    end
  end
end
