defmodule BrazilianSoccer.Queries.Competitions do
  @moduledoc """
  Competition-level queries. League standings are computed from match results
  using the standard 3-points-for-a-win system, ranked by points, then goal
  difference, then goals scored, then name.
  """

  alias BrazilianSoccer.{Dataset, Match}
  alias BrazilianSoccer.Queries.{Matches, Source}

  @doc """
  Compute the standings table for a competition and season. Each entry includes
  position, team, played, wins/draws/losses, goals for/against, goal difference
  and points.
  """
  @spec standings(Dataset.t(), binary(), integer()) :: [map()]
  def standings(%Dataset{} = ds, competition, season) do
    matches =
      ds
      |> Matches.find(competition: competition, season: season)
      |> Source.primary_per_season()
      |> Enum.filter(&(Match.winner(&1) != nil))

    matches
    |> Enum.reduce(%{}, &accumulate/2)
    |> Map.values()
    |> Enum.map(&finalize/1)
    |> Enum.sort(&rank/2)
    |> Enum.with_index(1)
    |> Enum.map(fn {row, pos} -> Map.put(row, :position, pos) end)
  end

  @doc "Return the team at the top of the standings, or nil when empty."
  @spec champion(Dataset.t(), binary(), integer()) :: map() | nil
  def champion(%Dataset{} = ds, competition, season) do
    ds |> standings(competition, season) |> List.first()
  end

  @doc "Sorted list of seasons present for a competition."
  @spec seasons(Dataset.t(), binary()) :: [integer()]
  def seasons(%Dataset{matches: matches}, competition) do
    matches
    |> Enum.filter(&(&1.competition == competition and &1.season != nil))
    |> Enum.map(& &1.season)
    |> Enum.uniq()
    |> Enum.sort()
  end

  @doc "Sorted list of distinct competitions in the dataset."
  @spec competitions(Dataset.t()) :: [binary()]
  def competitions(%Dataset{matches: matches}) do
    matches
    |> Enum.map(& &1.competition)
    |> Enum.reject(&is_nil/1)
    |> Enum.uniq()
    |> Enum.sort()
  end

  defp accumulate(%Match{} = m, acc) do
    acc
    |> upsert(m.home_team, m.home_key, m.home_goals, m.away_goals)
    |> upsert(m.away_team, m.away_key, m.away_goals, m.home_goals)
  end

  defp upsert(acc, team, key, gf, ga) do
    row = Map.get(acc, key, blank(team))

    result =
      cond do
        gf > ga -> :wins
        ga > gf -> :losses
        true -> :draws
      end

    row =
      row
      |> Map.update!(:played, &(&1 + 1))
      |> Map.update!(:goals_for, &(&1 + gf))
      |> Map.update!(:goals_against, &(&1 + ga))
      |> Map.update!(result, &(&1 + 1))

    Map.put(acc, key, row)
  end

  defp blank(team) do
    %{team: team, played: 0, wins: 0, draws: 0, losses: 0, goals_for: 0, goals_against: 0}
  end

  defp finalize(row) do
    row
    |> Map.put(:goal_difference, row.goals_for - row.goals_against)
    |> Map.put(:points, row.wins * 3 + row.draws)
  end

  # Brazilian league tie-break order: points, then wins, then goal difference,
  # then goals for; finally team name ascending for stable display.
  defp rank(a, b) do
    {a.points, a.wins, a.goal_difference, a.goals_for, sortable(b.team)} >=
      {b.points, b.wins, b.goal_difference, b.goals_for, sortable(a.team)}
  end

  # Names sort ascending as a tie-breaker; invert by comparing b vs a above.
  defp sortable(name), do: String.downcase(name)
end
