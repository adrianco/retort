defmodule Mix.Tasks.Mcp.Server do
  @shortdoc "Start the Brazilian Soccer MCP server on stdio"

  @moduledoc """
  Starts the MCP server, speaking JSON-RPC 2.0 over stdio.

      mix mcp.server [--data-dir DIR]

  Register in an MCP client (e.g. Claude Desktop / Claude Code) with
  command `mix` and args `["mcp.server"]`, cwd set to this project.
  """

  use Mix.Task

  @impl Mix.Task
  def run(argv) do
    Mix.Task.run("app.start")
    {opts, _rest, _invalid} = OptionParser.parse(argv, strict: [data_dir: :string])
    BrazilianSoccerMcp.Stdio.start(opts[:data_dir])
  end
end
