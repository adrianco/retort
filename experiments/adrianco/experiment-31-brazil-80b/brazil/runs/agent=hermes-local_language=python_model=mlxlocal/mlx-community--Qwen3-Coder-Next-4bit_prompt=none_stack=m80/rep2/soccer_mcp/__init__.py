# Brazilian Soccer MCP Server
"""
MCP (Model Context Protocol) Server for Brazilian Soccer Data
Provides natural language queries about players, teams, matches, and competitions.
"""

__version__ = "1.0.0"
__author__ = "Brazilian Soccer MCP Team"

from .server import SoccerMCPServer

__all__ = ["SoccerMCPServer"]
