"""Shared pytest fixtures.

Every test gets a throw-away SQLite file, so tests are fully isolated and the
developer's ``books.db`` is never touched.
"""

from __future__ import annotations

import sqlite3
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

import database
from main import app


@pytest.fixture()
def db_path(tmp_path, monkeypatch) -> str:
    """Point the app at a temporary database file for the duration of a test."""
    path = str(tmp_path / "test_books.db")
    monkeypatch.setenv("BOOKS_DB_PATH", path)
    return path


@pytest.fixture()
def client(db_path: str) -> Iterator[TestClient]:
    """A TestClient whose lifespan has run (so the schema exists)."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def conn(db_path: str) -> Iterator[sqlite3.Connection]:
    """A direct connection to an initialised temporary database."""
    database.init_db(db_path)
    with database.get_connection(db_path) as connection:
        yield connection


@pytest.fixture()
def sample_book() -> dict:
    return {
        "title": "The Left Hand of Darkness",
        "author": "Ursula K. Le Guin",
        "year": 1969,
        "isbn": "978-0-441-47812-5",
    }


def create(client: TestClient, **overrides) -> dict:
    """Create a book through the API and return the created resource."""
    payload = {"title": "A Book", "author": "An Author"}
    payload.update(overrides)
    response = client.post("/books", json=payload)
    assert response.status_code == 201, response.text
    return response.json()
