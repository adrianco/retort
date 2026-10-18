defmodule BrazilianSoccer.Tools do
  @moduledoc """
  MCP tool definitions and handlers. Each handler validates its arguments,
  calls `BrazilianSoccer.Queries`, and returns human-readable text in the
  style of the examples in the specification.
  """

  alias BrazilianSoccer.{Dates, Match, Queries}

  @sides ["home", "away", "either"]
  @rate_metrics ~w(home_win_rate away_win_rate win_rate)

  @doc "Tool descriptors for `tools/list`."
  def list do
    [
      tool(
        "search_matches",
        "Find matches by team (home, away or either), opponent, competition, season, date range or derby. Newest first.",
        %{
          team:
            str(
              "Team name, e.g. 'Flamengo'. Accents, state suffixes and full names are accepted."
            ),
          side: enum(@sides, "Restrict team to home or away matches (default: either)."),
          opponent: str("Second team; returns only matches between team and opponent."),
          derby: bool("Only traditional rivalry matches (e.g. Fla-Flu)."),
          competition:
            str("Competition, e.g. 'Brasileirão Série A', 'Copa do Brasil', 'Libertadores'."),
          season: int("Season year, e.g. 2023."),
          date_from: str("Earliest date (YYYY-MM-DD or DD/MM/YYYY)."),
          date_to: str("Latest date (YYYY-MM-DD or DD/MM/YYYY)."),
          limit: int("Maximum matches to list (default 20).")
        },
        []
      ),
      tool(
        "team_record",
        "Win/draw/loss record, goals and win rate for one team.",
        %{
          team: str("Team name."),
          side: enum(@sides, "Home or away matches only (default: either)."),
          competition: str("Competition filter."),
          season: int("Season year.")
        },
        ["team"]
      ),
      tool(
        "head_to_head",
        "Head-to-head record between two teams, with recent meetings.",
        %{
          team_a: str("First team."),
          team_b: str("Second team."),
          competition: str("Competition filter."),
          season: int("Season year."),
          limit: int("Number of recent meetings to list (default 5).")
        },
        ["team_a", "team_b"]
      ),
      tool(
        "standings",
        "League table calculated from match results (3 points for a win, 1 for a draw).",
        %{
          season: int("Season year."),
          competition: str("Competition (default 'Brasileirão Série A').")
        },
        ["season"]
      ),
      tool(
        "league_stats",
        "Aggregate statistics: matches, goals per match, home/away/draw rates.",
        %{
          competition: str("Competition filter."),
          season: int("Season year.")
        },
        []
      ),
      tool(
        "biggest_wins",
        "Matches with the largest winning margins.",
        %{
          competition: str("Competition filter."),
          season: int("Season year."),
          limit: int("Number of matches to list (default 5).")
        },
        []
      ),
      tool(
        "team_ranking",
        "Rank teams by home_win_rate, away_win_rate, win_rate, wins, points or goals_for.",
        %{
          metric: enum(Queries.ranking_metrics(), "Metric to rank by."),
          competition: str("Competition filter."),
          season: int("Season year."),
          min_matches: int("Minimum matches played in scope (default 10)."),
          limit: int("Number of teams to list (default 20).")
        },
        ["metric"]
      ),
      tool(
        "search_players",
        "Search FIFA player data by name, nationality, club, position or rating.",
        %{
          name: str("Player name (substring, e.g. 'Gabriel Barbosa')."),
          nationality: str("Nationality, e.g. 'Brazil'."),
          club: str("Club name substring, e.g. 'Flamengo'."),
          position:
            str("Position code (e.g. 'ST') or group: forward, midfielder, defender, goalkeeper."),
          min_overall: int("Minimum overall rating."),
          limit: int("Maximum players to list (default 20).")
        },
        []
      )
    ]
  end

  @doc """
  Runs a tool. Returns `{:ok, text}` or `{:error, message}` (the latter is
  reported to the client as a tool error, not a protocol error).
  """
  def call(name, args, data) when is_map(args) do
    case handle(name, args, data) do
      {:ok, text} -> {:ok, text}
      {:error, message} -> {:error, message}
    end
  rescue
    error in ArgumentError -> {:error, Exception.message(error)}
  end

  def call(_name, _args, _data), do: {:error, "arguments must be an object"}

  defp handle("search_matches", args, data) do
    with {:ok, side} <- side_arg(args),
         {:ok, scope} <- scope_args(args) do
      opts =
        compact(
          Keyword.merge(scope,
            team: args["team"],
            side: side,
            opponent: args["opponent"],
            derby: args["derby"] == true,
            limit: int_arg(args, "limit")
          )
        )

      %{total: total, matches: matches} = Queries.find_matches(data.matches, opts)

      header = "Found #{total} matches (showing #{length(matches)}):"
      {:ok, Enum.join([header | Enum.map(matches, &match_line/1)], "\n")}
    end
  end

  defp handle("team_record", args, data) do
    with {:ok, team} <- required(args, "team"),
         {:ok, side} <- side_arg(args),
         {:ok, scope} <- scope_args(args) do
      record = Queries.team_record(data.matches, team, compact(Keyword.put(scope, :side, side)))

      if record.played == 0 do
        {:ok, "No matches found for #{team} with these filters."}
      else
        {:ok, record_text(record, scope)}
      end
    end
  end

  defp handle("head_to_head", args, data) do
    with {:ok, team_a} <- required(args, "team_a"),
         {:ok, team_b} <- required(args, "team_b"),
         {:ok, scope} <- scope_args(args) do
      h2h = Queries.head_to_head(data.matches, team_a, team_b, scope)
      limit = int_arg(args, "limit") || 5

      lines = [
        "#{h2h.team_a} vs #{h2h.team_b} head-to-head in dataset:",
        "- Matches: #{h2h.played}",
        "- #{h2h.team_a} wins: #{h2h.wins_a}, #{h2h.team_b} wins: #{h2h.wins_b}, draws: #{h2h.draws}",
        "- Goals: #{h2h.team_a} #{h2h.goals_a}, #{h2h.team_b} #{h2h.goals_b}"
      ]

      recent = h2h.matches |> Enum.take(limit) |> Enum.map(&("  " <> match_line(&1)))
      recent_lines = if recent == [], do: [], else: ["- Most recent:" | recent]

      {:ok, Enum.join(lines ++ recent_lines, "\n")}
    end
  end

  defp handle("standings", args, data) do
    with {:ok, season} <- required_int(args, "season"),
         {:ok, scope} <- scope_args(args) do
      table = Queries.standings(data.matches, Keyword.put(scope, :season, season))
      competition = scope[:competition] || "Brasileirão Série A"

      if table == [] do
        {:ok, "No #{competition} matches found for #{season}."}
      else
        rows =
          table
          |> Enum.with_index(1)
          |> Enum.map(fn {row, pos} ->
            "#{pos}. #{row.team} - #{row.points} pts (#{row.wins}W, #{row.draws}D, #{row.losses}L, GF #{row.goals_for}, GA #{row.goals_against})"
          end)

        {:ok,
         Enum.join(["#{competition} #{season} standings (calculated from matches):" | rows], "\n")}
      end
    end
  end

  defp handle("league_stats", args, data) do
    with {:ok, scope} <- scope_args(args) do
      s = Queries.league_stats(data.matches, scope)

      if s.matches == 0 do
        {:ok, "No matches found with these filters."}
      else
        {:ok,
         Enum.join(
           [
             "League statistics#{scope_label(scope)}:",
             "- Matches: #{s.matches}",
             "- Total goals: #{s.total_goals} (average #{s.avg_goals_per_match} per match)",
             "- Home win rate: #{s.home_win_rate}%, away win rate: #{s.away_win_rate}%, draw rate: #{s.draw_rate}%"
           ],
           "\n"
         )}
      end
    end
  end

  defp handle("biggest_wins", args, data) do
    with {:ok, scope} <- scope_args(args) do
      wins =
        Queries.biggest_wins(
          data.matches,
          compact(Keyword.put(scope, :limit, int_arg(args, "limit")))
        )

      if wins == [] do
        {:ok, "No decisive matches found with these filters."}
      else
        lines = wins |> Enum.with_index(1) |> Enum.map(fn {m, i} -> "#{i}. #{match_line(m)}" end)
        {:ok, Enum.join(["Biggest wins#{scope_label(scope)}:" | lines], "\n")}
      end
    end
  end

  defp handle("team_ranking", args, data) do
    with {:ok, metric} <- metric_arg(args),
         {:ok, scope} <- scope_args(args) do
      opts =
        compact(
          Keyword.merge(scope,
            min_matches: int_arg(args, "min_matches"),
            limit: int_arg(args, "limit")
          )
        )

      rows = Queries.ranking(data.matches, metric, opts)
      suffix = if metric in @rate_metrics, do: "%", else: ""

      if rows == [] do
        {:ok, "No teams qualify for this ranking with these filters."}
      else
        lines =
          rows
          |> Enum.with_index(1)
          |> Enum.map(fn {row, i} ->
            "#{i}. #{row.team} - #{row.value}#{suffix} (#{row.played} played, #{row.wins}W #{row.draws}D #{row.losses}L)"
          end)

        {:ok, Enum.join(["Ranking by #{metric}#{scope_label(scope)}:" | lines], "\n")}
      end
    end
  end

  defp handle("search_players", args, data) do
    with {:ok, position} <- optional_str(args, "position") do
      opts =
        compact(
          name: args["name"],
          nationality: args["nationality"],
          club: args["club"],
          position: position,
          min_overall: int_arg(args, "min_overall"),
          limit: int_arg(args, "limit")
        )

      %{total: total, players: players} = Queries.search_players(data.players, opts)

      if players == [] do
        {:ok, "No players found."}
      else
        lines =
          players
          |> Enum.with_index(1)
          |> Enum.map(fn {p, i} ->
            "#{i}. #{p.name} - Overall: #{p.overall}, Position: #{p.position}, Club: #{p.club}, Nationality: #{p.nationality}, Age: #{p.age}"
          end)

        {:ok, Enum.join(["Players found: #{total} (showing #{length(players)}):" | lines], "\n")}
      end
    end
  end

  defp handle(name, _args, _data), do: {:error, "unknown tool: #{name}"}

  # --- formatting ---

  defp match_line(%Match{} = m) do
    context = [m.competition, m.stage] |> Enum.reject(&is_nil/1) |> Enum.join(", ")

    "#{Date.to_iso8601(m.date)}: #{m.home} #{m.home_goals}-#{m.away_goals} #{m.away} (#{context})"
  end

  defp record_text(record, scope) do
    [
      "#{record.team} record#{scope_label(scope)}#{side_label(record.side)}:",
      "- Matches: #{record.played}",
      "- Wins: #{record.wins}, Draws: #{record.draws}, Losses: #{record.losses}",
      "- Goals For: #{record.goals_for}, Goals Against: #{record.goals_against}",
      "- Win rate: #{record.win_rate}%"
    ]
    |> Enum.join("\n")
  end

  defp scope_label(scope) do
    parts = [scope[:competition], scope[:season]] |> Enum.reject(&is_nil/1)
    if parts == [], do: "", else: " (" <> Enum.join(parts, ", ") <> ")"
  end

  defp side_label(:either), do: ""
  defp side_label(side), do: " - #{side} matches"

  # --- argument handling ---

  defp tool(name, description, properties, required) do
    %{
      name: name,
      description: description,
      inputSchema: %{type: "object", properties: properties, required: required}
    }
  end

  defp str(description), do: %{type: "string", description: description}
  defp int(description), do: %{type: "integer", description: description}
  defp bool(description), do: %{type: "boolean", description: description}
  defp enum(values, description), do: %{type: "string", enum: values, description: description}

  defp required(args, key) do
    case optional_str(args, key) do
      {:ok, nil} -> {:error, "missing required argument: #{key}"}
      other -> other
    end
  end

  defp required_int(args, key) do
    case int_arg(args, key) do
      nil -> {:error, "missing required integer argument: #{key}"}
      n -> {:ok, n}
    end
  end

  defp optional_str(args, key) do
    case args[key] do
      nil -> {:ok, nil}
      value when is_binary(value) and value != "" -> {:ok, value}
      _ -> {:error, "#{key} must be a non-empty string"}
    end
  end

  defp int_arg(args, key) do
    case args[key] do
      value when is_integer(value) ->
        value

      value when is_binary(value) ->
        case Integer.parse(value) do
          {n, _} -> n
          :error -> nil
        end

      _ ->
        nil
    end
  end

  defp side_arg(args) do
    case args["side"] do
      nil -> {:ok, :either}
      "home" -> {:ok, :home}
      "away" -> {:ok, :away}
      "either" -> {:ok, :either}
      _ -> {:error, "side must be one of: #{Enum.join(@sides, ", ")}"}
    end
  end

  defp metric_arg(args) do
    case args["metric"] do
      metric when metric in @rate_metrics or metric in ~w(wins points goals_for) -> {:ok, metric}
      _ -> {:error, "metric must be one of: #{Enum.join(Queries.ranking_metrics(), ", ")}"}
    end
  end

  defp scope_args(args) do
    with {:ok, competition} <- optional_str(args, "competition"),
         {:ok, date_from} <- date_arg(args, "date_from"),
         {:ok, date_to} <- date_arg(args, "date_to") do
      {:ok,
       compact(
         season: int_arg(args, "season"),
         competition: competition,
         date_from: date_from,
         date_to: date_to
       )}
    end
  end

  defp date_arg(args, key) do
    case args[key] do
      nil ->
        {:ok, nil}

      text when is_binary(text) ->
        case Dates.parse(text) do
          {:ok, date} -> {:ok, date}
          :error -> {:error, "#{key} is not a recognised date: #{text}"}
        end

      _ ->
        {:error, "#{key} must be a date string"}
    end
  end

  defp compact(keyword), do: Enum.reject(keyword, fn {_k, v} -> is_nil(v) or v == false end)
end
