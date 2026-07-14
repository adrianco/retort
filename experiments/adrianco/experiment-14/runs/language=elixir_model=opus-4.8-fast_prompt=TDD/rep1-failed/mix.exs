defmodule BrasilSoccer.MixProject do
  use Mix.Project

  def project do
    [
      app: :brasil_soccer,
      version: "0.1.0",
      elixir: "~> 1.17",
      start_permanent: Mix.env() == :prod,
      elixirc_paths: elixirc_paths(Mix.env()),
      deps: deps()
    ]
  end

  def application do
    [
      extra_applications: [:logger],
      mod: {BrasilSoccer.Application, []}
    ]
  end

  defp elixirc_paths(:test), do: ["lib", "test/support"]
  defp elixirc_paths(_), do: ["lib"]

  # No external dependencies: CSV parsing is hand-rolled and JSON is provided
  # by the built-in Elixir `JSON` module (Elixir >= 1.18).
  defp deps do
    []
  end
end
