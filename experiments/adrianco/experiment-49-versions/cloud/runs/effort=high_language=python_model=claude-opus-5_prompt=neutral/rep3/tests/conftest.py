from __future__ import annotations

import pytest

from bookapi import create_app

# Real ISBNs, so the check-digit validation is exercised with valid input.
ORWELL = {"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "9780451524935"}
HUXLEY = {
    "title": "Brave New World",
    "author": "Aldous Huxley",
    "year": 1932,
    "isbn": "0-06-085052-3",
}


@pytest.fixture
def app(tmp_path):
    """An app backed by a throwaway SQLite file, fresh for every test."""
    return create_app(database=str(tmp_path / "test.db"))


@pytest.fixture
def client(app):
    return app.test_client()
