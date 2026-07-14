defmodule BrazilianSoccer.MCP.CLI do
  @moduledoc """
  stdio transport for the MCP server (the escript entry point).

  Messages are newline-delimited JSON-RPC objects read from standard input;
  responses are written, one JSON object per line, to standard output.
  Diagnostics go to standard error so they never corrupt the protocol stream.
  """

  alias BrazilianSoccer.{DataLoader, Dataset}
  alias BrazilianSoccer.MCP.Server

  @parse_error -32_700

  @doc "Escript entry point: load data, then serve requests from stdin."
  @spec main([String.t()]) :: :ok
  def main(args) do
    dir = data_dir(args)
    log("Loading Brazilian soccer data from #{dir} ...")
    dataset = DataLoader.load!(dir)

    log(
      "Ready: #{length(dataset.matches)} matches, #{length(dataset.players)} players. " <>
        "Listening on stdio."
    )

    loop(dataset)
  end

  @doc """
  Process a single input line against `dataset`. Returns `{:reply, json}` with
  the response to send, or `:noreply` for notifications.
  """
  @spec process_line(binary(), Dataset.t()) :: {:reply, binary()} | :noreply
  def process_line(line, %Dataset{} = dataset) do
    case decode(line) do
      {:ok, request} -> respond(Server.handle(request, dataset))
      {:error, _} -> {:reply, encode(parse_error())}
    end
  end

  defp loop(dataset) do
    case IO.read(:stdio, :line) do
      :eof ->
        :ok

      {:error, reason} ->
        log("stdin error: #{inspect(reason)}")
        :ok

      line ->
        line = String.trim_trailing(line, "\n")

        if line != "" do
          case process_line(line, dataset) do
            {:reply, json} -> IO.puts(json)
            :noreply -> :ok
          end
        end

        loop(dataset)
    end
  end

  defp respond(nil), do: :noreply
  defp respond(response), do: {:reply, encode(response)}

  defp decode(line) do
    JSON.decode(line)
  rescue
    _ -> {:error, :invalid}
  end

  defp encode(map), do: JSON.encode!(map)

  defp parse_error do
    %{
      "jsonrpc" => "2.0",
      "id" => nil,
      "error" => %{"code" => @parse_error, "message" => "Parse error"}
    }
  end

  defp data_dir([dir | _]) when is_binary(dir), do: dir

  defp data_dir(_) do
    System.get_env("DATA_DIR", DataLoader.default_dir())
  end

  defp log(message), do: IO.puts(:stderr, "[brazilian-soccer-mcp] #{message}")
end
