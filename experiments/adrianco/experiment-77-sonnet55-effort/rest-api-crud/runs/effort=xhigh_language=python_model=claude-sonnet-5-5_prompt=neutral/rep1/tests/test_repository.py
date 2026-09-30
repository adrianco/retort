import sqlite3
import threading

import pytest

from bookapi.db import BookRepository


@pytest.fixture
def repo():
    repo = BookRepository(":memory:")
    yield repo
    try:
        repo.close()
    except sqlite3.Error:
        pass


def test_create_and_get(repo):
    book = repo.create("Dune", "Frank Herbert", 1965, "123")
    assert book == {"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "123"}
    assert repo.get(1) == book
    assert repo.get(2) is None


def test_update_returns_none_for_missing_book(repo):
    assert repo.update(1, {"title": "x"}) is None


def test_update_rejects_unknown_columns(repo):
    repo.create("T", "A")
    with pytest.raises(ValueError):
        repo.update(1, {"id = 5, title": "x"})


def test_delete_reports_whether_a_row_was_removed(repo):
    repo.create("T", "A")
    assert repo.delete(1) is True
    assert repo.delete(1) is False


def test_data_persists_across_connections(tmp_path):
    path = str(tmp_path / "books.db")
    first = BookRepository(path)
    first.create("Dune", "Frank Herbert")
    first.close()

    second = BookRepository(path)
    try:
        assert [b["title"] for b in second.list_books()] == ["Dune"]
    finally:
        second.close()


def test_concurrent_writes_from_many_threads(repo):
    errors = []

    def worker(n):
        try:
            for i in range(20):
                repo.create(f"title-{n}-{i}", "Author")
        except Exception as exc:  # pragma: no cover - only hit on failure
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len(repo.list_books()) == 160
    assert len({b["id"] for b in repo.list_books()}) == 160
