defmodule Mix.Tasks.Mcp do
  use Mix.Task
  @shortdoc "Runs the Brazilian soccer MCP stdio server"
  def run(_), do: BrazilianSoccerMcp.Server.run()
end
