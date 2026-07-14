defmodule BrasilSoccer do
  @moduledoc """
  Convenience facade over the query modules, backed by the in-memory
  `BrasilSoccer.Store`. Handy for exploring the data from IEx:

      iex> BrasilSoccer.team_record("Flamengo", season: 2019)
      iex> BrasilSoccer.standings("Brasileirão", 2019)

  The MCP server itself goes through `BrasilSoccer.MCP.Tools`; these helpers are
  thin wrappers that pull the dataset from the Store.
  """

  alias BrasilSoccer.{Store, Matches, Teams, Players, Competitions, Stats}

  @doc "Find matches (see `BrasilSoccer.Matches.find/2`)."
  def matches(opts \\ []), do: Matches.find(Store.matches(), opts)

  @doc "Head-to-head between two teams."
  def head_to_head(a, b), do: Matches.head_to_head(Store.matches(), a, b)

  @doc "A team's win/draw/loss record."
  def team_record(team, opts \\ []), do: Teams.record(Store.matches(), team, opts)

  @doc "Compare two teams."
  def compare_teams(a, b), do: Teams.compare(Store.matches(), a, b)

  @doc "Search players."
  def players(opts \\ []), do: Players.search(Store.players(), opts)

  @doc "League standings for a competition and season."
  def standings(competition, season),
    do: Competitions.standings(Store.matches(), competition, season)

  @doc "Aggregate match statistics."
  def stats(opts \\ []), do: Stats.summary(Store.matches(), opts)
end
