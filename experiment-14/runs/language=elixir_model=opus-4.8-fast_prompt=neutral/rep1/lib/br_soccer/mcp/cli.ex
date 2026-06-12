defmodule BrSoccer.MCP.CLI do
  @moduledoc """
  Entry point for the MCP server escript / `mix run`.

  Ensures the application (and thus the data) is loaded, then hands control to
  the stdio serve loop. A leading `--ask` flag runs a single tool call from the
  command line — handy for a quick manual check without an MCP client.
  """

  alias BrSoccer.MCP.{Server, Tools}

  def main(argv \\ []) do
    {:ok, _} = Application.ensure_all_started(:br_soccer)

    case argv do
      ["--ask", tool | rest] ->
        ask(tool, rest)

      _ ->
        Server.serve()
    end
  end

  # Parse `key=value` pairs into a string-keyed argument map for one tool call.
  defp ask(tool, pairs) do
    args =
      Enum.reduce(pairs, %{}, fn pair, acc ->
        case String.split(pair, "=", parts: 2) do
          [k, v] -> Map.put(acc, k, v)
          _ -> acc
        end
      end)

    case Tools.call(tool, args) do
      {:ok, text} -> IO.puts(text)
      {:error, msg} -> IO.puts(:stderr, msg)
    end
  end
end
