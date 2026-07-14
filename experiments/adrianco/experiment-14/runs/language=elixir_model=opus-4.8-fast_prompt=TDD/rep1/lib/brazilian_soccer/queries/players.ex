defmodule BrazilianSoccer.Queries.Players do
  @moduledoc """
  Player queries over the FIFA dataset: name search, filtering by nationality,
  club and position, and per-club summaries. Results are ranked by overall
  rating (highest first).
  """

  alias BrazilianSoccer.{Dataset, Player, TeamName}

  @doc """
  Search players matching all given options, sorted by overall rating desc.

  Options: `:name` (substring), `:nationality`, `:club`, `:position`,
  `:brazilian` (boolean), `:min_overall`, `:limit`.
  """
  @spec search(Dataset.t(), keyword()) :: [Player.t()]
  def search(%Dataset{players: players}, opts \\ []) do
    limit = Keyword.get(opts, :limit)

    players
    |> Enum.filter(&matches_opts?(&1, opts))
    |> Enum.sort_by(&(&1.overall || -1), :desc)
    |> maybe_limit(limit)
  end

  @doc "Summarize the players at a club: count, average rating and the roster."
  @spec by_club(Dataset.t(), binary()) :: map()
  def by_club(%Dataset{} = ds, club) do
    players = search(ds, club: club)
    overalls = players |> Enum.map(& &1.overall) |> Enum.reject(&is_nil/1)

    %{
      club: TeamName.clean(club),
      count: length(players),
      avg_overall: average(overalls),
      players: players
    }
  end

  defp maybe_limit(list, nil), do: list
  defp maybe_limit(list, n) when is_integer(n), do: Enum.take(list, n)

  defp matches_opts?(player, opts), do: Enum.all?(opts, &match_opt?(player, &1))

  defp match_opt?(p, {:name, name}) do
    p.name != nil and contains_normalized?(p.name, name)
  end

  defp match_opt?(p, {:nationality, nat}) do
    p.nationality != nil and normalize(p.nationality) == normalize(nat)
  end

  defp match_opt?(p, {:brazilian, true}), do: Player.brazilian?(p)
  defp match_opt?(p, {:brazilian, false}), do: not Player.brazilian?(p)

  defp match_opt?(p, {:club, club}), do: p.club_key == TeamName.base(club)

  defp match_opt?(p, {:position, pos}) do
    p.position != nil and normalize(p.position) == normalize(pos)
  end

  defp match_opt?(p, {:min_overall, min}), do: is_integer(p.overall) and p.overall >= min

  defp match_opt?(_p, {:limit, _}), do: true
  defp match_opt?(_p, _opt), do: true

  defp contains_normalized?(haystack, needle) do
    String.contains?(normalize(haystack), normalize(needle))
  end

  defp normalize(string) do
    string
    |> String.normalize(:nfd)
    |> String.replace(~r/[\x{0300}-\x{036f}]/u, "")
    |> String.downcase()
    |> String.trim()
  end

  defp average([]), do: 0.0
  defp average(nums), do: Enum.sum(nums) / length(nums)
end
