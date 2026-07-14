defmodule BrazilianSoccerMcp.Tools do
  @moduledoc """
  MCP tool definitions and dispatch.
  """

  alias BrazilianSoccerMcp.QueryEngine

  def list_tools do
    [
      %{
        name: "search_matches",
        description: """
        Search Brazilian soccer matches across all competitions (Brasileirão, Copa do Brasil,
        Copa Libertadores, historical data). Filter by team, competition, season, or date range.
        Returns match results with scores.
        """,
        inputSchema: %{
          type: "object",
          properties: %{
            team: %{type: "string", description: "Team name to search (matches home or away)"},
            home_team: %{type: "string", description: "Home team name filter"},
            away_team: %{type: "string", description: "Away team name filter"},
            competition: %{
              type: "string",
              enum: ["brasileirao", "copa_brasil", "libertadores", "extended", "historical"],
              description: "Competition to filter by"
            },
            season: %{type: "integer", description: "Season year (e.g. 2023)"},
            date_from: %{type: "string", description: "Start date filter (YYYY-MM-DD)"},
            date_to: %{type: "string", description: "End date filter (YYYY-MM-DD)"},
            limit: %{type: "integer", description: "Max results to return (default: 20)"}
          }
        }
      },
      %{
        name: "get_team_stats",
        description: """
        Get win/loss/draw statistics for a team, including goals scored and conceded,
        home vs away breakdown, and overall performance.
        """,
        inputSchema: %{
          type: "object",
          required: ["team"],
          properties: %{
            team: %{type: "string", description: "Team name"},
            competition: %{
              type: "string",
              enum: ["brasileirao", "copa_brasil", "libertadores", "extended", "historical"],
              description: "Filter by competition"
            },
            season: %{type: "integer", description: "Filter by season year"}
          }
        }
      },
      %{
        name: "head_to_head",
        description: """
        Get head-to-head match history and record between two teams across all competitions.
        Shows recent matches and win/draw/loss summary.
        """,
        inputSchema: %{
          type: "object",
          required: ["team1", "team2"],
          properties: %{
            team1: %{type: "string", description: "First team name"},
            team2: %{type: "string", description: "Second team name"},
            competition: %{
              type: "string",
              enum: ["brasileirao", "copa_brasil", "libertadores", "extended", "historical"],
              description: "Filter by competition"
            },
            season: %{type: "integer", description: "Filter by season year"}
          }
        }
      },
      %{
        name: "search_players",
        description: """
        Search FIFA player database. Find players by name, nationality, club, or position.
        Returns player ratings, positions, and club information. Dataset covers top players
        from around 2019.
        """,
        inputSchema: %{
          type: "object",
          properties: %{
            name: %{type: "string", description: "Player name (partial match)"},
            nationality: %{type: "string", description: "Player nationality (e.g. 'Brazil')"},
            club: %{type: "string", description: "Club name (partial match, e.g. 'Flamengo')"},
            position: %{type: "string", description: "Position (e.g. 'GK', 'ST', 'CM')"},
            limit: %{type: "integer", description: "Max results (default: 20)"}
          }
        }
      },
      %{
        name: "get_standings",
        description: """
        Calculate league standings for a given season based on match results.
        Shows points, wins, draws, losses, goals for/against.
        """,
        inputSchema: %{
          type: "object",
          required: ["season"],
          properties: %{
            season: %{type: "integer", description: "Season year (e.g. 2019)"},
            competition: %{
              type: "string",
              enum: ["brasileirao", "copa_brasil", "libertadores", "historical"],
              description: "Competition (default: brasileirao)"
            }
          }
        }
      },
      %{
        name: "get_biggest_wins",
        description: """
        Find the biggest victories (by goal difference) across all competitions or
        filtered by competition and/or season.
        """,
        inputSchema: %{
          type: "object",
          properties: %{
            competition: %{
              type: "string",
              enum: ["brasileirao", "copa_brasil", "libertadores", "extended", "historical"],
              description: "Filter by competition"
            },
            season: %{type: "integer", description: "Filter by season year"},
            limit: %{type: "integer", description: "Number of results (default: 10)"}
          }
        }
      },
      %{
        name: "get_summary_stats",
        description: """
        Get overall summary statistics: total matches, average goals per match,
        home/away win rates. Can be filtered by competition or season.
        """,
        inputSchema: %{
          type: "object",
          properties: %{
            competition: %{
              type: "string",
              enum: ["brasileirao", "copa_brasil", "libertadores", "extended", "historical"],
              description: "Filter by competition"
            },
            season: %{type: "integer", description: "Filter by season year"}
          }
        }
      }
    ]
  end

  def call_tool(name, params) do
    case name do
      "search_matches" -> QueryEngine.search_matches(params)
      "get_team_stats" -> QueryEngine.get_team_stats(params)
      "head_to_head" -> QueryEngine.head_to_head(params)
      "search_players" -> QueryEngine.search_players(params)
      "get_standings" -> QueryEngine.get_standings(params)
      "get_biggest_wins" -> QueryEngine.get_biggest_wins(params)
      "get_summary_stats" -> QueryEngine.get_summary_stats(params)
      _ -> {:error, "Unknown tool: #{name}"}
    end
  end
end
