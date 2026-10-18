defmodule SoccerMcp.MixProject do
  use Mix.Project

  def project do
    [
      app: :soccer_mcp,
      version: "0.1.0",
      elixir: "~> 1.15",
      start_permanent: Mix.env() == :prod,
      deps: deps(),
      escript: [main_module: SoccerMcp.CLI, name: "soccer_mcp"]
    ]
  end

  def application do
    [
      extra_applications: [:logger]
    ]
  end

  defp deps do
    [
      {:jason, "~> 1.4"}
    ]
  end
end
