defmodule BrazilianSoccer.CLI do
  @moduledoc "Entry point of the `brazilian_soccer_mcp` escript: serves MCP on stdio."

  def main(args) do
    case args do
      [dir | _] -> System.put_env("BRAZILIAN_SOCCER_DATA_DIR", dir)
      _ -> :ok
    end

    :io.setopts(:standard_io, encoding: :unicode, binary: true)
    data = BrazilianSoccer.Data.get()

    IO.puts(
      :stderr,
      "brazilian-soccer MCP server ready: #{length(data.matches)} matches, #{length(data.players)} players (#{data.dir})"
    )

    BrazilianSoccer.MCP.Server.run()
  end
end
