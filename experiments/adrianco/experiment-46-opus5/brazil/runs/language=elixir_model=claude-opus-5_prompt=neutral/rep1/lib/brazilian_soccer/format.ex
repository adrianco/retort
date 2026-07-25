defmodule BrazilianSoccer.Format do
  @moduledoc """
  Renders query results as the plain text an LLM (or a human) reads back.

  Every formatter is total: it never raises on missing data, it says what is
  missing instead.  The MCP layer pairs this text with the structured JSON of
  the same result.
  """

  alias BrazilianSoccer.Data.Graph
  alias BrazilianSoccer.Dates
  alias BrazilianSoccer.Model.{Match, Player, Team}

  @doc "Format a single match: `2019-11-23: Flamengo 2-1 Palmeiras (Brasileirão, round 34)`."
  @spec match_line(Match.t(), keyword) :: binary
  def match_line(%Match{} = match, opts \\ []) do
    competition? = Keyword.get(opts, :competition, true)

    score =
      if Match.played?(match) do
        "#{match.home_goals}-#{match.away_goals}"
      else
        "vs"
      end

    context =
      [
        competition? && competition_label(match.competition),
        match.season && "#{match.season}",
        round_label(match)
      ]
      |> Enum.filter(&is_binary/1)
      |> Enum.join(", ")

    home = team_label(match.home_id, match.home_name)
    away = team_label(match.away_id, match.away_name)

    line = "#{Dates.format(match.date)}: #{home} #{score} #{away}"
    line = if context == "", do: line, else: "#{line} (#{context})"

    if Match.played?(match), do: line, else: line <> " [result not in dataset]"
  end

  defp team_label(nil, raw), do: raw || "?"

  defp team_label(id, raw) do
    case BrazilianSoccer.Repo.loaded?() && Graph.team(BrazilianSoccer.Repo.graph(), id) do
      %Team{name: name} -> name
      _ -> raw || id
    end
  end

  defp round_label(%Match{stage: stage}) when is_binary(stage), do: stage
  defp round_label(%Match{round: round}) when is_integer(round), do: "round #{round}"
  defp round_label(_), do: nil

  @doc "Short competition name from its id."
  def competition_label(nil), do: nil

  def competition_label(id) do
    case Graph.competition(id) do
      nil -> to_string(id)
      competition -> competition.short_name
    end
  end

  # --- matches -------------------------------------------------------------

  def matches(%{matches: matches, total: total} = result) do
    header =
      case filter_summary(result[:filters] || %{}) do
        "" -> "Matches"
        summary -> "Matches (#{summary})"
      end

    cond do
      total == 0 ->
        "#{header}\nNo matches in the dataset for those filters."

      true ->
        [
          "#{header}: #{total} found",
          "",
          Enum.map_join(matches, "\n", &("- " <> match_line(&1))),
          more_line(total, length(matches))
        ]
        |> compact_join()
    end
  end

  def last_meeting(%{match: nil} = result) do
    teams =
      result[:filters]
      |> Kernel.||(%{})
      |> Map.take([:team, :opponent])
      |> Map.values()
      |> Enum.join(" and ")

    "No match between #{teams} in the datasets."
  end

  def last_meeting(%{match: match} = result) do
    [
      "Most recent meeting: " <> match_line(match),
      "Total meetings in the datasets: #{result.total}"
    ]
    |> compact_join()
  end

  def head_to_head(%{team_a: a, team_b: b, summary: s} = result) do
    header = "#{a.name} vs #{b.name}"

    body =
      if s.matches == 0 do
        "No meetings between these teams in the dataset."
      else
        [
          "Head-to-head in dataset: #{a.name} #{s.team_a_wins} wins, #{b.name} #{s.team_b_wins} wins, #{s.draws} draws",
          "Goals: #{a.name} #{s.team_a_goals} - #{s.team_b_goals} #{b.name} (#{s.matches} matches played)",
          competition_breakdown(result.by_competition, a, b),
          "",
          "Most recent meetings:",
          result.matches |> Enum.take(10) |> Enum.map_join("\n", &("- " <> match_line(&1))),
          more_line(s.matches, min(10, length(result.matches)))
        ]
        |> compact_join()
      end

    "#{header}\n#{body}"
  end

  defp competition_breakdown(by_competition, a, b) when map_size(by_competition) > 0 do
    lines =
      by_competition
      |> Enum.sort_by(fn {_, stats} -> -stats.matches end)
      |> Enum.map_join("\n", fn {competition, stats} ->
        "- #{competition_label(competition)}: #{stats.matches} matches " <>
          "(#{a.name} #{stats.team_a_wins}, #{b.name} #{stats.team_b_wins}, #{stats.draws} draws)"
      end)

    "By competition:\n" <> lines
  end

  defp competition_breakdown(_, _, _), do: nil

  def derbies(%{derbies: []}), do: "No derby matches found for those filters."

  def derbies(%{derbies: derbies} = result) do
    header =
      case filter_summary(result[:filters] || %{}) do
        "" -> "Traditional rivalries in the dataset"
        summary -> "Traditional rivalries (#{summary})"
      end

    body =
      Enum.map_join(derbies, "\n\n", fn derby ->
        shown = Enum.take(derby.matches, 3)

        [
          "#{derby.name} — #{derby.team_a.name} vs #{derby.team_b.name}: #{derby.total} matches",
          Enum.map_join(shown, "\n", &("  - " <> match_line(&1))),
          more_line(derby.total, length(shown))
        ]
        |> compact_join()
      end)

    "#{header}\n\n#{body}"
  end

  # --- teams ---------------------------------------------------------------

  def team_stats(%{team: team, record: record} = result) do
    scope = filter_summary(result[:filters] || %{}, skip: [:team])
    title = if scope == "", do: team.name, else: "#{team.name} (#{scope})"

    if record.matches == 0 do
      "#{title}\nNo matches in the dataset for those filters."
    else
      [
        "#{title} record:",
        "- Matches: #{record.matches}",
        "- Wins: #{record.wins}, Draws: #{record.draws}, Losses: #{record.losses}",
        "- Goals For: #{record.goals_for}, Goals Against: #{record.goals_against} (diff #{signed(record.goal_difference)})",
        "- Win rate: #{record.win_rate}% | Points per match: #{record.points_per_match}",
        venue_line("Home", result.home),
        venue_line("Away", result.away),
        form_line(result[:form]),
        by_competition_lines(result[:by_competition]),
        biggest_line("Biggest win", result[:biggest_win]),
        biggest_line("Heaviest defeat", result[:biggest_loss])
      ]
      |> compact_join()
    end
  end

  defp venue_line(_label, %{matches: 0}), do: nil

  defp venue_line(label, record) do
    "- #{label}: #{record.matches} matches, #{record.wins}W #{record.draws}D #{record.losses}L, " <>
      "#{record.goals_for}-#{record.goals_against} goals, #{record.win_rate}% win rate"
  end

  defp form_line(nil), do: nil
  defp form_line([]), do: nil

  defp form_line(form) do
    "- Most recent form (newest first): " <> Enum.map_join(form, " ", & &1.symbol)
  end

  defp by_competition_lines(nil), do: nil
  defp by_competition_lines([]), do: nil

  defp by_competition_lines(entries) do
    lines =
      entries
      |> Enum.sort_by(fn {_, record} -> -record.matches end)
      |> Enum.map_join("\n", fn {competition, record} ->
        "- #{competition_label(competition)}: #{record.matches} matches, " <>
          "#{record.wins}W #{record.draws}D #{record.losses}L, #{record.win_rate}% win rate"
      end)

    "By competition:\n" <> lines
  end

  defp biggest_line(_label, nil), do: nil
  defp biggest_line(label, match), do: "- #{label}: #{match_line(match)}"

  def team_profile(%{team: team} = result) do
    [
      "#{team.name}#{state_suffix(team)}",
      "- Also spelled: #{Enum.join(Enum.take(team.aliases, 6), ", ")}",
      "- Competitions: #{Enum.map_join(team.competitions, ", ", &competition_label/1)}",
      seasons_line(result[:seasons]),
      "- Matches in dataset: #{result.record.matches} (#{result.record.wins}W #{result.record.draws}D #{result.record.losses}L)",
      "- Goals: #{result.record.goals_for} scored, #{result.record.goals_against} conceded",
      result[:first_match] && "- First match: #{match_line(result.first_match)}",
      result[:last_match] && "- Last match: #{match_line(result.last_match)}",
      players_line(result)
    ]
    |> compact_join()
  end

  defp state_suffix(%Team{state: nil, country: nil}), do: ""
  defp state_suffix(%Team{state: nil, country: country}), do: " (#{country})"

  defp state_suffix(%Team{state: state, state_name: name}) do
    " (#{name || state}, Brazil)"
  end

  defp seasons_line(nil), do: nil
  defp seasons_line([]), do: nil

  defp seasons_line(seasons) do
    "- Seasons: #{Enum.min(seasons)}-#{Enum.max(seasons)} (#{length(seasons)} seasons)"
  end

  defp players_line(%{player_count: 0}), do: "- FIFA player data: none for this club"

  defp players_line(%{player_count: count, players: players}) do
    top = players |> Enum.take(3) |> Enum.map_join(", ", &"#{&1.name} (#{&1.overall})")
    "- FIFA squad: #{count} players; best rated: #{top}"
  end

  defp players_line(_), do: nil

  def compare_teams(%{team_a: a, team_b: b, head_to_head: h2h}) do
    [
      "#{a.team.name} vs #{b.team.name}",
      "",
      team_stats(a),
      "",
      team_stats(b),
      "",
      head_to_head(h2h)
    ]
    |> compact_join()
  end

  def rankings(%{rankings: []}), do: "No teams matched those filters."

  def rankings(%{rankings: rows} = result) do
    scope = filter_summary(result[:filters] || %{})
    metric = metric_label(result.metric)

    header =
      "Team rankings by #{result.sort_by} (#{metric}#{if scope == "", do: "", else: ", " <> scope}, " <>
        "minimum #{result.min_matches} matches)"

    body =
      rows
      |> Enum.with_index(1)
      |> Enum.map_join("\n", fn {row, index} ->
        r = row.record

        "#{index}. #{row.team.name} - #{r.win_rate}% win rate " <>
          "(#{r.matches} matches, #{r.wins}W #{r.draws}D #{r.losses}L, #{r.goals_for}-#{r.goals_against}, #{r.points} pts)"
      end)

    "#{header}\n\n#{body}"
  end

  defp metric_label(:home), do: "home matches only"
  defp metric_label(:away), do: "away matches only"
  defp metric_label(_), do: "all matches"

  # --- players -------------------------------------------------------------

  def players(%{players: [], total: 0} = result) do
    "No players match #{filter_summary(result[:filters] || %{}, default: "those filters")}."
  end

  def players(%{players: players, total: total} = result) do
    header =
      "Players (#{filter_summary(result[:filters] || %{}, default: "no filters")}): #{total} found"

    body =
      players
      |> Enum.with_index(1)
      |> Enum.map_join("\n", fn {player, index} -> "#{index}. #{player_line(player)}" end)

    compact_join([header, "", body, more_line(total, length(players))])
  end

  @doc "One line summary of a player."
  def player_line(%Player{} = player) do
    [
      player.name,
      player.overall && "Overall: #{player.overall}",
      player.position && "Position: #{player.position}",
      player.club && "Club: #{player.club}",
      player.age && "Age: #{player.age}",
      player.nationality
    ]
    |> Enum.filter(&is_binary/1)
    |> Enum.join(" - ")
  end

  def player_profile(%{player: player} = result) do
    [
      "#{player.name} (#{player.nationality})",
      "- Age #{player.age}, #{player.position || "position unknown"}, #{player.club || "no club"}" <>
        if(player.jersey_number, do: ", shirt #{player.jersey_number}", else: ""),
      "- FIFA rating: #{player.overall} overall, #{player.potential} potential",
      player.value && "- Value: #{player.value}, wage: #{player.wage}",
      player.height &&
        "- Height #{player.height}, weight #{player.weight}, #{player.preferred_foot} footed",
      skills_line(result[:top_skills]),
      club_link_line(result)
    ]
    |> compact_join()
  end

  defp skills_line(nil), do: nil
  defp skills_line([]), do: nil

  defp skills_line(skills) do
    "- Best attributes: " <>
      Enum.map_join(skills, ", ", fn {skill, value} -> "#{skill} #{value}" end)
  end

  defp club_link_line(%{club_team: nil}), do: nil

  defp club_link_line(%{club_team: team} = result) do
    [
      "- Club in the match graph: #{team.name} (#{team.match_count} matches in the datasets)",
      recent_matches_block("Recent #{team.name} matches", result[:club_matches]),
      teammates_line(result[:teammates])
    ]
    |> compact_join()
  end

  defp teammates_line(nil), do: nil
  defp teammates_line([]), do: nil

  defp teammates_line(players) do
    "- Highest rated team-mates: " <>
      Enum.map_join(players, ", ", &"#{&1.name} (#{&1.overall})")
  end

  def club_squad(%{players: players} = result) do
    [
      "#{result.club_label} squad in the FIFA dataset: #{result.size} players",
      result[:average_overall] &&
        "- Average rating: #{result.average_overall}, average age: #{result.average_age}",
      result[:best_player] && "- Best rated: #{player_line(result.best_player)}",
      "",
      players
      |> Enum.take(15)
      |> Enum.with_index(1)
      |> Enum.map_join("\n", fn {player, index} -> "#{index}. #{player_line(player)}" end),
      more_line(result.size, min(15, length(players))),
      recent_matches_block("Recent matches", result[:recent_matches])
    ]
    |> compact_join()
  end

  defp recent_matches_block(_title, nil), do: nil
  defp recent_matches_block(_title, []), do: nil

  defp recent_matches_block(title, matches) do
    "#{title}:\n" <> Enum.map_join(matches, "\n", &("- " <> match_line(&1)))
  end

  def nationality_report(result) do
    [
      "#{result.nationality} players in the FIFA dataset: #{result.total}",
      "- Average rating #{result.average_overall}, average age #{result.average_age}",
      "",
      "Top rated:",
      result.top_players
      |> Enum.with_index(1)
      |> Enum.map_join("\n", fn {player, index} -> "#{index}. #{player_line(player)}" end),
      "",
      club_summary(result)
    ]
    |> compact_join()
  end

  defp club_summary(%{by_brazilian_club: []}), do: nil

  defp club_summary(%{by_brazilian_club: clubs, nationality: nationality}) do
    lines =
      Enum.map_join(clubs, "\n", fn entry ->
        "- #{entry.team.name}: #{entry.count} players (avg rating: #{entry.average_overall})"
      end)

    "#{nationality} players at Brazilian clubs in the match graph:\n#{lines}"
  end

  # --- competitions --------------------------------------------------------

  def competitions(%{competitions: competitions}) do
    body =
      Enum.map_join(competitions, "\n", fn entry ->
        {from, to} = entry.season_range || {nil, nil}

        "- #{entry.competition.name} (#{entry.competition.short_name}): " <>
          "#{entry.matches} matches, #{entry.teams} teams, seasons #{from}-#{to}"
      end)

    "Competitions in the knowledge graph:\n#{body}"
  end

  def standings(%{table: table} = result) do
    header =
      "#{result.competition.short_name} #{result.season} " <>
        "#{venue_qualifier(result.venue)}standings (calculated from #{result.matches_counted} matches)"

    rows =
      Enum.map_join(table, "\n", fn row ->
        r = row.record

        marker =
          cond do
            row.position == 1 and result[:champion] -> " - Champion"
            row.team in (result[:relegated] || []) -> " - Relegated"
            true -> ""
          end

        "#{row.position}. #{row.team.name} - #{r.points} pts " <>
          "(#{r.wins}W, #{r.draws}D, #{r.losses}L, #{r.goals_for}-#{r.goals_against}, #{signed(r.goal_difference)})#{marker}"
      end)

    [header, "", rows, "", result[:note], dropped_line(result[:dropped_teams])]
    |> compact_join()
  end

  defp venue_qualifier(:home), do: "home "
  defp venue_qualifier(:away), do: "away "
  defp venue_qualifier(_), do: ""

  defp dropped_line(nil), do: nil
  defp dropped_line([]), do: nil

  defp dropped_line(teams) do
    "Excluded as data artefacts (too few matches to be league entrants): " <>
      Enum.map_join(teams, ", ", & &1.name)
  end

  def champion(%{champion: nil} = result) do
    "The #{result.competition.short_name} #{result.season} winner cannot be derived from the data" <>
      case result.detail do
        %{legs: legs} -> ":\n" <> Enum.map_join(legs, "\n", &("- " <> match_line(&1)))
        _ -> "."
      end
  end

  def champion(%{basis: :league_table} = result) do
    r = result.detail.record

    [
      "#{result.competition.short_name} #{result.season}: #{result.champion.name}",
      "- #{r.points} points from #{r.matches} matches (#{r.wins}W, #{r.draws}D, #{r.losses}L), goals #{r.goals_for}-#{r.goals_against}",
      result[:runner_up] && "- Runner-up: #{result.runner_up.name}",
      result[:note]
    ]
    |> compact_join()
  end

  def champion(%{basis: :final} = result) do
    [
      "#{result.competition.short_name} #{result.season}: #{result.champion.name}",
      result[:runner_up] && "- Runner-up: #{result.runner_up.name}",
      "Final:",
      Enum.map_join(result.detail.legs, "\n", &("- " <> match_line(&1))),
      result[:note]
    ]
    |> compact_join()
  end

  @bracket_matches_per_stage 16

  def bracket(result) do
    stages =
      Enum.map_join(result.stages, "\n\n", fn stage ->
        shown = Enum.take(stage.matches, @bracket_matches_per_stage)

        [
          "#{String.upcase(stage.stage)} (#{length(stage.matches)} matches)",
          Enum.map_join(shown, "\n", &("- " <> match_line(&1, competition: false))),
          more_line(length(stage.matches), length(shown))
        ]
        |> compact_join()
      end)

    champion =
      case result[:champion] do
        %{champion: %Team{name: name}} -> "\n\nWinner: #{name}"
        _ -> ""
      end

    "#{result.competition.name} #{result.season} — #{result.matches_counted} matches\n\n#{stages}#{champion}"
  end

  def competition_summary(result) do
    scope = if result.season, do: "#{result.season}", else: "all seasons"

    [
      "#{result.competition.name} — #{scope}",
      "- Matches: #{result.matches}, teams: #{result.teams}",
      "- Goals: #{result.goals} (#{result.goals_per_match} per match)",
      "- Home wins #{result.home_win_rate}%, draws #{result.draw_rate}%, away wins #{result.away_win_rate}%",
      "",
      "Top scoring teams:",
      result.top_scoring_teams
      |> Enum.with_index(1)
      |> Enum.map_join("\n", fn {entry, index} ->
        "#{index}. #{entry.team.name} - #{entry.record.goals_for} goals in #{entry.record.matches} matches"
      end),
      "",
      "Best defences:",
      result.best_defences
      |> Enum.with_index(1)
      |> Enum.map_join("\n", fn {entry, index} ->
        "#{index}. #{entry.team.name} - #{entry.record.goals_against} conceded in #{entry.record.matches} matches"
      end),
      result[:biggest_win] && "\nBiggest win: #{match_line(result.biggest_win)}",
      champion_line(result[:champion])
    ]
    |> compact_join()
  end

  defp champion_line(nil), do: nil
  defp champion_line(%{champion: nil}), do: nil
  defp champion_line(%{champion: team}), do: "Champion (derived): #{team.name}"

  # --- stats ---------------------------------------------------------------

  def stats_overview(result) do
    scope = filter_summary(result[:filters] || %{}, default: "all competitions and seasons")

    [
      "Match statistics (#{scope})",
      "- Matches: #{result.matches}",
      "- Goals: #{result.goals}, average #{result.goals_per_match} per match",
      "- Home wins: #{result.home_win_rate}%, draws: #{result.draw_rate}%, away wins: #{result.away_win_rate}%",
      "- Both teams scored: #{result.both_scored_rate}%",
      result[:highest_scoring] && "- Highest scoring match: #{match_line(result.highest_scoring)}",
      result[:biggest_margin] && "- Biggest margin: #{match_line(result.biggest_margin)}",
      by_season_block(result[:by_season])
    ]
    |> compact_join()
  end

  defp by_season_block(nil), do: nil
  defp by_season_block([]), do: nil

  defp by_season_block(entries) when length(entries) > 1 do
    lines =
      Enum.map_join(entries, "\n", fn {season, stats} ->
        "- #{season || "unknown"}: #{stats.matches} matches, #{stats.goals_per_match} goals/match, " <>
          "#{stats.home_win_rate}% home wins"
      end)

    "By season:\n" <> lines
  end

  defp by_season_block(_), do: nil

  def biggest_wins(%{matches: []}), do: "No matches found for those filters."

  def biggest_wins(%{matches: matches} = result) do
    scope = filter_summary(result[:filters] || %{}, default: "all competitions")

    body =
      matches
      |> Enum.with_index(1)
      |> Enum.map_join("\n", fn {match, index} -> "#{index}. #{match_line(match)}" end)

    "Biggest victories (#{scope}):\n\n#{body}"
  end

  def highest_scoring(%{matches: []}), do: "No matches found for those filters."

  def highest_scoring(%{matches: matches} = result) do
    scope = filter_summary(result[:filters] || %{}, default: "all competitions")

    body =
      matches
      |> Enum.with_index(1)
      |> Enum.map_join("\n", fn {match, index} ->
        "#{index}. #{match_line(match)} — #{Match.total_goals(match)} goals"
      end)

    "Highest scoring matches (#{scope}):\n\n#{body}"
  end

  def compare_seasons(result) do
    body =
      Enum.map_join(result.seasons, "\n\n", fn block ->
        if block.available do
          [
            "#{block.season}:",
            "- Matches: #{block.stats.matches}, goals: #{block.stats.goals} (#{block.stats.goals_per_match} per match)",
            "- Home wins #{block.stats.home_win_rate}%, draws #{block.stats.draw_rate}%, away wins #{block.stats.away_win_rate}%",
            block[:champion] && "- Champion (derived): #{block.champion.name}",
            block[:top_scoring_team] &&
              "- Top scoring team: #{block.top_scoring_team.team.name} (#{block.top_scoring_team.goals} goals)"
          ]
          |> compact_join()
        else
          "#{block.season}: no matches in the dataset"
        end
      end)

    "#{result.competition.name} season comparison\n\n#{body}"
  end

  def home_advantage(result) do
    [
      "Home advantage in #{result.competition.name}",
      "- Overall: #{result.overall.home_win_rate}% home wins, #{result.overall.draw_rate}% draws, " <>
        "#{result.overall.away_win_rate}% away wins (#{result.overall.matches} matches)",
      "- Goals: #{result.overall.home_goals} home, #{result.overall.away_goals} away",
      by_season_block(result[:by_season])
    ]
    |> compact_join()
  end

  def info(meta) do
    files =
      Enum.map_join(meta.files, "\n", fn file ->
        "- #{file.file}: #{file.rows} rows — #{file.description}"
      end)

    [
      "Brazilian soccer knowledge graph",
      "- #{meta.matches} unique matches from #{meta.raw_match_rows} CSV rows (duplicates across files merged)",
      "- #{meta.teams} teams, #{meta.players} players",
      "- Data directory: #{meta.data_dir}",
      "",
      "Source files:",
      files,
      "",
      "Competitions: " <> Enum.map_join(meta.competitions, ", ", & &1.name)
    ]
    |> compact_join()
  end

  # --- errors --------------------------------------------------------------

  @doc "Explain an error tuple in plain English."
  @spec error(term) :: binary
  def error({:team_not_found, query, []}), do: "No team called \"#{query}\" in the datasets."

  def error({:team_not_found, query, suggestions}) do
    "No team called \"#{query}\" in the datasets. Closest names: #{Enum.join(suggestions, ", ")}."
  end

  def error({:player_not_found, query, suggestions}) do
    "No player called \"#{query}\" in the FIFA dataset." <>
      if suggestions == [], do: "", else: " Closest names: #{Enum.join(suggestions, ", ")}."
  end

  def error({:club_not_in_player_data, club, examples}) do
    "#{club} has no players in the FIFA dataset — that export does not license every Brazilian club. " <>
      "Clubs that do have players: #{Enum.join(examples, ", ")}."
  end

  def error({:club_not_found, club, examples}) do
    "No club called \"#{club}\" in the player data. Clubs with players: #{Enum.join(examples, ", ")}."
  end

  def error({:unknown_competition, value, known}) do
    "Unknown competition \"#{value}\". Known competitions: #{Enum.map_join(known, ", ", &to_string/1)}."
  end

  def error({:missing_argument, key}), do: "Missing required argument: #{key}."

  def error({:invalid_season, value}), do: "Could not read \"#{inspect(value)}\" as a season year."

  def error({:invalid_date, value}),
    do: "Could not read \"#{inspect(value)}\" as a date (try YYYY-MM-DD)."

  def error({:invalid_venue, value}), do: "Unknown venue \"#{value}\" (use home, away or all)."

  def error({:invalid_team, value}), do: "Could not read #{inspect(value)} as a team name."

  def error({:no_data, competition, season, seasons}) do
    "No #{competition_label(competition)} data for #{season}. Available seasons: #{Enum.join(seasons, ", ")}."
  end

  def error({:no_final, competition, season, seasons}) do
    "No final recorded for #{competition_label(competition)} #{season}. Available seasons: #{Enum.join(seasons, ", ")}."
  end

  def error({:no_matches, filters}) do
    "No matches in the dataset for #{filter_summary(filters, default: "those filters")}."
  end

  def error({:unknown_tool, name}), do: "Unknown tool: #{name}."

  def error(other), do: "Query failed: #{inspect(other)}"

  # --- helpers -------------------------------------------------------------

  defp filter_summary(filters, opts \\ []) do
    skip = Keyword.get(opts, :skip, [])

    summary =
      filters
      |> Enum.reject(fn {key, value} -> key in skip or is_nil(value) or value == :all end)
      |> Enum.sort_by(fn {key, _} -> key end)
      |> Enum.map_join(", ", fn {key, value} -> "#{key}: #{format_value(value)}" end)

    case {summary, Keyword.get(opts, :default)} do
      {"", nil} -> ""
      {"", default} -> default
      {summary, _} -> summary
    end
  end

  defp format_value(%Date{} = date), do: Date.to_iso8601(date)
  defp format_value(value) when is_atom(value), do: competition_label(value) || to_string(value)
  defp format_value(value), do: to_string(value)

  defp more_line(total, shown) when total > shown, do: "... (#{total - shown} more)"
  defp more_line(_total, _shown), do: nil

  defp signed(value) when value > 0, do: "+#{value}"
  defp signed(value), do: to_string(value)

  defp compact_join(parts) do
    parts
    |> Enum.filter(&is_binary/1)
    |> Enum.join("\n")
    |> String.replace(~r/\n{3,}/, "\n\n")
    |> String.trim()
  end
end
