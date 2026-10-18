defmodule BrazilianSoccerMcp.MixProject do
  use Mix.Project

  def project,
    do: [
      app: :brazilian_soccer_mcp,
      version: "0.1.0",
      elixir: "~> 1.15",
      start_permanent: Mix.env() == :prod
    ]

  def application, do: [extra_applications: [:logger]]
end
