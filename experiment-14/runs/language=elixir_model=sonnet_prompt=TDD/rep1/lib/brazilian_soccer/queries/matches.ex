defmodule BrazilianSoccer.Queries.Matches do
  alias BrazilianSoccer.DataStore

  def search_by_team(team_name) do
    term = String.downcase(team_name)

    DataStore.matches()
    |> Enum.filter(fn m ->
      String.contains?(String.downcase(m.home_team), term) or
        String.contains?(String.downcase(m.away_team), term)
    end)
  end

  def search_by_teams(team1, team2) do
    t1 = String.downcase(team1)
    t2 = String.downcase(team2)

    DataStore.matches()
    |> Enum.filter(fn m ->
      home = String.downcase(m.home_team)
      away = String.downcase(m.away_team)

      (String.contains?(home, t1) and String.contains?(away, t2)) or
        (String.contains?(home, t2) and String.contains?(away, t1))
    end)
  end

  def search_by_competition(competition) do
    term = String.downcase(competition)

    DataStore.matches()
    |> Enum.filter(fn m ->
      String.contains?(String.downcase(m.competition), term)
    end)
  end

  def search_by_season(season) do
    DataStore.matches()
    |> Enum.filter(fn m -> m.season == season end)
  end

  def search_by_team_and_season(team_name, season) do
    term = String.downcase(team_name)

    DataStore.matches()
    |> Enum.filter(fn m ->
      m.season == season and
        (String.contains?(String.downcase(m.home_team), term) or
           String.contains?(String.downcase(m.away_team), term))
    end)
  end

  def head_to_head_stats(team1, team2) do
    matches = search_by_teams(team1, team2)
    t1 = String.downcase(team1)

    {t1_wins, t2_wins, draws} =
      Enum.reduce(matches, {0, 0, 0}, fn m, {w1, w2, d} ->
        home = String.downcase(m.home_team)
        t1_is_home = String.contains?(home, t1)
        goal_diff = m.home_goal - m.away_goal

        cond do
          goal_diff == 0 -> {w1, w2, d + 1}
          t1_is_home and goal_diff > 0 -> {w1 + 1, w2, d}
          t1_is_home and goal_diff < 0 -> {w1, w2 + 1, d}
          not t1_is_home and goal_diff < 0 -> {w1 + 1, w2, d}
          not t1_is_home and goal_diff > 0 -> {w1, w2 + 1, d}
          true -> {w1, w2, d}
        end
      end)

    t1_key = team1 |> String.downcase() |> String.replace(" ", "_") |> String.to_atom()
    t2_key = team2 |> String.downcase() |> String.replace(" ", "_") |> String.to_atom()

    %{
      t1_key => t1_wins,
      t2_key => t2_wins,
      :draws => draws,
      :total => length(matches),
      :matches => matches
    }
    |> Map.merge(%{
      team1 => t1_wins,
      team2 => t2_wins
    })
    |> then(fn base ->
      # Also provide convenient atom keys with both team names
      Map.put(base, :flamengo_wins, if(String.contains?(String.downcase(team1), "flamengo"), do: t1_wins, else: t2_wins))
      |> Map.put(:fluminense_wins, if(String.contains?(String.downcase(team1), "fluminense"), do: t1_wins, else: t2_wins))
    end)
  end

  def biggest_wins(limit \\ 10) do
    DataStore.matches()
    |> Enum.filter(fn m -> is_integer(m.home_goal) and is_integer(m.away_goal) end)
    |> Enum.sort_by(fn m -> -abs(m.home_goal - m.away_goal) end)
    |> Enum.take(limit)
  end

  def search_by_date_range(from_date, to_date) do
    DataStore.matches()
    |> Enum.filter(fn m ->
      case m.datetime do
        nil -> false
        dt -> dt >= from_date and dt <= to_date
      end
    end)
  end
end
