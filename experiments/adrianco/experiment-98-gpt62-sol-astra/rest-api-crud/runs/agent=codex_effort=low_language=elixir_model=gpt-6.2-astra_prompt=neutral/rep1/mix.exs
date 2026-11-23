defmodule Books.MixProject do
  use Mix.Project

  def project do
    [
      app: :books,
      version: "0.1.0",
      elixir: "~> 1.18",
      deps: [{:bandit, "~> 1.14.0"}, {:plug, "~> 1.20.0"}]
    ]
  end

  def application, do: [mod: {Books.Application, []}, extra_applications: [:logger]]
end
