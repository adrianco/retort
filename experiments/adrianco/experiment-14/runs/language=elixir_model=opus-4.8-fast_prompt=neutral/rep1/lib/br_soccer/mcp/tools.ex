defmodule BrSoccer.MCP.Tools do
  @moduledoc """
  MCP tool catalogue and dispatch.

  `list/0` returns the tool definitions advertised over `tools/list`. `call/2`
  executes a tool by name with a map of string-keyed arguments and returns
  `{:ok, text}` or `{:error, message}`. Each tool wraps a `BrSoccer` query and
  renders the result with `BrSoccer.Format`.
  """

  alias BrSoccer.{Competition, Format, Loader}

  @doc "List of tool definitions for `tools/list`."
  def list, do: Enum.map(definitions(), &Map.delete(&1, :handler))

  @doc "Dispatch a tool call. Returns {:ok, text} | {:error, reason}."
  def call(name, args) when is_map(args) do
    case Enum.find(definitions(), &(&1.name == name)) do
      nil ->
        {:error, "Unknown tool: #{name}"}

      %{handler: handler} ->
        try do
          {:ok, handler.(args)}
        rescue
          e -> {:error, "Tool #{name} failed: #{Exception.message(e)}"}
        end
    end
  end

  def call(_name, _args), do: {:error, "Arguments must be an object"}

  # ---- tool definitions ----

  defp definitions do
    [
      %{
        name: "search_matches",
        description:
          "Find matches by team, opponent, competition, season and/or date range across all datasets (Brasileirão, Copa do Brasil, Libertadores, Série B/C).",
        inputSchema: %{
          type: "object",
          properties: %{
            team: %{type: "string", description: "Club involved (home or away). Name variations are normalised."},
            opponent: %{type: "string", description: "Restrict to matches against this club."},
            venue: %{type: "string", enum: ["home", "away", "either"], description: "Where `team` played. Default either."},
            competition: %{type: "string", description: "brasileirao | copa_do_brasil | libertadores | serie_b | serie_c (free text accepted)."},
            season: %{type: "integer", description: "Season year."},
            date_from: %{type: "string", description: "Inclusive start date (YYYY-MM-DD)."},
            date_to: %{type: "string", description: "Inclusive end date (YYYY-MM-DD)."},
            limit: %{type: "integer", description: "Max matches to return (default 20)."}
          }
        },
        handler: &handle_search_matches/1
      },
      %{
        name: "head_to_head",
        description: "Head-to-head record and match list between two clubs, optionally within a competition/season.",
        inputSchema: %{
          type: "object",
          properties: %{
            team_a: %{type: "string"},
            team_b: %{type: "string"},
            competition: %{type: "string"},
            season: %{type: "integer"}
          },
          required: ["team_a", "team_b"]
        },
        handler: &handle_head_to_head/1
      },
      %{
        name: "last_match",
        description: "The most recent match in the dataset between two clubs, with the score.",
        inputSchema: %{
          type: "object",
          properties: %{team_a: %{type: "string"}, team_b: %{type: "string"}},
          required: ["team_a", "team_b"]
        },
        handler: &handle_last_match/1
      },
      %{
        name: "team_record",
        description: "Win/draw/loss record, goals and win rate for a club, filtered by season, competition and venue (home/away).",
        inputSchema: %{
          type: "object",
          properties: %{
            team: %{type: "string"},
            season: %{type: "integer"},
            competition: %{type: "string"},
            venue: %{type: "string", enum: ["home", "away", "either"]}
          },
          required: ["team"]
        },
        handler: &handle_team_record/1
      },
      %{
        name: "team_competitions",
        description: "Which competitions a club has appeared in, with match counts and season ranges.",
        inputSchema: %{
          type: "object",
          properties: %{team: %{type: "string"}},
          required: ["team"]
        },
        handler: &handle_team_competitions/1
      },
      %{
        name: "league_standings",
        description: "Final league table for a competition and season, computed from match results (points, W/D/L, goal difference).",
        inputSchema: %{
          type: "object",
          properties: %{
            competition: %{type: "string", description: "Default brasileirao."},
            season: %{type: "integer"}
          },
          required: ["season"]
        },
        handler: &handle_standings/1
      },
      %{
        name: "relegated_teams",
        description: "Teams relegated in a Brasileirão season (bottom of a 20-team table).",
        inputSchema: %{
          type: "object",
          properties: %{season: %{type: "integer"}, count: %{type: "integer", description: "How many (default 4)."}},
          required: ["season"]
        },
        handler: &handle_relegated/1
      },
      %{
        name: "search_players",
        description: "Search FIFA players by name, nationality, club, position and/or minimum overall rating.",
        inputSchema: %{
          type: "object",
          properties: %{
            name: %{type: "string"},
            nationality: %{type: "string", description: "e.g. Brazil."},
            club: %{type: "string"},
            position: %{type: "string", description: "e.g. ST, GK, CB."},
            min_overall: %{type: "integer"},
            sort: %{type: "string", enum: ["overall", "potential", "age", "name"]},
            limit: %{type: "integer", description: "Default 20."}
          }
        },
        handler: &handle_search_players/1
      },
      %{
        name: "player_profile",
        description: "Detailed profile card for the best-matching player by name.",
        inputSchema: %{
          type: "object",
          properties: %{name: %{type: "string"}},
          required: ["name"]
        },
        handler: &handle_player_profile/1
      },
      %{
        name: "brazilian_clubs_squads",
        description: "Brazilian players grouped by their (Brazilian) club, with squad sizes and average ratings.",
        inputSchema: %{
          type: "object",
          properties: %{
            min_count: %{type: "integer", description: "Minimum players per club to include (default 1)."},
            limit: %{type: "integer", description: "Max clubs to list (default 20)."}
          }
        },
        handler: &handle_brazilian_clubs/1
      },
      %{
        name: "competition_stats",
        description: "Aggregate stats (avg goals/match, home/away/draw rates) for a competition/season, or the whole dataset.",
        inputSchema: %{
          type: "object",
          properties: %{competition: %{type: "string"}, season: %{type: "integer"}}
        },
        handler: &handle_competition_stats/1
      },
      %{
        name: "biggest_wins",
        description: "Largest-margin victories in a filtered set of matches (by competition/season/team).",
        inputSchema: %{
          type: "object",
          properties: %{
            competition: %{type: "string"},
            season: %{type: "integer"},
            team: %{type: "string"},
            limit: %{type: "integer", description: "Default 10."}
          }
        },
        handler: &handle_biggest_wins/1
      },
      %{
        name: "top_scoring_teams",
        description: "Teams ranked by goals scored in a competition/season.",
        inputSchema: %{
          type: "object",
          properties: %{competition: %{type: "string"}, season: %{type: "integer"}, limit: %{type: "integer"}},
          required: ["season"]
        },
        handler: &handle_top_scoring/1
      },
      %{
        name: "team_rankings",
        description: "Rank teams by win rate for a venue (home/away) — e.g. best home record — in a competition/season.",
        inputSchema: %{
          type: "object",
          properties: %{
            competition: %{type: "string"},
            season: %{type: "integer"},
            venue: %{type: "string", enum: ["home", "away", "either"]},
            limit: %{type: "integer"}
          }
        },
        handler: &handle_rankings/1
      },
      %{
        name: "compare_seasons",
        description: "Compare two seasons of a competition side by side (matches, goals, win rates).",
        inputSchema: %{
          type: "object",
          properties: %{
            competition: %{type: "string", description: "Default brasileirao."},
            season_a: %{type: "integer"},
            season_b: %{type: "integer"}
          },
          required: ["season_a", "season_b"]
        },
        handler: &handle_compare_seasons/1
      }
    ]
  end

  # ---- handlers ----

  defp handle_search_matches(args) do
    limit = int(args["limit"]) || 20

    opts =
      [
        team: args["team"],
        opponent: args["opponent"],
        venue: venue(args["venue"]),
        competition: args["competition"],
        season: int(args["season"]),
        from: Loader.parse_date(args["date_from"]),
        to: Loader.parse_date(args["date_to"]),
        limit: limit
      ]
      |> compact()

    {matches, total} = BrSoccer.Matches.search_with_total(opts)
    Format.matches(matches, total, header_for(args))
  end

  defp header_for(args) do
    parts =
      [args["team"], args["opponent"] && "vs #{args["opponent"]}", args["competition"], args["season"]]
      |> Enum.reject(&(is_nil(&1) or &1 == ""))
      |> Enum.map_join(" ", &to_string/1)

    if parts == "", do: "Matches:", else: "Matches — #{parts}:"
  end

  defp handle_head_to_head(args) do
    a = require_arg(args, "team_a")
    b = require_arg(args, "team_b")
    opts = compact(competition: args["competition"], season: int(args["season"]))
    BrSoccer.head_to_head(a, b, opts) |> Format.head_to_head()
  end

  defp handle_last_match(args) do
    a = require_arg(args, "team_a")
    b = require_arg(args, "team_b")

    case BrSoccer.last_match(a, b) do
      nil -> "No match found between #{a} and #{b} in the dataset."
      m -> "Most recent meeting:\n- " <> Format.match_line(m)
    end
  end

  defp handle_team_record(args) do
    team = require_arg(args, "team")
    opts = compact(season: int(args["season"]), competition: args["competition"], venue: venue(args["venue"]))
    record = BrSoccer.team_record(team, opts)
    Format.record(record, record_label(record.team, args))
  end

  defp record_label(team, args) do
    venue = if args["venue"] in ["home", "away"], do: " #{args["venue"]}", else: ""
    comp = args["competition"] && " #{Competition.name(Competition.parse(args["competition"]))}"
    season = args["season"] && " #{args["season"]}"
    "#{team}#{venue} record#{comp || ""}#{season || ""}"
  end

  defp handle_team_competitions(args) do
    team = require_arg(args, "team")
    BrSoccer.team_competitions(team) |> Format.competitions(BrSoccer.TeamName.display(team))
  end

  defp handle_standings(args) do
    comp = Competition.parse(args["competition"]) || :brasileirao
    season = require_int(args, "season")
    title = "#{Competition.name(comp)} #{season} — Final Standings (calculated from matches):"
    BrSoccer.standings(comp, season) |> Format.standings(title)
  end

  defp handle_relegated(args) do
    season = require_int(args, "season")
    count = int(args["count"]) || 4

    case BrSoccer.relegated(season, count) do
      [] ->
        "No standard 20-team standings available to determine relegation for #{season}."

      teams ->
        title = "Relegated from Brasileirão #{season} (bottom #{count}):"
        Format.standings(teams, title)
    end
  end

  defp handle_search_players(args) do
    limit = int(args["limit"]) || 20

    opts =
      compact(
        name: args["name"],
        nationality: args["nationality"],
        club: args["club"],
        position: args["position"],
        min_overall: int(args["min_overall"]),
        sort: sort(args["sort"]),
        limit: limit
      )

    BrSoccer.search_players(opts) |> Format.players(players_header(args))
  end

  defp players_header(args) do
    parts =
      [args["nationality"], args["position"] && "#{args["position"]}s", args["club"] && "at #{args["club"]}"]
      |> Enum.reject(&(is_nil(&1) or &1 == ""))
      |> Enum.map_join(" ", &to_string/1)

    if parts == "", do: "Players:", else: "Players — #{parts}:"
  end

  defp handle_player_profile(args) do
    name = require_arg(args, "name")

    case BrSoccer.search_players(name: name, limit: 1) do
      [p | _] -> Format.player_card(p)
      [] -> "No player found matching \"#{name}\"."
    end
  end

  defp handle_brazilian_clubs(args) do
    limit = int(args["limit"]) || 20
    min_count = int(args["min_count"]) || 1

    BrSoccer.brazilian_clubs_squads(min_count: min_count)
    |> Enum.take(limit)
    |> Format.players_by_club("Brazilian players at Brazilian clubs:")
  end

  defp handle_competition_stats(args) do
    opts = compact(competition: args["competition"], season: int(args["season"]))
    label = stats_label(args)
    BrSoccer.stats_summary(opts) |> Format.summary(label)
  end

  defp stats_label(args), do: "Statistics" <> maybe_space(scope_label(args))

  # "Brasileirão Série A 2019", "2019", or "" when nothing is scoped.
  defp scope_label(args) do
    comp = args["competition"] && Competition.name(Competition.parse(args["competition"]))
    season = args["season"]

    [comp, season && to_string(season)]
    |> Enum.reject(&is_nil/1)
    |> Enum.join(" ")
  end

  defp maybe_space(""), do: ""
  defp maybe_space(s), do: " " <> s

  defp handle_biggest_wins(args) do
    limit = int(args["limit"]) || 10
    opts = compact(competition: args["competition"], season: int(args["season"]), team: args["team"], limit: limit)
    BrSoccer.biggest_wins(opts) |> Format.biggest_wins("Biggest victories:")
  end

  defp handle_top_scoring(args) do
    season = require_int(args, "season")
    limit = int(args["limit"]) || 10
    opts = compact(competition: args["competition"], season: season)

    rows =
      BrSoccer.top_scoring_teams(opts)
      |> Enum.take(limit)
      |> Enum.with_index(1)
      |> Enum.map(fn {r, i} -> "#{i}. #{r.team} — #{r.goals} goals in #{r.matches} matches" end)

    header = "Top scoring teams#{maybe_space(scope_label(args))}:"
    Enum.join([header | (rows == [] && ["No data."] || rows)], "\n")
  end

  defp handle_rankings(args) do
    v = venue(args["venue"]) || :home
    limit = int(args["limit"]) || 10
    opts = compact(competition: args["competition"], season: int(args["season"]), venue: v)

    rows =
      BrSoccer.team_rankings(opts)
      |> Enum.take(limit)
      |> Enum.with_index(1)
      |> Enum.map(fn {r, i} ->
        "#{i}. #{r.team} — #{r.win_rate}% (#{r.wins}W #{r.draws}D #{r.losses}L, #{r.matches} #{v} matches)"
      end)

    header = "Best #{v} records#{maybe_space(scope_label(args))}:"
    Enum.join([header | (rows == [] && ["No data."] || rows)], "\n")
  end

  defp handle_compare_seasons(args) do
    comp = Competition.parse(args["competition"]) || :brasileirao
    a = require_int(args, "season_a")
    b = require_int(args, "season_b")
    c = BrSoccer.compare_seasons(comp, a, b)

    Format.summary(c.a, "#{Competition.name(comp)} #{a}") <>
      "\n\n" <> Format.summary(c.b, "#{Competition.name(comp)} #{b}")
  end

  # ---- argument helpers ----

  defp require_arg(args, key) do
    case args[key] do
      v when is_binary(v) and v != "" -> v
      _ -> raise ArgumentError, "missing required argument: #{key}"
    end
  end

  defp require_int(args, key) do
    case int(args[key]) do
      nil -> raise ArgumentError, "missing or invalid integer argument: #{key}"
      n -> n
    end
  end

  defp int(nil), do: nil
  defp int(n) when is_integer(n), do: n
  defp int(n) when is_float(n), do: trunc(n)

  defp int(s) when is_binary(s) do
    case Integer.parse(String.trim(s)) do
      {n, _} -> n
      :error -> nil
    end
  end

  defp venue("home"), do: :home
  defp venue("away"), do: :away
  defp venue("either"), do: :either
  defp venue(_), do: nil

  defp sort(s) when s in ["overall", "potential", "age", "name"], do: String.to_atom(s)
  defp sort(_), do: nil

  defp compact(opts) do
    Enum.reject(opts, fn {_k, v} -> is_nil(v) or v == "" end)
  end
end
