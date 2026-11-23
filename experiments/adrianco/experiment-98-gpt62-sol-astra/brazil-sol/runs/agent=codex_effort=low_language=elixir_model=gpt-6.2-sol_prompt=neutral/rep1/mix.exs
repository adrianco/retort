defmodule Soccer.MixProject do
  use Mix.Project

  def project do
    [
      app: :soccer,
      version: "1.0.0",
      elixir: "~> 1.18",
      escript: [main_module: Soccer.MCP],
      deps: []
    ]
  end
end
