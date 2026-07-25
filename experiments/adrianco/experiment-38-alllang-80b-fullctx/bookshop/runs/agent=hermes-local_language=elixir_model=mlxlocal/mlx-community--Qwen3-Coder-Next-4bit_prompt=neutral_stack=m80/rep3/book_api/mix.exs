defmodule BookAPI.MixProject do
  use Mix.Project

  def project do
    [
      app: :book_api,
      version: "0.1.0",
      elixir: "~> 1.15",
      start_permanent: Mix.env() == :prod,
      deps: deps()
    ]
  end

  def application do
    [
      extra_applications: [:logger],
      mod: {BookAPI.Application, []}
    ]
  end

  defp deps do
    [
      # Plug for HTTP handling
      {:plug, "~> 1.14"},
      {:plug_cowboy, "~> 2.5"},
      
      # Ecto for database access
      {:ecto, "~> 3.10"},
      {:ecto_sql, "~> 3.10"},
      {:ecto_sqlite3, "~> 0.10"},
      
      # JSON encoding
      {:jason, "~> 1.4"},
      
      # Logger
      {:logger, "~> 1.0"},
      
      # Test dependencies
      {:ex_unit_failures, "~> 0.3", only: :test}
    ]
  end
end
