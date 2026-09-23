defmodule Books.MixProject do
  use Mix.Project

  def project do
    [app: :books, version: "0.1.0", elixir: "~> 1.15", start_permanent: Mix.env() == :prod, deps: deps()]
  end

  def application do
    [extra_applications: [:logger], mod: {Books.Application, []}]
  end

  defp deps do
    [{:plug, "~> 1.16"}, {:bandit, "~> 1.5"}, {:jason, "~> 1.4"}, {:exqlite, "~> 0.27"}]
  end
end
