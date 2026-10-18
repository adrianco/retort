defmodule SoccerMcp.Tools do
  @moduledoc """
  The MCP tools exposed to the LLM: their JSON schemas and their dispatch.

  Each tool takes a JSON object of arguments and returns `{:ok, text}` or
  `{:error, message}`. Bad arguments and unknown names are errors, not
  crashes, so the LLM can read the message and retry.
  """

  alias SoccerMcp.{Format, Match, Parse, Query, Store}

  @competition_prop %{
    "type" => "string",
    "description" =>
      "Competition: 'Brasileirão' (Série A), 'Série B', 'Série C', 'Copa do Brasil' or 'Libertadores'"
  }
  @season_prop %{"type" => "integer", "description" => "Season year, e.g. 2019"}
  @limit_prop %{"type" => "integer", "description" => "Maximum results to return (default 20)"}

  @doc "Tool definitions in the MCP `tools/list` format."
  @spec definitions() :: [map()]
  def definitions do
    [
      %{
        name: "search_matches",
        description:
          "Find matches by team, opponent, competition, season, venue, stage (e.g. 'final') or date range. Returns scores, dates and competitions, most recent first. When both team and opponent are given, also returns a head-to-head summary.",
        inputSchema: %{
          type: "object",
          properties: %{
            team: %{type: "string", description: "Team name, e.g. 'Flamengo' or 'Palmeiras-SP'"},
            opponent: %{type: "string", description: "Opposing team name"},
            competition: @competition_prop,
            season: @season_prop,
            venue: %{
              type: "string",
              enum: ["any", "home", "away"],
              description: "Venue of the team (default any)"
            },
            stage: %{
              type: "string",
              description: "Stage or round text, e.g. 'final', 'semifinals', 'Round 22'"
            },
            date_from: %{type: "string", description: "Earliest date, YYYY-MM-DD"},
            date_to: %{type: "string", description: "Latest date, YYYY-MM-DD"},
            limit: @limit_prop
          }
        }
      },
      %{
        name: "team_stats",
        description:
          "Win, draw and loss record, goals for and against, and win rate for a team, optionally filtered by competition, season and venue.",
        inputSchema: %{
          type: "object",
          required: ["team"],
          properties: %{
            team: %{type: "string", description: "Team name"},
            competition: @competition_prop,
            season: @season_prop,
            venue: %{type: "string", enum: ["any", "home", "away"]}
          }
        }
      },
      %{
        name: "head_to_head",
        description:
          "Head-to-head record between two teams across all competitions in the dataset, with recent matches.",
        inputSchema: %{
          type: "object",
          required: ["team_a", "team_b"],
          properties: %{
            team_a: %{type: "string", description: "First team"},
            team_b: %{type: "string", description: "Second team"},
            limit: @limit_prop
          }
        }
      },
      %{
        name: "competition_standings",
        description:
          "League table for a Brasileirão season, calculated from match results (3 points for a win, 1 for a draw).",
        inputSchema: %{
          type: "object",
          required: ["competition", "season"],
          properties: %{
            competition: @competition_prop,
            season: @season_prop
          }
        }
      },
      %{
        name: "search_players",
        description:
          "Search the FIFA player database by name, nationality, club, position or minimum overall rating. Sorted by overall rating.",
        inputSchema: %{
          type: "object",
          properties: %{
            name: %{
              type: "string",
              description: "Part of the player name, e.g. 'Gabriel Barbosa'"
            },
            nationality: %{type: "string", description: "Country, e.g. 'Brazil'"},
            club: %{type: "string", description: "Club name or part of it, e.g. 'Flamengo'"},
            position: %{type: "string", description: "Position code, e.g. 'ST', 'GK', 'CDM'"},
            min_overall: %{type: "integer", description: "Minimum overall rating (0-99)"},
            limit: @limit_prop
          }
        }
      },
      %{
        name: "match_statistics",
        description:
          "Aggregate statistics over matches: 'averages' (goals per match, home/draw/away rates), 'biggest_wins', or 'best_home' / 'best_away' team records. Optionally filtered by competition and season.",
        inputSchema: %{
          type: "object",
          required: ["kind"],
          properties: %{
            kind: %{type: "string", enum: ["averages", "biggest_wins", "best_home", "best_away"]},
            competition: @competition_prop,
            season: @season_prop,
            limit: @limit_prop
          }
        }
      }
    ]
  end

  @doc "Dispatches a `tools/call` request to the named tool."
  @spec call(String.t(), map(), Store.t()) :: {:ok, String.t()} | {:error, String.t()}
  def call(name, args, store) when is_map(args) do
    run(name, args, store)
  rescue
    error in [ArgumentError, ArithmeticError, FunctionClauseError] ->
      {:error, "invalid arguments for #{name}: #{Exception.message(error)}"}
  end

  def call(_name, _args, _store), do: {:error, "arguments must be a JSON object"}

  defp run("search_matches", args, store) do
    with {:ok, opts} <- match_opts(args) do
      limit = limit(args)
      matches = Query.find_matches(store, opts)

      text =
        case {args["team"], args["opponent"]} do
          {team, opponent} when is_binary(team) and is_binary(opponent) ->
            Format.head_to_head_summary(matches, team, opponent) <>
              "\n\n" <> Format.match_list(matches, limit)

          _ ->
            Format.match_list(matches, limit)
        end

      {:ok, text}
    end
  end

  defp run("team_stats", args, store) do
    with {:ok, team} <- required(args, "team"),
         {:ok, opts} <- match_opts(Map.put(args, "team", team)) do
      matches = Query.find_matches(store, opts)
      rec = Query.record(matches, SoccerMcp.Team.key(team))
      scope = [args["competition"], args["season"]] |> Enum.reject(&is_nil/1) |> Enum.join(" ")
      label = if scope == "", do: team, else: "#{team} (#{scope})"

      if rec.played == 0,
        do: {:ok, "No matches found for #{label} in the dataset."},
        else: {:ok, Format.record_summary(label, rec)}
    end
  end

  defp run("head_to_head", args, store) do
    with {:ok, a} <- required(args, "team_a"),
         {:ok, b} <- required(args, "team_b") do
      matches = Query.head_to_head(store, a, b)

      {:ok,
       Format.head_to_head_summary(matches, a, b) <>
         "\n\n" <> Format.match_list(matches, limit(args))}
    end
  end

  defp run("competition_standings", args, store) do
    with {:ok, competition} <- competition(args),
         {:ok, season} <- season(args) do
      matches = Query.find_matches(store, competition: competition, season: season)
      {:ok, Format.standings_table(Query.standings(matches), competition, season)}
    end
  end

  defp run("search_players", args, store) do
    opts =
      [
        name: args["name"],
        nationality: args["nationality"],
        club: args["club"],
        position: args["position"],
        min_overall: args["min_overall"] && Parse.int(to_string(args["min_overall"])),
        limit: limit(args)
      ]
      |> Enum.reject(fn {_k, v} -> is_nil(v) end)

    if Enum.all?(opts, fn {k, _} -> k == :limit end),
      do: {:error, "give at least one of: name, nationality, club, position, min_overall"},
      else: {:ok, Format.players(Query.players(store, opts))}
  end

  defp run("match_statistics", args, store) do
    with {:ok, kind} <- required(args, "kind"),
         {:ok, opts} <- match_opts(Map.take(args, ["competition", "season"])) do
      matches = Query.find_matches(store, opts)
      statistics(kind, matches, args)
    end
  end

  defp run(name, _args, _store), do: {:error, "unknown tool: #{name}"}

  defp statistics("averages", matches, args) do
    scope = scope_label(args)
    {:ok, Format.averages(Query.averages(matches), "Matches#{scope}")}
  end

  defp statistics("biggest_wins", matches, args),
    do: {:ok, Format.biggest_wins(Query.biggest_wins(matches, limit(args)))}

  defp statistics("best_home", matches, _args),
    do: {:ok, Format.venue_ranking(Query.venue_ranking(matches, :home), "home")}

  defp statistics("best_away", matches, _args),
    do: {:ok, Format.venue_ranking(Query.venue_ranking(matches, :away), "away")}

  defp statistics(kind, _matches, _args),
    do:
      {:error,
       "unknown kind #{inspect(kind)}; use averages, biggest_wins, best_home or best_away"}

  defp scope_label(args) do
    case [args["competition"], args["season"]] |> Enum.reject(&is_nil/1) do
      [] -> ""
      parts -> " (" <> Enum.join(parts, " ") <> ")"
    end
  end

  # Builds Query.find_matches options from the shared match arguments.
  defp match_opts(args) do
    with {:ok, competition} <- optional_competition(args),
         {:ok, season} <- optional_season(args),
         {:ok, from} <- optional_date(args, "date_from"),
         {:ok, to} <- optional_date(args, "date_to"),
         {:ok, venue} <- venue(args) do
      {:ok,
       [
         team: args["team"],
         opponent: args["opponent"],
         competition: competition,
         season: season,
         venue: venue,
         stage: args["stage"],
         from: from,
         to: to
       ]
       |> Enum.reject(fn {_k, v} -> is_nil(v) end)}
    end
  end

  defp optional_competition(args) do
    case args["competition"] do
      nil ->
        {:ok, nil}

      text ->
        case Match.canonical_competition(text) do
          nil -> {:error, "unknown competition #{inspect(text)}"}
          canonical -> {:ok, canonical}
        end
    end
  end

  defp competition(args) do
    with {:ok, _text} <- required(args, "competition") do
      optional_competition(args)
    end
  end

  defp optional_season(args) do
    case args["season"] do
      nil -> {:ok, nil}
      value -> season_value(value)
    end
  end

  defp season(args) do
    case args["season"] do
      nil -> {:error, "missing required argument season"}
      value -> season_value(value)
    end
  end

  defp season_value(value) do
    case Parse.int(to_string(value)) do
      nil -> {:error, "season must be a year, got #{inspect(value)}"}
      year -> {:ok, year}
    end
  end

  defp optional_date(args, key) do
    case args[key] do
      nil ->
        {:ok, nil}

      text ->
        case Parse.date(text) do
          nil -> {:error, "#{key} must be a date like 2023-09-24, got #{inspect(text)}"}
          date -> {:ok, date}
        end
    end
  end

  defp venue(args) do
    case args["venue"] || "any" do
      "any" -> {:ok, :any}
      "home" -> {:ok, :home}
      "away" -> {:ok, :away}
      other -> {:error, "venue must be any, home or away, got #{inspect(other)}"}
    end
  end

  defp required(args, key) do
    case args[key] do
      value when is_binary(value) and value != "" -> {:ok, value}
      _ -> {:error, "missing required argument #{key}"}
    end
  end

  defp limit(args) do
    case Parse.int(to_string(args["limit"] || Query.default_limit())) do
      n when is_integer(n) and n > 0 -> min(n, 100)
      _ -> Query.default_limit()
    end
  end
end
