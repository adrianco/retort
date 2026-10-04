defmodule Mix.Tasks.Soccer.Mcp do
  @shortdoc "Runs the Brazilian soccer MCP server on stdio"
  @moduledoc """
  Runs the MCP server on stdio.

      mix soccer.mcp [DATA_DIR]

  `DATA_DIR` defaults to `$BRAZILIAN_SOCCER_DATA_DIR` or `data/kaggle`.
  """
  use Mix.Task

  @impl true
  def run(args) do
    Mix.Task.run("app.start")
    BrazilianSoccer.CLI.main(args)
  end
end
