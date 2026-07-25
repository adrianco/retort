defmodule BookApi.MixProject do
  use Mix.Project

  def project do
    [
      app: :book_api,
      version: "0.1.0",
      elixir: "~> 1.20",
      start_permanent: Mix.env() == :prod,
      elixirc_paths: elixirc_paths(Mix.env()),
      aliases: aliases(),
      deps: deps()
    ]
  end

  def application do
    [
      extra_applications: [:logger],
      mod: {BookApi.Application, []}
    ]
  end

  defp elixirc_paths(:test), do: ["lib", "test/support"]
  defp elixirc_paths(_), do: ["lib"]

  defp deps do
    [
      {:bandit, "~> 1.5"},
      {:plug, "~> 1.16"},
      {:jason, "~> 1.4"},
      {:ecto_sql, "~> 3.12"},
      {:ecto_sqlite3, "~> 0.17"}
    ]
  end

  defp aliases do
    [
      setup: ["deps.get", "ecto.setup"],
      "ecto.setup": ["ecto.create --quiet", "ecto.migrate"],
      "ecto.reset": ["ecto.drop", "ecto.setup"]
      # No ecto.* steps before `test`: SQLite creates the database file on first
      # connect, and test/test_helper.exs migrates the repo that `mix test`
      # already started. Restarting the repo between mix tasks makes the
      # outgoing connection race the incoming one for the database lock.
    ]
  end
end
