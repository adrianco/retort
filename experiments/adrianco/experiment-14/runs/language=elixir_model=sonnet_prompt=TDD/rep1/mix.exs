defmodule BrazilianSoccer.MixProject do
  use Mix.Project

  def project do
    [
      app: :brazilian_soccer,
      version: "0.1.0",
      elixir: "~> 1.14",
      start_permanent: Mix.env() == :prod,
      deps: deps()
    ]
  end

  def application do
    [
      extra_applications: [:logger],
      mod: {BrazilianSoccer.Application, []}
    ]
  end

  def cli do
    [main_module: BrazilianSoccer]
  end

  defp deps do
    [
      {:jason, "~> 1.4"},
      {:nimble_csv, "~> 1.2"}
    ]
  end
end
