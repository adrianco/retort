defmodule BrSoccer.MixProject do
  use Mix.Project

  def project do
    [
      app: :br_soccer,
      version: "1.0.0",
      elixir: "~> 1.16",
      elixirc_paths: elixirc_paths(Mix.env()),
      start_permanent: Mix.env() == :prod,
      escript: [main_module: BrSoccer.MCP.CLI],
      deps: deps()
    ]
  end

  def application do
    [
      extra_applications: [:logger],
      mod: {BrSoccer.Application, []}
    ]
  end

  defp deps do
    [
      {:jason, "~> 1.4"}
    ]
  end

  defp elixirc_paths(:test), do: ["lib", "test/support"]
  defp elixirc_paths(_), do: ["lib"]
end
