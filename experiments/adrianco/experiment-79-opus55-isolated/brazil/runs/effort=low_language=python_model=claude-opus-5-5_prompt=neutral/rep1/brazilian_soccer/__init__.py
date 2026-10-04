"""Brazilian soccer knowledge base and MCP server built on the bundled Kaggle CSVs."""

from .service import QueryError, SoccerData, load_default

__all__ = ["QueryError", "SoccerData", "load_default"]
