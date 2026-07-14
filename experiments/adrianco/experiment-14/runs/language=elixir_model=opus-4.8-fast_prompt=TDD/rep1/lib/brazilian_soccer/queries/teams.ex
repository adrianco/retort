defmodule BrazilianSoccer.Queries.Teams do
  @moduledoc """
  Team-centric queries: win/loss/draw records, goals for/against and win rate,
  optionally restricted by season, competition or venue (home/away).
  """

  alias BrazilianSoccer.{Dataset, Match, TeamName}
  alias BrazilianSoccer.Queries.{Matches, Source}

  @doc """
  Compute a team's record.

  Options: `:season`, `:competition`, and `:venue` (`:home`, `:away`, `:all`).
  Returns a map with played/wins/draws/losses, goals_for/against,
  goal_difference, points and win_rate.
  """
  @spec record(Dataset.t(), binary(), keyword()) :: map()
  def record(%Dataset{} = ds, team, opts \\ []) do
    key = TeamName.base(team)
    venue = Keyword.get(opts, :venue, :all)

    find_opts =
      opts
      |> Keyword.take([:season, :competition])
      |> Keyword.put(:team, team)

    matches =
      ds
      |> Matches.find(find_opts)
      |> Source.primary_per_season()
      |> Enum.filter(&venue_match?(&1, key, venue))
      |> Enum.filter(&(Match.winner(&1) != nil))

    Enum.reduce(matches, base(team), fn m, acc -> tally(m, key, acc) end)
    |> finalize()
  end

  @doc "Compare two teams: their individual records plus the head-to-head."
  @spec compare(Dataset.t(), binary(), binary()) :: map()
  def compare(%Dataset{} = ds, team_a, team_b) do
    %{
      team_a: record(ds, team_a),
      team_b: record(ds, team_b),
      head_to_head: Matches.head_to_head(ds, team_a, team_b)
    }
  end

  defp base(team) do
    %{
      team: TeamName.clean(team),
      played: 0,
      wins: 0,
      draws: 0,
      losses: 0,
      goals_for: 0,
      goals_against: 0
    }
  end

  defp venue_match?(%Match{home_base: hk}, key, :home), do: hk == key
  defp venue_match?(%Match{away_base: ak}, key, :away), do: ak == key
  defp venue_match?(_m, _key, _), do: true

  defp tally(%Match{} = m, key, acc) do
    {gf, ga} =
      if m.home_base == key do
        {m.home_goals, m.away_goals}
      else
        {m.away_goals, m.home_goals}
      end

    result =
      cond do
        gf > ga -> :wins
        ga > gf -> :losses
        true -> :draws
      end

    acc
    |> Map.update!(:played, &(&1 + 1))
    |> Map.update!(:goals_for, &(&1 + gf))
    |> Map.update!(:goals_against, &(&1 + ga))
    |> Map.update!(result, &(&1 + 1))
  end

  defp finalize(acc) do
    acc
    |> Map.put(:goal_difference, acc.goals_for - acc.goals_against)
    |> Map.put(:points, acc.wins * 3 + acc.draws)
    |> Map.put(:win_rate, win_rate(acc.wins, acc.played))
  end

  defp win_rate(_wins, 0), do: 0.0
  defp win_rate(wins, played), do: wins / played
end
