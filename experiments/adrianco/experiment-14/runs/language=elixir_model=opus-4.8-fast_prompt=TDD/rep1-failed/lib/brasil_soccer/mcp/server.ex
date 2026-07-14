defmodule BrasilSoccer.MCP.Server do
  @moduledoc """
  The stdio transport for the MCP server.

  It reads newline-delimited JSON-RPC messages from standard input, dispatches
  each through `BrasilSoccer.MCP.Protocol`, and writes the JSON responses to
  standard output (one per line). All logging goes to standard error so it never
  corrupts the protocol stream.

  `process_line/2` is the pure heart of the loop and is unit tested directly;
  `run/1` wires it to real IO.
  """

  alias BrasilSoccer.MCP.Protocol
  alias BrasilSoccer.Store

  @doc """
  Start the read/respond loop. Pulls the dataset from `BrasilSoccer.Store`
  (starting it if necessary) and blocks reading from stdin until EOF.
  """
  @spec run(keyword()) :: :ok
  def run(opts \\ []) do
    data = data(opts)
    io = Keyword.get(opts, :io, :stdio)
    log("Brazil Soccer MCP server ready (#{length(data.matches)} matches, #{length(data.players)} players)")
    loop(io, data)
  end

  defp loop(io, data) do
    case IO.read(io, :line) do
      :eof ->
        :ok

      {:error, reason} ->
        log("read error: #{inspect(reason)}")
        :ok

      line ->
        case process_line(line, data) do
          {:reply, json} -> IO.puts(io, json)
          :noreply -> :ok
        end

        loop(io, data)
    end
  end

  @doc """
  Process one input line. Returns `{:reply, json}` to send back, or `:noreply`
  for blank lines and notifications.
  """
  @spec process_line(String.t(), Protocol.data() | map()) :: {:reply, String.t()} | :noreply
  def process_line(line, data) do
    case String.trim(line) do
      "" ->
        :noreply

      trimmed ->
        case JSON.decode(trimmed) do
          {:ok, request} -> respond(Protocol.handle(request, data))
          {:error, _} -> {:reply, encode(parse_error())}
        end
    end
  end

  defp respond(nil), do: :noreply
  defp respond(response), do: {:reply, encode(response)}

  defp encode(map), do: JSON.encode!(map)

  defp parse_error do
    %{"jsonrpc" => "2.0", "id" => nil, "error" => %{"code" => -32700, "message" => "Parse error"}}
  end

  defp data(opts) do
    case Keyword.fetch(opts, :data) do
      {:ok, data} ->
        data

      :error ->
        ensure_store_started()
        %{matches: Store.matches(), players: Store.players()}
    end
  end

  defp ensure_store_started do
    case Process.whereis(Store) do
      nil -> {:ok, _} = Store.start_link([])
      _pid -> :ok
    end
  end

  defp log(message), do: IO.puts(:stderr, "[brazil-soccer-mcp] #{message}")
end
