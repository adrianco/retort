defmodule BrazilianSoccerMcp.MixProject do
  use Mix.Project

  def project,
    do: [
      app: :brazilian_soccer_mcp,
      version: "0.1.0",
      elixir: "~> 1.15",
      start_permanent: Mix.env() == :prod,
      # MCP clients launch servers as executables.  This makes
      # `mix escript.build` produce `./brazilian_soccer_mcp`, whose stdin and
      # stdout are owned by BrazilianSoccerMcp.Server.
      escript: [main_module: BrazilianSoccerMcp.Server]
    ]

  def application, do: [extra_applications: [:logger]]
end
