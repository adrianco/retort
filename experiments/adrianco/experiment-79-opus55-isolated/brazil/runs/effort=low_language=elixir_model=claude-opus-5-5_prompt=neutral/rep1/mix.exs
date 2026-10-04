defmodule BrazilianSoccer.MixProject do
  use Mix.Project

  def project do
    [
      app: :brazilian_soccer,
      version: "0.1.0",
      elixir: "~> 1.18",
      start_permanent: Mix.env() == :prod,
      escript: [main_module: BrazilianSoccer.CLI, name: "brazilian_soccer_mcp"],
      deps: []
    ]
  end

  def application do
    [extra_applications: [:logger]]
  end
end
