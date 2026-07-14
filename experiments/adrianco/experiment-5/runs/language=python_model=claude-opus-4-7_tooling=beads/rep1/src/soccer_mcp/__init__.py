"""Brazilian Soccer MCP package.

Exposes data access, query, and analysis helpers over the Kaggle Brazilian
soccer datasets shipped in ``data/kaggle/``. The MCP server in
``soccer_mcp.server`` wraps these helpers as MCP tools.
"""
from soccer_mcp.data_loader import DataStore, load_default_store
from soccer_mcp.normalizer import normalize_team

__all__ = ["DataStore", "load_default_store", "normalize_team"]
__version__ = "0.1.0"
