defmodule BrazilianSoccerMcp.Tools do
  @moduledoc """
  MCP tool catalogue: JSON schemas, argument validation, and text formatting.

  Each tool returns plain text, which the LLM reads directly. Errors are
  returned as `{:error, message}` and reported to the client with `isError`.
  """

  alias BrazilianSoccerMcp.{Competition, Match, Queries}

  @props %{
    team: %{
      type: "string",
      description: "Team name, e.g. 'Palmeiras'. State suffixes, accents and case are ignored."
    },
    team_a: %{type: "string", description: "First team name."},
    team_b: %{type: "string", description: "Second team name."},
    opponent: %{
      type: "string",
      description: "Opponent team name. With 'team', returns only matches between the two."
    },
    competition: %{
      type: "string",
      description:
        "brasileirao, brasileirao_b, brasileirao_c, copa_do_brasil or libertadores. Friendly names such as 'Copa do Brasil' also work."
    },
    season: %{type: "integer", description: "Season year, e.g. 2023."},
    venue: %{
      type: "string",
      enum: ["home", "away", "any"],
      description: "Restrict team results to home or away matches."
    },
    date_from: %{type: "string", description: "Earliest date, YYYY-MM-DD (inclusive)."},
    date_to: %{type: "string", description: "Latest date, YYYY-MM-DD (inclusive)."},
    limit: %{type: "integer", description: "Maximum number of results."},
    min_matches: %{
      type: "integer",
      description: "Minimum matches played to be ranked. Defaults to 10."
    },
    metric: %{
      type: "string",
      enum: ["win_rate", "wins", "goals_for"],
      description: "Ranking metric. Defaults to win_rate."
    },
    name: %{type: "string", description: "Player name or part of it, e.g. 'Neymar'."},
    club: %{type: "string", description: "Club name, e.g. 'Flamengo'."},
    nationality: %{type: "string", description: "Nationality, e.g. 'Brazil'."},
    position: %{type: "string", description: "FIFA position code, e.g. 'ST', 'GK', 'CDM'."},
    min_overall: %{type: "integer", description: "Minimum FIFA overall rating."}
  }

  @tools [
    {"search_matches",
     "Find matches by team, opponent, competition, season, venue or date range. Most recent first.",
     [:team, :opponent, :competition, :season, :venue, :date_from, :date_to, :limit], []},
    {"team_record", "Win/draw/loss record, goals and win rate for one team.",
     [:team, :competition, :season, :venue, :date_from, :date_to], [:team]},
    {"head_to_head", "Head-to-head record between two teams, with the most recent meetings.",
     [:team_a, :team_b, :competition, :season, :date_from, :date_to, :limit], [:team_a, :team_b]},
    {"standings",
     "League table for one season, calculated from match results. Defaults to Brasileirão Série A.",
     [:season, :competition], [:season]},
    {"league_stats", "Aggregate statistics: matches, goals per match, home/draw/away rates.",
     [:competition, :season, :date_from, :date_to], []},
    {"biggest_wins", "Largest winning margins in the dataset.", [:competition, :season, :limit],
     []},
    {"team_rankings",
     "Rank teams by win rate, wins or goals scored, optionally for home or away matches only.",
     [:metric, :venue, :competition, :season, :min_matches, :limit], []},
    {"search_players",
     "Search FIFA player data by name, nationality, club, position or minimum overall rating.",
     [:name, :nationality, :club, :position, :min_overall, :limit], []},
    {"club_summary",
     "Players of one nationality (default Brazil), grouped by clubs that appear in the match data.",
     [:nationality, :limit], []},
    {"team_overview", "Cross-file view of a team: its match record plus its FIFA squad.", [:team],
     [:team]}
  ]

  @doc "MCP `tools/list` payload."
  def definitions do
    Enum.map(@tools, fn {name, description, props, required} ->
      %{
        name: name,
        description: description,
        inputSchema: %{
          type: "object",
          properties: Map.take(@props, props),
          required: Enum.map(required, &Atom.to_string/1)
        }
      }
    end)
  end

  @doc "Runs a tool against the loaded data: `data` is `%{matches: [...], players: [...]}`."
  @spec call(binary(), map(), map()) :: {:ok, binary()} | {:error, binary()}
  def call("search_matches", args, data) do
    with {:ok, opts} <- options(args),
         {:ok, result} <- Queries.search_matches(data.matches, opts) do
      {:ok, format_matches(result, opts)}
    end
  end

  def call("team_record", args, data) do
    with {:ok, team} <- fetch(args, "team"),
         {:ok, opts} <- options(args),
         {:ok, stats} <- Queries.team_record(data.matches, team, opts) do
      {:ok, format_record(stats, opts)}
    end
  end

  def call("head_to_head", args, data) do
    with {:ok, a} <- fetch(args, "team_a"),
         {:ok, b} <- fetch(args, "team_b"),
         {:ok, opts} <- options(args),
         {:ok, h2h} <- Queries.head_to_head(data.matches, a, b, opts) do
      {:ok, format_head_to_head(h2h, opts)}
    end
  end

  def call("standings", args, data) do
    with {:ok, opts} <- options(args),
         {:ok, table} <- Queries.standings(data.matches, opts) do
      {:ok, format_standings(table, opts)}
    end
  end

  def call("league_stats", args, data) do
    with {:ok, opts} <- options(args),
         {:ok, stats} <- Queries.league_stats(data.matches, opts) do
      {:ok, format_league_stats(stats, opts)}
    end
  end

  def call("biggest_wins", args, data) do
    with {:ok, opts} <- options(args),
         {:ok, wins} <- Queries.biggest_wins(data.matches, opts) do
      {:ok, format_biggest_wins(wins, opts)}
    end
  end

  def call("team_rankings", args, data) do
    with {:ok, opts} <- options(args),
         {:ok, rows} <- Queries.team_rankings(data.matches, opts) do
      {:ok, format_rankings(rows, opts)}
    end
  end

  def call("search_players", args, data) do
    with {:ok, opts} <- options(args),
         {:ok, players} <- Queries.search_players(data.players, opts) do
      {:ok, format_players(players)}
    end
  end

  def call("club_summary", args, data) do
    with {:ok, opts} <- options(args),
         {:ok, rows} <- Queries.club_summary(data.players, data.matches, opts) do
      {:ok, format_club_summary(rows, opts)}
    end
  end

  def call("team_overview", args, data) do
    with {:ok, team} <- fetch(args, "team"),
         {:ok, overview} <- Queries.team_overview(data.matches, data.players, team) do
      {:ok, format_overview(overview, team)}
    end
  end

  def call(name, _args, _data), do: {:error, "Unknown tool: #{name}"}

  ## Argument parsing

  defp fetch(args, key) do
    case string(args[key]) do
      nil -> {:error, "Missing required argument: #{key}"}
      value -> {:ok, value}
    end
  end

  # Converts the JSON argument map into the keyword options used by Queries.
  # Absent or blank arguments are dropped so Queries applies its defaults.
  defp options(args) do
    with {:ok, venue} <- venue(args["venue"]),
         {:ok, date_from} <- date(args["date_from"]),
         {:ok, date_to} <- date(args["date_to"]) do
      opts = [
        team: string(args["team"]),
        opponent: string(args["opponent"]),
        competition: string(args["competition"]),
        season: integer(args["season"]),
        venue: venue,
        date_from: date_from,
        date_to: date_to,
        limit: integer(args["limit"]),
        min_matches: integer(args["min_matches"]),
        metric: metric(args["metric"]),
        name: string(args["name"]),
        club: string(args["club"]),
        nationality: string(args["nationality"]),
        position: string(args["position"]),
        min_overall: integer(args["min_overall"])
      ]

      {:ok, Enum.reject(opts, fn {_key, value} -> is_nil(value) end)}
    end
  end

  defp string(value) when is_binary(value) do
    case String.trim(value) do
      "" -> nil
      trimmed -> trimmed
    end
  end

  defp string(_value), do: nil

  defp integer(value) when is_integer(value), do: value

  defp integer(value) when is_binary(value) do
    case Integer.parse(String.trim(value)) do
      {number, ""} -> number
      _ -> nil
    end
  end

  defp integer(_value), do: nil

  defp venue(nil), do: {:ok, nil}
  defp venue("home"), do: {:ok, :home}
  defp venue("away"), do: {:ok, :away}
  defp venue("any"), do: {:ok, :any}
  defp venue(_other), do: {:error, "venue must be one of: home, away, any"}

  defp date(nil), do: {:ok, nil}

  defp date(value) when is_binary(value) do
    case Date.from_iso8601(value) do
      {:ok, date} -> {:ok, date}
      _ -> {:error, "Dates must be YYYY-MM-DD, got: #{value}"}
    end
  end

  defp date(_value), do: {:error, "Dates must be YYYY-MM-DD"}

  defp metric("win_rate"), do: :win_rate
  defp metric("wins"), do: :wins
  defp metric("goals_for"), do: :gf
  defp metric(_other), do: nil

  ## Formatting

  defp format_matches(%{total: total, matches: list}, opts) do
    lines([
      "#{total} matches (showing #{length(list)}, #{scope(opts)}):"
      | Enum.map(list, &match_line/1)
    ])
  end

  defp format_record(stats, opts) do
    lines([
      "#{stats.team} (#{scope(opts)}):",
      "- Matches: #{stats.played}",
      "- Wins: #{stats.wins}, Draws: #{stats.draws}, Losses: #{stats.losses}",
      "- Goals For: #{stats.gf}, Goals Against: #{stats.ga}",
      "- Win rate: #{stats.win_rate}%"
    ])
  end

  defp format_head_to_head(h2h, opts) do
    header = "#{h2h.team_a} vs #{h2h.team_b} (#{scope(opts)}):"

    summary = [
      "- Matches: #{h2h.matches}",
      "- #{h2h.team_a} wins: #{h2h.a_wins}, #{h2h.team_b} wins: #{h2h.b_wins}, Draws: #{h2h.draws}",
      "- Goals: #{h2h.team_a} #{h2h.a_goals} - #{h2h.b_goals} #{h2h.team_b}"
    ]

    recent =
      if h2h.recent == [], do: [], else: ["Most recent:" | Enum.map(h2h.recent, &match_line/1)]

    lines([header | summary] ++ recent)
  end

  defp format_standings(table, opts) do
    key = Competition.canonical(opts[:competition]) || "brasileirao"
    season = opts[:season]

    rows =
      table
      |> Enum.with_index(1)
      |> Enum.map(fn {row, position} ->
        champion = if position == 1 and key == "brasileirao", do: " - Champion", else: ""

        "#{position}. #{row.team} - #{row.points} pts (#{row.wins}W, #{row.draws}D, #{row.losses}L)#{champion}"
      end)

    lines(["#{season} #{Competition.label(key)} standings (calculated from matches):" | rows])
  end

  defp format_league_stats(stats, opts) do
    lines([
      "Statistics (#{scope(opts)}):",
      "- Matches: #{stats.matches}",
      "- Goals per match: #{stats.goals_per_match}",
      "- Home win rate: #{stats.home_win_rate}%, Draw rate: #{stats.draw_rate}%, Away win rate: #{stats.away_win_rate}%"
    ])
  end

  defp format_biggest_wins(wins, opts) do
    rows =
      wins
      |> Enum.with_index(1)
      |> Enum.map(fn {m, position} -> "#{position}. #{match_text(m)}" end)

    lines(["Biggest wins (#{scope(opts)}):" | rows])
  end

  defp format_rankings(rows, opts) do
    metric = opts[:metric] || :win_rate
    min_matches = opts[:min_matches] || 10

    body =
      rows
      |> Enum.with_index(1)
      |> Enum.map(fn {row, position} ->
        "#{position}. #{row.team} - #{metric_value(row, metric)} (played #{row.played}, #{row.wins}W-#{row.draws}D-#{row.losses}L, GF #{row.gf})"
      end)

    lines([
      "Top #{length(rows)} by #{metric_label(metric)} (#{scope(opts)}, minimum #{min_matches} matches):"
      | body
    ])
  end

  defp format_players([]), do: "No players found."

  defp format_players(players) do
    rows =
      players
      |> Enum.with_index(1)
      |> Enum.map(fn {p, position} ->
        "#{position}. #{p.name} - Overall: #{p.overall}, Position: #{p.position || "n/a"}, Club: #{p.club || "n/a"}"
      end)

    lines(["Players (#{length(players)}):" | rows])
  end

  defp format_club_summary(rows, opts) do
    nationality = opts[:nationality] || "Brazil"

    body =
      Enum.map(rows, fn row ->
        "- #{row.club}: #{row.squad_size} players (avg overall #{row.avg_overall}, top: #{row.best.name} #{row.best.overall})"
      end)

    lines(["Players by club (nationality: #{nationality}, clubs in match data):" | body])
  end

  defp format_overview(%{record: r, squad_size: size, avg_overall: avg, top: top}, team) do
    squad_line =
      if size == 0,
        do: "- FIFA squad: no players found for this club",
        else: "- FIFA squad: #{size} players (avg overall #{avg})"

    players =
      Enum.with_index(top, 1)
      |> Enum.map(fn {p, position} ->
        "  #{position}. #{p.name} (#{p.overall}, #{p.position || "n/a"})"
      end)

    lines(
      [
        "#{r.team || team} overview (all data):",
        "- Matches: #{r.played}, Wins: #{r.wins}, Draws: #{r.draws}, Losses: #{r.losses}",
        "- Goals For: #{r.gf}, Goals Against: #{r.ga}, Win rate: #{r.win_rate}%",
        squad_line
      ] ++ if(top == [], do: [], else: ["Top players:" | players])
    )
  end

  defp match_line(%Match{} = m), do: "- " <> match_text(m)

  defp match_text(m) do
    "#{Date.to_iso8601(m.date)}: #{m.home} #{m.home_goals}-#{m.away_goals} #{m.away} (#{match_context(m)})"
  end

  defp match_context(m) do
    round =
      case m.round do
        nil -> nil
        round -> if String.match?(round, ~r/^\d+$/), do: "Round #{round}", else: round
      end

    [Competition.label(m.competition), round]
    |> Enum.reject(&is_nil/1)
    |> Enum.join(", ")
  end

  defp metric_value(row, :win_rate), do: "#{row.win_rate}%"
  defp metric_value(row, :wins), do: row.wins
  defp metric_value(row, :gf), do: row.gf

  defp metric_label(:win_rate), do: "win rate"
  defp metric_label(:wins), do: "wins"
  defp metric_label(:gf), do: "goals scored"

  defp scope(opts) do
    parts = [
      opts[:season] && to_string(opts[:season]),
      opts[:competition] && Competition.label(Competition.canonical(opts[:competition])),
      opts[:venue] in [:home, :away] && "#{opts[:venue]} matches only"
    ]

    case Enum.filter(parts, & &1) do
      [] -> "all competitions"
      present -> Enum.join(present, ", ")
    end
  end

  defp lines(items), do: Enum.join(items, "\n")
end
