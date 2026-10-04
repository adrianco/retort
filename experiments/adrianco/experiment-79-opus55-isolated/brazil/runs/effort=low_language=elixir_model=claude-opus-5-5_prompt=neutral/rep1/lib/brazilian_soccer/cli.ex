defmodule BrazilianSoccer.CLI do
  @moduledoc "Entry point of the `brazilian_soccer_mcp` escript: runs the MCP server on stdio."

  def main(args) do
    case args do
      [dir | _] -> System.put_env("BRAZILIAN_SOCCER_DATA_DIR", dir)
      _ -> :ok
    end

    :logger.update_handler_config(:default, :config, %{type: :standard_error})
    :io.setopts(:standard_io, encoding: :unicode)
    # Load eagerly so the first query is fast and a bad data dir fails early.
    BrazilianSoccer.Store.load()
    BrazilianSoccer.MCP.Server.run()
  end
end
