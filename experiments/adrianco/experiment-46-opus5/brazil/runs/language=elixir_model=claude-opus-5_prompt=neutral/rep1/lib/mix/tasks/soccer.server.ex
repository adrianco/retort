defmodule Mix.Tasks.Soccer.Server do
  @shortdoc "Run the Brazilian soccer MCP server on stdio"

  @moduledoc """
  Run the MCP server, speaking newline delimited JSON-RPC on stdin/stdout.

      mix soccer.server

  Point an MCP client at it with:

      {"command": "mix", "args": ["soccer.server"], "cwd": "<this directory>"}
  """

  use Mix.Task

  @requirements ["app.start"]

  @impl true
  def run(_argv) do
    # Loading before the first request keeps `initialize` fast.
    _ = BrazilianSoccer.Repo.graph()
    BrazilianSoccer.MCP.Stdio.run()
  end
end
