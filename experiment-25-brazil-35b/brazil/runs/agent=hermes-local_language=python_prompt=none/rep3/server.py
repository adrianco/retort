# Brazilian Soccer MCP Server
# MCP (Model Context Protocol) server implementation that exposes soccer data tools.
# Connects to an LLM for natural language query processing.

import json
import logging
import sys
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.client.stdio import stdio_client
import mcp.types as types

from data_loader import MatchDataset, normalize_team_name
from knowledge_graph import KnowledgeGraph

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("brazilian-soccer-mcp")

# Initialize the MCP server
app = Server("brazilian-soccer-mcp")

# Global dataset and knowledge graph
dataset: Optional[MatchDataset] = None
knowledge_graph: Optional[KnowledgeGraph] = None


def initialize():
    """Initialize data loading and knowledge graph."""
    global dataset, knowledge_graph
    
    logger.info("Loading soccer data...")
    dataset = MatchDataset()
    dataset.load_all()
    
    logger.info(f"Loaded {len(dataset.all_matches)} matches")
    logger.info(f"Loaded {len(dataset.all_players)} players")
    logger.info(f"Found {len(dataset.all_teams)} unique teams")
    
    logger.info("Building knowledge graph...")
    knowledge_graph = KnowledgeGraph(dataset)
    stats = knowledge_graph.get_graph_statistics()
    logger.info(f"Knowledge graph: {stats['total_nodes']} nodes, {stats['total_edges']} edges")
    
    return True


def format_match_list(matches: List[Dict], max_show: int = 10) -> str:
    """Format a list of matches into a readable string."""
    if not matches:
        return "No matches found."
    
    lines = []
    for m in matches[:max_show]:
        date_str = m.get('date', 'Unknown')[:10] if m.get('date') else 'Unknown'
        comp = m.get('competition', '')
        round_str = f" - Round {m.get('round', '')}" if m.get('round') else ""
        stage_str = f" - {m.get('stage', '')}" if m.get('stage') else ""
        lines.append(f"  - {date_str}: {m['home_team']} {m['home_goals']}-{m['away_goals']} {m['away_team']} ({comp}{round_str}{stage_str})")
    
    total = len(matches)
    if total > max_show:
        lines.append(f"  ... and {total - max_show} more matches")
    
    return "\n".join(lines)


def format_head_to_head(result: Dict) -> str:
    """Format head-to-head comparison."""
    lines = [f"{result['team1']} vs {result['team2']}"]
    lines.append(f"Total matches: {result['total_matches']}")
    lines.append(f"  {result['team1']}: {result['team1_wins']} wins")
    lines.append(f"  {result['team2']}: {result['team2_wins']} wins")
    lines.append(f"  Draws: {result['draws']}")
    return "\n".join(lines)


def format_team_stats(result: Dict) -> str:
    """Format team statistics."""
    return (f"Team: {result['team']}\n"
            f"  Matches: {result['matches']}\n"
            f"  Wins: {result['wins']}, Draws: {result['draws']}, Losses: {result['losses']}\n"
            f"  Goals For: {result['goals_for']}, Goals Against: {result['goals_against']}\n"
            f"  Win Rate: {result['win_rate']}%")


def format_player_list(players: List[Dict], max_show: int = 10) -> str:
    """Format a list of players."""
    if not players:
        return "No players found."
    
    lines = []
    for i, p in enumerate(players[:max_show], 1):
        lines.append(f"  {i}. {p['name']} - Overall: {p['overall']}, Age: {p['age']}, "
                     f"Position: {p['position']}, Club: {p['club']}, Nationality: {p['nationality']}")
    
    if len(players) > max_show:
        lines.append(f"  ... and {len(players) - max_show} more players")
    
    return "\n".join(lines)


def format_standings(standings: List[Dict], season: int, competition: str) -> str:
    """Format season standings."""
    lines = [f"{season} {competition} Final Standings:"]
    for i, s in enumerate(standings[:20], 1):
        champion = " - Champion" if i == 1 else ""
        lines.append(f"  {i}. {s['team']} - {s['points']} pts ({s['wins']}W, {s['draws']}D, {s['losses']}L){champion}")
    return "\n".join(lines)


