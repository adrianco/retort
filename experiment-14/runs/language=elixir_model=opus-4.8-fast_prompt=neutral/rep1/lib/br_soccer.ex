defmodule BrSoccer do
  @moduledoc """
  Brazilian Soccer knowledge base — a thin facade over the query modules.

  This is the programmatic API behind the MCP server. Each function returns
  plain data structures; `BrSoccer.Format` turns them into the text the MCP
  tools hand back to an LLM.
  """

  alias BrSoccer.{Competitions, Matches, Players, Stats, Teams}

  defdelegate search_matches(opts), to: Matches, as: :search
  defdelegate head_to_head(a, b, opts \\ []), to: Matches
  defdelegate team_competitions(team), to: Matches, as: :competitions_for

  defdelegate team_record(team, opts \\ []), to: Teams, as: :record
  defdelegate team_rankings(opts), to: Teams, as: :rankings
  defdelegate biggest_wins(opts), to: Teams
  defdelegate top_scoring_teams(opts), to: Teams

  defdelegate search_players(opts), to: Players, as: :search
  defdelegate brazilian_players(opts \\ []), to: Players, as: :brazilians
  defdelegate brazilian_clubs_squads(opts \\ []), to: Players, as: :brazilians_at_brazilian_clubs

  defdelegate standings(competition, season), to: Competitions
  defdelegate champion(competition, season), to: Competitions
  defdelegate relegated(season, count \\ 4), to: Competitions

  defdelegate stats_summary(opts), to: Stats, as: :summary
  defdelegate compare_seasons(comp, a, b), to: Stats

  @doc "Most recent match between two clubs, or nil."
  def last_match(team_a, team_b) do
    head_to_head(team_a, team_b).matches |> List.first()
  end
end
