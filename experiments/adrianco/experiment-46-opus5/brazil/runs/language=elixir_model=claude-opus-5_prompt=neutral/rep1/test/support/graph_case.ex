defmodule BrazilianSoccer.GraphCase do
  @moduledoc """
  Case template for tests that query the real knowledge graph.

  The graph is loaded once for the suite (see `test/test_helper.exs`) and
  handed to each test as `graph` in the context.
  """

  use ExUnit.CaseTemplate

  using do
    quote do
      alias BrazilianSoccer.Data.Graph
      alias BrazilianSoccer.Model.{Match, Player, Team}
      alias BrazilianSoccer.Query.{Competitions, Matches, Players, Stats, Teams}

      import BrazilianSoccer.GraphCase
    end
  end

  setup_all do
    {:ok, graph: BrazilianSoccer.Repo.graph()}
  end

  @doc "Assert that a result is `{:ok, value}` and return the value."
  def ok!({:ok, value}), do: value

  def ok!({:error, reason}) do
    raise ExUnit.AssertionError,
      message: "expected {:ok, _}, got error: #{BrazilianSoccer.Format.error(reason)}"
  end
end
