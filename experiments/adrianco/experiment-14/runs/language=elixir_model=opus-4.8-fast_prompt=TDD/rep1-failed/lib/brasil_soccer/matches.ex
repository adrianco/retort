defmodule BrasilSoccer.Matches do
  @moduledoc """
  Querying the match collection: flexible filtering by team, opponent,
  competition, season, and date range, plus head-to-head summaries.
  """

  alias BrasilSoccer.Match

  @doc """
  Filter `matches` by the given options. Results are returned most-recent first.

  Options:

    * `:team` — either side matches this team (fuzzy)
    * `:opponent` — together with `:team`, restrict to that pairing
    * `:home` / `:away` — restrict that specific side
    * `:competition` — exact (case-insensitive) competition name
    * `:season` — integer season/year
    * `:from` / `:to` — inclusive `Date` bounds
    * `:limit` — keep at most N results after sorting
  """
  @spec find([Match.t()], keyword()) :: [Match.t()]
  def find(matches, opts \\ []) do
    matches
    |> Enum.filter(&keep?(&1, opts))
    |> sort_recent_first()
    |> maybe_limit(opts[:limit])
  end

  defp keep?(match, opts) do
    Enum.all?(opts, fn
      {:team, team} -> Match.involves?(match, team)
      {:opponent, team} -> Match.involves?(match, team)
      {:home, team} -> match.home_team && BrasilSoccer.Normalize.matches?(match.home_team, team)
      {:away, team} -> match.away_team && BrasilSoccer.Normalize.matches?(match.away_team, team)
      {:competition, comp} -> comp_match?(match.competition, comp)
      {:season, season} -> match.season == season
      {:from, date} -> match.date && Date.compare(match.date, date) != :lt
      {:to, date} -> match.date && Date.compare(match.date, date) != :gt
      {:limit, _} -> true
    end)
  end

  defp comp_match?(nil, _), do: false

  defp comp_match?(actual, wanted) do
    String.downcase(actual) == String.downcase(wanted)
  end

  @doc "Sort matches most-recent first; undated matches sort last."
  @spec sort_recent_first([Match.t()]) :: [Match.t()]
  def sort_recent_first(matches) do
    Enum.sort(matches, fn a, b -> not date_before?(a.date, b.date) end)
  end

  # a strictly before b? (nil dates are treated as the earliest)
  defp date_before?(nil, nil), do: false
  defp date_before?(nil, _), do: true
  defp date_before?(_, nil), do: false
  defp date_before?(a, b), do: Date.compare(a, b) == :lt

  defp maybe_limit(matches, nil), do: matches
  defp maybe_limit(matches, n) when is_integer(n), do: Enum.take(matches, n)

  @doc """
  Head-to-head summary between two teams: win counts from each perspective,
  draws, and the matches themselves (most-recent first).
  """
  @spec head_to_head([Match.t()], String.t(), String.t()) :: map()
  def head_to_head(matches, team_a, team_b) do
    relevant = find(matches, team: team_a, opponent: team_b)

    {a_wins, b_wins, draws} =
      Enum.reduce(relevant, {0, 0, 0}, fn match, {a, b, d} ->
        case Match.result_for(match, team_a) do
          :win -> {a + 1, b, d}
          :loss -> {a, b + 1, d}
          :draw -> {a, b, d + 1}
          nil -> {a, b, d}
        end
      end)

    %{
      team_a: BrasilSoccer.Normalize.team_name(team_a),
      team_b: BrasilSoccer.Normalize.team_name(team_b),
      a_wins: a_wins,
      b_wins: b_wins,
      draws: draws,
      total: length(relevant),
      matches: relevant
    }
  end
end
