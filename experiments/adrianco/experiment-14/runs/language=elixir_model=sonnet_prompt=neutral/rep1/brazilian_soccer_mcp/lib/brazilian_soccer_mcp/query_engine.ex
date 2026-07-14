defmodule BrazilianSoccerMcp.QueryEngine do
  @moduledoc """
  Query logic for all MCP tools. Each function returns a formatted string response.
  """

  alias BrazilianSoccerMcp.{DataStore, TeamNormalizer}

  @competition_names %{
    brasileirao: "Brasileirão Serie A",
    copa_brasil: "Copa do Brasil",
    libertadores: "Copa Libertadores",
    extended: "Brazilian Football (Extended)",
    historical: "Brasileirão (Historical 2003-2019)"
  }

  # ─── Match Search ────────────────────────────────────────────────────────────

  @doc """
  Search matches by optional filters:
    - team: string (matches either home or away)
    - home_team: string
    - away_team: string
    - competition: "brasileirao" | "copa_brasil" | "libertadores" | "extended" | "historical"
    - season: integer
    - date_from: "YYYY-MM-DD"
    - date_to: "YYYY-MM-DD"
    - limit: integer (default 20)
  """
  def search_matches(params) do
    matches =
      DataStore.get_all_matches()
      |> filter_by_competition(params["competition"])
      |> filter_by_team(params["team"])
      |> filter_by_home_team(params["home_team"])
      |> filter_by_away_team(params["away_team"])
      |> filter_by_season(params["season"])
      |> filter_by_date_range(params["date_from"], params["date_to"])
      |> Enum.sort_by(& &1.datetime, :desc)

    total = length(matches)
    limit = Map.get(params, "limit", 20) |> parse_limit()
    shown = Enum.take(matches, limit)

    if total == 0 do
      "No matches found for the given criteria."
    else
      lines =
        shown
        |> Enum.map(&format_match/1)

      header =
        if total > limit,
          do: "Found #{total} matches (showing first #{limit}):\n",
          else: "Found #{total} match(es):\n"

      header <> Enum.join(lines, "\n")
    end
  end

  # ─── Team Stats ──────────────────────────────────────────────────────────────

  @doc """
  Get statistics for a team.
  Params: team (required), competition (optional), season (optional)
  """
  def get_team_stats(params) do
    team = params["team"]

    if is_nil(team) or team == "" do
      "Error: 'team' parameter is required."
    else
      matches =
        DataStore.get_all_matches()
        |> filter_by_team(team)
        |> filter_by_competition(params["competition"])
        |> filter_by_season(params["season"])

      if Enum.empty?(matches) do
        "No matches found for team '#{team}'."
      else
        stats = calculate_team_stats(matches, team)
        format_team_stats(stats, team, params)
      end
    end
  end

  # ─── Head to Head ────────────────────────────────────────────────────────────

  @doc """
  Get head-to-head record between two teams.
  Params: team1, team2 (required), competition (optional), season (optional)
  """
  def head_to_head(params) do
    team1 = params["team1"]
    team2 = params["team2"]

    if is_nil(team1) or is_nil(team2) do
      "Error: 'team1' and 'team2' parameters are required."
    else
      matches =
        DataStore.get_all_matches()
        |> filter_by_both_teams(team1, team2)
        |> filter_by_competition(params["competition"])
        |> filter_by_season(params["season"])
        |> Enum.sort_by(& &1.datetime, :desc)

      if Enum.empty?(matches) do
        "No matches found between '#{team1}' and '#{team2}'."
      else
        format_head_to_head(matches, team1, team2)
      end
    end
  end

  # ─── Player Search ───────────────────────────────────────────────────────────

  @doc """
  Search players by name, nationality, club, or position.
  Params: name, nationality, club, position (all optional), limit (default 20)
  """
  def search_players(params) do
    players =
      DataStore.get_players()
      |> filter_players_by_name(params["name"])
      |> filter_players_by_nationality(params["nationality"])
      |> filter_players_by_club(params["club"])
      |> filter_players_by_position(params["position"])
      |> Enum.sort_by(& &1.overall, :desc)

    total = length(players)
    limit = Map.get(params, "limit", 20) |> parse_limit()
    shown = Enum.take(players, limit)

    if total == 0 do
      "No players found for the given criteria."
    else
      header =
        if total > limit,
          do: "Found #{total} players (showing top #{limit} by overall rating):\n",
          else: "Found #{total} player(s):\n"

      lines = shown |> Enum.with_index(1) |> Enum.map(&format_player/1)
      header <> Enum.join(lines, "\n")
    end
  end

  # ─── Standings ───────────────────────────────────────────────────────────────

  @doc """
  Calculate league standings for a season.
  Params: season (required), competition (optional, defaults to brasileirao)
  """
  def get_standings(params) do
    season = params["season"]

    if is_nil(season) do
      "Error: 'season' parameter is required."
    else
      season_int = parse_int(season)
      competition = Map.get(params, "competition", "brasileirao")

      matches =
        case competition do
          "historical" ->
            DataStore.get_historical()
          "brasileirao" ->
            # Brasileirao_Matches.csv covers 2012+; historical covers 2003-2019.
            # Use brasileirao for 2012+ to avoid double-counting.
            if season_int >= 2012 do
              DataStore.get_brasileirao()
            else
              DataStore.get_historical()
            end
          _ ->
            DataStore.get_all_matches()
            |> filter_by_competition(competition)
        end

      season_matches =
        matches
        |> Enum.filter(&(&1.season == season_int))
        |> Enum.reject(&(is_nil(&1.home_goal) or is_nil(&1.away_goal)))

      if Enum.empty?(season_matches) do
        "No match data found for season #{season}."
      else
        standings = calculate_standings(season_matches)
        comp_name = Map.get(@competition_names, String.to_atom(competition), competition)
        format_standings(standings, season_int, comp_name)
      end
    end
  end

  # ─── Biggest Wins ────────────────────────────────────────────────────────────

  @doc """
  Find biggest wins (by goal difference).
  Params: competition (optional), season (optional), limit (default 10)
  """
  def get_biggest_wins(params) do
    limit = Map.get(params, "limit", 10) |> parse_limit()

    matches =
      DataStore.get_all_matches()
      |> filter_by_competition(params["competition"])
      |> filter_by_season(params["season"])
      |> Enum.reject(&(is_nil(&1.home_goal) or is_nil(&1.away_goal)))
      |> Enum.sort_by(&abs(&1.home_goal - &1.away_goal), :desc)
      |> Enum.take(limit)

    if Enum.empty?(matches) do
      "No matches found."
    else
      lines = matches |> Enum.with_index(1) |> Enum.map(fn {m, i} ->
        diff = abs(m.home_goal - m.away_goal)
        "#{i}. #{m.datetime || "?"}: #{m.home_team} #{m.home_goal}-#{m.away_goal} #{m.away_team} " <>
        "(#{comp_label(m)}, goal diff: #{diff})"
      end)
      "Biggest wins:\n" <> Enum.join(lines, "\n")
    end
  end

  # ─── Summary Statistics ──────────────────────────────────────────────────────

  @doc """
  Get overall summary statistics.
  Params: competition (optional), season (optional)
  """
  def get_summary_stats(params) do
    matches =
      DataStore.get_all_matches()
      |> filter_by_competition(params["competition"])
      |> filter_by_season(params["season"])
      |> Enum.reject(&(is_nil(&1.home_goal) or is_nil(&1.away_goal)))

    if Enum.empty?(matches) do
      "No match data found."
    else
      total = length(matches)
      total_goals = Enum.sum(Enum.map(matches, &(&1.home_goal + &1.away_goal)))
      avg_goals = Float.round(total_goals / total, 2)

      home_wins = Enum.count(matches, &(&1.home_goal > &1.away_goal))
      draws = Enum.count(matches, &(&1.home_goal == &1.away_goal))
      away_wins = Enum.count(matches, &(&1.home_goal < &1.away_goal))

      home_win_pct = Float.round(home_wins / total * 100, 1)
      draw_pct = Float.round(draws / total * 100, 1)
      away_win_pct = Float.round(away_wins / total * 100, 1)

      seasons =
        matches
        |> Enum.map(& &1.season)
        |> Enum.reject(&is_nil/1)
        |> Enum.uniq()
        |> Enum.sort()

      season_range =
        if length(seasons) > 0,
          do: "#{List.first(seasons)}-#{List.last(seasons)}",
          else: "unknown"

      """
      Summary Statistics:
      - Total matches: #{total}
      - Season range: #{season_range}
      - Total goals: #{total_goals}
      - Average goals per match: #{avg_goals}
      - Home wins: #{home_wins} (#{home_win_pct}%)
      - Draws: #{draws} (#{draw_pct}%)
      - Away wins: #{away_wins} (#{away_win_pct}%)
      """
    end
  end

  # ─── Filtering Helpers ───────────────────────────────────────────────────────

  defp filter_by_competition(matches, nil), do: matches
  defp filter_by_competition(matches, ""), do: matches
  defp filter_by_competition(matches, comp) when is_binary(comp) do
    atom = String.to_atom(comp)
    Enum.filter(matches, &(&1.competition == atom))
  end

  defp filter_by_team(matches, nil), do: matches
  defp filter_by_team(matches, ""), do: matches
  defp filter_by_team(matches, team) do
    Enum.filter(matches, fn m ->
      TeamNormalizer.matches?(m.home_team, team) or
      TeamNormalizer.matches?(m.away_team, team)
    end)
  end

  defp filter_by_home_team(matches, nil), do: matches
  defp filter_by_home_team(matches, ""), do: matches
  defp filter_by_home_team(matches, team) do
    Enum.filter(matches, &TeamNormalizer.matches?(&1.home_team, team))
  end

  defp filter_by_away_team(matches, nil), do: matches
  defp filter_by_away_team(matches, ""), do: matches
  defp filter_by_away_team(matches, team) do
    Enum.filter(matches, &TeamNormalizer.matches?(&1.away_team, team))
  end

  defp filter_by_both_teams(matches, team1, team2) do
    Enum.filter(matches, fn m ->
      (TeamNormalizer.matches?(m.home_team, team1) and
       TeamNormalizer.matches?(m.away_team, team2)) or
      (TeamNormalizer.matches?(m.home_team, team2) and
       TeamNormalizer.matches?(m.away_team, team1))
    end)
  end

  defp filter_by_season(matches, nil), do: matches
  defp filter_by_season(matches, ""), do: matches
  defp filter_by_season(matches, season) when is_binary(season) do
    filter_by_season(matches, parse_int(season))
  end
  defp filter_by_season(matches, season) when is_integer(season) do
    Enum.filter(matches, &(&1.season == season))
  end

  defp filter_by_date_range(matches, nil, nil), do: matches
  defp filter_by_date_range(matches, from, to) do
    Enum.filter(matches, fn m ->
      date = m.datetime
      (is_nil(from) or is_nil(date) or date >= from) and
      (is_nil(to) or is_nil(date) or date <= to)
    end)
  end

  defp filter_players_by_name(players, nil), do: players
  defp filter_players_by_name(players, ""), do: players
  defp filter_players_by_name(players, name) do
    name_lower = String.downcase(name)
    Enum.filter(players, fn p ->
      String.contains?(String.downcase(p.name), name_lower)
    end)
  end

  defp filter_players_by_nationality(players, nil), do: players
  defp filter_players_by_nationality(players, ""), do: players
  defp filter_players_by_nationality(players, nat) do
    nat_lower = String.downcase(nat)
    Enum.filter(players, fn p ->
      String.contains?(String.downcase(p.nationality), nat_lower)
    end)
  end

  defp filter_players_by_club(players, nil), do: players
  defp filter_players_by_club(players, ""), do: players
  defp filter_players_by_club(players, club) do
    club_lower = String.downcase(club)
    Enum.filter(players, fn p ->
      String.contains?(String.downcase(p.club), club_lower)
    end)
  end

  defp filter_players_by_position(players, nil), do: players
  defp filter_players_by_position(players, ""), do: players
  defp filter_players_by_position(players, pos) do
    pos_lower = String.downcase(pos)
    Enum.filter(players, fn p ->
      String.contains?(String.downcase(p.position), pos_lower)
    end)
  end

  # ─── Statistics Calculation ──────────────────────────────────────────────────

  defp calculate_team_stats(matches, team) do
    matches
    |> Enum.reject(&(is_nil(&1.home_goal) or is_nil(&1.away_goal)))
    |> Enum.reduce(%{played: 0, wins: 0, draws: 0, losses: 0,
                     goals_for: 0, goals_against: 0,
                     home_played: 0, home_wins: 0, home_draws: 0, home_losses: 0,
                     away_played: 0, away_wins: 0, away_draws: 0, away_losses: 0},
      fn m, acc ->
        is_home = TeamNormalizer.matches?(m.home_team, team)
        {gf, ga} = if is_home, do: {m.home_goal, m.away_goal}, else: {m.away_goal, m.home_goal}
        result = cond do
          gf > ga -> :win
          gf == ga -> :draw
          true -> :loss
        end

        acc
        |> Map.update!(:played, &(&1 + 1))
        |> Map.update!(:goals_for, &(&1 + gf))
        |> Map.update!(:goals_against, &(&1 + ga))
        |> update_result(result)
        |> update_home_away(is_home, result)
      end)
  end

  defp update_result(acc, :win), do: Map.update!(acc, :wins, &(&1 + 1))
  defp update_result(acc, :draw), do: Map.update!(acc, :draws, &(&1 + 1))
  defp update_result(acc, :loss), do: Map.update!(acc, :losses, &(&1 + 1))

  defp update_home_away(acc, true, result) do
    acc
    |> Map.update!(:home_played, &(&1 + 1))
    |> case do
      a when result == :win -> Map.update!(a, :home_wins, &(&1 + 1))
      a when result == :draw -> Map.update!(a, :home_draws, &(&1 + 1))
      a -> Map.update!(a, :home_losses, &(&1 + 1))
    end
  end
  defp update_home_away(acc, false, result) do
    acc
    |> Map.update!(:away_played, &(&1 + 1))
    |> case do
      a when result == :win -> Map.update!(a, :away_wins, &(&1 + 1))
      a when result == :draw -> Map.update!(a, :away_draws, &(&1 + 1))
      a -> Map.update!(a, :away_losses, &(&1 + 1))
    end
  end

  defp calculate_standings(matches) do
    # Use light normalization for standings to keep teams distinct (e.g. Atletico-MG vs Atletico-PR)
    norm_matches =
      matches
      |> Enum.reject(&(is_nil(&1.home_goal) or is_nil(&1.away_goal)))
      |> Enum.map(fn m ->
        Map.merge(m, %{
          norm_home: standings_key(m.home_team),
          norm_away: standings_key(m.away_team)
        })
      end)

    teams =
      norm_matches
      |> Enum.flat_map(&[&1.norm_home, &1.norm_away])
      |> Enum.uniq()

    teams
    |> Enum.map(fn norm_team ->
      stats =
        norm_matches
        |> Enum.filter(&(&1.norm_home == norm_team or &1.norm_away == norm_team))
        |> Enum.reduce(%{played: 0, wins: 0, draws: 0, losses: 0,
                         goals_for: 0, goals_against: 0, points: 0},
          fn m, acc ->
            is_home = m.norm_home == norm_team
            {gf, ga} = if is_home, do: {m.home_goal, m.away_goal}, else: {m.away_goal, m.home_goal}
            {w, d, l, pts} = cond do
              gf > ga -> {1, 0, 0, 3}
              gf == ga -> {0, 1, 0, 1}
              true -> {0, 0, 1, 0}
            end
            %{
              played: acc.played + 1,
              wins: acc.wins + w,
              draws: acc.draws + d,
              losses: acc.losses + l,
              goals_for: acc.goals_for + gf,
              goals_against: acc.goals_against + ga,
              points: acc.points + pts
            }
          end)

      Map.put(stats, :team, norm_team)
    end)
    |> Enum.sort_by(&{&1.points, &1.wins, &1.goals_for - &1.goals_against}, :desc)
  end

  # ─── Formatting ──────────────────────────────────────────────────────────────

  defp format_match(m) do
    date = m.datetime || "?"
    comp = comp_label(m)
    round_info = if m.round, do: " Round #{m.round}", else: ""
    stage_info = if m.stage, do: " (#{m.stage})", else: ""
    "  #{date}: #{m.home_team} #{m.home_goal}-#{m.away_goal} #{m.away_team} [#{comp}#{round_info}#{stage_info}]"
  end

  defp format_team_stats(stats, team, params) do
    comp = Map.get(params, "competition", "all competitions")
    season = Map.get(params, "season", "all seasons")

    win_rate =
      if stats.played > 0,
        do: Float.round(stats.wins / stats.played * 100, 1),
        else: 0.0

    gd = stats.goals_for - stats.goals_against

    """
    #{team} - #{comp} (#{season}):
    - Matches played: #{stats.played}
    - Record: #{stats.wins}W / #{stats.draws}D / #{stats.losses}L
    - Points: #{stats.wins * 3 + stats.draws}
    - Goals For: #{stats.goals_for}, Goals Against: #{stats.goals_against} (GD: #{gd})
    - Win rate: #{win_rate}%
    - Home: #{stats.home_wins}W/#{stats.home_draws}D/#{stats.home_losses}L (#{stats.home_played} games)
    - Away: #{stats.away_wins}W/#{stats.away_draws}D/#{stats.away_losses}L (#{stats.away_played} games)
    """
  end

  defp format_head_to_head(matches, team1, team2) do
    total = length(matches)
    valid = Enum.reject(matches, &(is_nil(&1.home_goal) or is_nil(&1.away_goal)))

    team1_wins =
      Enum.count(valid, fn m ->
        (TeamNormalizer.matches?(m.home_team, team1) and m.home_goal > m.away_goal) or
        (TeamNormalizer.matches?(m.away_team, team1) and m.away_goal > m.home_goal)
      end)

    team2_wins =
      Enum.count(valid, fn m ->
        (TeamNormalizer.matches?(m.home_team, team2) and m.home_goal > m.away_goal) or
        (TeamNormalizer.matches?(m.away_team, team2) and m.away_goal > m.home_goal)
      end)

    draws = Enum.count(valid, &(&1.home_goal == &1.away_goal))

    limit = 10
    shown = Enum.take(matches, limit)
    lines = Enum.map(shown, &format_match/1)

    header =
      if total > limit,
        do: "Head-to-head: #{team1} vs #{team2} (showing #{limit} most recent of #{total}):\n",
        else: "Head-to-head: #{team1} vs #{team2} (#{total} matches):\n"

    summary = "\nSummary: #{team1} #{team1_wins} wins, #{team2} #{team2_wins} wins, #{draws} draws"

    header <> Enum.join(lines, "\n") <> summary
  end

  defp format_player({player, index}) do
    "#{index}. #{player.name} | Overall: #{player.overall || "?"} | " <>
    "Position: #{player.position || "?"} | Club: #{player.club || "?"} | " <>
    "Nationality: #{player.nationality || "?"} | Age: #{player.age || "?"}"
  end

  defp format_standings(standings, season, comp_name) do
    limit = 20
    shown = Enum.take(standings, limit)

    lines =
      shown
      |> Enum.with_index(1)
      |> Enum.map(fn {s, i} ->
        gd = s.goals_for - s.goals_against
        "#{String.pad_leading("#{i}", 2)}. #{String.pad_trailing(s.team, 30)} " <>
        "#{s.points}pts  #{s.wins}W #{s.draws}D #{s.losses}L  " <>
        "GF:#{s.goals_for} GA:#{s.goals_against} GD:#{gd}"
      end)

    "#{season} #{comp_name} Standings (top #{min(limit, length(standings))}):\n" <>
    Enum.join(lines, "\n")
  end

  # Light normalization for standings: remove only parenthetical notes, keep state codes.
  defp standings_key(name) do
    name
    |> String.trim()
    |> String.replace(~r/\s*\([^)]*\)/, "")
    |> String.trim()
  end

  defp comp_label(%{competition: :brasileirao}), do: "Brasileirão"
  defp comp_label(%{competition: :copa_brasil}), do: "Copa do Brasil"
  defp comp_label(%{competition: :libertadores}), do: "Libertadores"
  defp comp_label(%{competition: :extended, tournament: t}) when not is_nil(t), do: t
  defp comp_label(%{competition: :extended}), do: "Brazilian Football"
  defp comp_label(%{competition: :historical}), do: "Brasileirão (hist.)"
  defp comp_label(_), do: "Unknown"

  defp parse_int(nil), do: nil
  defp parse_int(n) when is_integer(n), do: n
  defp parse_int(s) when is_binary(s) do
    case Integer.parse(s) do
      {n, _} -> n
      :error -> nil
    end
  end

  defp parse_limit(nil), do: 20
  defp parse_limit(n) when is_integer(n), do: n
  defp parse_limit(s) when is_binary(s) do
    case Integer.parse(s) do
      {n, _} -> n
      :error -> 20
    end
  end
end
