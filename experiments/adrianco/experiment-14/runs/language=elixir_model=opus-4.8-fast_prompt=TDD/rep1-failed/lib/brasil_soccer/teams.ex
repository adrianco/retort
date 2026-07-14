defmodule BrasilSoccer.Teams do
  @moduledoc """
  Team-centric aggregates: win/draw/loss records, goals for/against, and
  head-to-head comparisons. Records can be scoped with the same options that
  `BrasilSoccer.Matches.find/2` accepts (`:season`, `:competition`, `:home`,
  `:away`, date range).
  """

  alias BrasilSoccer.{Match, Matches}

  @doc """
  Build a record for `team` over the matching subset of `matches`.

  Returns a map with `:team`, `:played`, `:wins`, `:draws`, `:losses`,
  `:goals_for`, `:goals_against`, `:goal_difference`, and `:win_rate` (percent).
  """
  @spec record([Match.t()], String.t(), keyword()) :: map()
  def record(matches, team, opts \\ []) do
    relevant = Matches.find(matches, Keyword.put(opts, :team, team))

    init = %{
      team: BrasilSoccer.Normalize.team_name(team),
      played: 0,
      wins: 0,
      draws: 0,
      losses: 0,
      goals_for: 0,
      goals_against: 0
    }

    relevant
    |> Enum.reduce(init, fn match, acc -> tally(acc, match, team) end)
    |> finalize()
  end

  defp tally(acc, match, team) do
    case Match.side(match, team) do
      nil ->
        acc

      side ->
        {gf, ga} = goals(match, side)

        acc
        |> Map.update!(:played, &(&1 + 1))
        |> Map.update!(:goals_for, &(&1 + (gf || 0)))
        |> Map.update!(:goals_against, &(&1 + (ga || 0)))
        |> bump_result(Match.result_for(match, team))
    end
  end

  defp goals(match, :home), do: {match.home_goal, match.away_goal}
  defp goals(match, :away), do: {match.away_goal, match.home_goal}

  defp bump_result(acc, :win), do: Map.update!(acc, :wins, &(&1 + 1))
  defp bump_result(acc, :loss), do: Map.update!(acc, :losses, &(&1 + 1))
  defp bump_result(acc, :draw), do: Map.update!(acc, :draws, &(&1 + 1))
  defp bump_result(acc, nil), do: acc

  defp finalize(acc) do
    win_rate = if acc.played > 0, do: acc.wins / acc.played * 100, else: 0.0

    acc
    |> Map.put(:goal_difference, acc.goals_for - acc.goals_against)
    |> Map.put(:win_rate, Float.round(win_rate, 1))
  end

  @doc "Compare two teams: head-to-head summary plus each side's full record."
  @spec compare([Match.t()], String.t(), String.t()) :: map()
  def compare(matches, team_a, team_b) do
    %{
      head_to_head: Matches.head_to_head(matches, team_a, team_b),
      record_a: record(matches, team_a),
      record_b: record(matches, team_b)
    }
  end
end
