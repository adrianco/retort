defmodule BrazilianSoccerMcp.MixProject do
  use Mix.Project

  def project do
    [
      app: :brazilian_soccer_mcp,
      version: "0.1.0",
      elixir: "~> 1.18",
      start_permanent: Mix.env() == :prod,
      escript: [main_module: BrazilianSoccerMcp.CLI],
      deps: []
    ]
  end

  def application do
    [
      extra_applications: [:logger]
    ]
  end
end
