defmodule BrazilianSoccerMcp.Query do
  @moduledoc false
  def normalize(nil), do: ""
  def normalize(value) when is_number(value), do: to_string(value)

  def normalize(value) do
    value
    |> String.downcase()
    |> String.normalize(:nfd)
    |> String.replace(~r/[\p{Mn}]/u, "")
    |> String.replace(~r/\s*[-–]\s*[a-z]{2}$/u, "")
    |> String.replace(~r/[^a-z0-9]/u, "")
  end

  def matches(matches, filters) do
    Enum.filter(matches, fn m ->
      team_ok?(m, filters) and eq?(m.competition, filters["competition"] || filters[:competition]) and
        eq?(m.season, filters["season"] || filters[:season]) and date_ok?(m.date, filters)
    end)
    |> Enum.sort_by(&(&1.date || ""), :desc)
  end

  def players(players, filters) do
    Enum.filter(players, fn p ->
      contains?(p.name, filters["name"] || filters[:name]) &&
        contains?(p.club, filters["club"] || filters[:club]) &&
        contains?(p.nationality, filters["nationality"] || filters[:nationality]) &&
        eq?(p.position, filters["position"] || filters[:position])
    end)
    |> Enum.sort_by(&(&1.overall || 0), :desc)
  end

  def team_stats(all, team, filters) do
    ms = matches(all, Map.put(filters, :team, team))

    Enum.reduce(
      ms,
      %{team: team, matches: 0, wins: 0, draws: 0, losses: 0, goals_for: 0, goals_against: 0},
      fn m, a ->
        home = normalize(m.home_team) == normalize(team)
        gf = if home, do: m.home_goal, else: m.away_goal
        ga = if home, do: m.away_goal, else: m.home_goal

        result =
          cond do
            gf > ga -> :wins
            gf == ga -> :draws
            true -> :losses
          end

        a
        |> Map.update!(:matches, &(&1 + 1))
        |> Map.update!(result, &(&1 + 1))
        |> Map.update!(:goals_for, &(&1 + gf))
        |> Map.update!(:goals_against, &(&1 + ga))
      end
    )
    |> then(fn x ->
      Map.put(
        x,
        :win_rate,
        if(x.matches == 0, do: 0.0, else: Float.round(x.wins * 100 / x.matches, 1))
      )
    end)
  end

  def head_to_head(all, one, two, filters) do
    ms =
      matches(all, filters)
      |> Enum.filter(fn m ->
        (same?(m.home_team, one) && same?(m.away_team, two)) or
          (same?(m.home_team, two) && same?(m.away_team, one))
      end)

    stats =
      Enum.reduce(ms, %{first_wins: 0, second_wins: 0, draws: 0}, fn m, a ->
        cond do
          m.home_goal == m.away_goal ->
            Map.update!(a, :draws, &(&1 + 1))

          (same?(m.home_team, one) && m.home_goal > m.away_goal) ||
              (same?(m.away_team, one) && m.away_goal > m.home_goal) ->
            Map.update!(a, :first_wins, &(&1 + 1))

          true ->
            Map.update!(a, :second_wins, &(&1 + 1))
        end
      end)

    %{first_team: one, second_team: two, matches: ms, record: stats}
  end

  def standings(all, season, competition) do
    matches(all, %{season: season, competition: competition})
    |> Enum.reduce(%{}, fn m, table ->
      table
      |> result(m.home_team, m.home_goal, m.away_goal)
      |> result(m.away_team, m.away_goal, m.home_goal)
    end)
    |> Map.values()
    |> Enum.sort_by(&{-&1.points, -&1.goal_difference, -&1.goals_for, &1.team})
  end

  def aggregate(all, filters) do
    ms = matches(all, filters)
    total = Enum.sum(Enum.map(ms, &(&1.home_goal + &1.away_goal)))
    hw = Enum.count(ms, &(&1.home_goal > &1.away_goal))

    %{
      matches: length(ms),
      goals: total,
      average_goals: if(ms == [], do: 0.0, else: Float.round(total / length(ms), 2)),
      home_win_rate: if(ms == [], do: 0.0, else: Float.round(hw * 100 / length(ms), 1))
    }
  end

  defp result(t, team, gf, ga) do
    Map.update(
      t,
      normalize(team),
      %{
        team: team,
        matches: 1,
        wins: if(gf > ga, do: 1, else: 0),
        draws: if(gf == ga, do: 1, else: 0),
        losses: if(gf < ga, do: 1, else: 0),
        goals_for: gf,
        goals_against: ga,
        goal_difference: gf - ga,
        points: if(gf > ga, do: 3, else: if(gf == ga, do: 1, else: 0))
      },
      fn x ->
        result(%{}, team, gf, ga)
        |> Map.values()
        |> hd()
        |> Map.merge(x, fn _, a, b -> if is_number(a), do: a + b, else: a end)
      end
    )
  end

  defp team_ok?(m, f) do
    case f["team"] || f[:team] do
      nil -> true
      team -> same?(m.home_team, team) || same?(m.away_team, team)
    end
  end

  defp same?(a, b), do: normalize(a) == normalize(b)
  defp contains?(_, nil), do: true
  defp contains?(v, q), do: String.contains?(normalize(v), normalize(q))
  defp eq?(_, nil), do: true
  defp eq?(nil, _), do: false

  defp eq?(v, q) when is_integer(v),
    do: v == if(is_integer(q), do: q, else: String.to_integer(to_string(q)))

  defp eq?(v, q), do: contains?(v, q)

  defp date_ok?(date, f) do
    from = f["from"] || f[:from]
    to = f["to"] || f[:to]
    (is_nil(from) || date >= from) && (is_nil(to) || date <= to)
  end
end
