"""Brazilian Soccer MCP server package."""

from .data_loader import DataStore, load_all
from .queries import SoccerQueries

__all__ = ["DataStore", "load_all", "SoccerQueries"]
