defmodule BrazilianSoccer.MixProject do
  use Mix.Project

  @version "1.0.0"

  def project do
    [
      app: :brazilian_soccer,
      version: @version,
      elixir: "~> 1.15",
      start_permanent: Mix.env() == :prod,
      elixirc_paths: elixirc_paths(Mix.env()),
      deps: deps(),
      escript: [main_module: BrazilianSoccer.CLI, name: "brazilian_soccer_mcp"],
      description: "MCP knowledge-graph server for Brazilian soccer data",
      aliases: aliases()
    ]
  end

  def application do
    [
      extra_applications: [:logger],
      mod: {BrazilianSoccer.Application, []}
    ]
  end

  defp elixirc_paths(:test), do: ["lib", "test/support"]
  defp elixirc_paths(_), do: ["lib"]

  defp deps do
    [
      {:jason, "~> 1.4"},
      {:nimble_csv, "~> 1.2"}
    ]
  end

  defp aliases do
    [
      server: ["soccer.server"],
      demo: ["soccer.demo"]
    ]
  end
end
