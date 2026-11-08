defmodule Books.MixProject do
  use Mix.Project

  def project do
    [
      app: :books,
      version: "0.1.0",
      elixir: "~> 1.15",
      start_permanent: Mix.env() == :prod,
      deps: [
        {:bandit, "~> 1.0"},
        {:plug, "~> 1.0"},
        {:jason, "~> 1.4"},
        {:ecto_sqlite3, "~> 0.24"}
      ]
    ]
  end

  def application do
    [extra_applications: [:logger], mod: {Books.Application, []}]
  end
end
