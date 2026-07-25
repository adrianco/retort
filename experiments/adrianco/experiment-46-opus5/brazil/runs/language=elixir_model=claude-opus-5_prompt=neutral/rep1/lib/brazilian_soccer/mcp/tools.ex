defmodule BrazilianSoccer.MCP.Tools do
  @moduledoc """
  The MCP tool catalogue.

  Each entry is data: a name, a description the model reads to choose the
  tool, a JSON schema for the arguments, the query function that answers it
  and the formatter that turns the answer into text.  `call/2` returns both
  the text (for `content`) and the sanitised structured result (for
  `structuredContent`).
  """

  alias BrazilianSoccer.Data.Graph
  alias BrazilianSoccer.Format
  alias BrazilianSoccer.MCP.JSON
  alias BrazilianSoccer.Query.{Competitions, Matches, Players, Stats, Teams}
  alias BrazilianSoccer.Repo

  @team_arg %{
    type: "string",
    description: "Team name in any spelling, e.g. \"Flamengo\", \"Atlético-MG\", \"Sao Paulo\""
  }
  @competition_arg %{
    type: "string",
    description:
      "Competition: \"Brasileirão\"/\"Serie A\", \"Serie B\", \"Serie C\", \"Copa do Brasil\" or \"Libertadores\""
  }
  @season_arg %{type: "integer", description: "Season year, e.g. 2019"}
  @limit_arg %{type: "integer", description: "Maximum number of rows to return"}

  @tools [
    %{
      name: "list_datasets",
      description:
        "Describe the loaded knowledge graph: source CSV files, row counts, competitions, teams and players available.",
      input_schema: %{type: "object", properties: %{}},
      run: {__MODULE__, :info},
      format: {Format, :info}
    },
    %{
      name: "search_matches",
      description:
        "Find matches by team, opponent, competition, season, date range, stage or round. Use it for questions like \"show me all Flamengo vs Fluminense matches\" or \"what matches did Palmeiras play in 2023?\".",
      input_schema: %{
        type: "object",
        properties: %{
          team: @team_arg,
          opponent: %{type: "string", description: "Restrict to matches against this team"},
          home_team: %{type: "string", description: "Team that played at home"},
          away_team: %{type: "string", description: "Team that played away"},
          competition: @competition_arg,
          season: @season_arg,
          season_from: %{type: "integer", description: "Earliest season (inclusive)"},
          season_to: %{type: "integer", description: "Latest season (inclusive)"},
          date_from: %{type: "string", description: "Earliest date, YYYY-MM-DD"},
          date_to: %{type: "string", description: "Latest date, YYYY-MM-DD"},
          stage: %{
            type: "string",
            description:
              "Cup stage: \"final\", \"semifinals\", \"quarterfinals\", \"round of 16\", \"group stage\""
          },
          round: %{type: "integer", description: "League round number"},
          venue: %{
            type: "string",
            enum: ["home", "away", "all"],
            description: "Where `team` played"
          },
          limit: @limit_arg
        }
      },
      run: {Matches, :search},
      format: {Format, :matches}
    },
    %{
      name: "head_to_head",
      description:
        "Head-to-head record between two teams: wins, draws, goals, breakdown by competition and the most recent meetings.",
      input_schema: %{
        type: "object",
        properties: %{
          team_a: @team_arg,
          team_b: @team_arg,
          competition: @competition_arg,
          season: @season_arg,
          limit: @limit_arg
        },
        required: ["team_a", "team_b"]
      },
      run: {Matches, :head_to_head},
      format: {Format, :head_to_head}
    },
    %{
      name: "last_meeting",
      description:
        "The most recent match between two teams (\"when did Flamengo last play Corinthians?\").",
      input_schema: %{
        type: "object",
        properties: %{team_a: @team_arg, team_b: @team_arg},
        required: ["team_a", "team_b"]
      },
      run: {__MODULE__, :last_meeting},
      format: {Format, :last_meeting}
    },
    %{
      name: "find_derbies",
      description:
        "Matches between traditional rivals (Fla-Flu, Derby Paulista, Gre-Nal, Atletiba...), optionally filtered by team, season or competition.",
      input_schema: %{
        type: "object",
        properties: %{
          team: @team_arg,
          season: @season_arg,
          competition: @competition_arg,
          limit: @limit_arg
        }
      },
      run: {Matches, :derbies},
      format: {Format, :derbies}
    },
    %{
      name: "team_stats",
      description:
        "Win/draw/loss record, goals, home and away splits, recent form and per-competition breakdown for one team. Filter by season, competition, venue or date range.",
      input_schema: %{
        type: "object",
        properties: %{
          team: @team_arg,
          season: @season_arg,
          season_from: %{type: "integer"},
          season_to: %{type: "integer"},
          competition: @competition_arg,
          venue: %{type: "string", enum: ["home", "away", "all"]},
          date_from: %{type: "string"},
          date_to: %{type: "string"}
        },
        required: ["team"]
      },
      run: {Teams, :stats},
      format: {Format, :team_stats}
    },
    %{
      name: "team_profile",
      description:
        "Identity card for a club: canonical name, every spelling found in the data, state, competitions, seasons, overall record and FIFA squad.",
      input_schema: %{
        type: "object",
        properties: %{team: @team_arg},
        required: ["team"]
      },
      run: {Teams, :profile},
      format: {Format, :team_profile}
    },
    %{
      name: "compare_teams",
      description: "Compare two teams: both records side by side plus their head-to-head.",
      input_schema: %{
        type: "object",
        properties: %{
          team_a: @team_arg,
          team_b: @team_arg,
          season: @season_arg,
          competition: @competition_arg
        },
        required: ["team_a", "team_b"]
      },
      run: {Teams, :compare},
      format: {Format, :compare_teams}
    },
    %{
      name: "team_rankings",
      description:
        "Rank teams by record — best home record, best away record, most wins, best attack or defence — over a competition, a season or the whole dataset.",
      input_schema: %{
        type: "object",
        properties: %{
          metric: %{
            type: "string",
            enum: ["home", "away", "overall"],
            description: "Which matches to count"
          },
          sort_by: %{
            type: "string",
            enum: [
              "win_rate",
              "points",
              "wins",
              "goals_for",
              "goals_against",
              "goal_difference",
              "matches"
            ]
          },
          competition: @competition_arg,
          season: @season_arg,
          min_matches: %{type: "integer", description: "Ignore teams with fewer matches"},
          limit: @limit_arg
        }
      },
      run: {Teams, :rankings},
      format: {Format, :rankings}
    },
    %{
      name: "search_players",
      description:
        "Search the FIFA player database by name, nationality, club, position, rating or age. Sort by overall, potential, age or value.",
      input_schema: %{
        type: "object",
        properties: %{
          name: %{type: "string", description: "Full or partial player name"},
          nationality: %{type: "string", description: "e.g. \"Brazil\""},
          club: %{type: "string", description: "Club name, e.g. \"Grêmio\""},
          position: %{
            type: "string",
            description: "FIFA position code, e.g. \"ST\", \"GK\", \"CAM\""
          },
          position_group: %{
            type: "string",
            enum: ["forward", "midfielder", "defender", "goalkeeper"]
          },
          min_overall: %{type: "integer"},
          max_overall: %{type: "integer"},
          min_age: %{type: "integer"},
          max_age: %{type: "integer"},
          brazilian_clubs_only: %{
            type: "boolean",
            description: "Only players whose club is a Brazilian club in the match graph"
          },
          sort_by: %{type: "string", enum: ["overall", "potential", "age", "value", "name"]},
          limit: @limit_arg
        }
      },
      run: {Players, :search},
      format: {Format, :players}
    },
    %{
      name: "player_profile",
      description:
        "Everything about one player: ratings, attributes, club, and — when the club plays in the match datasets — its recent matches and top team-mates.",
      input_schema: %{
        type: "object",
        properties: %{
          name: %{type: "string", description: "Player name, e.g. \"Neymar\""},
          player_id: %{type: "integer", description: "FIFA player id"}
        }
      },
      run: {Players, :profile},
      format: {Format, :player_profile}
    },
    %{
      name: "club_squad",
      description:
        "The FIFA squad of a club: size, average rating and age, best player, breakdown by position, plus the club's recent matches.",
      input_schema: %{
        type: "object",
        properties: %{club: @team_arg, limit: @limit_arg},
        required: ["club"]
      },
      run: {Players, :club_squad},
      format: {Format, :club_squad}
    },
    %{
      name: "players_by_nationality",
      description:
        "Report on the players of one nationality (default Brazil): top rated players and how they are spread across Brazilian clubs.",
      input_schema: %{
        type: "object",
        properties: %{nationality: %{type: "string"}, limit: @limit_arg}
      },
      run: {Players, :nationality_report},
      format: {Format, :nationality_report}
    },
    %{
      name: "list_competitions",
      description: "Competitions in the graph with their seasons, match counts and team counts.",
      input_schema: %{type: "object", properties: %{}},
      run: {__MODULE__, :list_competitions},
      format: {Format, :competitions}
    },
    %{
      name: "league_standings",
      description:
        "League table for a season, computed from match results (3 points per win). Use venue to get home-only or away-only tables. Marks the champion and the relegation zone.",
      input_schema: %{
        type: "object",
        properties: %{
          competition: @competition_arg,
          season: @season_arg,
          venue: %{type: "string", enum: ["home", "away", "all"]}
        },
        required: ["season"]
      },
      run: {Competitions, :standings},
      format: {Format, :standings}
    },
    %{
      name: "competition_champion",
      description:
        "Who won a competition in a season: top of the computed league table, or the winner of the final (on aggregate) for the cups.",
      input_schema: %{
        type: "object",
        properties: %{competition: @competition_arg, season: @season_arg},
        required: ["season"]
      },
      run: {Competitions, :champion},
      format: {Format, :champion}
    },
    %{
      name: "cup_bracket",
      description:
        "Knock-out bracket for a cup season: every stage from the group stage / early rounds to the final.",
      input_schema: %{
        type: "object",
        properties: %{competition: @competition_arg, season: @season_arg},
        required: ["season"]
      },
      run: {Competitions, :bracket},
      format: {Format, :bracket}
    },
    %{
      name: "competition_summary",
      description:
        "Season summary for a competition: goals, home advantage, top scoring teams, best defences, biggest win and derived champion.",
      input_schema: %{
        type: "object",
        properties: %{competition: @competition_arg, season: @season_arg}
      },
      run: {Competitions, :summary},
      format: {Format, :competition_summary}
    },
    %{
      name: "match_statistics",
      description:
        "Aggregate statistics for any slice of the data: matches, goals per match, home/draw/away rates, season-by-season trend, highest scoring match and biggest margin.",
      input_schema: %{
        type: "object",
        properties: %{
          competition: @competition_arg,
          season: @season_arg,
          season_from: %{type: "integer"},
          season_to: %{type: "integer"},
          team: @team_arg
        }
      },
      run: {Stats, :overview},
      format: {Format, :stats_overview}
    },
    %{
      name: "biggest_wins",
      description:
        "Biggest victories by goal margin, optionally for one team, competition or season.",
      input_schema: %{
        type: "object",
        properties: %{
          team: @team_arg,
          competition: @competition_arg,
          season: @season_arg,
          limit: @limit_arg
        }
      },
      run: {Stats, :biggest_wins},
      format: {Format, :biggest_wins}
    },
    %{
      name: "highest_scoring_matches",
      description: "Matches with the most goals, optionally for one team, competition or season.",
      input_schema: %{
        type: "object",
        properties: %{
          team: @team_arg,
          competition: @competition_arg,
          season: @season_arg,
          limit: @limit_arg
        }
      },
      run: {Stats, :highest_scoring},
      format: {Format, :highest_scoring}
    },
    %{
      name: "compare_seasons",
      description:
        "Compare two or more seasons of a competition: goals, home advantage, champion and top scoring team.",
      input_schema: %{
        type: "object",
        properties: %{
          seasons: %{type: "array", items: %{type: "integer"}, description: "Seasons to compare"},
          competition: @competition_arg
        },
        required: ["seasons"]
      },
      run: {Stats, :compare_seasons},
      format: {Format, :compare_seasons}
    },
    %{
      name: "home_advantage",
      description: "How big home advantage is in a competition, overall and season by season.",
      input_schema: %{type: "object", properties: %{competition: @competition_arg}},
      run: {Stats, :home_advantage},
      format: {Format, :home_advantage}
    },
    %{
      name: "resolve_team_name",
      description:
        "Resolve a team name spelling to the canonical club in the graph, with the alternative spellings found in the datasets. Useful when a name is ambiguous (\"Botafogo\", \"América\", \"Atlético\").",
      input_schema: %{
        type: "object",
        properties: %{name: @team_arg, limit: @limit_arg},
        required: ["name"]
      },
      run: {__MODULE__, :resolve_team_name},
      format: {__MODULE__, :format_resolution}
    }
  ]

  @doc "All tool definitions."
  @spec all() :: [map]
  def all, do: @tools

  @doc "Tool definitions in MCP `tools/list` shape."
  @spec list() :: [map]
  def list do
    Enum.map(@tools, fn tool ->
      %{
        "name" => tool.name,
        "description" => tool.description,
        "inputSchema" => JSON.sanitize(tool.input_schema)
      }
    end)
  end

  @doc "Look up a tool definition by name."
  @spec fetch(binary) :: {:ok, map} | :error
  def fetch(name) do
    case Enum.find(@tools, &(&1.name == name)) do
      nil -> :error
      tool -> {:ok, tool}
    end
  end

  @doc """
  Run a tool.

  Returns `{:ok, %{text: text, data: structured}}` for a successful call and
  `{:error, text}` when the query could not be answered (unknown team, missing
  argument, no data for that season...).
  """
  @spec call(binary, map) :: {:ok, %{text: binary, data: map}} | {:error, binary}
  def call(name, args \\ %{}) do
    args = args || %{}

    with {:ok, tool} <- fetch_tool(name) do
      {module, function} = tool.run
      {format_module, format_function} = tool.format

      case apply(module, function, [Repo.graph(), args]) do
        {:ok, result} ->
          {:ok,
           %{
             text: apply(format_module, format_function, [result]),
             data: JSON.sanitize(result)
           }}

        {:error, reason} ->
          {:error, Format.error(reason)}

        other ->
          {:error, Format.error({:unexpected_result, other})}
      end
    end
  end

  defp fetch_tool(name) do
    case fetch(name) do
      {:ok, tool} -> {:ok, tool}
      :error -> {:error, Format.error({:unknown_tool, name})}
    end
  end

  # --- handlers that are not a plain query call ----------------------------

  @doc false
  def info(graph, _args) do
    {:ok, Map.put(graph.meta, :competitions, Graph.competitions())}
  end

  @doc false
  def list_competitions(graph, _args), do: Competitions.list(graph)

  @doc false
  def last_meeting(graph, args) do
    team_a = BrazilianSoccer.Query.Filters.get(args, :team_a)
    team_b = BrazilianSoccer.Query.Filters.get(args, :team_b)

    cond do
      is_nil(team_a) -> {:error, {:missing_argument, :team_a}}
      is_nil(team_b) -> {:error, {:missing_argument, :team_b}}
      true -> Matches.last_meeting(graph, team_a, team_b)
    end
  end

  @doc false
  def resolve_team_name(graph, args) do
    name = BrazilianSoccer.Query.Filters.get(args, :name)
    limit = BrazilianSoccer.Query.Filters.limit(BrazilianSoccer.Query.Filters.get(args, :limit), 5)

    case name do
      nil ->
        {:error, {:missing_argument, :name}}

      name ->
        case Graph.find_teams(graph, name, limit) do
          [] -> {:error, {:team_not_found, name, []}}
          teams -> {:ok, %{query: name, teams: teams}}
        end
    end
  end

  @doc false
  def format_resolution(%{query: query, teams: teams}) do
    body =
      Enum.map_join(teams, "\n", fn team ->
        "- #{team.name} (id: #{team.id}#{if team.state, do: ", " <> team.state, else: ""}) — " <>
          "#{team.match_count} matches; spellings: #{Enum.join(Enum.take(team.aliases, 5), ", ")}"
      end)

    "\"#{query}\" resolves to:\n#{body}"
  end
end
