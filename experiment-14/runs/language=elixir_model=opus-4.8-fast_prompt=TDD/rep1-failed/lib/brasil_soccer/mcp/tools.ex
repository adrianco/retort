defmodule BrasilSoccer.MCP.Tools do
  @moduledoc """
  The catalogue of MCP tools exposed by the server and the logic that runs them.

  `specs/0` returns the JSON-schema tool definitions advertised via `tools/list`.
  `call/3` dispatches a `tools/call` to the right query module and renders the
  result with `BrasilSoccer.Formatter`. Both are pure given the dataset, which
  keeps them straightforward to unit test.
  """

  alias BrasilSoccer.{Matches, Teams, Players, Competitions, Stats, Formatter}

  @type data :: %{matches: list(), players: list()}

  @doc "Tool definitions advertised to MCP clients."
  @spec specs() :: [map()]
  def specs do
    [
      %{
        name: "find_matches",
        description:
          "Find soccer matches by team, opponent, competition, season, or date range. " <>
            "Provide two teams to also get their head-to-head record.",
        inputSchema:
          object(%{
            "team" => string("Team name (matches either home or away)."),
            "opponent" => string("Second team, to restrict to a specific pairing."),
            "home" => string("Restrict to matches where this team played at home."),
            "away" => string("Restrict to matches where this team played away."),
            "competition" =>
              string("Competition name, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'."),
            "season" => integer("Season year, e.g. 2019."),
            "from" => string("Start date (YYYY-MM-DD), inclusive."),
            "to" => string("End date (YYYY-MM-DD), inclusive."),
            "limit" => integer("Maximum number of matches to return (default 20).")
          })
      },
      %{
        name: "team_record",
        description:
          "Win/draw/loss record, goals, and win rate for a team. Optionally scope by " <>
            "season, competition, or home/away.",
        inputSchema:
          object(
            %{
              "team" => string("Team name (required)."),
              "season" => integer("Season year."),
              "competition" => string("Competition name."),
              "side" => enum_string("Restrict to 'home' or 'away' matches.", ["home", "away"])
            },
            ["team"]
          )
      },
      %{
        name: "compare_teams",
        description: "Compare two teams head-to-head and show each team's overall record.",
        inputSchema:
          object(
            %{
              "team_a" => string("First team (required)."),
              "team_b" => string("Second team (required).")
            },
            ["team_a", "team_b"]
          )
      },
      %{
        name: "search_players",
        description:
          "Search FIFA players by name, nationality, club, or position. Results are " <>
            "sorted by overall rating.",
        inputSchema:
          object(%{
            "name" => string("Full or partial player name."),
            "nationality" => string("Nationality, e.g. 'Brazil'."),
            "club" => string("Club name, e.g. 'Flamengo'."),
            "position" => string("Position code, e.g. 'ST', 'GK', 'LW'."),
            "min_overall" => integer("Minimum overall rating."),
            "limit" => integer("Maximum number of players to return (default 20).")
          })
      },
      %{
        name: "players_by_club",
        description:
          "Summarise players grouped by club (count and average rating), optionally " <>
            "filtered by nationality.",
        inputSchema:
          object(%{
            "nationality" => string("Nationality filter, e.g. 'Brazil'."),
            "club" => string("Club name filter."),
            "limit" => integer("Maximum number of clubs to return (default 20).")
          })
      },
      %{
        name: "standings",
        description:
          "Compute the league table for a competition and season from match results " <>
            "(3 points for a win).",
        inputSchema:
          object(
            %{
              "competition" => string("Competition name (required), e.g. 'Brasileirão'."),
              "season" => integer("Season year (required), e.g. 2019.")
            },
            ["competition", "season"]
          )
      },
      %{
        name: "competition_champion",
        description: "Return the champion (top of the computed table) for a competition and season.",
        inputSchema:
          object(
            %{
              "competition" => string("Competition name (required)."),
              "season" => integer("Season year (required).")
            },
            ["competition", "season"]
          )
      },
      %{
        name: "match_statistics",
        description:
          "Aggregate statistics (average goals, home/away/draw rates) over matches, " <>
            "optionally scoped by competition, season, or team.",
        inputSchema:
          object(%{
            "competition" => string("Competition name filter."),
            "season" => integer("Season year filter."),
            "team" => string("Team filter.")
          })
      },
      %{
        name: "biggest_wins",
        description: "List the matches with the largest goal margins.",
        inputSchema:
          object(%{
            "competition" => string("Competition name filter."),
            "season" => integer("Season year filter."),
            "limit" => integer("Maximum number of matches to return (default 10).")
          })
      },
      %{
        name: "dataset_info",
        description:
          "Describe the loaded datasets: number of matches, players, and the list of " <>
            "competitions available.",
        inputSchema: object(%{})
      }
    ]
  end

  @doc "Run a tool by name with string-keyed `args` against `data`."
  @spec call(String.t(), map(), data()) :: {:ok, String.t()} | {:error, String.t()}
  def call("find_matches", args, data), do: find_matches(args, data)
  def call("team_record", args, data), do: team_record(args, data)
  def call("compare_teams", args, data), do: compare_teams(args, data)
  def call("search_players", args, data), do: search_players(args, data)
  def call("players_by_club", args, data), do: players_by_club(args, data)
  def call("standings", args, data), do: standings(args, data)
  def call("competition_champion", args, data), do: champion(args, data)
  def call("match_statistics", args, data), do: statistics(args, data)
  def call("biggest_wins", args, data), do: biggest_wins(args, data)
  def call("dataset_info", args, data), do: dataset_info(args, data)
  def call(name, _args, _data), do: {:error, "Unknown tool: #{name}"}

  # ── Tool implementations ──────────────────────────────────────────────────

  defp find_matches(args, data) do
    opts = match_opts(args)

    if opts == [] do
      {:error, "Provide at least one filter (team, competition, season, or date range)."}
    else
      matches = Matches.find(data.matches, Keyword.put_new(opts, :limit, 20))
      title = describe_filters(opts)

      text =
        if args["team"] && args["opponent"] do
          h2h = Matches.head_to_head(data.matches, args["team"], args["opponent"])
          Formatter.head_to_head(h2h)
        else
          Formatter.matches(matches, title)
        end

      {:ok, text}
    end
  end

  defp team_record(args, data) do
    with {:ok, team} <- require_string(args, "team") do
      opts =
        []
        |> put_if(args["season"], &Keyword.put(&1, :season, to_int(args["season"])))
        |> put_if(args["competition"], &Keyword.put(&1, :competition, args["competition"]))
        |> put_if(args["side"] == "home", &Keyword.put(&1, :home, team))
        |> put_if(args["side"] == "away", &Keyword.put(&1, :away, team))

      {:ok, Formatter.record(Teams.record(data.matches, team, opts))}
    end
  end

  defp compare_teams(args, data) do
    with {:ok, a} <- require_string(args, "team_a"),
         {:ok, b} <- require_string(args, "team_b") do
      {:ok, Formatter.compare(Teams.compare(data.matches, a, b))}
    end
  end

  defp search_players(args, data) do
    opts =
      []
      |> put_if(args["name"], &Keyword.put(&1, :name, args["name"]))
      |> put_if(args["nationality"], &Keyword.put(&1, :nationality, args["nationality"]))
      |> put_if(args["club"], &Keyword.put(&1, :club, args["club"]))
      |> put_if(args["position"], &Keyword.put(&1, :position, args["position"]))
      |> put_if(args["min_overall"], &Keyword.put(&1, :min_overall, to_int(args["min_overall"])))
      |> Keyword.put(:limit, to_int(args["limit"]) || 20)

    {:ok, Formatter.players(Players.search(data.players, opts), "Players")}
  end

  defp players_by_club(args, data) do
    opts =
      []
      |> put_if(args["nationality"], &Keyword.put(&1, :nationality, args["nationality"]))
      |> put_if(args["club"], &Keyword.put(&1, :club, args["club"]))

    summary =
      data.players
      |> Players.by_club_summary(opts)
      |> Enum.take(to_int(args["limit"]) || 20)

    {:ok, Formatter.club_summary(summary, "Players by club")}
  end

  defp standings(args, data) do
    with {:ok, comp} <- require_string(args, "competition"),
         {:ok, season} <- require_int(args, "season") do
      table = Competitions.standings(data.matches, comp, season)
      {:ok, Formatter.standings(table, comp, season)}
    end
  end

  defp champion(args, data) do
    with {:ok, comp} <- require_string(args, "competition"),
         {:ok, season} <- require_int(args, "season") do
      case Competitions.champion(data.matches, comp, season) do
        nil -> {:ok, "No #{comp} matches found for #{season}."}
        row -> {:ok, "#{season} #{comp} champion: #{row.team} (#{row.points} pts)."}
      end
    end
  end

  defp statistics(args, data) do
    opts =
      []
      |> put_if(args["competition"], &Keyword.put(&1, :competition, args["competition"]))
      |> put_if(args["season"], &Keyword.put(&1, :season, to_int(args["season"])))
      |> put_if(args["team"], &Keyword.put(&1, :team, args["team"]))

    {:ok, Formatter.summary(Stats.summary(data.matches, opts), "Match statistics" <> scope_suffix(opts))}
  end

  defp biggest_wins(args, data) do
    opts =
      []
      |> put_if(args["competition"], &Keyword.put(&1, :competition, args["competition"]))
      |> put_if(args["season"], &Keyword.put(&1, :season, to_int(args["season"])))
      |> Keyword.put(:limit, to_int(args["limit"]) || 10)

    wins = Stats.biggest_wins(data.matches, opts)
    {:ok, Formatter.matches(wins, "Biggest wins" <> scope_suffix(opts))}
  end

  defp dataset_info(_args, data) do
    competitions =
      data.matches |> Enum.map(& &1.competition) |> Enum.reject(&is_nil/1) |> Enum.uniq() |> Enum.sort()

    text =
      "Loaded datasets:\n" <>
        "- Matches: #{length(data.matches)}\n" <>
        "- Players: #{length(data.players)}\n" <>
        "- Competitions: #{Enum.join(competitions, ", ")}"

    {:ok, text}
  end

  # ── Helpers ───────────────────────────────────────────────────────────────

  defp match_opts(args) do
    []
    |> put_if(args["team"], &Keyword.put(&1, :team, args["team"]))
    |> put_if(args["opponent"], &Keyword.put(&1, :opponent, args["opponent"]))
    |> put_if(args["home"], &Keyword.put(&1, :home, args["home"]))
    |> put_if(args["away"], &Keyword.put(&1, :away, args["away"]))
    |> put_if(args["competition"], &Keyword.put(&1, :competition, args["competition"]))
    |> put_if(args["season"], &Keyword.put(&1, :season, to_int(args["season"])))
    |> put_if(args["from"], &Keyword.put(&1, :from, parse_date(args["from"])))
    |> put_if(args["to"], &Keyword.put(&1, :to, parse_date(args["to"])))
    |> put_if(args["limit"], &Keyword.put(&1, :limit, to_int(args["limit"])))
    |> Enum.reject(fn {_k, v} -> is_nil(v) end)
  end

  defp describe_filters(opts) do
    parts =
      Enum.map(opts, fn
        {:team, v} -> "team #{v}"
        {:competition, v} -> "competition #{v}"
        {:season, v} -> "season #{v}"
        {:home, v} -> "#{v} at home"
        {:away, v} -> "#{v} away"
        {:from, v} -> "from #{v}"
        {:to, v} -> "to #{v}"
        _ -> nil
      end)
      |> Enum.reject(&is_nil/1)

    "Matches (" <> Enum.join(parts, ", ") <> ")"
  end

  defp scope_suffix(opts) do
    parts =
      for {k, v} <- opts, k in [:competition, :season, :team], do: "#{v}"

    case parts do
      [] -> ""
      list -> " (" <> Enum.join(list, ", ") <> ")"
    end
  end

  defp put_if(opts, condition, fun) do
    if condition, do: fun.(opts), else: opts
  end

  defp require_string(args, key) do
    case args[key] do
      value when is_binary(value) and value != "" -> {:ok, value}
      _ -> {:error, "Missing required '#{key}'."}
    end
  end

  defp require_int(args, key) do
    case to_int(args[key]) do
      nil -> {:error, "Missing required integer '#{key}'."}
      n -> {:ok, n}
    end
  end

  defp to_int(nil), do: nil
  defp to_int(n) when is_integer(n), do: n
  defp to_int(n) when is_float(n), do: trunc(n)
  defp to_int(s) when is_binary(s), do: BrasilSoccer.Loader.to_int(s)

  defp parse_date(value), do: BrasilSoccer.Loader.parse_date(value)

  # Schema builders for the tool input definitions.
  defp object(properties, required \\ []) do
    %{"type" => "object", "properties" => properties, "required" => required}
  end

  defp string(description), do: %{"type" => "string", "description" => description}
  defp integer(description), do: %{"type" => "integer", "description" => description}

  defp enum_string(description, values),
    do: %{"type" => "string", "description" => description, "enum" => values}
end
