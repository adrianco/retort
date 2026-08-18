defmodule BrazilianSoccerMcp.Query do
  @moduledoc "Pure catalog queries used by the MCP transport and test suite."
  alias BrazilianSoccerMcp.Catalog

  def matches(catalog, filters \\ %{}) do
    catalog.matches
    |> Enum.filter(&match_filters?(&1, filters))
    |> Enum.sort_by(&{&1.date || "", &1.home, &1.away}, :desc)
    |> limit(filters)
  end

  def team_statistics(catalog, team, filters \\ %{}) do
    key = Catalog.team_key(team)
    # A display-oriented match search defaults to 50 records, but aggregate
    # calculations must always include every matching fixture.
    games = matches(catalog, filters |> Map.put("team", team) |> Map.put("limit", 100_000))
    side = Map.get(filters, "venue", "all")

    games =
      Enum.filter(games, fn match ->
        side == "all" or (side == "home" and match.home_key == key) or
          (side == "away" and match.away_key == key)
      end)

    Enum.reduce(games, empty_record(team), fn match, record ->
      home? = match.home_key == key
      goals_for = if home?, do: match.home_goals, else: match.away_goals
      goals_against = if home?, do: match.away_goals, else: match.home_goals
      outcome = outcome(goals_for, goals_against)

      record
      |> Map.update!(:matches, &(&1 + 1))
      |> Map.update!(:wins, &(&1 + if(outcome == :win, do: 1, else: 0)))
      |> Map.update!(:draws, &(&1 + if(outcome == :draw, do: 1, else: 0)))
      |> Map.update!(:losses, &(&1 + if(outcome == :loss, do: 1, else: 0)))
      |> Map.update!(:goals_for, &(&1 + (goals_for || 0)))
      |> Map.update!(:goals_against, &(&1 + (goals_against || 0)))
    end)
    |> add_rates()
  end

  def head_to_head(catalog, first, second, filters \\ %{}) do
    first_key = Catalog.team_key(first)
    second_key = Catalog.team_key(second)

    games =
      matches(catalog, Map.put(filters, "limit", 100_000))
      |> Enum.filter(fn m ->
        MapSet.new([m.home_key, m.away_key]) == MapSet.new([first_key, second_key])
      end)

    first_record = record_for(games, first, first_key)
    second_record = record_for(games, second, second_key)

    %{
      first: first_record,
      second: second_record,
      draws: Enum.count(games, &(outcome(&1.home_goals, &1.away_goals) == :draw)),
      matches: games
    }
  end

  def players(catalog, filters \\ %{}) do
    catalog.players
    |> Enum.filter(fn player ->
      contains?(player.name_key, filters["name"]) and
        contains?(Catalog.search_key(player.nationality), filters["nationality"]) and
        contains?(player.club_key, filters["club"]) and position?(player, filters["position"])
    end)
    |> Enum.sort_by(&{&1.overall || -1, &1.potential || -1}, :desc)
    |> limit(filters)
  end

  def standings(catalog, season, competition \\ "Brasileirão") do
    matches(catalog, %{"season" => season, "competition" => competition, "limit" => 100_000})
    |> Enum.reduce(%{}, &add_standing/2)
    |> Map.values()
    |> Enum.map(&Map.put(&1, :goal_difference, &1.goals_for - &1.goals_against))
    |> Enum.sort_by(&{-&1.points, -&1.wins, -&1.goal_difference, -&1.goals_for, &1.team})
    |> Enum.with_index(1)
    |> Enum.map(fn {team, rank} -> Map.put(team, :rank, rank) end)
  end

  def competition_statistics(catalog, filters \\ %{}) do
    games = matches(catalog, Map.put_new(filters, "limit", 100_000))
    total_goals = Enum.sum(Enum.map(games, &((&1.home_goals || 0) + (&1.away_goals || 0))))
    decided = Enum.filter(games, &(&1.home_goals != nil and &1.away_goals != nil))

    %{
      matches: length(games),
      average_goals: rate(total_goals, length(games)),
      home_wins: Enum.count(decided, &(outcome(&1.home_goals, &1.away_goals) == :win)),
      draws: Enum.count(decided, &(outcome(&1.home_goals, &1.away_goals) == :draw)),
      away_wins: Enum.count(decided, &(outcome(&1.away_goals, &1.home_goals) == :win)),
      biggest_wins:
        Enum.sort_by(decided, &abs(&1.home_goals - &1.away_goals), :desc) |> Enum.take(10)
    }
  end

  defp match_filters?(match, filters) do
    team = filters["team"]

    teams =
      [filters["team_a"], filters["team_b"]]
      |> Enum.reject(&is_nil/1)
      |> Enum.map(&Catalog.team_key/1)

    team_ok =
      is_nil(team) or match.home_key == Catalog.team_key(team) or
        match.away_key == Catalog.team_key(team)

    teams_ok = Enum.all?(teams, &(&1 in [match.home_key, match.away_key]))

    team_ok and teams_ok and exact_or_contains?(match.competition, filters["competition"]) and
      season?(match.season, filters["season"]) and date?(match.date, filters["from"], :gte) and
      date?(match.date, filters["to"], :lte) and stage?(match, filters["stage"])
  end

  defp exact_or_contains?(_value, nil), do: true

  defp exact_or_contains?(value, query),
    do: String.contains?(Catalog.search_key(value), Catalog.search_key(query))

  defp season?(_value, nil), do: true
  defp season?(value, expected), do: value == to_int(expected)
  defp date?(nil, _bound, _direction), do: false
  defp date?(_value, nil, _direction), do: true
  defp date?(value, bound, :gte), do: value >= bound
  defp date?(value, bound, :lte), do: value <= bound
  defp stage?(_match, nil), do: true
  defp stage?(match, stage), do: exact_or_contains?(match.stage || "", stage)
  defp contains?(_value, nil), do: true
  defp contains?(value, query), do: String.contains?(value || "", Catalog.search_key(query))
  defp position?(_player, nil), do: true
  defp position?(player, position), do: contains?(Catalog.search_key(player.position), position)
  defp limit(results, filters), do: Enum.take(results, min(to_int(filters["limit"]) || 50, 1_000))
  defp to_int(nil), do: nil
  defp to_int(value) when is_integer(value), do: value

  defp to_int(value) do
    case Integer.parse(to_string(value)) do
      {number, _} -> number
      :error -> nil
    end
  end

  defp empty_record(team),
    do: %{team: team, matches: 0, wins: 0, draws: 0, losses: 0, goals_for: 0, goals_against: 0}

  defp outcome(nil, _), do: :unknown
  defp outcome(_, nil), do: :unknown
  defp outcome(a, b) when a > b, do: :win
  defp outcome(a, b) when a < b, do: :loss
  defp outcome(_, _), do: :draw

  defp add_rates(record),
    do:
      Map.merge(record, %{
        points: record.wins * 3 + record.draws,
        win_rate: rate(record.wins * 100, record.matches)
      })

  defp rate(_total, 0), do: 0.0
  defp rate(total, count), do: Float.round(total / count, 2)

  defp record_for(games, team, key),
    do:
      Enum.reduce(games, empty_record(team), fn m, acc ->
        home? = m.home_key == key
        gf = if home?, do: m.home_goals, else: m.away_goals
        ga = if home?, do: m.away_goals, else: m.home_goals
        result = outcome(gf, ga)

        acc
        |> Map.update!(:matches, &(&1 + 1))
        |> Map.update!(:wins, &(&1 + if(result == :win, do: 1, else: 0)))
        |> Map.update!(:draws, &(&1 + if(result == :draw, do: 1, else: 0)))
        |> Map.update!(:losses, &(&1 + if(result == :loss, do: 1, else: 0)))
        |> Map.update!(:goals_for, &(&1 + (gf || 0)))
        |> Map.update!(:goals_against, &(&1 + (ga || 0)))
      end)
      |> add_rates()

  defp add_standing(match, table),
    do:
      table
      |> add_team(match.home, match.home_goals, match.away_goals)
      |> add_team(match.away, match.away_goals, match.home_goals)

  defp add_team(table, _team, nil, _against), do: table
  defp add_team(table, _team, _goals, nil), do: table

  defp add_team(table, team, goals, against),
    do:
      Map.update(
        table,
        Catalog.team_key(team),
        %{
          team: team,
          matches: 1,
          wins: if(goals > against, do: 1, else: 0),
          draws: if(goals == against, do: 1, else: 0),
          losses: if(goals < against, do: 1, else: 0),
          goals_for: goals,
          goals_against: against,
          points: if(goals > against, do: 3, else: if(goals == against, do: 1, else: 0))
        },
        fn row ->
          %{
            row
            | matches: row.matches + 1,
              wins: row.wins + if(goals > against, do: 1, else: 0),
              draws: row.draws + if(goals == against, do: 1, else: 0),
              losses: row.losses + if(goals < against, do: 1, else: 0),
              goals_for: row.goals_for + goals,
              goals_against: row.goals_against + against,
              points:
                row.points +
                  if(goals > against, do: 3, else: if(goals == against, do: 1, else: 0))
          }
        end
      )
end
