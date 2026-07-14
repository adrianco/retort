defmodule BrazilianSoccerMcp do
  @moduledoc """
  Brazilian Soccer MCP Server.

  Starts the MCP server that communicates via stdio (JSON-RPC 2.0).
  """

  def main(_args \\ []) do
    BrazilianSoccerMcp.McpServer.run()
  end
end
