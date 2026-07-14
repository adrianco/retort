defmodule BrazilianSoccer do
  @moduledoc """
  Brazilian Soccer MCP Server.

  Provides MCP (Model Context Protocol) tools for querying Brazilian soccer data,
  including match results from Brasileirão, Copa do Brasil, Copa Libertadores,
  and FIFA player data.

  ## Running the server

      mix run --no-halt
      # or as an escript:
      ./brazilian_soccer

  The server communicates over stdio using JSON-RPC 2.0.
  """

  def main(args \\ []) do
    _ = args
    BrazilianSoccer.MCP.Server.run()
  end
end
