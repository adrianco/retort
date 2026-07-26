"""Unit tests for the SQLite storage layer."""

from __future__ import annotations

import threading

import pytest

from bookapi.db import BookNotFound, Database


@pytest.fixture
def db() -> Database:
    database = Database(":memory:")
    try:
        yield database
    finally:
        database.close()


def make(title="T", author="A", year=None, isbn=None):
    return {"title": title, "author": author, "year": year, "isbn": isbn}


def test_create_assigns_an_id_and_timestamps(db):
    book = db.create(make("Dune", "Frank Herbert", 1965))

    assert book["id"] >= 1
    assert book["title"] == "Dune"
    assert book["created_at"] == book["updated_at"]


def test_get_returns_none_for_unknown_id(db):
    assert db.get(999) is None


def test_list_is_newest_first(db):
    first = db.create(make("First", "A"))
    second = db.create(make("Second", "B"))

    assert [book["id"] for book in db.list()] == [second["id"], first["id"]]


def test_list_filters_by_author_substring_case_insensitively(db):
    db.create(make("Nineteen Eighty-Four", "George Orwell"))
    db.create(make("Dune", "Frank Herbert"))

    assert [book["title"] for book in db.list(author="orwell")] == [
        "Nineteen Eighty-Four"
    ]
    assert len(db.list(author="")) == 2
    assert len(db.list(author=None)) == 2
    assert db.list(author="Tolkien") == []


def test_list_escapes_like_wildcards(db):
    db.create(make("Dune", "Frank Herbert"))

    assert db.list(author="%") == []
    assert db.list(author="_") == []


def test_update_replaces_fields_and_keeps_created_at(db):
    created = db.create(make("Dune", "Frank Herbert", 1965, "9780441013593"))

    updated = db.update(created["id"], make("Dune Messiah", "F. Herbert"))

    assert updated["id"] == created["id"]
    assert updated["title"] == "Dune Messiah"
    assert updated["year"] is None
    assert updated["isbn"] is None
    assert updated["created_at"] == created["created_at"]


def test_update_unknown_id_raises(db):
    with pytest.raises(BookNotFound):
        db.update(999, make())


def test_delete_removes_the_row(db):
    created = db.create(make())

    db.delete(created["id"])

    assert db.get(created["id"]) is None
    with pytest.raises(BookNotFound):
        db.delete(created["id"])


def test_ping_reports_healthy(db):
    assert db.ping() is True


def test_ping_reports_unhealthy_after_close():
    database = Database(":memory:")
    database.close()

    assert database.ping() is False


def test_persists_to_disk(tmp_path):
    path = str(tmp_path / "books.db")

    database = Database(path)
    book_id = database.create(make("Dune", "Frank Herbert"))["id"]
    database.close()

    reopened = Database(path)
    try:
        assert reopened.get(book_id)["title"] == "Dune"
    finally:
        reopened.close()


def test_concurrent_writes_are_serialised(db):
    """The shared connection is lock-guarded, so parallel inserts all land."""
    errors = []

    def insert(index: int) -> None:
        try:
            db.create(make(f"Book {index}", "Author"))
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [threading.Thread(target=insert, args=(i,)) for i in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len({book["id"] for book in db.list()}) == 20
