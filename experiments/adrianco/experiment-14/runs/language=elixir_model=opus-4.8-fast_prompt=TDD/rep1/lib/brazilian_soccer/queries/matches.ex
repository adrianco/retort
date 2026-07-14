defmodule BrazilianSoccer.Queries.Matches do
  @moduledoc """
  Queries over match data: filtering by team, competition, season and date
  range, plus head-to-head records between two teams.
  """

  alias BrazilianSoccer.{Dataset, Match, TeamName}

  @doc """
  Find matches matching all given options. Results are sorted most-recent first.

  Options:
    * `:team`        — involves this team on either side
    * `:home`        — home team
    * `:away`        — away team
    * `:teams`       — `{a, b}`; matches between exactly these two teams
    * `:competition` — competition name (normalized substring match)
    * `:season`      — integer year
    * `:from`, `:to` — inclusive `Date` bounds
  """
  @spec find(Dataset.t(), keyword()) :: [Match.t()]
  def find(%Dataset{matches: matches}, opts \\ []) do
    matches
    |> Enum.filter(&matches_opts?(&1, opts))
    |> sort_recent()
  end

  @doc """
  Head-to-head summary between two teams from `team_a`'s perspective.
  """
  @spec head_to_head(Dataset.t(), binary(), binary()) :: map()
  def head_to_head(%Dataset{} = ds, team_a, team_b) do
    key_a = TeamName.base(team_a)

    matches =
      ds
      |> find(teams: {team_a, team_b})
      |> BrazilianSoccer.Queries.Source.primary_per_season()
      |> sort_recent()

    Enum.reduce(
      matches,
      %{
        team_a: TeamName.clean(team_a),
        team_b: TeamName.clean(team_b),
        matches: matches,
        total: length(matches),
        a_wins: 0,
        b_wins: 0,
        draws: 0,
        a_goals: 0,
        b_goals: 0
      },
      fn m, acc -> tally_h2h(m, key_a, acc) end
    )
  end

  defp tally_h2h(%Match{} = m, key_a, acc) do
    {a_gf, b_gf} =
      if m.home_base == key_a do
        {m.home_goals, m.away_goals}
      else
        {m.away_goals, m.home_goals}
      end

    acc =
      acc
      |> add(:a_goals, a_gf)
      |> add(:b_goals, b_gf)

    case {a_gf, b_gf} do
      {a, b} when is_integer(a) and is_integer(b) and a > b -> Map.update!(acc, :a_wins, &(&1 + 1))
      {a, b} when is_integer(a) and is_integer(b) and b > a -> Map.update!(acc, :b_wins, &(&1 + 1))
      {a, b} when is_integer(a) and is_integer(b) -> Map.update!(acc, :draws, &(&1 + 1))
      _ -> acc
    end
  end

  defp add(acc, _key, nil), do: acc
  defp add(acc, key, n), do: Map.update!(acc, key, &(&1 + n))

  @doc "Sort matches most-recent first; matches without a date sort last."
  @spec sort_recent([Match.t()]) :: [Match.t()]
  def sort_recent(matches) do
    Enum.sort_by(matches, & &1.date, fn
      _, nil -> true
      nil, _ -> false
      a, b -> Date.compare(a, b) != :lt
    end)
  end

  defp matches_opts?(match, opts) do
    Enum.all?(opts, &match_opt?(match, &1))
  end

  defp match_opt?(m, {:team, team}), do: Match.involves?(m, team)
  defp match_opt?(m, {:home, team}), do: m.home_base == TeamName.base(team)
  defp match_opt?(m, {:away, team}), do: m.away_base == TeamName.base(team)

  defp match_opt?(m, {:teams, {a, b}}) do
    ka = TeamName.base(a)
    kb = TeamName.base(b)
    MapSet.new([m.home_base, m.away_base]) == MapSet.new([ka, kb])
  end

  defp match_opt?(m, {:season, season}), do: m.season == season

  defp match_opt?(m, {:competition, comp}) do
    m.competition != nil and
      String.contains?(String.downcase(m.competition), String.downcase(comp))
  end

  defp match_opt?(%Match{date: nil}, {:from, _}), do: false
  defp match_opt?(%Match{date: d}, {:from, from}), do: Date.compare(d, from) != :lt
  defp match_opt?(%Match{date: nil}, {:to, _}), do: false
  defp match_opt?(%Match{date: d}, {:to, to}), do: Date.compare(d, to) != :gt

  defp match_opt?(_m, _opt), do: true
end
