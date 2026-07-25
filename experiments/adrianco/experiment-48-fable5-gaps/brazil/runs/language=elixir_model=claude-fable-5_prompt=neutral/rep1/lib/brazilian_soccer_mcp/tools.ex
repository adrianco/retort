defmodule BrazilianSoccerMcp.Tools do
  @moduledoc """
  MCP tool definitions (name, description, JSON Schema) and dispatch.

  Each tool takes JSON arguments from a `tools/call` request and returns
  `{:ok, text}` or `{:error, message}`.
  """

  alias BrazilianSoccerMcp.{DataStore, Format, Queries}

  @tools [
    %{
      name: "search_matches",
      description:
        "Search soccer matches by team, opponent, competition (Brasileirão/Série A, Série B, " <>
          "Série C, Copa do Brasil, Copa Libertadores), season year, date range, and/or " <>
          "stage (e.g. 'final'). Returns matches sorted most recent first.",
      inputSchema: %{
        type: "object",
        properties: %{
          team: %{type: "string", description: "Team name, e.g. 'Flamengo' or 'América-MG'"},
          opponent: %{type: "string", description: "Opponent team name (requires team)"},
          competition: %{type: "string", description: "Competition name"},
          season: %{type: "integer", description: "Season year, e.g. 2023"},
          date_from: %{type: "string", description: "Earliest date, ISO format YYYY-MM-DD"},
          date_to: %{type: "string", description: "Latest date, ISO format YYYY-MM-DD"},
          stage: %{
            type: "string",
            description: "Stage or round filter, e.g. 'final', 'semifinals'"
          },
          limit: %{type: "integer", description: "Max matches to display (default 20)"}
        }
      }
    },
    %{
      name: "head_to_head",
      description:
        "Head-to-head record between two teams: all matches, win/draw counts and goals.",
      inputSchema: %{
        type: "object",
        properties: %{
          team1: %{type: "string", description: "First team name"},
          team2: %{type: "string", description: "Second team name"},
          competition: %{type: "string", description: "Optional competition filter"},
          season: %{type: "integer", description: "Optional season year filter"}
        },
        required: ["team1", "team2"]
      }
    },
    %{
      name: "team_stats",
      description:
        "Win/draw/loss record, goals for/against and win rate for a team, optionally " <>
          "filtered by season, competition, and venue (home/away/all). Includes a " <>
          "per-competition breakdown.",
      inputSchema: %{
        type: "object",
        properties: %{
          team: %{type: "string", description: "Team name"},
          season: %{type: "integer", description: "Season year"},
          competition: %{type: "string", description: "Competition name"},
          venue: %{
            type: "string",
            enum: ["home", "away", "all"],
            description: "Venue filter (default all)"
          }
        },
        required: ["team"]
      }
    },
    %{
      name: "league_standings",
      description:
        "League table for a season calculated from match results (3 points per win). " <>
          "Sorted by Brazilian tiebreakers: points, wins, goal difference, goals for. " <>
          "The first team listed is the champion. Brasileirão data covers 2003-2023.",
      inputSchema: %{
        type: "object",
        properties: %{
          season: %{type: "integer", description: "Season year, e.g. 2019"},
          competition: %{type: "string", description: "Competition (default Brasileirão Série A)"},
          limit: %{type: "integer", description: "Max table rows to display (default 20)"}
        },
        required: ["season"]
      }
    },
    %{
      name: "search_players",
      description:
        "Search FIFA player data by name, nationality, club, position " <>
          "(exact code like ST/GK or a group: forward, midfielder, defender, goalkeeper), " <>
          "and/or minimum overall rating. Sorted by overall rating. When exactly one player " <>
          "matches, full attribute details are shown.",
      inputSchema: %{
        type: "object",
        properties: %{
          name: %{type: "string", description: "Player name (partial match, accent-insensitive)"},
          nationality: %{type: "string", description: "Nationality, e.g. 'Brazil'"},
          club: %{type: "string", description: "Club name (partial match)"},
          position: %{type: "string", description: "Position code or group"},
          min_overall: %{type: "integer", description: "Minimum overall rating"},
          limit: %{type: "integer", description: "Max players to return (default 10)"}
        }
      }
    },
    %{
      name: "top_players",
      description:
        "Highest-rated FIFA players, optionally filtered by nationality, club, or position.",
      inputSchema: %{
        type: "object",
        properties: %{
          nationality: %{type: "string", description: "Nationality filter, e.g. 'Brazil'"},
          club: %{type: "string", description: "Club filter"},
          position: %{type: "string", description: "Position code or group"},
          limit: %{type: "integer", description: "Max players to return (default 10)"}
        }
      }
    },
    %{
      name: "biggest_wins",
      description:
        "Matches with the largest winning margins, optionally filtered by team, " <>
          "competition, or season.",
      inputSchema: %{
        type: "object",
        properties: %{
          team: %{type: "string", description: "Optional team filter"},
          competition: %{type: "string", description: "Optional competition filter"},
          season: %{type: "integer", description: "Optional season year filter"},
          limit: %{type: "integer", description: "Max matches to return (default 10)"}
        }
      }
    },
    %{
      name: "competition_stats",
      description:
        "Aggregate statistics: match count, average goals per match, home win / draw / " <>
          "away win rates. Optionally filtered by competition and season.",
      inputSchema: %{
        type: "object",
        properties: %{
          competition: %{type: "string", description: "Competition name"},
          season: %{type: "integer", description: "Season year"}
        }
      }
    },
    %{
      name: "list_teams",
      description: "List known teams (canonical names), optionally filtered by a search string.",
      inputSchema: %{
        type: "object",
        properties: %{
          search: %{type: "string", description: "Optional name filter"},
          limit: %{type: "integer", description: "Max teams to return (default 50)"}
        }
      }
    }
  ]

  def list, do: @tools

  @doc "Dispatch a tools/call. Returns {:ok, text} | {:error, message}."
  def call(name, args) when is_map(args) do
    dispatch(name, args)
  rescue
    e -> {:error, "tool execution failed: #{Exception.message(e)}"}
  end

  def call(name, _args), do: call(name, %{})

  defp dispatch("search_matches", args) do
    opts =
      [
        team: str(args, "team"),
        opponent: str(args, "opponent"),
        competition: str(args, "competition"),
        season: int(args, "season"),
        date_from: date(args, "date_from"),
        date_to: date(args, "date_to"),
        stage: str(args, "stage")
      ]
      |> prune()

    case validate_search_matches(args) do
      :ok ->
        matches = Queries.search_matches(opts)
        {:ok, Format.matches(matches, search_header(opts), int(args, "limit") || 20)}

      {:error, _} = err ->
        err
    end
  end

  defp dispatch("head_to_head", args) do
    with {:ok, t1} <- require_str(args, "team1"),
         {:ok, t2} <- require_str(args, "team2"),
         {:ok, n1} <- resolve_team(t1),
         {:ok, n2} <- resolve_team(t2) do
      opts = prune(competition: str(args, "competition"), season: int(args, "season"))
      {:ok, Format.head_to_head(n1, n2, Queries.head_to_head(t1, t2, opts))}
    end
  end

  defp dispatch("team_stats", args) do
    with {:ok, team} <- require_str(args, "team"),
         {:ok, _name} <- resolve_team(team) do
      venue =
        case str(args, "venue") do
          "home" -> :home
          "away" -> :away
          _ -> :all
        end

      opts =
        prune(
          season: int(args, "season"),
          competition: str(args, "competition"),
          venue: venue
        )

      {:ok, Format.team_stats(team, Queries.team_stats(team, opts), opts)}
    end
  end

  defp dispatch("league_standings", args) do
    case int(args, "season") do
      nil ->
        {:error, "missing required argument: season"}

      season ->
        comp = Queries.normalize_competition(str(args, "competition")) || :brasileirao

        if comp == :unknown do
          {:error, "unknown competition: #{str(args, "competition")}"}
        else
          rows = Queries.standings(season, comp)
          {:ok, Format.standings(season, comp, rows, int(args, "limit") || 20)}
        end
    end
  end

  defp dispatch("search_players", args) do
    opts =
      prune(
        name: str(args, "name"),
        nationality: str(args, "nationality"),
        club: str(args, "club"),
        position: str(args, "position"),
        min_overall: int(args, "min_overall"),
        limit: int(args, "limit") || 10
      )

    case Queries.search_players(opts) do
      [player] -> {:ok, Format.player_details(player)}
      players -> {:ok, Format.players(players, players_header(opts))}
    end
  end

  defp dispatch("top_players", args) do
    opts =
      prune(
        nationality: str(args, "nationality"),
        club: str(args, "club"),
        position: str(args, "position"),
        limit: int(args, "limit") || 10
      )

    {:ok,
     Format.players(Queries.search_players(opts), "Top-rated players" <> filters_suffix(opts))}
  end

  defp dispatch("biggest_wins", args) do
    opts =
      prune(
        team: str(args, "team"),
        competition: str(args, "competition"),
        season: int(args, "season"),
        limit: int(args, "limit") || 10
      )

    {:ok,
     Format.biggest_wins(Queries.biggest_wins(opts), "Biggest victories" <> filters_suffix(opts))}
  end

  defp dispatch("competition_stats", args) do
    opts = prune(competition: str(args, "competition"), season: int(args, "season"))

    {:ok,
     Format.competition_stats(
       Queries.competition_stats(opts),
       "Statistics" <> filters_suffix(opts)
     )}
  end

  defp dispatch("list_teams", args) do
    search = str(args, "search")
    limit = int(args, "limit") || 50

    teams =
      DataStore.teams()
      |> Map.values()
      |> Enum.filter(fn t ->
        search == nil or
          String.contains?(
            BrazilianSoccerMcp.TeamNames.clean(t.display),
            BrazilianSoccerMcp.TeamNames.clean(search)
          )
      end)
      |> Enum.sort_by(& &1.display)

    shown = Enum.take(teams, limit)
    rest = length(teams) - length(shown)

    text =
      "Known teams (#{length(teams)}):\n" <>
        Enum.map_join(shown, "\n", &"- #{&1.display}") <>
        if(rest > 0, do: "\n... (#{rest} more)", else: "")

    {:ok, text}
  end

  defp dispatch(name, _args), do: {:error, "unknown tool: #{name}"}

  # -- helpers ---------------------------------------------------------------

  defp validate_search_matches(args) do
    keys = ~w(team opponent competition season date_from date_to stage limit)

    cond do
      str(args, "opponent") != nil and str(args, "team") == nil ->
        {:error, "opponent requires team"}

      Enum.all?(keys -- ["limit"], &(Map.get(args, &1) in [nil, ""])) ->
        {:error, "provide at least one filter (team, competition, season, date range, or stage)"}

      str(args, "competition") != nil and
          Queries.normalize_competition(str(args, "competition")) == :unknown ->
        {:error,
         "unknown competition '#{str(args, "competition")}'. Known: Brasileirão/Série A, " <>
           "Série B, Série C, Copa do Brasil, Copa Libertadores"}

      true ->
        :ok
    end
  end

  defp resolve_team(name) do
    keys = Queries.find_team_keys(name)

    case MapSet.size(keys) do
      0 ->
        {:error,
         "no team matching '#{name}' found in the dataset. Try the list_teams tool to see known team names."}

      _ ->
        display = keys |> Enum.map(&DataStore.display/1) |> Enum.sort() |> Enum.join(" / ")
        {:ok, display}
    end
  end

  defp search_header(opts) do
    "Matches" <> filters_suffix(opts)
  end

  defp players_header(opts) do
    "Players" <> filters_suffix(Keyword.delete(opts, :limit))
  end

  defp filters_suffix(opts) do
    parts =
      opts
      |> Keyword.delete(:limit)
      |> Enum.reject(fn {_k, v} -> v in [nil, :all] end)
      |> Enum.map(fn {k, v} -> "#{k}: #{v}" end)

    case parts do
      [] -> ""
      _ -> " (" <> Enum.join(parts, ", ") <> ")"
    end
  end

  defp str(args, key) do
    case Map.get(args, key) do
      s when is_binary(s) -> if String.trim(s) == "", do: nil, else: String.trim(s)
      other when is_number(other) -> to_string(other)
      _ -> nil
    end
  end

  defp int(args, key) do
    case Map.get(args, key) do
      i when is_integer(i) -> i
      f when is_float(f) -> trunc(f)
      s when is_binary(s) -> BrazilianSoccerMcp.DataStore.parse_int(s)
      _ -> nil
    end
  end

  defp date(args, key) do
    case str(args, key) do
      nil -> nil
      s -> BrazilianSoccerMcp.DataStore.parse_date(s)
    end
  end

  defp require_str(args, key) do
    case str(args, key) do
      nil -> {:error, "missing required argument: #{key}"}
      s -> {:ok, s}
    end
  end

  defp prune(opts), do: Enum.reject(opts, fn {_k, v} -> is_nil(v) end)
end
