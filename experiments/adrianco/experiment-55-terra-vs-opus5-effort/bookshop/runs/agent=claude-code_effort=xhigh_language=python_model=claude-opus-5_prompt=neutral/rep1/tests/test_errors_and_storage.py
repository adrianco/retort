"""Framework-level error responses, and that SQLite really persists the data."""

from __future__ import annotations

import sqlite3

from bookapi import create_app
from conftest import ORWELL


def test_unknown_route_returns_json_404(client):
    response = client.get("/nope")

    assert response.status_code == 404
    assert response.mimetype == "application/json"
    assert response.get_json()["error"] == "not_found"


def test_wrong_method_returns_json_405_with_allow_header(client):
    response = client.delete("/books")

    assert response.status_code == 405
    assert response.mimetype == "application/json"
    assert response.get_json()["error"] == "method_not_allowed"
    assert "GET" in response.headers["Allow"]


def test_non_numeric_id_returns_404(client):
    assert client.get("/books/not-a-number").status_code == 404


def test_unexpected_errors_become_json_500(app, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setattr("bookapi.routes.repository.list_books", boom)
    # Let the handler run instead of re-raising into the test client.
    app.config["PROPAGATE_EXCEPTIONS"] = False

    response = app.test_client().get("/books")

    assert response.status_code == 500
    assert response.get_json()["error"] == "internal_server_error"
    assert "kaboom" not in response.get_json()["message"]


def test_books_persist_across_application_restarts(db_path):
    first_app = create_app({"TESTING": True, "DATABASE": str(db_path)})
    created = first_app.test_client().post("/books", json=ORWELL).get_json()

    # A brand new app object, same database file on disk.
    second_app = create_app({"TESTING": True, "DATABASE": str(db_path)})
    response = second_app.test_client().get(f"/books/{created['id']}")

    assert response.status_code == 200
    assert response.get_json() == created


def test_rows_land_in_the_books_table(client, db_path, create_book):
    created = create_book()

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT title, author, year, isbn FROM books WHERE id = ?",
            (created["id"],),
        ).fetchone()
    finally:
        conn.close()

    assert row == (ORWELL["title"], ORWELL["author"], ORWELL["year"], ORWELL["isbn"])


def test_init_db_is_idempotent(db_path):
    create_app({"DATABASE": str(db_path)})
    app = create_app({"DATABASE": str(db_path)})

    assert app.test_client().get("/health").status_code == 200


def test_database_path_can_come_from_the_environment(tmp_path, monkeypatch):
    target = tmp_path / "nested" / "from-env.db"
    monkeypatch.setenv("BOOK_API_DATABASE", str(target))

    app = create_app()
    app.test_client().post("/books", json=ORWELL)

    assert target.exists()


def test_init_db_cli_command(app, db_path):
    db_path.unlink()

    result = app.test_cli_runner().invoke(args=["init-db"])

    assert result.exit_code == 0
    assert db_path.exists()
