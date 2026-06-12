defmodule BrSoccer.Teams do
  @moduledoc "Team-level records and statistics derived from match data."

  alias BrSoccer.{Match, Matches, TeamName}

  @doc """
  Win/draw/loss record for a club over a filtered set of matches.

  Accepts the same filter options as `BrSoccer.Matches.search/1` (`:season`,
  `:competition`, `:venue`, date range, …). Returns a stats map.
  """
  def record(team, opts \\ []) do
    key = TeamName.key(team)
    opts = Keyword.merge(opts, team: team, scored_only: true)
    matches = Matches.search(opts)

    init = %{
      team: display(matches, key, team),
      key: key,
      matches: 0,
      wins: 0,
      draws: 0,
      losses: 0,
      goals_for: 0,
      goals_against: 0
    }

    stats =
      Enum.reduce(matches, init, fn m, acc ->
        {gf, ga} =
          if m.home_key == key,
            do: {m.home_goal, m.away_goal},
            else: {m.away_goal, m.home_goal}

        outcome =
          cond do
            gf > ga -> :wins
            gf < ga -> :losses
            true -> :draws
          end

        acc
        |> Map.update!(:matches, &(&1 + 1))
        |> Map.update!(outcome, &(&1 + 1))
        |> Map.update!(:goals_for, &(&1 + gf))
        |> Map.update!(:goals_against, &(&1 + ga))
      end)

    stats
    |> Map.put(:points, stats.wins * 3 + stats.draws)
    |> Map.put(:goal_diff, stats.goals_for - stats.goals_against)
    |> Map.put(:win_rate, pct(stats.wins, stats.matches))
  end

  defp pct(_n, 0), do: 0.0
  defp pct(n, total), do: Float.round(n * 100 / total, 1)

  defp display(matches, key, fallback) do
    Enum.find_value(matches, TeamName.display(fallback), fn m ->
      cond do
        m.home_key == key -> m.home
        m.away_key == key -> m.away
        true -> nil
      end
    end)
  end

  @doc """
  Rank teams in a competition/season by total goals scored.

  Returns `[%{team:, key:, goals:, matches:}]` sorted descending.
  """
  def top_scoring_teams(opts \\ []) do
    opts = opts |> Keyword.drop([:limit]) |> Keyword.put(:scored_only, true)

    Matches.search(opts)
    |> Enum.flat_map(fn m ->
      [
        {m.home_key, m.home, m.home_goal},
        {m.away_key, m.away, m.away_goal}
      ]
    end)
    |> Enum.group_by(fn {k, _name, _g} -> k end)
    |> Enum.map(fn {key, entries} ->
      name = entries |> List.first() |> elem(1)
      goals = entries |> Enum.map(&elem(&1, 2)) |> Enum.sum()
      %{key: key, team: name, goals: goals, matches: length(entries)}
    end)
    |> Enum.sort_by(& &1.goals, :desc)
  end

  @doc """
  Rank teams by record, restricted to a venue (`:home`, `:away`, `:either`).

  Useful for "best home/away record". Only counts teams with at least
  `:min_matches` games (default 5). Sorted by win rate then points.
  """
  def rankings(opts \\ []) do
    venue = Keyword.get(opts, :venue, :either)
    min_matches = Keyword.get(opts, :min_matches, 5)
    base = Keyword.drop(opts, [:min_matches, :limit])

    teams =
      Matches.search(Keyword.put(base, :scored_only, true))
      |> teams_in()

    teams
    |> Enum.map(fn {key, name} ->
      record(name, Keyword.merge(base, team: name, venue: venue))
      |> Map.put(:team, name)
      |> Map.put(:key, key)
    end)
    |> Enum.filter(&(&1.matches >= min_matches))
    |> Enum.sort_by(&{&1.win_rate, &1.points, &1.goal_diff}, :desc)
  end

  defp teams_in(matches) do
    matches
    |> Enum.flat_map(&[{&1.home_key, &1.home}, {&1.away_key, &1.away}])
    |> Enum.uniq_by(&elem(&1, 0))
  end

  @doc "Biggest-margin victories across a filtered match set."
  def biggest_wins(opts \\ []) do
    limit = Keyword.get(opts, :limit, 10)
    # `:limit` must bound the final ranked result, not the match set we scan.
    search_opts = opts |> Keyword.drop([:limit]) |> Keyword.put(:scored_only, true)

    Matches.search(search_opts)
    |> Enum.map(&{&1, abs(&1.home_goal - &1.away_goal)})
    |> Enum.reject(fn {_m, margin} -> margin == 0 end)
    |> Enum.sort_by(fn {m, margin} -> {margin, total_goals(m)} end, :desc)
    |> Enum.take(limit)
    |> Enum.map(fn {m, margin} -> %{match: m, margin: margin} end)
  end

  defp total_goals(%Match{home_goal: h, away_goal: a}), do: h + a
end
