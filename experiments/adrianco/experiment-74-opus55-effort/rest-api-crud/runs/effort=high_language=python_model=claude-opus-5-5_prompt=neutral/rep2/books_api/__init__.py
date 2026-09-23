"""Book collection REST API built on the Python standard library."""

from .server import create_server
from .store import BookStore

__all__ = ["BookStore", "create_server"]
