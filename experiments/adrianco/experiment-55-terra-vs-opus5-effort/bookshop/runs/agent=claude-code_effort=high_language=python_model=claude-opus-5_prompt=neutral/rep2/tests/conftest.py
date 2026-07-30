"""Shared pytest fixtures: every test gets a throwaway SQLite file."""

from __future__ import annotations

import pytest

from app import create_app


@pytest.fixture()
def db_path(tmp_path):
    return str(tmp_path / "books.db")


@pytest.fixture()
def app(db_path):
    application = create_app(database_path=db_path)
    application.config.update(TESTING=True)
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def sample_book():
    return {
        "title": "The Left Hand of Darkness",
        "author": "Ursula K. Le Guin",
        "year": 1969,
        "isbn": "978-0-441-47812-5",
    }
