defmodule BrazilianSoccerMcp.Tools.GetStatistics do
  alias BrazilianSoccerMcp.DataStore

  def call(args) do
    stat_type = args["stat_type"]
    filters = %{
      team1: nil,
      team2: nil,
      season: parse_int(args["season"]),
      competition: args["competition"]
    }

    case stat_type do
      "biggest_wins" -> biggest_wins(filters)
      "goals_per_match" -> goals_per_match(filters)
      "home_away_record" -> home_away_record(filters)
      "best_home_teams" -> best_home_teams(filters)
      _ -> {:error, "Unknown stat_type: #{stat_type}. Valid: biggest_wins, goals_per_match, home_away_record, best_home_teams"}
    end
  end

  defp biggest_wins(filters) do
    matches =
      DataStore.query_matches(filters)
      |> Enum.uniq_by(&{&1.home, &1.away, &1.date})
      |> Enum.filter(&valid_score?/1)
      |> Enum.sort_by(&score_margin/1, :desc)
      |> Enum.take(20)

    if matches == [] do
      {:ok, "No match data available"}
    else
      rows =
        matches
        |> Enum.with_index(1)
        |> Enum.map_join("\n", fn {m, i} ->
          margin = score_margin(m)
          "  #{i}. #{format_date(m.date)}: #{m.home} #{m.home_goal}-#{m.away_goal} #{m.away}" <>
            "  (margin: #{margin}, #{m.competition})"
        end)

      {:ok, "Biggest Wins in Dataset:\n#{rows}"}
    end
  end

  defp goals_per_match(filters) do
    matches =
      DataStore.query_matches(filters)
      |> Enum.uniq_by(&{&1.home, &1.away, &1.date})
      |> Enum.filter(&valid_score?/1)

    if matches == [] do
      {:ok, "No match data available"}
    else
      total_matches = length(matches)
      total_goals = Enum.reduce(matches, 0, fn m, acc -> acc + (m.home_goal || 0) + (m.away_goal || 0) end)
      avg = Float.round(total_goals / total_matches, 2)

      {:ok,
       """
       Goals Per Match Statistics
       --------------------------
       Total matches analyzed: #{total_matches}
       Total goals: #{total_goals}
       Average goals per match: #{avg}
       """}
    end
  end

  defp home_away_record(filters) do
    matches =
      DataStore.query_matches(filters)
      |> Enum.uniq_by(&{&1.home, &1.away, &1.date})
      |> Enum.filter(&valid_score?/1)

    if matches == [] do
      {:ok, "No match data available"}
    else
      total = length(matches)

      {home_wins, away_wins, draws} =
        Enum.reduce(matches, {0, 0, 0}, fn m, {hw, aw, d} ->
          cond do
            m.home_goal > m.away_goal -> {hw + 1, aw, d}
            m.home_goal < m.away_goal -> {hw, aw + 1, d}
            true -> {hw, aw, d + 1}
          end
        end)

      home_pct = Float.round(home_wins / total * 100, 1)
      away_pct = Float.round(away_wins / total * 100, 1)
      draw_pct = Float.round(draws / total * 100, 1)

      {:ok,
       """
       Home vs Away Record (all competitions)
       ---------------------------------------
       Total matches: #{total}
       Home wins: #{home_wins} (#{home_pct}%)
       Away wins: #{away_wins} (#{away_pct}%)
       Draws: #{draws} (#{draw_pct}%)
       """}
    end
  end

  defp best_home_teams(filters) do
    matches =
      DataStore.query_matches(filters)
      |> Enum.uniq_by(&{&1.home, &1.away, &1.date})
      |> Enum.filter(&valid_score?/1)

    if matches == [] do
      {:ok, "No match data available"}
    else
      home_stats =
        matches
        |> Enum.group_by(& &1.home)
        |> Enum.map(fn {team, team_matches} ->
          total = length(team_matches)
          wins = Enum.count(team_matches, &(&1.home_goal > &1.away_goal))
          win_rate = if total >= 5, do: Float.round(wins / total * 100, 1), else: nil
          %{team: team, played: total, wins: wins, win_rate: win_rate}
        end)
        |> Enum.filter(&(&1.win_rate != nil and &1.played >= 10))
        |> Enum.sort_by(& &1.win_rate, :desc)
        |> Enum.take(15)

      rows =
        home_stats
        |> Enum.with_index(1)
        |> Enum.map_join("\n", fn {s, i} ->
          "  #{i}. #{String.pad_trailing(s.team, 25)} #{s.wins} wins in #{s.played} home games (#{s.win_rate}%)"
        end)

      {:ok, "Best Home Records (min 10 home games):\n#{rows}"}
    end
  end

  defp valid_score?(%{home_goal: hg, away_goal: ag}) do
    is_integer(hg) and is_integer(ag)
  end

  defp valid_score?(_), do: false

  defp score_margin(%{home_goal: hg, away_goal: ag}) when is_integer(hg) and is_integer(ag) do
    abs(hg - ag)
  end

  defp score_margin(_), do: 0

  defp format_date(nil), do: "unknown date"
  defp format_date(d), do: d

  defp parse_int(nil), do: nil
  defp parse_int(i) when is_integer(i), do: i

  defp parse_int(s) when is_binary(s) do
    case Integer.parse(s) do
      {i, _} -> i
      :error -> nil
    end
  end
end
