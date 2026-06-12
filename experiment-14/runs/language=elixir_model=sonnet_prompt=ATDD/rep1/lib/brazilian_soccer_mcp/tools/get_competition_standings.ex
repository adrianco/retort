defmodule BrazilianSoccerMcp.Tools.GetCompetitionStandings do
  alias BrazilianSoccerMcp.DataStore

  def call(args) do
    competition = args["competition"]
    season = parse_int(args["season"])

    if is_nil(competition) or is_nil(season) do
      {:error, "competition and season are required"}
    else
      filters = %{
        team1: nil,
        team2: nil,
        season: season,
        competition: competition
      }

      matches =
        DataStore.query_matches(filters)
        |> Enum.uniq_by(&{&1.home, &1.away, &1.date})

      if matches == [] do
        {:ok, "No matches found for #{competition} #{season}"}
      else
        {:ok, format_standings(competition, season, matches)}
      end
    end
  end

  defp format_standings(competition, season, matches) do
    standings =
      matches
      |> Enum.reduce(%{}, fn m, acc ->
        acc
        |> update_team(m.home, m.home_goal, m.away_goal)
        |> update_team(m.away, m.away_goal, m.home_goal)
      end)
      |> Enum.map(fn {team, s} ->
        pts = s.wins * 3 + s.draws
        total = s.wins + s.draws + s.losses
        %{
          team: team,
          pts: pts,
          wins: s.wins,
          draws: s.draws,
          losses: s.losses,
          gf: s.gf,
          ga: s.ga,
          gd: s.gf - s.ga,
          played: total
        }
      end)
      |> Enum.sort_by(&{-&1.pts, -&1.gd, -&1.gf})

    header = "#{competition} #{season} Standings\n#{String.duplicate("-", 50)}"
    rows =
      standings
      |> Enum.with_index(1)
      |> Enum.map_join("\n", fn {t, i} ->
        "  #{String.pad_leading(Integer.to_string(i), 2)}. #{String.pad_trailing(t.team, 25)} " <>
          "#{String.pad_leading(Integer.to_string(t.pts), 3)} pts " <>
          "(#{t.wins}W #{t.draws}D #{t.losses}L) " <>
          "GF:#{t.gf} GA:#{t.ga} GD:#{if t.gd >= 0, do: "+"}#{t.gd}"
      end)

    "#{header}\n#{rows}"
  end

  defp update_team(acc, team, my_goals, opp_goals) when is_binary(team) do
    my_goals = my_goals || 0
    opp_goals = opp_goals || 0

    result =
      cond do
        my_goals > opp_goals -> :win
        my_goals == opp_goals -> :draw
        true -> :loss
      end

    default = %{wins: 0, draws: 0, losses: 0, gf: 0, ga: 0}

    Map.update(acc, team, default, fn s ->
      s
      |> Map.update!(:wins, &if(result == :win, do: &1 + 1, else: &1))
      |> Map.update!(:draws, &if(result == :draw, do: &1 + 1, else: &1))
      |> Map.update!(:losses, &if(result == :loss, do: &1 + 1, else: &1))
      |> Map.update!(:gf, &(&1 + my_goals))
      |> Map.update!(:ga, &(&1 + opp_goals))
    end)
  end

  defp update_team(acc, _team, _my, _opp), do: acc

  defp parse_int(nil), do: nil
  defp parse_int(i) when is_integer(i), do: i

  defp parse_int(s) when is_binary(s) do
    case Integer.parse(s) do
      {i, _} -> i
      :error -> nil
    end
  end
end
