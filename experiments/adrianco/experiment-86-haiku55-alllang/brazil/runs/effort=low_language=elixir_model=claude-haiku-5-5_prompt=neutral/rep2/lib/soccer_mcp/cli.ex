defmodule SoccerMcp.CLI do
  @moduledoc """
  Entry point for the stdio MCP server.

      soccer_mcp [--data-dir PATH]

  Loads the datasets once, then reads JSON-RPC requests from stdin, one per
  line, and writes responses to stdout. Diagnostics go to stderr only.
  The data directory defaults to `$SOCCER_DATA_DIR`, then `data/kaggle`.
  """

  alias SoccerMcp.{Server, Store}

  @default_data_dir "data/kaggle"

  @doc "Escript entry point."
  @spec main([String.t()]) :: :ok
  def main(argv) do
    {opts, _rest, _invalid} = OptionParser.parse(argv, strict: [data_dir: :string])

    dir = opts[:data_dir] || System.get_env("SOCCER_DATA_DIR") || @default_data_dir
    store = Store.load(dir)

    IO.puts(
      :stderr,
      "soccer_mcp ready: #{length(store.matches)} matches, #{length(store.players)} players"
    )

    serve(store, :stdio, :stdio)
  end

  @doc """
  Reads requests from `input` until end of input and writes each response
  line to `output`. Takes IO devices so tests can drive it with `StringIO`.
  """
  @spec serve(Store.t(), IO.device(), IO.device()) :: :ok
  def serve(store, input, output) do
    case IO.read(input, :line) do
      :eof ->
        :ok

      {:error, reason} ->
        IO.puts(:stderr, "read error: #{inspect(reason)}")
        :ok

      line ->
        case String.trim(line) do
          "" -> :ok
          request -> request |> Server.handle_line(store) |> write(output)
        end

        serve(store, input, output)
    end
  end

  defp write(nil, _output), do: :ok
  defp write(response, output), do: IO.write(output, response <> "\n")
end
