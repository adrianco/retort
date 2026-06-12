defmodule BrazilianSoccer.Queries.Stats do
  @moduledoc """
  Aggregate statistical analysis over match data: goals-per-match averages,
  home/away/draw outcome rates, biggest victories and best home/away records.
  """

  alias BrazilianSoccer.{Dataset, Match}
  alias BrazilianSoccer.Queries.{Matches, Source}

  @doc """
  Summary statistics over matches (optionally scoped by `:competition` and
  `:season`). Only matches with a known score are considered.
  """
  @spec summary(Dataset.t(), keyword()) :: map()
  def summary(%Dataset{} = ds, opts \\ []) do
    matches = scored_matches(ds, opts)
    n = length(matches)

    total_goals = matches |> Enum.map(&Match.total_goals/1) |> Enum.sum()
    {home, away, draw} = outcome_counts(matches)

    %{
      matches: n,
      total_goals: total_goals,
      avg_goals_per_match: ratio(total_goals, n),
      home_win_rate: ratio(home, n),
      away_win_rate: ratio(away, n),
      draw_rate: ratio(draw, n)
    }
  end

  @doc """
  Matches ranked by goal margin (largest first), tie-broken by total goals.
  Options: `:competition`, `:season`, `:team`, `:limit` (default 10).
  """
  @spec biggest_wins(Dataset.t(), keyword()) :: [Match.t()]
  def biggest_wins(%Dataset{} = ds, opts \\ []) do
    limit = Keyword.get(opts, :limit, 10)

    ds
    |> scored_matches(opts)
    |> Enum.reject(&(Match.winner(&1) == :draw))
    |> Enum.sort_by(&{margin(&1), Match.total_goals(&1)}, :desc)
    |> Enum.take(limit)
  end

  @doc """
  Rank teams by win rate at a venue (`:home`, `:away` or `:all`). Options:
  `:competition`, `:season`, `:min_matches` (default 1), `:limit`.
  """
  @spec best_record(Dataset.t(), :home | :away | :all, keyword()) :: [map()]
  def best_record(%Dataset{} = ds, venue \\ :all, opts \\ []) do
    min_matches = Keyword.get(opts, :min_matches, 1)
    limit = Keyword.get(opts, :limit)

    ds
    |> scored_matches(opts)
    |> Enum.reduce(%{}, fn m, acc -> tally_venue(m, venue, acc) end)
    |> Map.values()
    |> Enum.filter(&(&1.played >= min_matches))
    |> Enum.map(&Map.put(&1, :win_rate, ratio(&1.wins, &1.played)))
    |> Enum.sort_by(&{&1.win_rate, &1.played}, :desc)
    |> maybe_limit(limit)
  end

  defp scored_matches(%Dataset{} = ds, opts) do
    find_opts = Keyword.take(opts, [:competition, :season, :team])

    ds
    |> Matches.find(find_opts)
    |> Source.primary_per_season()
    |> Enum.filter(&(Match.total_goals(&1) != nil))
  end

  defp outcome_counts(matches) do
    Enum.reduce(matches, {0, 0, 0}, fn m, {h, a, d} ->
      case Match.winner(m) do
        :home -> {h + 1, a, d}
        :away -> {h, a + 1, d}
        :draw -> {h, a, d + 1}
        _ -> {h, a, d}
      end
    end)
  end

  defp tally_venue(%Match{} = m, venue, acc) do
    acc =
      if venue in [:home, :all],
        do: add_team(acc, m.home_team, m.home_base, m.home_goals, m.away_goals),
        else: acc

    if venue in [:away, :all],
      do: add_team(acc, m.away_team, m.away_base, m.away_goals, m.home_goals),
      else: acc
  end

  defp add_team(acc, team, key, gf, ga) do
    row = Map.get(acc, key, %{team: team, played: 0, wins: 0, draws: 0, losses: 0})

    result =
      cond do
        gf > ga -> :wins
        ga > gf -> :losses
        true -> :draws
      end

    row =
      row
      |> Map.update!(:played, &(&1 + 1))
      |> Map.update!(result, &(&1 + 1))

    Map.put(acc, key, row)
  end

  defp margin(%Match{home_goals: h, away_goals: a}), do: abs(h - a)

  defp maybe_limit(list, nil), do: list
  defp maybe_limit(list, n), do: Enum.take(list, n)

  defp ratio(_num, 0), do: 0.0
  defp ratio(num, den), do: num / den
end
