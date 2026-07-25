defmodule Mix.Tasks.Soccer.Demo do
  @shortdoc "Answer every sample question through the MCP tool layer"

  @moduledoc """
  Runs `BrazilianSoccer.SampleQuestions` end to end and prints the answers.

      mix soccer.demo
  """

  use Mix.Task

  @requirements ["app.start"]

  @impl true
  def run(_argv), do: BrazilianSoccer.CLI.demo()
end
