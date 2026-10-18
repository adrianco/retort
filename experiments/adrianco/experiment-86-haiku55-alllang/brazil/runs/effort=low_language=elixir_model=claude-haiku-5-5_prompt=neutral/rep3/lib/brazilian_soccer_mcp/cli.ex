defmodule BrazilianSoccerMcp.CLI do
  @moduledoc """
  Entry point for the packaged escript: `./brazilian_soccer_mcp`.

  Logs go to stderr, because stdout carries the MCP protocol. Set
  `SOCCER_DATA_DIR` to point at a directory other than `data/kaggle`.
  """

  alias BrazilianSoccerMcp.Stdio

  def main(_args \\ []) do
    # The default logger handler writes to stdout, which would corrupt the protocol stream.
    :logger.update_handler_config(:default, :config, %{type: :standard_error})
    {:ok, _apps} = Application.ensure_all_started(:brazilian_soccer_mcp)
    Stdio.run()
  end
end
