defmodule BrazilianSoccer.MCP.Tools do
  @moduledoc """
  The MCP tool registry and dispatcher.

  `list/0` returns the tool specifications (name, description, JSON input
  schema) advertised to MCP clients. `call/3` runs a tool by name against a
  `Dataset`, returning `{:ok, text}` or `{:error, message}`.
  """

  alias BrazilianSoccer.{Dataset, Match}
  alias BrazilianSoccer.MCP.Format
  alias BrazilianSoccer.Queries.{Competitions, Matches, Players, Source, Stats, Teams}

  @tools [
    %{
      name: "search_matches",
      description:
        "Find matches by team, opponent, competition, season or date range. " <>
          "When both a team and opponent are given, includes a head-to-head summary.",
      input_schema: %{
        "type" => "object",
        "properties" => %{
          "team" => %{"type" => "string", "description" => "Team name (matches home or away)"},
          "opponent" => %{"type" => "string", "description" => "Opponent team name"},
          "competition" => %{"type" => "string"},
          "season" => %{"type" => "integer", "description" => "Season year, e.g. 2023"},
          "from" => %{"type" => "string", "description" => "Start date (YYYY-MM-DD)"},
          "to" => %{"type" => "string", "description" => "End date (YYYY-MM-DD)"},
          "limit" => %{"type" => "integer"}
        }
      }
    },
    %{
      name: "head_to_head",
      description: "Head-to-head record between two teams across all competitions.",
      input_schema: %{
        "type" => "object",
        "properties" => %{
          "team_a" => %{"type" => "string"},
          "team_b" => %{"type" => "string"}
        },
        "required" => ["team_a", "team_b"]
      }
    },
    %{
      name: "team_record",
      description:
        "Win/loss/draw record, goals and win rate for a team, optionally by " <>
          "season, competition and venue (home/away).",
      input_schema: %{
        "type" => "object",
        "properties" => %{
          "team" => %{"type" => "string"},
          "season" => %{"type" => "integer"},
          "competition" => %{"type" => "string"},
          "venue" => %{"type" => "string", "enum" => ["home", "away", "all"]}
        },
        "required" => ["team"]
      }
    },
    %{
      name: "compare_teams",
      description: "Compare two teams: individual records plus their head-to-head.",
      input_schema: %{
        "type" => "object",
        "properties" => %{
          "team_a" => %{"type" => "string"},
          "team_b" => %{"type" => "string"}
        },
        "required" => ["team_a", "team_b"]
      }
    },
    %{
      name: "search_players",
      description:
        "Search FIFA players by name, nationality, club or position. Use " <>
          "brazilian=true for Brazilian players. Results ranked by overall rating.",
      input_schema: %{
        "type" => "object",
        "properties" => %{
          "name" => %{"type" => "string"},
          "nationality" => %{"type" => "string"},
          "club" => %{"type" => "string"},
          "position" => %{"type" => "string"},
          "brazilian" => %{"type" => "boolean"},
          "min_overall" => %{"type" => "integer"},
          "limit" => %{"type" => "integer"}
        }
      }
    },
    %{
      name: "standings",
      description: "League standings for a competition and season, computed from match results.",
      input_schema: %{
        "type" => "object",
        "properties" => %{
          "competition" => %{"type" => "string"},
          "season" => %{"type" => "integer"}
        },
        "required" => ["competition", "season"]
      }
    },
    %{
      name: "list_competitions",
      description: "List the competitions available in the dataset and their seasons.",
      input_schema: %{"type" => "object", "properties" => %{}}
    },
    %{
      name: "match_stats",
      description:
        "Aggregate statistics (average goals per match, home/away win rates) " <>
          "over all matches or a competition/season.",
      input_schema: %{
        "type" => "object",
        "properties" => %{
          "competition" => %{"type" => "string"},
          "season" => %{"type" => "integer"}
        }
      }
    },
    %{
      name: "biggest_wins",
      description: "Largest victories by goal margin, optionally by competition/season/team.",
      input_schema: %{
        "type" => "object",
        "properties" => %{
          "competition" => %{"type" => "string"},
          "season" => %{"type" => "integer"},
          "team" => %{"type" => "string"},
          "limit" => %{"type" => "integer"}
        }
      }
    },
    %{
      name: "best_record",
      description:
        "Rank teams by win rate at a venue (home/away/all), with a minimum match threshold.",
      input_schema: %{
        "type" => "object",
        "properties" => %{
          "venue" => %{"type" => "string", "enum" => ["home", "away", "all"]},
          "competition" => %{"type" => "string"},
          "season" => %{"type" => "integer"},
          "min_matches" => %{"type" => "integer"},
          "limit" => %{"type" => "integer"}
        }
      }
    }
  ]

  @doc "Return all tool specifications."
  @spec list() :: [map()]
  def list, do: @tools

  @doc "Dispatch a tool call. Returns `{:ok, text}` or `{:error, message}`."
  @spec call(String.t(), map(), Dataset.t()) :: {:ok, String.t()} | {:error, String.t()}
  def call(name, args, dataset) when is_map(args) do
    do_call(name, args, dataset)
  rescue
    e -> {:error, "Tool execution failed: #{Exception.message(e)}"}
  end

  # --- individual tools ---

  defp do_call("search_matches", args, ds) do
    opts = []
    opts = put_opt(opts, :competition, str(args, "competition"))
    opts = put_opt(opts, :season, int(args, "season"))
    opts = put_opt(opts, :from, date(args, "from"))
    opts = put_opt(opts, :to, date(args, "to"))

    team = str(args, "team")
    opponent = str(args, "opponent")

    opts =
      cond do
        team && opponent -> Keyword.put(opts, :teams, {team, opponent})
        team -> Keyword.put(opts, :team, team)
        true -> opts
      end

    limit = int(args, "limit") || 15
    matches = ds |> Matches.find(opts) |> Source.primary_per_season() |> Matches.sort_recent()

    body =
      case matches do
        [] -> "No matches found."
        list -> Format.matches(list, limit)
      end

    body =
      if team && opponent do
        h2h = Matches.head_to_head(ds, team, opponent)
        body <> "\n\n" <> Format.head_to_head(h2h)
      else
        body
      end

    {:ok, "Found #{length(matches)} match(es).\n\n#{body}"}
  end

  defp do_call("head_to_head", args, ds) do
    with {:ok, a} <- require_arg(args, "team_a"),
         {:ok, b} <- require_arg(args, "team_b") do
      h2h = Matches.head_to_head(ds, a, b)
      recent = Format.matches(h2h.matches, int(args, "limit") || 10)
      {:ok, Format.head_to_head(h2h) <> "\n\n" <> recent}
    end
  end

  defp do_call("team_record", args, ds) do
    with {:ok, team} <- require_arg(args, "team") do
      opts = []
      opts = put_opt(opts, :season, int(args, "season"))
      opts = put_opt(opts, :competition, str(args, "competition"))
      opts = put_opt(opts, :venue, venue(args))

      record = Teams.record(ds, team, opts)
      {:ok, Format.record(record, record_title(team, opts))}
    end
  end

  defp do_call("compare_teams", args, ds) do
    with {:ok, a} <- require_arg(args, "team_a"),
         {:ok, b} <- require_arg(args, "team_b") do
      cmp = Teams.compare(ds, a, b)

      text =
        [
          Format.record(cmp.team_a, "#{cmp.team_a.team} (overall record)"),
          Format.record(cmp.team_b, "#{cmp.team_b.team} (overall record)"),
          Format.head_to_head(cmp.head_to_head)
        ]
        |> Enum.join("\n\n")

      {:ok, text}
    end
  end

  defp do_call("search_players", args, ds) do
    opts = []
    opts = put_opt(opts, :name, str(args, "name"))
    opts = put_opt(opts, :nationality, str(args, "nationality"))
    opts = put_opt(opts, :club, str(args, "club"))
    opts = put_opt(opts, :position, str(args, "position"))
    opts = put_opt(opts, :min_overall, int(args, "min_overall"))
    opts = put_opt(opts, :limit, int(args, "limit") || 20)
    opts = if args["brazilian"] == true, do: Keyword.put(opts, :brazilian, true), else: opts

    case Players.search(ds, opts) do
      [] -> {:ok, "No players found."}
      players -> {:ok, "Found #{length(players)} player(s):\n\n#{Format.players(players)}"}
    end
  end

  defp do_call("standings", args, ds) do
    with {:ok, competition} <- require_arg(args, "competition"),
         {:ok, season} <- require_int(args, "season") do
      case Competitions.standings(ds, competition, season) do
        [] -> {:ok, "No standings available for #{competition} #{season}."}
        table -> {:ok, Format.standings(table, "#{season} #{competition} standings")}
      end
    end
  end

  defp do_call("list_competitions", _args, ds) do
    text =
      ds
      |> Competitions.competitions()
      |> Enum.map_join("\n", fn comp ->
        seasons = Competitions.seasons(ds, comp)
        "- #{comp}: #{format_seasons(seasons)}"
      end)

    {:ok, "Competitions in dataset:\n#{text}"}
  end

  defp do_call("match_stats", args, ds) do
    opts = []
    opts = put_opt(opts, :competition, str(args, "competition"))
    opts = put_opt(opts, :season, int(args, "season"))

    s = Stats.summary(ds, opts)

    text = """
    Matches analyzed: #{s.matches}
    Total goals: #{s.total_goals}
    Average goals per match: #{Float.round(s.avg_goals_per_match, 2)}
    Home win rate: #{Format.percent(s.home_win_rate)}
    Away win rate: #{Format.percent(s.away_win_rate)}
    Draw rate: #{Format.percent(s.draw_rate)}
    """

    {:ok, String.trim_trailing(text)}
  end

  defp do_call("biggest_wins", args, ds) do
    opts = []
    opts = put_opt(opts, :competition, str(args, "competition"))
    opts = put_opt(opts, :season, int(args, "season"))
    opts = put_opt(opts, :team, str(args, "team"))
    opts = Keyword.put(opts, :limit, int(args, "limit") || 10)

    case Stats.biggest_wins(ds, opts) do
      [] -> {:ok, "No matches found."}
      matches -> {:ok, "Biggest wins:\n" <> Enum.map_join(matches, "\n", &("- " <> Format.match_line(&1)))}
    end
  end

  defp do_call("best_record", args, ds) do
    venue = venue(args) || :all
    opts = []
    opts = put_opt(opts, :competition, str(args, "competition"))
    opts = put_opt(opts, :season, int(args, "season"))
    opts = Keyword.put(opts, :min_matches, int(args, "min_matches") || 5)
    opts = Keyword.put(opts, :limit, int(args, "limit") || 10)

    case Stats.best_record(ds, venue, opts) do
      [] ->
        {:ok, "No teams meet the criteria."}

      rows ->
        body =
          rows
          |> Enum.with_index(1)
          |> Enum.map_join("\n", fn {r, i} ->
            "#{i}. #{r.team} - #{Format.percent(r.win_rate)} " <>
              "(#{r.wins}W, #{r.draws}D, #{r.losses}L in #{r.played})"
          end)

        {:ok, "Best #{venue} records:\n#{body}"}
    end
  end

  defp do_call(name, _args, _ds), do: {:error, "Unknown tool: #{name}"}

  # --- argument helpers ---

  defp put_opt(opts, _key, nil), do: opts
  defp put_opt(opts, key, value), do: Keyword.put(opts, key, value)

  defp require_arg(args, key) do
    case str(args, key) do
      nil -> {:error, "Missing required argument: #{key}"}
      value -> {:ok, value}
    end
  end

  defp require_int(args, key) do
    case int(args, key) do
      nil -> {:error, "Missing or invalid integer argument: #{key}"}
      value -> {:ok, value}
    end
  end

  defp str(args, key) do
    case Map.get(args, key) do
      nil -> nil
      "" -> nil
      value when is_binary(value) -> value
      value -> to_string(value)
    end
  end

  defp int(args, key) do
    case Map.get(args, key) do
      n when is_integer(n) -> n
      n when is_float(n) -> trunc(n)
      s when is_binary(s) -> parse_int(s)
      _ -> nil
    end
  end

  defp parse_int(s) do
    case Integer.parse(String.trim(s)) do
      {n, _} -> n
      :error -> nil
    end
  end

  defp date(args, key) do
    case str(args, key) do
      nil -> nil
      s -> Match.parse_date(s)
    end
  end

  defp venue(args) do
    case str(args, "venue") do
      "home" -> :home
      "away" -> :away
      "all" -> :all
      _ -> nil
    end
  end

  defp record_title(team, opts) do
    clean = BrazilianSoccer.TeamName.clean(team)
    parts = []
    parts = if opts[:season], do: parts ++ ["#{opts[:season]}"], else: parts
    parts = if opts[:competition], do: parts ++ [opts[:competition]], else: parts

    parts =
      case opts[:venue] do
        :home -> parts ++ ["home"]
        :away -> parts ++ ["away"]
        _ -> parts
      end

    case parts do
      [] -> "#{clean} record"
      list -> "#{clean} record (#{Enum.join(list, " ")})"
    end
  end

  defp format_seasons([]), do: "no seasons"
  defp format_seasons(seasons), do: "#{List.first(seasons)}–#{List.last(seasons)} (#{length(seasons)} seasons)"
end
