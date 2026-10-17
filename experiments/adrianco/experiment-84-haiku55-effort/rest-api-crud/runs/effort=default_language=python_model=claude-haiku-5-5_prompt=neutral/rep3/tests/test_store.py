import pytest

from bookapi import BookStore


@pytest.fixture
def store():
    s = BookStore(":memory:")
    yield s
    s.close()


def book(**overrides):
    base = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": None}
    base.update(overrides)
    return base


def test_persists_across_connections(tmp_path):
    path = str(tmp_path / "books.db")
    first = BookStore(path)
    created = first.create(book())
    first.close()

    second = BookStore(path)
    try:
        assert second.get(created["id"]) == created
    finally:
        second.close()


def test_ids_are_not_reused_after_delete(store):
    first = store.create(book())
    assert store.delete(first["id"])
    second = store.create(book(title="Other"))
    assert second["id"] > first["id"]


def test_update_and_delete_report_missing_rows(store):
    assert store.update(42, book()) is None
    assert store.delete(42) is False


def test_author_filter_is_case_insensitive_exact_match(store):
    store.create(book(author="Ursula K. Le Guin"))
    store.create(book(author="Ursula"))
    assert [b["author"] for b in store.list("ursula k. le guin")] == ["Ursula K. Le Guin"]
    assert store.list("Le Guin") == []


def test_ping_succeeds_on_open_store(store):
    store.ping()
