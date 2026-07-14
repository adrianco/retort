defmodule BookApi.MixProject do
  use Mix.Project

  def project do
    [
      app: :book_api,
      version: "0.1.0",
      elixir: "~> 1.20",
      elixirc_paths: elixirc_paths(Mix.env()),
      start_permanent: Mix.env() == :prod,
      deps: deps()
    ]
  end

  def application do
    [
      mod: {BookApi.Application, []},
      extra_applications: [:logger, :runtime_tools]
    ]
  end

  defp elixirc_paths(:test), do: ["lib", "test/support"]
  defp elixirc_paths(_), do: ["lib"]

  defp deps do
    [
      {:phoenix, "~> 1.8.9"},
      {:phoenix_view, "~> 2.0"},
      {:jason, "~> 1.4"},
      {:plug, "~> 1.15"},
      {:cowboy, "~> 2.13"},
      {:ecto, "~> 3.11"},
      {:ecto_sqlite3, "~> 0.24.1"},
      {:ex_doc, "~> 0.31", only: :dev, runtime: false}
    ]
  end
end
