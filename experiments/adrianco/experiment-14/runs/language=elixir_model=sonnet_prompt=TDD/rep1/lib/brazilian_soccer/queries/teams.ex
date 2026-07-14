defmodule BrazilianSoccer.Queries.Teams do
  alias BrazilianSoccer.DataStore

  def team_record(team_name, opts \\ []) do
    term = String.downcase(team_name)
    home_only = Keyword.get(opts, :home_only, false)
    season = Keyword.get(opts, :season)
    competition = Keyword.get(opts, :competition)

    matches =
      DataStore.matches()
      |> Enum.filter(fn m ->
        relevant =
          if home_only do
            String.contains?(String.downcase(m.home_team), term)
          else
            String.contains?(String.downcase(m.home_team), term) or
              String.contains?(String.downcase(m.away_team), term)
          end

        relevant =
          if season, do: relevant and m.season == season, else: relevant

        if competition do
          relevant and String.contains?(String.downcase(m.competition), String.downcase(competition))
        else
          relevant
        end
      end)

    Enum.reduce(matches, %{wins: 0, draws: 0, losses: 0, goals_for: 0, goals_against: 0, matches: 0}, fn m, acc ->
      is_home = String.contains?(String.downcase(m.home_team), term)
      {gf, ga} = if is_home, do: {m.home_goal || 0, m.away_goal || 0}, else: {m.away_goal || 0, m.home_goal || 0}
      diff = gf - ga

      result =
        cond do
          diff > 0 -> :win
          diff == 0 -> :draw
          true -> :loss
        end

      %{acc |
        wins: acc.wins + if(result == :win, do: 1, else: 0),
        draws: acc.draws + if(result == :draw, do: 1, else: 0),
        losses: acc.losses + if(result == :loss, do: 1, else: 0),
        goals_for: acc.goals_for + gf,
        goals_against: acc.goals_against + ga,
        matches: acc.matches + 1
      }
    end)
  end

  def top_scoring_teams(season, competition, limit \\ 10) do
    comp_term = String.downcase(competition)

    matches =
      DataStore.matches()
      |> Enum.filter(fn m ->
        m.season == season and
          String.contains?(String.downcase(m.competition), comp_term)
      end)

    teams =
      Enum.reduce(matches, %{}, fn m, acc ->
        home_goals = m.home_goal || 0
        away_goals = m.away_goal || 0
        acc
        |> Map.update(m.home_team, home_goals, &(&1 + home_goals))
        |> Map.update(m.away_team, away_goals, &(&1 + away_goals))
      end)

    teams
    |> Enum.sort_by(fn {_team, goals} -> -goals end)
    |> Enum.take(limit)
  end

  def competition_standings(season, competition) do
    comp_term = String.downcase(competition)

    matches =
      DataStore.matches()
      |> Enum.filter(fn m ->
        m.season == season and
          String.contains?(String.downcase(m.competition), comp_term) and
          is_integer(m.home_goal) and is_integer(m.away_goal)
      end)

    table =
      Enum.reduce(matches, %{}, fn m, acc ->
        home_diff = m.home_goal - m.away_goal

        home_result = cond do
          home_diff > 0 -> :win
          home_diff == 0 -> :draw
          true -> :loss
        end

        away_result = case home_result do
          :win -> :loss
          :loss -> :win
          :draw -> :draw
        end

        acc
        |> update_standing(m.home_team, home_result, m.home_goal, m.away_goal)
        |> update_standing(m.away_team, away_result, m.away_goal, m.home_goal)
      end)

    table
    |> Enum.map(fn {team, s} ->
      %{
        team: team,
        points: s.wins * 3 + s.draws,
        wins: s.wins,
        draws: s.draws,
        losses: s.losses,
        goals_for: s.goals_for,
        goals_against: s.goals_against,
        goal_diff: s.goals_for - s.goals_against,
        played: s.wins + s.draws + s.losses
      }
    end)
    |> Enum.sort_by(fn s -> {-s.points, -s.goal_diff, -s.goals_for} end)
  end

  def average_goals_per_match(competition) do
    comp_term = String.downcase(competition)

    matches =
      DataStore.matches()
      |> Enum.filter(fn m ->
        String.contains?(String.downcase(m.competition), comp_term) and
          is_integer(m.home_goal) and is_integer(m.away_goal)
      end)

    if Enum.empty?(matches) do
      0.0
    else
      total_goals = Enum.sum(Enum.map(matches, fn m -> m.home_goal + m.away_goal end))
      total_goals / length(matches)
    end
  end

  def home_win_rate do
    matches =
      DataStore.matches()
      |> Enum.filter(fn m -> is_integer(m.home_goal) and is_integer(m.away_goal) end)

    if Enum.empty?(matches) do
      0.0
    else
      home_wins = Enum.count(matches, fn m -> m.home_goal > m.away_goal end)
      home_wins / length(matches)
    end
  end

  def best_away_teams(limit \\ 10) do
    matches =
      DataStore.matches()
      |> Enum.filter(fn m -> is_integer(m.home_goal) and is_integer(m.away_goal) end)

    away_records =
      Enum.reduce(matches, %{}, fn m, acc ->
        diff = m.away_goal - m.home_goal
        result = cond do
          diff > 0 -> :win
          diff == 0 -> :draw
          true -> :loss
        end
        acc |> update_standing(m.away_team, result, m.away_goal, m.home_goal)
      end)

    away_records
    |> Enum.map(fn {team, s} ->
      played = s.wins + s.draws + s.losses
      win_rate = if played > 0, do: s.wins / played, else: 0.0
      %{team: team, wins: s.wins, draws: s.draws, losses: s.losses, played: played, win_rate: win_rate}
    end)
    |> Enum.filter(fn s -> s.played >= 5 end)
    |> Enum.sort_by(fn s -> {-s.win_rate, -s.wins} end)
    |> Enum.take(limit)
  end

  defp update_standing(table, team, result, goals_for, goals_against) do
    default = %{wins: 0, draws: 0, losses: 0, goals_for: 0, goals_against: 0}
    Map.update(table, team, default, fn s ->
      %{s |
        wins: s.wins + if(result == :win, do: 1, else: 0),
        draws: s.draws + if(result == :draw, do: 1, else: 0),
        losses: s.losses + if(result == :loss, do: 1, else: 0),
        goals_for: s.goals_for + goals_for,
        goals_against: s.goals_against + goals_against
      }
    end)
  end
end
