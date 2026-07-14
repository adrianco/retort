defmodule BrazilianSoccer.MixProject do
  use Mix.Project

  def project do
    [
      app: :brazilian_soccer,
      version: "0.1.0",
      elixir: "~> 1.15",
      start_permanent: Mix.env() == :prod,
      elixirc_paths: elixirc_paths(Mix.env()),
      escript: [main_module: BrazilianSoccer.CLI],
      deps: deps()
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
end
