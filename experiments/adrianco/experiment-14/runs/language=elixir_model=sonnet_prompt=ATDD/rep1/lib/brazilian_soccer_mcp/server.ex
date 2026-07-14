defmodule BrazilianSoccerMcp.Server do
  @moduledoc """
  MCP JSON-RPC 2.0 protocol handler.

  Receives a decoded request map and returns {:ok, response_map} or {:error, reason}.
  The stdio runner (for production use) wraps this with JSON encode/decode.
  """

  alias BrazilianSoccerMcp.Tools

  @server_info %{
    "name" => "brazilian-soccer-mcp",
    "version" => "1.0.0"
  }

  @capabilities %{
    "tools" => %{}
  }

  # ---------- public ----------

  def handle_request(%{"method" => "initialize"} = req) do
    {:ok,
     success(req["id"], %{
       "protocolVersion" => "2024-11-05",
       "serverInfo" => @server_info,
       "capabilities" => @capabilities
     })}
  end

  def handle_request(%{"method" => "initialized"}), do: {:ok, nil}

  def handle_request(%{"method" => "tools/list"} = req) do
    {:ok, success(req["id"], %{"tools" => tools_list()})}
  end

  def handle_request(%{"method" => "tools/call"} = req) do
    name = req["params"]["name"]
    args = req["params"]["arguments"] || %{}

    result =
      case name do
        "find_matches" -> Tools.FindMatches.call(args)
        "get_team_stats" -> Tools.GetTeamStats.call(args)
        "find_players" -> Tools.FindPlayers.call(args)
        "get_competition_standings" -> Tools.GetCompetitionStandings.call(args)
        "get_statistics" -> Tools.GetStatistics.call(args)
        _ -> {:error, "Unknown tool: #{name}"}
      end

    case result do
      {:ok, text} ->
        {:ok,
         success(req["id"], %{
           "content" => [%{"type" => "text", "text" => text}]
         })}

      {:error, msg} ->
        {:ok, error_response(req["id"], -32_603, msg)}
    end
  end

  def handle_request(%{"method" => method} = req) do
    {:ok, error_response(req["id"], -32_601, "Method not found: #{method}")}
  end

  # ---------- private ----------

  defp success(id, result), do: %{"jsonrpc" => "2.0", "id" => id, "result" => result}

  defp error_response(id, code, message) do
    %{"jsonrpc" => "2.0", "id" => id, "error" => %{"code" => code, "message" => message}}
  end

  defp tools_list do
    [
      %{
        "name" => "find_matches",
        "description" =>
          "Find soccer matches from Brazilian competitions. Search by team, season, competition, or head-to-head.",
        "inputSchema" => %{
          "type" => "object",
          "properties" => %{
            "team1" => %{"type" => "string", "description" => "First team name (partial match ok)"},
            "team2" => %{
              "type" => "string",
              "description" => "Second team name for head-to-head search"
            },
            "season" => %{"type" => "integer", "description" => "Season year (e.g. 2023)"},
            "competition" => %{
              "type" => "string",
              "description" => "Competition: Brasileirao, Copa do Brasil, Libertadores"
            },
            "limit" => %{
              "type" => "integer",
              "description" => "Max number of matches to return (default 20)"
            }
          }
        }
      },
      %{
        "name" => "get_team_stats",
        "description" =>
          "Get win/draw/loss statistics, goals scored/conceded, and win rate for a team.",
        "inputSchema" => %{
          "type" => "object",
          "required" => ["team"],
          "properties" => %{
            "team" => %{"type" => "string", "description" => "Team name"},
            "season" => %{"type" => "integer", "description" => "Season year (optional)"},
            "competition" => %{
              "type" => "string",
              "description" => "Competition filter (optional)"
            }
          }
        }
      },
      %{
        "name" => "find_players",
        "description" =>
          "Search FIFA player database by name, nationality, club, position, or minimum overall rating.",
        "inputSchema" => %{
          "type" => "object",
          "properties" => %{
            "name" => %{"type" => "string", "description" => "Player name (partial match ok)"},
            "nationality" => %{"type" => "string", "description" => "Nationality (e.g. Brazil)"},
            "club" => %{"type" => "string", "description" => "Club name (partial match ok)"},
            "position" => %{
              "type" => "string",
              "description" => "Position (e.g. GK, ST, CAM)"
            },
            "min_overall" => %{
              "type" => "integer",
              "description" => "Minimum FIFA overall rating"
            },
            "limit" => %{
              "type" => "integer",
              "description" => "Max results to return (default 20)"
            }
          }
        }
      },
      %{
        "name" => "get_competition_standings",
        "description" =>
          "Calculate league standings (points, W/D/L, goals) from match results for a given competition and season.",
        "inputSchema" => %{
          "type" => "object",
          "required" => ["competition", "season"],
          "properties" => %{
            "competition" => %{
              "type" => "string",
              "description" => "Competition name: Brasileirao, Copa do Brasil, Libertadores"
            },
            "season" => %{"type" => "integer", "description" => "Season year"}
          }
        }
      },
      %{
        "name" => "get_statistics",
        "description" =>
          "Compute aggregated statistics: biggest_wins, goals_per_match, home_away_record, best_home_teams.",
        "inputSchema" => %{
          "type" => "object",
          "required" => ["stat_type"],
          "properties" => %{
            "stat_type" => %{
              "type" => "string",
              "enum" => [
                "biggest_wins",
                "goals_per_match",
                "home_away_record",
                "best_home_teams"
              ],
              "description" => "Type of statistic to compute"
            },
            "competition" => %{
              "type" => "string",
              "description" => "Optionally filter by competition"
            },
            "season" => %{"type" => "integer", "description" => "Optionally filter by season"}
          }
        }
      }
    ]
  end
end
