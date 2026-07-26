"""Tests that data really lands in SQLite rather than in process memory."""

from __future__ import annotations

import sqlite3

from bookapi import create_app


def test_books_survive_a_restart(client, db_path, add_book):
    created = add_book(title="Persisted")

    # A brand new application object, pointed at the same file, as if the
    # process had been restarted.
    restarted = create_app({"TESTING": True, "DATABASE": db_path})

    response = restarted.test_client().get(f"/books/{created['id']}")

    assert response.status_code == 200
    assert response.get_json() == created


def test_rows_are_written_to_the_books_table(client, db_path, add_book):
    add_book(title="Nineteen Eighty-Four", author="George Orwell", year=1949)

    connection = sqlite3.connect(db_path)
    try:
        row = connection.execute(
            "SELECT title, author, year FROM books"
        ).fetchone()
    finally:
        connection.close()

    assert row == ("Nineteen Eighty-Four", "George Orwell", 1949)


def test_deletes_are_committed(client, db_path, add_book):
    created = add_book()

    client.delete(f"/books/{created['id']}")

    connection = sqlite3.connect(db_path)
    try:
        count = connection.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    finally:
        connection.close()

    assert count == 0


def test_creating_the_app_twice_does_not_wipe_existing_data(client, db_path, add_book):
    """Schema setup is idempotent, so restarts are safe."""
    add_book()

    create_app({"TESTING": True, "DATABASE": db_path})
    create_app({"TESTING": True, "DATABASE": db_path})

    assert len(client.get("/books").get_json()) == 1


def test_ids_are_not_reused_after_a_delete(client, add_book):
    first = add_book()
    client.delete(f"/books/{first['id']}")

    second = add_book()

    assert second["id"] != first["id"]
