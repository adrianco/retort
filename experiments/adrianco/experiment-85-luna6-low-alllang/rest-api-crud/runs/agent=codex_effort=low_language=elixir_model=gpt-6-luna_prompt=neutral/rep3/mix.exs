defmodule BookApi.MixProject do
  use Mix.Project

  def project do
    [app: :book_api, version: "0.1.0", elixir: "~> 1.14", start_permanent: Mix.env() == :prod,
     deps: [], application: [extra_applications: [:logger], mod: {BookApi.Application, []}]]
  end
end
