defmodule BrasilSoccer.Players do
  @moduledoc """
  Querying the FIFA player dataset: search by name, nationality, club, or
  position (sorted by overall rating), and per-club summaries useful for
  questions like "Brazilian players at Brazilian clubs".
  """

  @doc """
  Search players. All provided filters must match; results are sorted by
  `:overall` descending.

  Options: `:name`, `:nationality`, `:club`, `:position`, `:min_overall`,
  `:limit`. String filters are case-insensitive substring matches (except
  nationality and position, which match the leading text case-insensitively).
  """
  @spec search([map()], keyword()) :: [map()]
  def search(players, opts \\ []) do
    players
    |> Enum.filter(&keep?(&1, opts))
    |> Enum.sort_by(&(&1.overall || 0), :desc)
    |> maybe_limit(opts[:limit])
  end

  defp keep?(player, opts) do
    Enum.all?(opts, fn
      {:name, value} -> contains?(player.name, value)
      {:club, value} -> contains?(player.club, value)
      {:nationality, value} -> equals_ci?(player.nationality, value)
      {:position, value} -> equals_ci?(player.position, value)
      {:min_overall, value} -> (player.overall || 0) >= value
      {:limit, _} -> true
    end)
  end

  defp contains?(nil, _), do: false
  defp contains?(field, value), do: String.contains?(downcase(field), downcase(value))

  defp equals_ci?(nil, _), do: false
  defp equals_ci?(field, value), do: downcase(field) == downcase(value)

  defp downcase(s), do: s |> to_string() |> String.downcase()

  defp maybe_limit(list, nil), do: list
  defp maybe_limit(list, n) when is_integer(n), do: Enum.take(list, n)

  @doc """
  Group the matching players by club and return `%{club, count, avg_overall}`
  entries sorted by player count descending.
  """
  @spec by_club_summary([map()], keyword()) :: [map()]
  def by_club_summary(players, opts \\ []) do
    players
    |> search(Keyword.delete(opts, :limit))
    |> Enum.reject(&is_nil(&1.club))
    |> Enum.group_by(& &1.club)
    |> Enum.map(fn {club, group} ->
      overalls = group |> Enum.map(&(&1.overall || 0))
      avg = if overalls == [], do: 0.0, else: Enum.sum(overalls) / length(overalls)

      %{club: club, count: length(group), avg_overall: Float.round(avg, 1)}
    end)
    |> Enum.sort_by(& &1.count, :desc)
  end
end
