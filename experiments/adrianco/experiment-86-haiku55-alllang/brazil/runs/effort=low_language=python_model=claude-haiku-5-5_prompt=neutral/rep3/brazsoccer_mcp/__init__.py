"""Brazilian soccer knowledge MCP server.

Loads the Kaggle match and FIFA player datasets into memory and exposes
query tools over the Model Context Protocol (stdio transport).
"""

from .store import QueryError, SoccerData

__all__ = ["QueryError", "SoccerData"]
