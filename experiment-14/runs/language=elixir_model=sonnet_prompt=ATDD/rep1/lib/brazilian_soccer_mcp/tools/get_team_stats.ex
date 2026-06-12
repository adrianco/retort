defmodule BrazilianSoccerMcp.Tools.GetTeamStats do
  alias BrazilianSoccerMcp.DataStore

  def call(args) do
    team = args["team"]

    if is_nil(team) or String.trim(team) == "" do
      {:error, "team parameter is required"}
    else
      filters = %{
        team1: team,
        team2: nil,
        season: parse_int(args["season"]),
        competition: args["competition"]
      }

      matches = DataStore.query_matches(filters) |> Enum.uniq_by(&{&1.home, &1.away, &1.date})

      if matches == [] do
        {:ok, "No matches found for team: #{team}"}
      else
        {:ok, format_stats(team, matches, filters)}
      end
    end
  end

  defp format_stats(team, matches, filters) do
    team_down = String.downcase(team)

    stats =
      Enum.reduce(matches, %{wins: 0, draws: 0, losses: 0, gf: 0, ga: 0, home: 0, away: 0}, fn m, acc ->
        is_home = String.contains?(String.downcase(m.home), team_down)

        {my_goals, opp_goals} =
          if is_home,
            do: {m.home_goal || 0, m.away_goal || 0},
            else: {m.away_goal || 0, m.home_goal || 0}

        result =
          cond do
            my_goals > opp_goals -> :win
            my_goals == opp_goals -> :draw
            true -> :loss
          end

        acc
        |> Map.update!(:wins, &if(result == :win, do: &1 + 1, else: &1))
        |> Map.update!(:draws, &if(result == :draw, do: &1 + 1, else: &1))
        |> Map.update!(:losses, &if(result == :loss, do: &1 + 1, else: &1))
        |> Map.update!(:gf, &(&1 + my_goals))
        |> Map.update!(:ga, &(&1 + opp_goals))
        |> Map.update!(:home, &if(is_home, do: &1 + 1, else: &1))
        |> Map.update!(:away, &if(not is_home, do: &1 + 1, else: &1))
      end)

    total = stats.wins + stats.draws + stats.losses
    win_rate = if total > 0, do: Float.round(stats.wins / total * 100, 1), else: 0.0

    season_label = if filters.season, do: " (#{filters.season})", else: ""
    comp_label = if filters.competition, do: " - #{filters.competition}", else: ""

    """
    #{team}#{season_label}#{comp_label}

    Matches played: #{total}
    Wins: #{stats.wins}, Draws: #{stats.draws}, Losses: #{stats.losses}
    Goals For: #{stats.gf}, Goals Against: #{stats.ga}
    Goal Difference: #{stats.gf - stats.ga}
    Win rate: #{win_rate}%
    Home matches: #{stats.home}, Away matches: #{stats.away}
    Points (3W+1D): #{stats.wins * 3 + stats.draws}
    """
    |> String.trim()
  end

  defp parse_int(nil), do: nil
  defp parse_int(i) when is_integer(i), do: i

  defp parse_int(s) when is_binary(s) do
    case Integer.parse(s) do
      {i, _} -> i
      :error -> nil
    end
  end
end
