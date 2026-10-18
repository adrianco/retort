"""Brazilian soccer MCP server: natural-language-friendly queries over Kaggle CSVs."""

from .dataset import Dataset
from .server import serve

__all__ = ["Dataset", "serve"]
