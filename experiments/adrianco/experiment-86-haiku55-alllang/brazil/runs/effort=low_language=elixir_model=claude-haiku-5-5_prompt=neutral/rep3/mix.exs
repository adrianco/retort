defmodule BrazilianSoccerMcp.MixProject do
  use Mix.Project

  def project do
    [
      app: :brazilian_soccer_mcp,
      version: "0.1.0",
      elixir: "~> 1.20",
      start_permanent: Mix.env() == :prod,
      deps: deps(),
      escript: [main_module: BrazilianSoccerMcp.CLI, name: "brazilian_soccer_mcp"]
    ]
  end

  def application do
    [
      mod: {BrazilianSoccerMcp.Application, []},
      extra_applications: [:logger]
    ]
  end

  defp deps do
    [
      {:jason, "~> 1.4"}
    ]
  end
end
