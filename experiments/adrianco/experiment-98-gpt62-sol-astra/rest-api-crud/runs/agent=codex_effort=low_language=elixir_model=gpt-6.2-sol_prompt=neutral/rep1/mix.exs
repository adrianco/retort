defmodule BookCollection.MixProject do
  use Mix.Project

  def project do
    [
      app: :book_collection,
      version: "0.1.0",
      elixir: "~> 1.18",
      deps: [{:plug, "~> 1.20"}, {:bandit, "~> 1.14"}, {:exqlite, "~> 0.43"}]
    ]
  end

  def application do
    [extra_applications: [:logger], mod: {BookCollection.Application, []}]
  end
end
