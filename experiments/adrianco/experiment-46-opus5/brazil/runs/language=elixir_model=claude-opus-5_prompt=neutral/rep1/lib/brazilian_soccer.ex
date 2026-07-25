defmodule BrazilianSoccer do
  @moduledoc """
  Brazilian soccer knowledge graph — the convenience API.

  Every function here takes a plain argument map and returns
  `{:ok, result} | {:error, reason}`; the graph itself is loaded lazily by
  `BrazilianSoccer.Repo`.

      iex> {:ok, result} = BrazilianSoccer.head_to_head(%{team_a: "Flamengo", team_b: "Fluminense"})
      iex> result.summary.matches > 0
      true

  The same functions back the MCP tools in `BrazilianSoccer.MCP.Tools`.
  """

  alias BrazilianSoccer.Data.Graph
  alias BrazilianSoccer.Query.{Competitions, Matches, Players, Stats, Teams}
  alias BrazilianSoccer.Repo

  @doc "The loaded knowledge graph."
  defdelegate graph(), to: Repo

  @doc "Dataset / graph metadata."
  def info, do: {:ok, Map.put(graph().meta, :competitions, Graph.competitions())}

  def search_matches(args \\ %{}), do: Matches.search(graph(), args)
  def head_to_head(args), do: Matches.head_to_head(graph(), args)
  def last_meeting(team_a, team_b), do: Matches.last_meeting(graph(), team_a, team_b)
  def derbies(args \\ %{}), do: Matches.derbies(graph(), args)

  def team_stats(args), do: Teams.stats(graph(), args)
  def team_profile(args), do: Teams.profile(graph(), args)
  def compare_teams(args), do: Teams.compare(graph(), args)
  def team_rankings(args \\ %{}), do: Teams.rankings(graph(), args)

  def search_players(args \\ %{}), do: Players.search(graph(), args)
  def player_profile(args), do: Players.profile(graph(), args)
  def club_squad(args), do: Players.club_squad(graph(), args)
  def nationality_report(args \\ %{}), do: Players.nationality_report(graph(), args)

  def competitions, do: Competitions.list(graph())
  def standings(args), do: Competitions.standings(graph(), args)
  def champion(args), do: Competitions.champion(graph(), args)
  def bracket(args), do: Competitions.bracket(graph(), args)
  def competition_summary(args \\ %{}), do: Competitions.summary(graph(), args)

  def stats_overview(args \\ %{}), do: Stats.overview(graph(), args)
  def biggest_wins(args \\ %{}), do: Stats.biggest_wins(graph(), args)
  def highest_scoring(args \\ %{}), do: Stats.highest_scoring(graph(), args)
  def compare_seasons(args), do: Stats.compare_seasons(graph(), args)
  def home_advantage(args \\ %{}), do: Stats.home_advantage(graph(), args)

  @doc "Resolve a team name the way the queries do."
  def find_team(name), do: Graph.find_team(graph(), name)
end
