defmodule BrazilianSoccer.MixProject do
  use Mix.Project

  def project do
    [
      app: :brazilian_soccer,
      version: "0.1.0",
      elixir: "~> 1.16",
      start_permanent: Mix.env() == :prod,
      deps: [],
      escript: [main_module: BrazilianSoccer.MCP]
    ]
  end

  def application, do: [extra_applications: [:logger]]
end
