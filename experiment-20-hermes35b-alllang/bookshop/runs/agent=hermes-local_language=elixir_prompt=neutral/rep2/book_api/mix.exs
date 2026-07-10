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

  def application do
    [
      mod: {BookApi.Server, []},
      extra_applications: [:logger]
    ]
  end

  defp deps do
    [
      {:plug_cowboy, "~> 2.7"}
    ]
  end
end
