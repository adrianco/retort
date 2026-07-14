"""
Brazilian Soccer MCP Server package.

A knowledge-graph style query layer over six bundled Kaggle datasets covering
Brazilian soccer matches (Brasileirão, Copa do Brasil, Libertadores) and FIFA
player attributes, exposed both as a Python API (`queries`) and as an MCP server
(`server`).
"""

from .data_loader import get_data, load_data, SoccerData, Match, Player

__all__ = ["get_data", "load_data", "SoccerData", "Match", "Player"]
__version__ = "1.0.0"
