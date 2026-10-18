defmodule BrazilianSoccer.CLI do
  @moduledoc """
  Entry point for the MCP server. Reads newline-delimited JSON-RPC requests
  from stdin and writes responses to stdout. Logs go to stderr so they never
  corrupt the protocol stream.

  Usage:

      brazilian_soccer [--data-dir data/kaggle]

  Or without building an escript:

      mix run -e 'BrazilianSoccer.CLI.main(["--data-dir", "data/kaggle"])'
  """

  alias BrazilianSoccer.{Data, Server}

  @default_data_dir "data/kaggle"

  @doc "Loads the datasets and serves MCP requests until stdin closes."
  def main(args \\ []) do
    {opts, _rest, _invalid} =
      OptionParser.parse(args, strict: [data_dir: :string, help: :boolean])

    if opts[:help] do
      IO.puts(:stderr, "usage: brazilian_soccer [--data-dir #{@default_data_dir}]")
    else
      dir = Keyword.get(opts, :data_dir, @default_data_dir)
      data = Data.load(dir)

      IO.puts(
        :stderr,
        "brazilian-soccer: loaded #{length(data.matches)} matches and #{length(data.players)} players from #{dir}"
      )

      serve(data)
    end
  end

  # The standard streams are unicode devices, so text I/O (not binread/binwrite)
  # is what keeps UTF-8 bytes intact in both directions.
  defp serve(data) do
    case IO.read(:stdio, :line) do
      line when is_binary(line) ->
        case String.trim(line) do
          "" -> :ok
          request -> respond(Server.handle_line(request, data))
        end

        serve(data)

      _eof ->
        :ok
    end
  end

  defp respond(nil), do: :ok

  defp respond(response) do
    IO.write(:stdio, [JSON.encode!(response), "\n"])
  end
end
