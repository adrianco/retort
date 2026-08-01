defmodule BookApi.MixProject do
  use Mix.Project

  def project do
    [app: :book_api, version: "0.1.0", elixir: "~> 1.20", start_permanent: Mix.env() == :prod]
  end

  def application, do: [extra_applications: [:logger], mod: {BookApi.Application, []}]
end
