"""Unit tests for the SQLite storage layer."""

import pytest

from bookapi import BookStore

BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": None}


@pytest.fixture
def store():
    s = BookStore(":memory:")
    yield s
    s.close()


def test_create_assigns_increasing_ids(store):
    first = store.create(BOOK)
    second = store.create({**BOOK, "title": "Emma"})
    assert second["id"] > first["id"]


def test_get_missing_returns_none(store):
    assert store.get(42) is None


def test_update_missing_returns_none(store):
    assert store.update(42, BOOK) is None


def test_delete_reports_whether_row_existed(store):
    created = store.create(BOOK)
    assert store.delete(created["id"]) is True
    assert store.delete(created["id"]) is False


def test_data_persists_to_file_across_connections(tmp_path):
    path = str(tmp_path / "books.db")
    first = BookStore(path)
    created = first.create(BOOK)
    first.close()

    second = BookStore(path)
    try:
        assert second.get(created["id"]) == created
    finally:
        second.close()
