"""Storage behaviour: durability, isolation and concurrent access."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from bookapi import create_app
from bookapi.db import BUSY_TIMEOUT_SECONDS, get_db

from .samples import SAMPLE_BOOKS


def test_data_survives_a_restart(tmp_path):
    database = str(tmp_path / "books.db")

    first = create_app({"DATABASE": database, "TESTING": True})
    created = first.test_client().post("/books", json=SAMPLE_BOOKS[0]).get_json()

    # A brand-new application object, same file on disk.
    second = create_app({"DATABASE": database, "TESTING": True})
    reloaded = second.test_client().get(f"/books/{created['id']}")

    assert reloaded.status_code == 200
    assert reloaded.get_json() == created


def test_schema_bootstrapping_is_idempotent(tmp_path):
    database = str(tmp_path / "books.db")

    for _ in range(3):
        app = create_app({"DATABASE": database, "TESTING": True})
        assert app.test_client().get("/health").status_code == 200


@pytest.mark.parametrize(
    ("title", "author"),
    [
        ("", "A"),
        (" ", "A"),
        ("\t\n", "A"),
        # length(trim(x)) sees a NUL-only string as empty; trim(x) <> '' does not,
        # which is why the CHECK is written with length().
        ("\x00", "A"),
        ("\x00\x00", "A"),
        ("T", ""),
        ("T", "   "),
        ("T", "\x00"),
    ],
)
def test_table_constraints_reject_blank_text_at_the_storage_layer(app, title, author):
    """Defence in depth: the CHECK constraints hold even if validation is bypassed."""
    with app.app_context(), pytest.raises(sqlite3.IntegrityError):
        get_db().execute(
            "INSERT INTO books (title, author, created_at, updated_at)"
            " VALUES (?, ?, 'now', 'now')",
            (title, author),
        )


def test_table_constraints_accept_ordinary_text(app):
    with app.app_context():
        get_db().execute(
            "INSERT INTO books (title, author, created_at, updated_at)"
            " VALUES ('T', 'A', 'now', 'now')"
        )


def test_in_memory_databases_work_and_touch_no_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = create_app({"DATABASE": ":memory:", "TESTING": True}).test_client()

    created = client.post("/books", json=SAMPLE_BOOKS[0])
    assert created.status_code == 201
    # Two requests, two connections: the second must see the first one's write.
    assert len(client.get("/books").get_json()) == 1
    assert list(tmp_path.iterdir()) == []


def test_in_memory_databases_are_isolated_from_each_other():
    first = create_app({"DATABASE": ":memory:", "TESTING": True}).test_client()
    second = create_app({"DATABASE": ":memory:", "TESTING": True}).test_client()

    first.post("/books", json=SAMPLE_BOOKS[0])

    assert len(first.get("/books").get_json()) == 1
    assert second.get("/books").get_json() == []


def test_the_request_connection_is_closed_on_teardown(app):
    """Without the teardown hook every request would leak a file handle."""
    with app.app_context():
        connection = get_db()
        connection.execute("SELECT 1")  # usable inside the context

    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")


def test_each_request_gets_its_own_connection(app):
    with app.app_context():
        first = get_db()
        assert get_db() is first  # reused within one context
    with app.app_context():
        second = get_db()

    assert second is not first


def test_file_databases_run_in_wal_mode(app):
    """WAL is what lets a reader proceed while a writer holds the database."""
    with app.app_context():
        mode = get_db().execute("PRAGMA journal_mode").fetchone()[0]

    assert mode == "wal"


def test_writers_wait_instead_of_failing_immediately(app):
    with app.app_context():
        timeout = get_db().execute("PRAGMA busy_timeout").fetchone()[0]

    assert timeout == int(BUSY_TIMEOUT_SECONDS * 1000) == 5000


def test_concurrent_writers_all_succeed(tmp_path):
    """Each request opens its own connection, and the busy timeout makes a writer
    queue behind whoever holds the write lock rather than erroring out."""
    app = create_app({"DATABASE": str(tmp_path / "books.db"), "TESTING": True})
    writers, per_writer = 4, 3

    def write(worker: int) -> list[int]:
        client = app.test_client()
        statuses = []
        for index in range(per_writer):
            response = client.post(
                "/books", json={"title": f"w{worker}-b{index}", "author": "Author"}
            )
            statuses.append(response.status_code)
        return statuses

    with ThreadPoolExecutor(max_workers=writers) as pool:
        statuses = [s for result in pool.map(write, range(writers)) for s in result]

    assert statuses == [201] * (writers * per_writer)

    books = app.test_client().get("/books").get_json()
    assert len(books) == writers * per_writer
    assert len({book["id"] for book in books}) == len(books)
