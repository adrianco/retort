defmodule BrazilianSoccer.MCP.Tools do
  @moduledoc "Tool definitions and handlers for the Brazilian Soccer MCP server."

  alias BrazilianSoccer.Queries.{Matches, Players, Teams}

  def definitions do
    [
      %{
        "name" => "search_matches",
        "description" => "Search for matches by team, competition, season, or date range",
        "inputSchema" => %{
          "type" => "object",
          "properties" => %{
            "team" => %{"type" => "string", "description" => "Team name to search for"},
            "team2" => %{"type" => "string", "description" => "Second team for head-to-head search"},
            "competition" => %{"type" => "string", "description" => "Competition name (Brasileirão, Copa do Brasil, Copa Libertadores)"},
            "season" => %{"type" => "integer", "description" => "Season year"},
            "from_date" => %{"type" => "string", "description" => "Start date (YYYY-MM-DD)"},
            "to_date" => %{"type" => "string", "description" => "End date (YYYY-MM-DD)"},
            "limit" => %{"type" => "integer", "description" => "Maximum number of results (default 20)"}
          }
        }
      },
      %{
        "name" => "get_team_stats",
        "description" => "Get win/draw/loss record and goals for a team",
        "inputSchema" => %{
          "type" => "object",
          "properties" => %{
            "team" => %{"type" => "string", "description" => "Team name"},
            "season" => %{"type" => "integer", "description" => "Filter by season"},
            "competition" => %{"type" => "string", "description" => "Filter by competition"},
            "home_only" => %{"type" => "boolean", "description" => "Only home matches"}
          },
          "required" => ["team"]
        }
      },
      %{
        "name" => "search_players",
        "description" => "Search for players in the FIFA database by name, nationality, club, or position",
        "inputSchema" => %{
          "type" => "object",
          "properties" => %{
            "name" => %{"type" => "string", "description" => "Player name"},
            "nationality" => %{"type" => "string", "description" => "Player nationality"},
            "club" => %{"type" => "string", "description" => "Club name"},
            "position" => %{"type" => "string", "description" => "Playing position (GK, ST, LW, etc.)"},
            "top" => %{"type" => "integer", "description" => "Return top N players by overall rating"},
            "limit" => %{"type" => "integer", "description" => "Maximum results (default 20)"}
          }
        }
      },
      %{
        "name" => "get_standings",
        "description" => "Get competition standings calculated from match results",
        "inputSchema" => %{
          "type" => "object",
          "properties" => %{
            "season" => %{"type" => "integer", "description" => "Season year"},
            "competition" => %{"type" => "string", "description" => "Competition name"}
          },
          "required" => ["season", "competition"]
        }
      },
      %{
        "name" => "head_to_head",
        "description" => "Get head-to-head record between two teams",
        "inputSchema" => %{
          "type" => "object",
          "properties" => %{
            "team1" => %{"type" => "string", "description" => "First team name"},
            "team2" => %{"type" => "string", "description" => "Second team name"},
            "limit" => %{"type" => "integer", "description" => "Max recent matches to show (default 10)"}
          },
          "required" => ["team1", "team2"]
        }
      },
      %{
        "name" => "biggest_wins",
        "description" => "Get the biggest winning margins in the dataset",
        "inputSchema" => %{
          "type" => "object",
          "properties" => %{
            "limit" => %{"type" => "integer", "description" => "Number of results (default 10)"},
            "competition" => %{"type" => "string", "description" => "Filter by competition"}
          }
        }
      },
      %{
        "name" => "competition_stats",
        "description" => "Get statistics for a competition (average goals, home win rate, top scorers)",
        "inputSchema" => %{
          "type" => "object",
          "properties" => %{
            "competition" => %{"type" => "string", "description" => "Competition name"},
            "season" => %{"type" => "integer", "description" => "Season year (optional)"}
          }
        }
      }
    ]
  end

  def call("search_matches", args) do
    team = Map.get(args, "team")
    team2 = Map.get(args, "team2")
    competition = Map.get(args, "competition")
    season = Map.get(args, "season")
    from_date = Map.get(args, "from_date")
    to_date = Map.get(args, "to_date")
    limit = Map.get(args, "limit", 20)

    matches =
      cond do
        team && team2 -> Matches.search_by_teams(team, team2)
        team && season -> Matches.search_by_team_and_season(team, season)
        team && competition ->
          Matches.search_by_team(team)
          |> Enum.filter(fn m -> String.contains?(String.downcase(m.competition), String.downcase(competition)) end)
        team -> Matches.search_by_team(team)
        from_date && to_date -> Matches.search_by_date_range(from_date, to_date)
        competition && season ->
          Matches.search_by_competition(competition)
          |> Enum.filter(fn m -> m.season == season end)
        competition -> Matches.search_by_competition(competition)
        season -> Matches.search_by_season(season)
        true -> []
      end

    matches = Enum.take(matches, limit)
    format_matches(matches, team || team2 || competition || "matches")
  end

  def call("get_team_stats", args) do
    team = Map.get(args, "team")
    opts = []
    opts = if Map.get(args, "season"), do: [{:season, args["season"]} | opts], else: opts
    opts = if Map.get(args, "competition"), do: [{:competition, args["competition"]} | opts], else: opts
    opts = if Map.get(args, "home_only"), do: [{:home_only, true} | opts], else: opts

    stats = Teams.team_record(team, opts)
    win_rate = if stats.matches > 0, do: Float.round(stats.wins / stats.matches * 100, 1), else: 0.0

    label = [team, args["season"] && "Season #{args["season"]}", args["competition"]] |> Enum.filter(& &1) |> Enum.join(" | ")

    text = """
    #{label} Record:
    - Matches: #{stats.matches}
    - Wins: #{stats.wins}, Draws: #{stats.draws}, Losses: #{stats.losses}
    - Goals For: #{stats.goals_for}, Goals Against: #{stats.goals_against}
    - Goal Difference: #{stats.goals_for - stats.goals_against}
    - Win Rate: #{win_rate}%
    """

    {:ok, text}
  end

  def call("search_players", args) do
    name = Map.get(args, "name")
    nationality = Map.get(args, "nationality")
    club = Map.get(args, "club")
    position = Map.get(args, "position")
    top = Map.get(args, "top")
    limit = Map.get(args, "limit", 20)

    players =
      cond do
        top && nationality -> Players.top_rated(top, nationality: nationality)
        top && club -> Players.top_rated(top, club: club)
        top -> Players.top_rated(top)
        name -> Players.search_by_name(name)
        nationality && club -> Players.players_by_club_with_nationality(club, nationality)
        nationality -> Players.search_by_nationality(nationality)
        club -> Players.search_by_club(club)
        position -> Players.search_by_position(position)
        true -> []
      end

    players = Enum.take(players, limit)
    format_players(players)
  end

  def call("get_standings", args) do
    season = Map.get(args, "season")
    competition = Map.get(args, "competition", "Brasileirão")

    standings = Teams.competition_standings(season, competition)

    if Enum.empty?(standings) do
      {:ok, "No standings data found for #{competition} #{season}"}
    else
      top20 = Enum.take(standings, 20)
      rows =
        top20
        |> Enum.with_index(1)
        |> Enum.map(fn {s, i} ->
          "#{i}. #{s.team} - #{s.points} pts (#{s.wins}W #{s.draws}D #{s.losses}L, GD: #{s.goal_diff})"
        end)
        |> Enum.join("\n")

      {:ok, "#{season} #{competition} Standings:\n#{rows}"}
    end
  end

  def call("head_to_head", args) do
    team1 = Map.get(args, "team1")
    team2 = Map.get(args, "team2")
    limit = Map.get(args, "limit", 10)

    matches = Matches.search_by_teams(team1, team2)
    total = length(matches)

    t1_wins = Enum.count(matches, fn m ->
      home_t1 = String.contains?(String.downcase(m.home_team), String.downcase(team1))
      (home_t1 and m.home_goal > m.away_goal) or
        (not home_t1 and m.away_goal > m.home_goal)
    end)

    t2_wins = Enum.count(matches, fn m ->
      home_t2 = String.contains?(String.downcase(m.home_team), String.downcase(team2))
      (home_t2 and m.home_goal > m.away_goal) or
        (not home_t2 and m.away_goal > m.home_goal)
    end)

    draws = total - t1_wins - t2_wins

    recent = matches |> Enum.sort_by(fn m -> m.datetime || "" end, :desc) |> Enum.take(limit)
    recent_text = format_match_list(recent)

    text = """
    Head-to-Head: #{team1} vs #{team2}
    Total matches: #{total}
    #{team1} wins: #{t1_wins}, #{team2} wins: #{t2_wins}, Draws: #{draws}

    Recent matches:
    #{recent_text}
    """

    {:ok, text}
  end

  def call("biggest_wins", args) do
    limit = Map.get(args, "limit", 10)
    competition = Map.get(args, "competition")

    matches = Matches.biggest_wins(limit * 3)

    matches =
      if competition do
        Enum.filter(matches, fn m ->
          String.contains?(String.downcase(m.competition), String.downcase(competition))
        end)
      else
        matches
      end

    matches = Enum.take(matches, limit)

    rows =
      matches
      |> Enum.with_index(1)
      |> Enum.map(fn {m, i} ->
        diff = abs(m.home_goal - m.away_goal)
        "#{i}. #{m.datetime || "?"}: #{m.home_team} #{m.home_goal}-#{m.away_goal} #{m.away_team} (#{m.competition}, margin: #{diff})"
      end)
      |> Enum.join("\n")

    {:ok, "Biggest wins:\n#{rows}"}
  end

  def call("competition_stats", args) do
    competition = Map.get(args, "competition", "Brasileirão")
    season = Map.get(args, "season")

    avg_goals = Teams.average_goals_per_match(competition)
    home_rate = Float.round(Teams.home_win_rate() * 100, 1)

    season_line = if season, do: " (#{season})", else: ""

    top_teams =
      if season do
        Teams.top_scoring_teams(season, competition, 5)
      else
        []
      end

    top_text =
      if Enum.empty?(top_teams) do
        ""
      else
        rows =
          top_teams
          |> Enum.with_index(1)
          |> Enum.map(fn {{team, goals}, i} -> "#{i}. #{team}: #{goals} goals" end)
          |> Enum.join("\n")

        "\nTop scoring teams:\n#{rows}"
      end

    {:ok, """
    #{competition}#{season_line} Statistics:
    - Average goals per match: #{Float.round(avg_goals, 2)}
    - Home win rate: #{home_rate}%#{top_text}
    """}
  end

  def call(unknown_tool, _args) do
    {:error, "Unknown tool: #{unknown_tool}"}
  end

  # Formatting helpers

  defp format_matches([], _label), do: {:ok, "No matches found."}

  defp format_matches(matches, _label) do
    rows = format_match_list(matches)
    count = length(matches)
    {:ok, "Found #{count} match(es):\n#{rows}"}
  end

  defp format_match_list(matches) do
    matches
    |> Enum.map(fn m ->
      "- #{m.datetime || "?"}: #{m.home_team} #{m.home_goal}-#{m.away_goal} #{m.away_team} (#{m.competition}#{if m.season, do: ", #{m.season}", else: ""})"
    end)
    |> Enum.join("\n")
  end

  defp format_players([]), do: {:ok, "No players found."}

  defp format_players(players) do
    rows =
      players
      |> Enum.with_index(1)
      |> Enum.map(fn {p, i} ->
        "#{i}. #{p.name} - Overall: #{p.overall}, Position: #{p.position}, Club: #{p.club}, Nationality: #{p.nationality}"
      end)
      |> Enum.join("\n")

    {:ok, "Found #{length(players)} player(s):\n#{rows}"}
  end
end
