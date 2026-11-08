defmodule BookCollection.MixProject do
  use Mix.Project

  def project do
    [app: :book_collection, version: "0.1.0", elixir: "~> 1.15", deps: deps()]
  end

  def application do
    [extra_applications: [:logger], mod: {BookCollection.Application, []}]
  end

  defp deps do
    [
      {:bandit, "~> 1.0"},
      {:plug, "~> 1.0"},
      {:jason, "~> 1.4"},
      {:ecto_sqlite3, "~> 0.24"}
    ]
  end
end
