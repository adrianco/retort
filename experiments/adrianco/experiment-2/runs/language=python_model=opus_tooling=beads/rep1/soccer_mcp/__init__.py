"""Brazilian Soccer MCP server package."""
from .data_loader import load_all, DATA_DIR
from .query import QueryEngine

__all__ = ["load_all", "QueryEngine", "DATA_DIR"]
