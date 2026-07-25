defmodule BookApi.MixProject do
  use Mix.Project

  def project do
    [
      app: :book_api,
      version: "0.1.0",
      elixir: "~> 1.18",
      start_permanent: Mix.env() == :prod,
      deps: deps()
    ]
  end

  # Run "mix help compile.app" to learn about applications.
  def application do
    [
      extra_applications: [:gettext, :logger],
      mod: {BookApi.Application, []}
    ]
  end

  # Run "mix help deps" to learn about dependencies.
  defp deps do
    [
      {:gettext, "~> 0.24"},
      {:phoenix, "~> 1.7"},
      {:phoenix_ecto, "~> 4.4"},
      {:ecto_sql, "~> 3.10"},
      {:sqlite3, "~> 1.1"},
      {:jason, "~> 1.4"},
      {:plug_cowboy, "~> 2.5"},
      {:ecto_sqlite3, "~> 0.10"}
    ]
  end
end
