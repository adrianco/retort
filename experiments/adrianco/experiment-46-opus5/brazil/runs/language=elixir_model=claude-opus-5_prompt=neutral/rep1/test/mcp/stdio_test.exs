defmodule BrazilianSoccer.MCP.StdioTest do
  @moduledoc """
  Feature: MCP stdio transport

  Scenario: A client speaks newline delimited JSON-RPC
    Given a line of JSON on stdin
    When the server handles it
    Then exactly one line of JSON comes back on stdout
  """

  use BrazilianSoccer.GraphCase, async: true

  alias BrazilianSoccer.MCP.Stdio

  describe "Scenario: one line in, one line out" do
    test "Given a request line Then a single JSON line comes back" do
      line = Jason.encode!(%{"jsonrpc" => "2.0", "id" => 7, "method" => "ping"})
      response = Stdio.handle_line(line)

      refute String.contains?(response, "\n")
      assert Jason.decode!(response) == %{"jsonrpc" => "2.0", "id" => 7, "result" => %{}}
    end

    test "Given a notification Then nothing is written" do
      line = Jason.encode!(%{"jsonrpc" => "2.0", "method" => "notifications/initialized"})
      assert Stdio.handle_line(line) == nil
    end

    test "Given a blank line Then nothing is written" do
      assert Stdio.handle_line("") == nil
    end

    test "Given malformed JSON Then a parse error comes back" do
      response = Stdio.handle_line("{not json")
      assert Jason.decode!(response)["error"]["code"] == -32_700
    end

    test "Given UTF-8 in the answer Then it survives the round trip" do
      line =
        Jason.encode!(%{
          "jsonrpc" => "2.0",
          "id" => 1,
          "method" => "tools/call",
          "params" => %{"name" => "team_profile", "arguments" => %{"team" => "Gremio"}}
        })

      text =
        Stdio.handle_line(line)
        |> Jason.decode!()
        |> get_in(["result", "content", Access.at(0), "text"])

      assert text =~ "Grêmio"
      assert text =~ "Rio Grande do Sul"
    end
  end

  describe "Scenario: a full session over pipes" do
    @tag :integration
    test "Given a client script Then initialize, tools/list and tools/call all work" do
      requests =
        [
          %{
            "jsonrpc" => "2.0",
            "id" => 1,
            "method" => "initialize",
            "params" => %{
              "protocolVersion" => "2025-06-18",
              "capabilities" => %{},
              "clientInfo" => %{"name" => "test-client", "version" => "1.0"}
            }
          },
          %{"jsonrpc" => "2.0", "method" => "notifications/initialized"},
          %{"jsonrpc" => "2.0", "id" => 2, "method" => "tools/list"},
          %{
            "jsonrpc" => "2.0",
            "id" => 3,
            "method" => "tools/call",
            "params" => %{
              "name" => "competition_champion",
              "arguments" => %{"competition" => "Brasileirão", "season" => 2019}
            }
          }
        ]
        |> Enum.map_join("", &(Jason.encode!(&1) <> "\n"))

      input_file = Path.join(System.tmp_dir!(), "brazilian_soccer_mcp_session.jsonl")
      File.write!(input_file, requests)
      on_exit(fn -> File.rm(input_file) end)

      {output, status} =
        System.cmd("sh", ["-c", "mix soccer.server < #{input_file}"],
          stderr_to_stdout: false,
          env: [{"MIX_ENV", "test"}]
        )

      assert status == 0

      responses =
        output
        |> String.split("\n", trim: true)
        |> Enum.map(&Jason.decode!/1)

      assert length(responses) == 3
      assert Enum.map(responses, & &1["id"]) == [1, 2, 3]
      assert hd(responses)["result"]["serverInfo"]["name"] == "brazilian-soccer"
      assert length(Enum.at(responses, 1)["result"]["tools"]) >= 20

      text = Enum.at(responses, 2)["result"]["content"] |> hd() |> Map.get("text")
      assert text =~ "Flamengo"
    end
  end
end
