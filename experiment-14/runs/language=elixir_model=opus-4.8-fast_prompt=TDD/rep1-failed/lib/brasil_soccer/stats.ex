defmodule BrasilSoccer.Stats do
  @moduledoc """
  Aggregate statistics across a set of matches: goals-per-match averages,
  home/away/draw outcome rates, the biggest victories, and the highest-scoring
  teams. Every function accepts the same filtering options as
  `BrasilSoccer.Matches.find/2` so stats can be scoped to a competition, season,
  team, or date range.
  """

  alias BrasilSoccer.{Match, Matches}

  @doc "Headline summary over the (optionally filtered) matches."
  @spec summary([Match.t()], keyword()) :: map()
  def summary(matches, opts \\ []) do
    scored = matches |> Matches.find(opts) |> Enum.filter(&(&1.winner != nil))
    count = length(scored)

    total_goals = Enum.reduce(scored, 0, fn m, acc -> acc + m.home_goal + m.away_goal end)
    home_wins = Enum.count(scored, &(&1.winner == :home))
    away_wins = Enum.count(scored, &(&1.winner == :away))
    draws = Enum.count(scored, &(&1.winner == :draw))

    %{
      matches: count,
      total_goals: total_goals,
      avg_goals: rate(total_goals, count),
      home_wins: home_wins,
      away_wins: away_wins,
      draws: draws,
      home_win_rate: percent(home_wins, count),
      away_win_rate: percent(away_wins, count),
      draw_rate: percent(draws, count)
    }
  end

  @doc "Matches with the largest goal margin, biggest first."
  @spec biggest_wins([Match.t()], keyword()) :: [Match.t()]
  def biggest_wins(matches, opts \\ []) do
    limit = Keyword.get(opts, :limit, 10)

    matches
    |> Matches.find(Keyword.delete(opts, :limit))
    |> Enum.filter(&(&1.winner in [:home, :away]))
    |> Enum.sort_by(&abs(&1.home_goal - &1.away_goal), :desc)
    |> Enum.take(limit)
  end

  @doc "Teams ranked by total goals scored across the matching matches."
  @spec top_scoring_teams([Match.t()], keyword()) :: [map()]
  def top_scoring_teams(matches, opts \\ []) do
    limit = Keyword.get(opts, :limit, 10)

    matches
    |> Matches.find(Keyword.delete(opts, :limit))
    |> Enum.reduce(%{}, fn m, acc ->
      acc
      |> add_goals(m.home_team, m.home_goal)
      |> add_goals(m.away_team, m.away_goal)
    end)
    |> Enum.map(fn {team, goals} -> %{team: team, goals_for: goals} end)
    |> Enum.sort_by(& &1.goals_for, :desc)
    |> Enum.take(limit)
  end

  defp add_goals(acc, nil, _goals), do: acc
  defp add_goals(acc, _team, nil), do: acc
  defp add_goals(acc, team, goals), do: Map.update(acc, team, goals, &(&1 + goals))

  defp rate(_total, 0), do: 0.0
  defp rate(total, count), do: Float.round(total / count, 2)

  defp percent(_part, 0), do: 0.0
  defp percent(part, count), do: Float.round(part / count * 100, 1)
end
