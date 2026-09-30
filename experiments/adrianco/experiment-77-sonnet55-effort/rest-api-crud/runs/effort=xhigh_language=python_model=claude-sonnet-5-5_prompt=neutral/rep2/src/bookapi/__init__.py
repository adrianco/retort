"""Book collection REST API."""

from .app import BookApp
from .db import BookStore

__all__ = ["BookApp", "BookStore"]
