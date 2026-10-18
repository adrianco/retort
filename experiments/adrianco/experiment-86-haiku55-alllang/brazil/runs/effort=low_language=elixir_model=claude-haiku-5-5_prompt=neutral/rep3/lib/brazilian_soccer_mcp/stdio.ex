defmodule BrazilianSoccerMcp.Stdio do
  @moduledoc """
  stdio transport for MCP. Reads newline-delimited JSON-RPC from stdin and
  writes one response line per request to stdout.
  """

  alias BrazilianSoccerMcp.{Server, Store}

  @doc "Serves requests until stdin closes. `data` defaults to the loaded store snapshot."
  def run(data \\ nil) do
    loop(data || Store.snapshot())
  end

  defp loop(data) do
    case IO.read(:stdio, :line) do
      line when is_binary(line) ->
        case Server.handle_line(line, data) do
          nil -> :ok
          response -> IO.write(response <> "\n")
        end

        loop(data)

      _eof_or_error ->
        :ok
    end
  end
end
