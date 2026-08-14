"""Brazilian soccer dataset query service and MCP server."""

from .repository import SoccerCatalog
from .service import SoccerQueryService

__all__ = ["SoccerCatalog", "SoccerQueryService"]