def format_average_goals(result: Dict) -> str:
    """Format average goals statistics."""
    return (f"Average Goals Per Match: {result['average_goals_per_match']}\n"
            f"  Total Matches: {result['total_matches']}\n"
            f"  Total Goals: {result['total_goals']}\n"
            f"  Home Win Rate: {result['home_win_rate']}%\n"
            f"  Away Win Rate: {result['away_win_rate']}%\n"
            f"  Draw Rate: {result['draw_rate']}%")


def format_top_scoring(matches: List[Dict]) -> str:
    """Format top scoring matches."""
    lines = ["Biggest victories in dataset:"]
    for i, m in enumerate(matches[:10], 1):
        date_str = m.get('date', 'Unknown')[:10] if m.get('date') else 'Unknown'
        lines.append(f"  {i}. {date_str}: {m['home_team']} {m['home_goals']}-{m['away_goals']} {m['away_team']} ({m['competition']})")
    return "\n".join(lines)


@app.tool()
def search_matches(
    team: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> Dict[str, Any]:
    """Search for matches by various criteria. Returns all matching matches with date, scores, and competition info."""
    try:
        matches = dataset.get_match_by_criteria(
            team=team,
            date_from=date_from,
            date_to=date_to,
            competition=competition,
            season=season,
        )
        
        # Calculate head-to-head if team specified
        extra = {}
        if team:
            team_stats = dataset.get_team_statistics(team)
            extra['team_statistics'] = team_stats
        
        return {
            'success': True,
            'message': f"Found {len(matches)} matches",
            'data': {
                'matches': matches,
                'count': len(matches),
                **extra,
            }
        }
    except Exception as e:
        logger.error(f"Error searching matches: {e}")
        return {'success': False, 'message': str(e), 'data': {}, 'errors': [str(e)]}


@app.tool()
def get_team_stats(
    team: str,
    competition: Optional[str] = None,
) -> Dict[str, Any]:
    """Get detailed team statistics including wins, losses, draws, and goals."""
    try:
        stats = dataset.get_team_statistics(team, competition=competition)
        return {
            'success': True,
            'message': format_team_stats(stats),
            'data': stats,
        }
    except Exception as e:
        logger.error(f"Error getting team stats: {e}")
        return {'success': False, 'message': str(e), 'data': {}, 'errors': [str(e)]}


@app.tool()
def get_head_to_head(
    team1: str,
    team2: str,
    competition: Optional[str] = None,
) -> Dict[str, Any]:
    """Get head-to-head comparison between two teams."""
    try:
        result = dataset.get_head_to_head(team1, team2, competition=competition)
        return {
            'success': True,
            'message': format_head_to_head(result),
            'data': result,
        }
    except Exception as e:
        logger.error(f"Error getting head-to-head: {e}")
        return {'success': False, 'message': str(e), 'data': {}, 'errors': [str(e)]}


@app.tool()
def search_players(
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    max_results: int = 20,
) -> Dict[str, Any]:
    """Search FIFA player database by nationality, club, position, or rating."""
    try:
        players = dataset.get_players_by_filter(
            nationality=nationality,
            club=club,
            position=position,
            min_overall=min_overall,
            max_results=max_results,
        )
        return {
            'success': True,
            'message': f"Found {len(players)} players matching criteria",
            'data': {
                'players': players,
                'count': len(players),
            }
        }
    except Exception as e:
        logger.error(f"Error searching players: {e}")
        return {'success': False, 'message': str(e), 'data': {}, 'errors': [str(e)]}


@app.tool()
def get_season_standings(
    season: int,
    competition: str = "Brasileirao",
) -> Dict[str, Any]:
    """Calculate and return season standings based on match results."""
    try:
        standings = dataset.get_standings_by_season(season, competition=competition)
        return {
            'success': True,
            'message': format_standings(standings, season, competition),
            'data': {
                'season': season,
                'competition': competition,
                'standings': standings,
            }
        }
    except Exception as e:
        logger.error(f"Error getting standings: {e}")
        return {'success': False, 'message': str(e), 'data': {}, 'errors': [str(e)]}


@app.tool()
def get_average_goals() -> Dict[str, Any]:
    """Calculate average goals per match across all datasets."""
    try:
        result = dataset.get_average_goals_per_match()
        return {
            'success': True,
            'message': format_average_goals(result),
            'data': result,
        }
    except Exception as e:
        logger.error(f"Error calculating average goals: {e}")
        return {'success': False, 'message': str(e), 'data': {}, 'errors': [str(e)]}


@app.tool()
def get_top_scoring_matches(
    limit: int = 20,
) -> Dict[str, Any]:
    """Find matches with the highest total goals."""
    try:
        matches = dataset.get_top_scorers_per_match()
        return {
            'success': True,
            'message': format_top_scoring(matches),
            'data': {
                'matches': matches[:limit],
                'count': len(matches),
            }
        }
    except Exception as e:
        logger.error(f"Error getting top scoring matches: {e}")
        return {'success': False, 'message': str(e), 'data': {}, 'errors': [str(e)]}


@app.tool()
def get_graph_stats() -> Dict[str, Any]:
    """Get statistics about the knowledge graph."""
    try:
        stats = knowledge_graph.get_graph_statistics()
        return {
            'success': True,
            'message': f"Knowledge graph: {json.dumps(stats, indent=2)}",
            'data': stats,
        }
    except Exception as e:
        logger.error(f"Error getting graph stats: {e}")
        return {'success': False, 'message': str(e), 'data': {}, 'errors': [str(e)]}


@app.tool()
def find_team_connections(
    team: str,
) -> Dict[str, Any]:
    """Find teams connected to a given team via shared competitions."""
    try:
        competitors = knowledge_graph.get_connected_teams(team)
        return {
            'success': True,
            'message': f"Teams connected to {team} via competitions: {len(competitors)}",
            'data': {
                'team': team,
                'competitors': competitors,
            }
        }
    except Exception as e:
        logger.error(f"Error finding team connections: {e}")
        return {'success': False, 'message': str(e), 'data': {}, 'errors': [str(e)]}


@app.tool()
def get_health_check() -> Dict[str, Any]:
    """Check server health and data status."""
    try:
        if dataset is None:
            return {
                'success': False,
                'message': 'Data not loaded. Call initialize() first.',
                'data': {},
            }
        
        stats = {
            'status': 'healthy',
            'datasets_loaded': True,
            'total_matches': len(dataset.all_matches),
            'total_players': len(dataset.all_players),
            'teams_count': len(dataset.all_teams),
            'data_sources': {
                'Brasileirao': len(dataset.brasileirao),
                'Copa do Brasil': len(dataset.copa_brasil),
                'Libertadores': len(dataset.libertadores),
                'Extended Stats': len(dataset.extended_stats),
                'Historic': len(dataset.historic),
            }
        }
        return {
            'success': True,
            'message': 'Server is healthy',
            'data': stats,
        }
    except Exception as e:
        return {
            'success': False,
            'message': str(e),
            'data': {},
            'errors': [str(e)],
        }


@app.tool()
def find_path_between_teams(
    team1: str,
    team2: str,
    max_depth: int = 3,
) -> Dict[str, Any]:
    """Find connection paths between two teams in the knowledge graph."""
    try:
        paths = knowledge_graph.find_path_between_teams(team1, team2, max_depth=max_depth)
        return {
            'success': True,
            'message': f"Found {len(paths)} path(s) between {team1} and {team2}",
            'data': {
                'team1': team1,
                'team2': team2,
                'paths': paths,
            }
        }
    except Exception as e:
        logger.error(f"Error finding path: {e}")
        return {'success': False, 'message': str(e), 'data': {}, 'errors': [str(e)]}


@app.tool()
def get_common_opponents(
    team1: str,
    team2: str,
) -> Dict[str, Any]:
    """Find teams both teams have played against."""
    try:
        opponents = knowledge_graph.get_common_opponents(team1, team2)
        return {
            'success': True,
            'message': f"Common opponents of {team1} and {team2}: {len(opponents)}",
            'data': {
                'team1': team1,
                'team2': team2,
                'common_opponents': opponents,
            }
        }
    except Exception as e:
        logger.error(f"Error finding common opponents: {e}")
        return {'success': False, 'message': str(e), 'data': {}, 'errors': [str(e)]}


async def main():
    """Main entry point for the MCP server."""
    import mcp.server.stdio
    
    await initialize()
    
    logger.info("Starting Brazilian Soccer MCP Server...")
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
