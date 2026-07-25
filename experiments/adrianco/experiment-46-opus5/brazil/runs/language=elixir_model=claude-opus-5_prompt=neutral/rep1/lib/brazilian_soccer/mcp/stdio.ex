defmodule BrazilianSoccer.MCP.Stdio do
  @moduledoc """
  MCP stdio transport: newline delimited JSON-RPC on stdin/stdout.

  One JSON message per line in, one per line out, nothing else on stdout —
  logs go to stderr so they cannot corrupt the protocol stream.
  """

  alias BrazilianSoccer.MCP.Server

  @doc """
  Read requests from `device` until EOF, writing responses to `output`.
  """
  @spec run(keyword) :: :ok
  def run(opts \\ []) do
    input = Keyword.get(opts, :input, :stdio)
    output = Keyword.get(opts, :output, :stdio)

    :ok = configure(input, output)
    loop(input, output)
  end

  defp configure(:stdio, _output) do
    :io.setopts(:standard_io, binary: true, encoding: :unicode)
    :ok
  end

  defp configure(_input, _output), do: :ok

  defp loop(input, output) do
    case IO.read(input, :line) do
      :eof ->
        :ok

      {:error, reason} ->
        log("stdin error: #{inspect(reason)}")
        :ok

      line ->
        line
        |> String.trim()
        |> handle_line()
        |> case do
          nil -> :ok
          response -> IO.write(output, response <> "\n")
        end

        loop(input, output)
    end
  end

  @doc """
  Decode a line, handle it and encode the response (`nil` when there is none).
  """
  @spec handle_line(binary) :: binary | nil
  def handle_line(""), do: nil

  def handle_line(line) do
    case Jason.decode(line) do
      {:ok, message} ->
        case Server.handle(message) do
          nil -> nil
          response -> Jason.encode!(response)
        end

      {:error, error} ->
        log("could not parse request: #{Exception.message(error)}")

        Jason.encode!(%{
          "jsonrpc" => "2.0",
          "id" => nil,
          "error" => %{"code" => -32_700, "message" => "parse error"}
        })
    end
  end

  defp log(message), do: IO.puts(:standard_error, "[brazilian-soccer] #{message}")
end
