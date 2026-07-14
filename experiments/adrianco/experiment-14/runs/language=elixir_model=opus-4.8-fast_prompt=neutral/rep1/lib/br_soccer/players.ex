defmodule BrSoccer.Players do
  @moduledoc "Querying the FIFA player dataset."

  alias BrSoccer.{Repo, TeamName}

  @doc """
  Search players by any combination of criteria.

  Options:

    * `:name`         — substring match on player name (accent-insensitive)
    * `:nationality`  — exact-ish match on nationality (accent/case-insensitive)
    * `:club`         — club the player belongs to (normalised, so "Flamengo"
                        matches the FIFA `Club` field)
    * `:position`     — position code (e.g. "ST", "GK"); substring match
    * `:min_overall`  — minimum FIFA overall rating
    * `:sort`         — `:overall` (default), `:potential`, `:age`, `:name`
    * `:limit`        — maximum results
  """
  def search(opts \\ []) do
    name = opts[:name] && normalize(opts[:name])
    nat = opts[:nationality] && normalize(opts[:nationality])
    club_key = opts[:club] && TeamName.key(opts[:club])
    position = opts[:position] && normalize(opts[:position])
    min_overall = opts[:min_overall]

    Repo.players()
    |> Enum.filter(fn p ->
      (is_nil(name) or String.contains?(normalize(p.name), name)) and
        (is_nil(nat) or normalize(p.nationality) == nat) and
        (is_nil(club_key) or p.club_key == club_key) and
        (is_nil(position) or position_match?(p.position, position)) and
        (is_nil(min_overall) or (is_integer(p.overall) and p.overall >= min_overall))
    end)
    |> sort(Keyword.get(opts, :sort, :overall))
    |> maybe_limit(opts[:limit])
  end

  defp position_match?(nil, _q), do: false
  defp position_match?(pos, q), do: String.contains?(normalize(pos), q)

  defp normalize(nil), do: ""
  defp normalize(s), do: s |> to_string() |> TeamName.deaccent() |> String.downcase() |> String.trim()

  defp sort(players, :overall), do: Enum.sort_by(players, &(&1.overall || 0), :desc)
  defp sort(players, :potential), do: Enum.sort_by(players, &(&1.potential || 0), :desc)
  defp sort(players, :age), do: Enum.sort_by(players, &(&1.age || 999))
  defp sort(players, :name), do: Enum.sort_by(players, & &1.name)
  defp sort(players, _), do: players

  defp maybe_limit(list, nil), do: list
  defp maybe_limit(list, n) when is_integer(n) and n >= 0, do: Enum.take(list, n)
  defp maybe_limit(list, _), do: list

  @doc "Convenience: Brazilian players, highest-rated first."
  def brazilians(opts \\ []) do
    search(Keyword.put(opts, :nationality, "Brazil"))
  end

  @doc """
  Group Brazilian players who play at Brazilian clubs, by club.

  A "Brazilian club" is any club whose normalised key also appears in the match
  datasets. Returns `[%{club:, key:, count:, avg_overall:, players:}]` sorted by
  squad size.
  """
  def brazilians_at_brazilian_clubs(opts \\ []) do
    brazilian_keys = Repo.team_keys()
    min_count = Keyword.get(opts, :min_count, 1)

    brazilians()
    |> Enum.filter(fn p -> p.club_key && MapSet.member?(brazilian_keys, p.club_key) end)
    |> Enum.group_by(& &1.club_key)
    |> Enum.map(fn {key, players} ->
      overalls = players |> Enum.map(& &1.overall) |> Enum.reject(&is_nil/1)

      %{
        key: key,
        club: List.first(players).club,
        count: length(players),
        avg_overall: avg(overalls),
        players: Enum.sort_by(players, &(&1.overall || 0), :desc)
      }
    end)
    |> Enum.filter(&(&1.count >= min_count))
    |> Enum.sort_by(&{&1.count, &1.avg_overall}, :desc)
  end

  defp avg([]), do: 0.0
  defp avg(nums), do: Float.round(Enum.sum(nums) / length(nums), 1)
end
