defmodule BrazilianSoccerMcp.Stdio do
  @moduledoc """
  stdio transport for the MCP server: reads newline-delimited JSON-RPC
  messages from stdin and writes responses to stdout. All diagnostics go to
  stderr (stdout carries protocol messages only).
  """

  alias BrazilianSoccerMcp.{DataStore, Server}

  def start(data_dir \\ nil) do
    # Take stdio out of unicode translation mode: JSON-RPC messages are raw
    # UTF-8 bytes, and latin1 (byte passthrough) keeps binread/binwrite exact.
    :io.setopts(:standard_io, binary: true, encoding: :latin1)

    IO.write(:stderr, "[brazilian-soccer-mcp] loading datasets...\n")
    {micros, :ok} = :timer.tc(fn -> DataStore.ensure_loaded!(data_dir) end)

    IO.write(
      :stderr,
      "[brazilian-soccer-mcp] ready: #{length(DataStore.matches())} matches, " <>
        "#{length(DataStore.players())} players loaded in #{div(micros, 1000)}ms\n"
    )

    loop()
  end

  defp loop do
    case IO.binread(:stdio, :line) do
      :eof ->
        :ok

      {:error, reason} ->
        IO.write(:stderr, "[brazilian-soccer-mcp] stdin error: #{inspect(reason)}\n")
        :ok

      line ->
        case Server.handle_line(line) do
          {:reply, json} -> IO.binwrite(:stdio, [json, "\n"])
          :noreply -> :ok
        end

        loop()
    end
  end
end
