defmodule BrazilianSoccerMcp.CLI do
  @moduledoc "Executable stdio entrypoint for the MCP server."

  @doc "Starts the JSON-RPC MCP transport when invoked by the generated escript."
  def main(_args) do
    {:ok, _started} = Application.ensure_all_started(:brazilian_soccer_mcp)
    BrazilianSoccerMcp.MCP.run()
  end
end
