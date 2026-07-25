defmodule BookApi.MixProject do
  use Mix.Project

  def project do
    [
      app: :book_api,
      version: "0.1.0",
      elixir: "~> 1.20",
      start_permanent: Mix.env() == :prod,
      deps: deps()
    ]
  end

  # Run "mix help compile.app" to learn about applications.
  def application do
    [
      extra_applications: [:logger],
      mod: {BookApi.Application, []}
    ]
  end

  # Run "mix help deps" to learn about dependencies.
  defp deps do
    [
      # Phoenix framework
      {:phoenix, "~> 1.7"},
      {:phoenix_html, "~> 4.0"},
      {:phoenix_live_view, "~> 0.20.2"},
      {:floki, ">= 0.30.0", only: :test},
      {:phoenix_live_dashboard, "~> 0.8.3"},
      {:esbuild, "~> 0.7", runtime: false},
      {:phoenix_view, "~> 2.0"},
      
      # Database with SQLite
      {:sqlite3, "~> 1.6"},
      {:ecto_sqlite3, "~> 0.14.0"},
      
      # HTTP
      {:plug_cowboy, "~> 2.7"},
      {:jason, "~> 1.4"},
      
      # Development tools
      {:dialyxir, "~> 1.4", only: [:dev], runtime: false},
      {:earmark, "~> 1.4", only: :dev},
      {:ex_doc, "~> 0.34", only: :dev, runtime: false}
    ]
  end
end
