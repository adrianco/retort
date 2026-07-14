"""Brazilian Soccer MCP server package."""

from .data_loader import DataStore, default_data_dir, load_all
from .normalize import normalize_team_name

__all__ = ["DataStore", "default_data_dir", "load_all", "normalize_team_name"]
