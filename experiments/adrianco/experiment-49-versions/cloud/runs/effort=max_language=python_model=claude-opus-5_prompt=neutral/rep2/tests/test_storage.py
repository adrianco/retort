"""Tests for the SQLite storage layer itself."""

from __future__ import annotations

import sqlite3
import threading

from book_api import create_app

from .conftest import SAMPLE_BOOK


def test_books_survive_an_application_restart(tmp_path):
    database = tmp_path / "books.db"

    first = create_app({"DATABASE": str(database), "TESTING": True})
    created = first.test_client().post("/books", json=SAMPLE_BOOK).get_json()

    second = create_app({"DATABASE": str(database), "TESTING": True})
    fetched = second.test_client().get("/books/{}".format(created["id"]))

    assert database.exists()
    assert fetched.status_code == 200
    assert fetched.get_json() == created


def test_the_schema_is_created_on_first_use(tmp_path):
    database = tmp_path / "nested" / "directory" / "books.db"

    app = create_app({"DATABASE": str(database), "TESTING": True})

    assert app.test_client().get("/health").status_code == 200
    with sqlite3.connect(database) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "books" in tables


def test_in_memory_databases_are_isolated_per_application():
    first = create_app({"DATABASE": ":memory:", "TESTING": True})
    second = create_app({"DATABASE": ":memory:", "TESTING": True})

    first.test_client().post("/books", json=SAMPLE_BOOK)

    assert len(first.test_client().get("/books").get_json()) == 1
    assert second.test_client().get("/books").get_json() == []


def test_each_request_to_a_file_database_uses_its_own_connection(tmp_path):
    from book_api.db import get_db

    app = create_app({"DATABASE": str(tmp_path / "books.db"), "TESTING": True})

    with app.test_request_context("/health"):
        first = get_db()
        assert get_db() is first  # reused within one request

    with app.test_request_context("/health"):
        assert get_db() is not first  # a new request gets a fresh connection


def test_in_memory_requests_share_one_connection(app):
    from book_api.db import get_db

    with app.test_request_context("/health"):
        first = get_db()
    with app.test_request_context("/health"):
        # Shared-cache SQLite fails rather than waits when two connections
        # touch the same table, so requests take turns on a single connection.
        assert get_db() is first


def test_concurrent_requests_against_an_in_memory_database(app):
    """The ``:memory:`` mode must survive the threaded development server."""
    failures = []
    created = []

    def work(index: int) -> None:
        client = app.test_client()
        for offset in range(3):
            number = index * 3 + offset
            response = client.post(
                "/books", json={"title": "Book {}".format(number), "author": "Author"}
            )
            if response.status_code != 201:
                failures.append((response.status_code, response.get_json()))
            else:
                created.append(response.get_json()["id"])
            if client.get("/books").status_code != 200:
                failures.append(("list", None))

    threads = [threading.Thread(target=work, args=(index,)) for index in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert failures == []
    assert len(set(created)) == 24
    assert app.test_client().get("/books").headers["X-Total-Count"] == "24"


def test_concurrent_writers_do_not_lose_books(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "books.db"), "TESTING": True})
    threads = []
    failures = []

    def create(index: int) -> None:
        client = app.test_client()
        for offset in range(3):
            number = index * 3 + offset
            response = client.post(
                "/books", json={"title": "Book {}".format(number), "author": "Author"}
            )
            if response.status_code != 201:
                failures.append(response.get_json())

    for index in range(8):
        thread = threading.Thread(target=create, args=(index,))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()

    assert failures == []
    listing = app.test_client().get("/books")
    assert listing.headers["X-Total-Count"] == "24"
    assert len({book["id"] for book in listing.get_json()}) == 24


def test_values_are_bound_rather_than_interpolated(client, create_book):
    create_book(title="Robert'); DROP TABLE books; --", isbn=None)

    listing = client.get("/books")

    assert listing.status_code == 200
    assert listing.get_json()[0]["title"] == "Robert'); DROP TABLE books; --"
