defmodule BrazilianSoccer do
  @moduledoc "A queryable, in-memory view of the Brazilian soccer CSV datasets."

  alias BrazilianSoccer.{Data, Normalize}

  @type match :: map()
  @type player :: map()

  @doc "Loads all supplied CSV files. `path` defaults to `data/kaggle`."
  def load(path \\ "data/kaggle"), do: Data.load(path)

  @doc "Finds matches. Supported options: `:team`, `:home_team`, `:away_team`, `:opponent`, `:season`, `:competition`, `:from`, `:to`, `:stage`, and `:limit`."
  def search_matches(data, opts \\ []) do
    opts = Map.new(opts)

    data.matches
    |> Enum.filter(&match_filter?(&1, opts))
    |> Enum.sort_by(& &1.date, {:desc, Date})
    |> Enum.take(Map.get(opts, :limit, 100))
  end

  @doc "Returns W/D/L and goals for a team, optionally limited by season, competition, and venue (`:home`, `:away`, or `:all`)."
  def team_statistics(data, team, opts \\ []) do
    opts = Map.new(opts)
    venue = Map.get(opts, :venue, :all)
    matches = search_matches(data, Map.put(opts, :team, team)) |> Enum.filter(&completed?/1)
    team_key = Normalize.team(team)

    matches =
      Enum.filter(matches, fn m ->
        venue == :all or (venue == :home and m.home_key == team_key) or
          (venue == :away and m.away_key == team_key)
      end)

    Enum.reduce(
      matches,
      %{
        team: Normalize.display_team(team),
        matches: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goals_for: 0,
        goals_against: 0
      },
      fn m, acc ->
        home? = m.home_key == team_key
        gf = if home?, do: m.home_goals, else: m.away_goals
        ga = if home?, do: m.away_goals, else: m.home_goals

        result =
          cond do
            gf > ga -> :wins
            gf == ga -> :draws
            true -> :losses
          end

        acc
        |> Map.update!(:matches, &(&1 + 1))
        |> Map.update!(result, &(&1 + 1))
        |> Map.update!(:goals_for, &(&1 + gf))
        |> Map.update!(:goals_against, &(&1 + ga))
      end
    )
    |> then(fn stats ->
      Map.put(
        stats,
        :win_rate,
        if(stats.matches == 0, do: 0.0, else: Float.round(stats.wins * 100 / stats.matches, 1))
      )
    end)
  end

  @doc "Calculates the record between two teams regardless of home/away ordering."
  def head_to_head(data, first, second, opts \\ []) do
    a = Normalize.team(first)
    b = Normalize.team(second)
    matches = search_matches(data, Keyword.merge(opts, team: first, opponent: second)) |> Enum.filter(&completed?/1)

    record =
      Enum.reduce(
        matches,
        %{
          first: Normalize.display_team(first),
          second: Normalize.display_team(second),
          matches: length(matches),
          first_wins: 0,
          second_wins: 0,
          draws: 0
        },
        fn m, acc ->
          first_goals = if m.home_key == a, do: m.home_goals, else: m.away_goals
          second_goals = if m.home_key == b, do: m.home_goals, else: m.away_goals

          key =
            cond do
              first_goals > second_goals -> :first_wins
              first_goals < second_goals -> :second_wins
              true -> :draws
            end

          Map.update!(acc, key, &(&1 + 1))
        end
      )

    Map.put(record, :matches_data, matches)
  end

  @doc "Searches FIFA players by case/accent-insensitive name, nationality, club, position, and minimum rating."
  def search_players(data, opts \\ []) do
    opts = Map.new(opts)

    data.players
    |> Enum.filter(fn p ->
      contains?(p.name, opts[:name]) and contains?(p.nationality, opts[:nationality]) and
        contains?(p.club, opts[:club]) and
        (is_nil(opts[:position]) or Normalize.text(p.position) == Normalize.text(opts[:position])) and
        (is_nil(opts[:min_overall]) or p.overall >= opts[:min_overall])
    end)
    |> Enum.sort_by(& &1.overall, :desc)
    |> Enum.take(Map.get(opts, :limit, 100))
  end

  @doc "Calculates a three-points-for-a-win league table from the selected results."
  def standings(data, season, opts \\ []) do
    matches = search_matches(data, Keyword.merge(opts, season: season)) |> Enum.filter(&completed?/1)

    matches
    |> Enum.reduce(%{}, &table_match/2)
    |> Map.values()
    |> Enum.map(fn row -> Map.put(row, :goal_difference, row.goals_for - row.goals_against) end)
    |> Enum.sort_by(fn r -> {-r.points, -r.wins, -r.goal_difference, -r.goals_for, r.team} end)
    |> Enum.with_index(1)
    |> Enum.map(fn {row, position} -> Map.put(row, :position, position) end)
  end

  @doc "Returns aggregate goal and result metrics for the selected matches."
  def competition_statistics(data, opts \\ []) do
    matches = search_matches(data, opts) |> Enum.filter(&completed?/1)
    total = length(matches)
    goals = Enum.sum_by(matches, &(&1.home_goals + &1.away_goals))
    home_wins = Enum.count(matches, &(&1.home_goals > &1.away_goals))
    draws = Enum.count(matches, &(&1.home_goals == &1.away_goals))

    %{
      matches: total,
      total_goals: goals,
      average_goals: if(total == 0, do: 0.0, else: Float.round(goals / total, 2)),
      home_win_rate: if(total == 0, do: 0.0, else: Float.round(home_wins * 100 / total, 1)),
      draw_rate: if(total == 0, do: 0.0, else: Float.round(draws * 100 / total, 1))
    }
  end

  defp match_filter?(m, opts) do
    team = opts[:team] && Normalize.team(opts[:team])
    home = opts[:home_team] && Normalize.team(opts[:home_team])
    away = opts[:away_team] && Normalize.team(opts[:away_team])
    opponent = opts[:opponent] && Normalize.team(opts[:opponent])

    (is_nil(team) or team in [m.home_key, m.away_key]) and (is_nil(home) or home == m.home_key) and
      (is_nil(away) or away == m.away_key) and
      (is_nil(opponent) or opponent in [m.home_key, m.away_key]) and
      (is_nil(opts[:season]) or to_string(m.season) == to_string(opts[:season])) and
      (is_nil(opts[:competition]) or
         Normalize.text(m.competition) == Normalize.text(opts[:competition])) and
      (is_nil(opts[:stage]) or
         String.contains?(Normalize.text(m.stage || ""), Normalize.text(opts[:stage]))) and
      date_in_range?(m.date, opts[:from], opts[:to])
  end

  defp date_in_range?(date, from, to),
    do:
      (is_nil(from) or Date.compare(date, Normalize.date!(from)) != :lt) and
        (is_nil(to) or Date.compare(date, Normalize.date!(to)) != :gt)

  defp completed?(m), do: is_integer(m.home_goals) and is_integer(m.away_goals)

  defp contains?(_value, nil), do: true

  defp contains?(value, expected),
    do: String.contains?(Normalize.text(value || ""), Normalize.text(expected))

  defp table_match(m, table),
    do:
      table
      |> update_row(m.home, m.home_goals, m.away_goals)
      |> update_row(m.away, m.away_goals, m.home_goals)

  defp update_row(table, team, gf, ga) do
    row =
      Map.get(table, Normalize.team(team), %{
        team: Normalize.display_team(team),
        played: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goals_for: 0,
        goals_against: 0,
        points: 0
      })

    row = %{
      row
      | played: row.played + 1,
        goals_for: row.goals_for + gf,
        goals_against: row.goals_against + ga
    }

    row =
      cond do
        gf > ga -> %{row | wins: row.wins + 1, points: row.points + 3}
        gf == ga -> %{row | draws: row.draws + 1, points: row.points + 1}
        true -> %{row | losses: row.losses + 1}
      end

    Map.put(table, Normalize.team(team), row)
  end
end
