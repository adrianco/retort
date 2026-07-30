"""Tests covering the SQLite storage layer itself."""

from __future__ import annotations

import sqlite3

from bookapi import create_app


def test_data_survives_an_application_restart(tmp_path):
    """A second app instance on the same file sees the first one's writes."""
    database = str(tmp_path / "books.db")

    first = create_app({"DATABASE": database, "TESTING": True})
    created = first.test_client().post(
        "/books", json={"title": "Persisted", "author": "Someone", "year": 1999}
    ).get_json()

    second = create_app({"DATABASE": database, "TESTING": True})
    fetched = second.test_client().get(f"/books/{created['id']}")

    assert fetched.status_code == 200
    assert fetched.get_json()["title"] == "Persisted"


def test_schema_creation_is_idempotent(tmp_path):
    database = str(tmp_path / "books.db")
    create_app({"DATABASE": database})
    create_app({"DATABASE": database})

    app = create_app({"DATABASE": database})
    assert app.test_client().get("/health").status_code == 200


def test_rows_are_written_with_timestamps(tmp_path):
    database = str(tmp_path / "books.db")
    app = create_app({"DATABASE": database, "TESTING": True})
    app.test_client().post("/books", json={"title": "T", "author": "A"})

    with sqlite3.connect(database) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM books").fetchone()

    assert row["title"] == "T"
    assert row["created_at"].endswith("Z")
    assert row["updated_at"].endswith("Z")


def test_updated_at_advances_on_write(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "books.db"), "TESTING": True})
    client = app.test_client()

    created = client.post("/books", json={"title": "T", "author": "A"}).get_json()
    updated = client.put(
        f"/books/{created['id']}", json={"title": "T2", "author": "A"}
    ).get_json()

    assert updated["created_at"] == created["created_at"]
    assert updated["updated_at"] >= created["updated_at"]


def test_health_reports_503_when_the_table_is_missing(tmp_path):
    """Simulate a corrupted/incomplete database to prove health really checks."""
    database = str(tmp_path / "books.db")
    app = create_app({"DATABASE": database, "TESTING": True})

    with sqlite3.connect(database) as conn:
        conn.execute("DROP TABLE books")

    response = app.test_client().get("/health")
    assert response.status_code == 503
    assert response.get_json()["status"] == "error"


def test_title_is_stored_verbatim_and_not_interpreted_as_sql(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "books.db"), "TESTING": True})
    client = app.test_client()

    nasty = "Robert'); DROP TABLE books;--"
    created = client.post("/books", json={"title": nasty, "author": "A"}).get_json()

    assert created["title"] == nasty
    assert client.get("/health").status_code == 200
    assert client.get(f"/books/{created['id']}").get_json()["title"] == nasty
