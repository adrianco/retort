"""Tests for the SQLite layer: persistence, configuration and the repository API."""

from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from bookapi import db, repository
from bookapi.app import create_app


def test_data_survives_a_restart(db_path):
    with TestClient(create_app(db_path)) as first:
        created = first.post("/books", json={"title": "Dune", "author": "Frank Herbert"}).json()

    with TestClient(create_app(db_path)) as second:  # fresh app, same file
        response = second.get(f"/books/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_rows_are_written_to_sqlite(client, make_book, db_path):
    created = make_book(title="Dune", isbn="9780441013593")

    with db.connect(db_path) as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (created["id"],)).fetchone()

    assert row["title"] == "Dune"
    assert row["isbn"] == "9780441013593"


def test_db_path_can_come_from_the_environment(tmp_path, monkeypatch):
    configured = tmp_path / "from-env.db"
    monkeypatch.setenv("BOOKS_DB_PATH", str(configured))

    app = create_app()

    assert app.state.db_path == str(configured)
    assert configured.exists()


def test_init_db_creates_missing_parent_directories(tmp_path):
    nested = tmp_path / "data" / "nested" / "books.db"

    db.init_db(nested)

    assert nested.exists()


def test_init_db_is_idempotent(db_path):
    db.init_db(db_path)
    db.init_db(db_path)

    with db.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0


@pytest.fixture()
def conn(db_path):
    db.init_db(db_path)
    connection = db.connect(db_path)
    yield connection
    connection.close()


def test_repository_round_trip(conn):
    created = repository.create(conn, {"title": "Dune", "author": "FH", "year": 1965})

    assert repository.get(conn, created["id"]) == created
    assert repository.list_books(conn) == [created]

    replaced = repository.replace(conn, created["id"], {"title": "Dune 2", "author": "FH"})
    assert replaced["title"] == "Dune 2"
    assert replaced["year"] is None

    assert repository.delete(conn, created["id"]) is True
    assert repository.get(conn, created["id"]) is None
    assert repository.delete(conn, created["id"]) is False


def test_repository_replace_returns_none_for_unknown_id(conn):
    assert repository.replace(conn, 999, {"title": "T", "author": "A"}) is None


def test_repository_raises_on_duplicate_isbn(conn):
    repository.create(conn, {"title": "Dune", "author": "FH", "isbn": "9780441013593"})

    with pytest.raises(repository.DuplicateIsbnError):
        repository.create(conn, {"title": "Other", "author": "FH", "isbn": "9780441013593"})


def test_repository_propagates_other_integrity_errors(conn):
    # NOT NULL on title: not an ISBN clash, so it must not be disguised as one.
    with pytest.raises(sqlite3.IntegrityError) as excinfo:
        repository.create(conn, {"title": None, "author": "FH"})

    assert not isinstance(excinfo.value, repository.DuplicateIsbnError)
