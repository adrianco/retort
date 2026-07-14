"""
MCP Server for Brazilian Soccer Knowledge Graph.
Provides tools for querying match data, team stats, player data, and competitions.
"""

import asyncio
import json
import pandas as pd

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from repository import SoccerRepository


def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("brazilian-soccer-mcp")

    # Initialize repository
    repo = SoccerRepository()

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="search_matches",
                description="Search for soccer matches by team, date, competition, or season",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team": {
                            "type": "string",
                            "description": "Team name (matches as home or away)"
                        },
                        "home_team": {
                            "type": "string",
                            "description": "Home team name"
                        },
                        "away_team": {
                            "type": "string",
                            "description": "Away team name"
                        },
                        "date_from": {
                            "type": "string",
                            "description": "Start date (ISO format YYYY-MM-DD)"
                        },
                        "date_to": {
                            "type": "string",
                            "description": "End date (ISO format YYYY-MM-DD)"
                        },
                        "competition": {
                            "type": "string",
                            "description": "Competition name (e.g., 'Brasileirao Serie A', 'Copa do Brasil', 'Copa Libertadores')"
                        },
                        "season": {
                            "type": "string",
                            "description": "Season year"
                        },
                        "round": {
                            "type": "string",
                            "description": "Round number"
                        },
                        "stage": {
                            "type": "string",
                            "description": "Tournament stage (e.g., 'Final', 'Semi-Final', 'group stage')"
                        },
                        "min_score": {
                            "type": "integer",
                            "description": "Minimum total goals in the match"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 100
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="get_team_stats",
                description="Get team statistics including wins, losses, draws, and goals",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team": {
                            "type": "string",
                            "description": "Team name"
                        },
                        "season": {
                            "type": "string",
                            "description": "Season year"
                        },
                        "competition": {
                            "type": "string",
                            "description": "Competition name"
                        }
                    },
                    "required": ["team"]
                }
            ),
            Tool(
                name="get_head_to_head",
                description="Get head-to-head statistics between two teams",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team1": {
                            "type": "string",
                            "description": "First team name"
                        },
                        "team2": {
                            "type": "string",
                            "description": "Second team name"
                        }
                    },
                    "required": ["team1", "team2"]
                }
            ),
            Tool(
                name="search_players",
                description="Search FIFA player database by name, nationality, club, or position",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Player name (partial match)"
                        },
                        "nationality": {
                            "type": "string",
                            "description": "Nationality"
                        },
                        "club": {
                            "type": "string",
                            "description": "Club name"
                        },
                        "position": {
                            "type": "string",
                            "description": "Position (e.g., 'ST', 'GK', 'CAM')"
                        },
                        "min_overall": {
                            "type": "integer",
                            "description": "Minimum overall rating"
                        },
                        "max_overall": {
                            "type": "integer",
                            "description": "Maximum overall rating"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 50
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="get_league_standings",
                description="Calculate league standings from match results",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "season": {
                            "type": "string",
                            "description": "Season year"
                        },
                        "competition": {
                            "type": "string",
                            "description": "Competition name"
                        }
                    },
                    "required": ["season"]
                }
            ),
            Tool(
                name="get_biggest_wins",
                description="Find the biggest wins/margins in the dataset",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "competition": {
                            "type": "string",
                            "description": "Competition name (optional)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="get_average_goals",
                description="Calculate average goals per match and win/draw rates",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "competition": {
                            "type": "string",
                            "description": "Competition name"
                        },
                        "season": {
                            "type": "string",
                            "description": "Season year"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="get_competitions",
                description="Get list of all competitions in the dataset",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="get_all_teams",
                description="Get list of all unique teams in the dataset",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="get_top_scorers",
                description="Get top scoring teams for a season (player-level data not available)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "season": {
                            "type": "string",
                            "description": "Season year"
                        },
                        "competition": {
                            "type": "string",
                            "description": "Competition name"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10
                        }
                    },
                    "required": []
                }
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Handle tool calls."""
        try:
            # Search matches
            if name == "search_matches":
                result = repo.search_matches(
                    team=arguments.get("team"),
                    home_team=arguments.get("home_team"),
                    away_team=arguments.get("away_team"),
                    date_from=arguments.get("date_from"),
                    date_to=arguments.get("date_to"),
                    competition=arguments.get("competition"),
                    season=arguments.get("season"),
                    round_num=arguments.get("round"),
                    stage=arguments.get("stage"),
                    min_score=arguments.get("min_score"),
                    limit=arguments.get("limit", 100)
                )
                if len(result) == 0:
                    return [TextContent(type="text", text="No matches found for the specified criteria.")]

                # Format results
                output = []
                for _, row in result.iterrows():
                    date = row.get('date', 'N/A')
                    ht = row.get('home_team', 'Unknown')
                    at = row.get('away_team', 'Unknown')
                    hg = int(row['home_goal']) if pd.notna(row.get('home_goal')) else '-'
                    ag = int(row['away_goal']) if pd.notna(row.get('away_goal')) else '-'
                    comp = row.get('competition', 'Unknown')
                    season = row.get('season', 'Unknown')
                    rnd = row.get('round', '')

                    rnd_str = f" Round {rnd}" if rnd and str(rnd) != 'nan' else ""
                    output.append(f"{date}: {ht} {hg}-{ag} {at} ({comp} {season}{rnd_str})")

                return [TextContent(
                    type="text",
                    text=f"Found {len(result)} matches:\n" + "\n".join(output)
                )]

            # Get team stats
            elif name == "get_team_stats":
                stats = repo.get_team_stats(
                    team=arguments["team"],
                    season=arguments.get("season"),
                    competition=arguments.get("competition"),
                )
                return [TextContent(type="text", text=json.dumps(stats, indent=2))]

            # Get head-to-head
            elif name == "get_head_to_head":
                h2h = repo.get_head_to_head(
                    team1=arguments["team1"],
                    team2=arguments["team2"],
                )
                return [TextContent(type="text", text=json.dumps(h2h, indent=2))]

            # Search players
            elif name == "search_players":
                result = repo.search_players(
                    name=arguments.get("name"),
                    nationality=arguments.get("nationality"),
                    club=arguments.get("club"),
                    position=arguments.get("position"),
                    min_overall=arguments.get("min_overall"),
                    max_overall=arguments.get("max_overall"),
                    limit=arguments.get("limit", 50)
                )
                if len(result) == 0:
                    return [TextContent(type="text", text="No players found for the specified criteria.")]

                output = []
                for _, row in result.iterrows():
                    output.append(
                        f"{row['Name']} - Overall: {row['Overall']}, "
                        f"Position: {row['Position']}, "
                        f"Club: {row['Club']}"
                    )
                return [TextContent(
                    type="text",
                    text=f"Found {len(result)} players:\n" + "\n".join(output)
                )]

            # Get league standings
            elif name == "get_league_standings":
                standings = repo.get_league_standings(
                    season=arguments["season"],
                    competition=arguments.get("competition"),
                )
                if len(standings) == 0:
                    return [TextContent(type="text", text="No standings found for the specified season/competition.")]

                output = []
                for _, row in standings.iterrows():
                    pos = row['position']
                    team = row['team']
                    pts = row['points']
                    w = row['wins']
                    d = row['draws']
                    l = row['losses']
                    gf = row['goals_for']
                    ga = row['goals_against']
                    gd = row['goal_difference']
                    output.append(
                        f"{pos}. {team} - {pts} pts ({w}W, {d}D, {l}L, GF={gf}, GA={ga}, GD={gd})"
                    )
                return [TextContent(
                    type="text",
                    text="League Standings:\n" + "\n".join(output)
                )]

            # Get biggest wins
            elif name == "get_biggest_wins":
                result = repo.get_biggest_wins(
                    limit=arguments.get("limit", 10),
                    competition=arguments.get("competition"),
                )
                if len(result) == 0:
                    return [TextContent(type="text", text="No matches found.")]

                output = []
                for i, (_, row) in enumerate(result.iterrows(), 1):
                    date = row.get('date', 'N/A')
                    ht = row.get('home_team', 'Unknown')
                    at = row.get('away_team', 'Unknown')
                    hg = int(row['home_goal']) if pd.notna(row.get('home_goal')) else '-'
                    ag = int(row['away_goal']) if pd.notna(row.get('away_goal')) else '-'
                    comp = row.get('competition', 'Unknown')
                    output.append(
                        f"{i}. {date}: {ht} {hg}-{ag} {at} ({comp})"
                    )
                return [TextContent(
                    type="text",
                    text="Biggest wins:\n" + "\n".join(output)
                )]

            # Get average goals
            elif name == "get_average_goals":
                stats = repo.get_average_goals(
                    competition=arguments.get("competition"),
                    season=arguments.get("season"),
                )
                return [TextContent(
                    type="text",
                    text=json.dumps(stats, indent=2)
                )]

            # Get competitions
            elif name == "get_competitions":
                comps = repo.get_competitions()
                return [TextContent(
                    type="text",
                    text="Competitions:\n" + "\n".join(f"- {c}" for c in comps)
                )]

            # Get all teams
            elif name == "get_all_teams":
                teams = repo.get_all_teams()
                return [TextContent(
                    type="text",
                    text=f"Total teams: {len(teams)}\n\n" + "\n".join(f"- {t}" for t in teams)
                )]

            # Get top scorers
            elif name == "get_top_scorers":
                scorers = repo.get_top_scorers(
                    season=arguments.get("season"),
                    competition=arguments.get("competition"),
                    limit=arguments.get("limit", 10)
                )
                if len(scorers) == 0:
                    return [TextContent(type="text", text="No data found.")]

                output = []
                for i, (team, goals) in enumerate(scorers.items(), 1):
                    output.append(f"{i}. {team}: {int(goals)} goals")
                return [TextContent(
                    type="text",
                    text="Top scoring teams:\n" + "\n".join(output)
                )]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    return server


async def _run_server():
    """Run the MCP server using stdio transport."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream=read_stream,
            write_stream=write_stream,
            initialization_options=server.create_initialization_options(),
        )


def main():
    """Main entry point for the MCP server."""
    asyncio.run(_run_server())


if __name__ == "__main__":
    main()
