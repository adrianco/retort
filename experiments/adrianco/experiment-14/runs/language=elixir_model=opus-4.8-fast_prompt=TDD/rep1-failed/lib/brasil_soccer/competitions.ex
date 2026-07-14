defmodule BrasilSoccer.Competitions do
  @moduledoc """
  Competition-level views derived from match results: league standings (points,
  goal difference, ordering), the implied champion, and the seasons available.

  Standings use the conventional three-points-for-a-win system and break ties on
  goal difference, then goals scored.
  """

  alias BrasilSoccer.{Match, Matches}

  @doc """
  Compute the standings table for `competition` in `season`. Returns a list of
  team rows ordered best-first, each carrying a `:position`.
  """
  @spec standings([Match.t()], String.t(), integer()) :: [map()]
  def standings(matches, competition, season) do
    matches
    |> Matches.find(competition: competition, season: season)
    |> Enum.reduce(%{}, &accumulate/2)
    |> Map.values()
    |> Enum.map(&finalize/1)
    |> Enum.sort_by(&{&1.points, &1.goal_difference, &1.goals_for}, :desc)
    |> Enum.with_index(1)
    |> Enum.map(fn {row, pos} -> Map.put(row, :position, pos) end)
  end

  @doc "The champion (top of the table), or `nil` if there are no matches."
  @spec champion([Match.t()], String.t(), integer()) :: map() | nil
  def champion(matches, competition, season) do
    case standings(matches, competition, season) do
      [first | _] -> first
      [] -> nil
    end
  end

  @doc "Distinct seasons present for a competition, ascending."
  @spec seasons([Match.t()], String.t()) :: [integer()]
  def seasons(matches, competition) do
    matches
    |> Matches.find(competition: competition)
    |> Enum.map(& &1.season)
    |> Enum.reject(&is_nil/1)
    |> Enum.uniq()
    |> Enum.sort()
  end

  # Only count matches with a known scoreline towards the table.
  defp accumulate(%Match{winner: nil}, acc), do: acc

  defp accumulate(%Match{} = match, acc) do
    acc
    |> add_side(match, :home)
    |> add_side(match, :away)
  end

  defp add_side(acc, match, side) do
    {team, gf, ga} = side_fields(match, side)

    row =
      Map.get(acc, team, %{
        team: team,
        played: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goals_for: 0,
        goals_against: 0,
        points: 0
      })

    row =
      row
      |> Map.update!(:played, &(&1 + 1))
      |> Map.update!(:goals_for, &(&1 + gf))
      |> Map.update!(:goals_against, &(&1 + ga))
      |> apply_result(result(match, side))

    Map.put(acc, team, row)
  end

  defp side_fields(match, :home), do: {match.home_team, match.home_goal, match.away_goal}
  defp side_fields(match, :away), do: {match.away_team, match.away_goal, match.home_goal}

  defp result(%Match{winner: :draw}, _side), do: :draw
  defp result(%Match{winner: side}, side), do: :win
  defp result(_match, _side), do: :loss

  defp apply_result(row, :win),
    do: row |> Map.update!(:wins, &(&1 + 1)) |> Map.update!(:points, &(&1 + 3))

  defp apply_result(row, :draw),
    do: row |> Map.update!(:draws, &(&1 + 1)) |> Map.update!(:points, &(&1 + 1))

  defp apply_result(row, :loss), do: Map.update!(row, :losses, &(&1 + 1))

  defp finalize(row), do: Map.put(row, :goal_difference, row.goals_for - row.goals_against)
end
