defmodule SoccerMcp.CLITest do
  # Feature: the stdio loop reads requests and writes only protocol lines
  use ExUnit.Case, async: true

  import ExUnit.CaptureIO

  alias SoccerMcp.{CLI, Store}

  @fixtures Path.expand("../fixtures", __DIR__)

  test "Scenario: a session of requests produces one line per request" do
    # Given a store and a client session with a notification in the middle
    capture_io(:stderr, fn -> send(self(), {:store, Store.load(@fixtures)}) end)
    assert_received {:store, store}

    input =
      Enum.join(
        [
          ~s({"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}),
          ~s({"jsonrpc":"2.0","method":"notifications/initialized"}),
          "",
          ~s({"jsonrpc":"2.0","id":2,"method":"ping"})
        ],
        "\n"
      ) <> "\n"

    # When the loop runs over that input
    {:ok, output} = StringIO.open("")
    {:ok, in_dev} = StringIO.open(input)
    :ok = CLI.serve(store, in_dev, output)

    {_remaining_input, written} = StringIO.contents(output)

    # Then exactly two response lines are written, each valid JSON
    lines = written |> String.split("\n", trim: true)
    assert length(lines) == 2
    assert [%{"id" => 1}, %{"id" => 2}] = Enum.map(lines, &Jason.decode!/1)
  end
end
