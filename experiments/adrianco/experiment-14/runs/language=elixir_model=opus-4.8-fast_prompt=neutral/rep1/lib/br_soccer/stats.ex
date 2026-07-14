defmodule BrSoccer.Stats do
  @moduledoc "Aggregate statistics over filtered match sets."

  alias BrSoccer.{Match, Matches}

  @doc """
  Aggregate stats for a filtered match set (same options as
  `BrSoccer.Matches.search/1`).

  Returns counts, average goals per match, home/away/draw win rates and goal
  totals.
  """
  def summary(opts \\ []) do
    matches = Matches.search(Keyword.put(opts, :scored_only, true))
    count = length(matches)

    {home, away, draw, goals} =
      Enum.reduce(matches, {0, 0, 0, 0}, fn m, {h, a, d, g} ->
        total = m.home_goal + m.away_goal

        case Match.result(m) do
          :home_win -> {h + 1, a, d, g + total}
          :away_win -> {h, a + 1, d, g + total}
          :draw -> {h, a, d + 1, g + total}
          _ -> {h, a, d, g}
        end
      end)

    %{
      matches: count,
      total_goals: goals,
      avg_goals: ratio(goals, count),
      home_wins: home,
      away_wins: away,
      draws: draw,
      home_win_rate: pct(home, count),
      away_win_rate: pct(away, count),
      draw_rate: pct(draw, count)
    }
  end

  @doc "Compare two seasons of a competition side by side."
  def compare_seasons(competition, season_a, season_b) do
    %{
      competition: competition,
      season_a: season_a,
      season_b: season_b,
      a: summary(competition: competition, season: season_a),
      b: summary(competition: competition, season: season_b)
    }
  end

  defp ratio(_n, 0), do: 0.0
  defp ratio(n, total), do: Float.round(n / total, 2)

  defp pct(_n, 0), do: 0.0
  defp pct(n, total), do: Float.round(n * 100 / total, 1)
end
