from bookapi.db import BookStore


def test_create_and_get(store):
    book = store.create("Dune", "Frank Herbert", 1965, "9780441172719")
    assert store.get(book["id"]) == book


def test_get_missing_returns_none(store):
    assert store.get(1) is None


def test_update_with_no_fields_returns_current_row(store):
    book = store.create("Dune", "Frank Herbert", None, None)
    assert store.update(book["id"], {}) == book


def test_update_ignores_non_updatable_keys(store):
    book = store.create("Dune", "Frank Herbert", None, None)
    updated = store.update(book["id"], {"id": 99, "title": "New", "nonsense": "x"})
    assert updated == {**book, "title": "New"}


def test_update_missing_returns_none(store):
    assert store.update(1, {"title": "x"}) is None


def test_delete(store):
    book = store.create("Dune", "Frank Herbert", None, None)
    assert store.delete(book["id"]) is True
    assert store.delete(book["id"]) is False


def test_list_books_filters_by_author(store):
    store.create("A", "X", None, None)
    store.create("B", "Y", None, None)
    assert [b["title"] for b in store.list_books("x")] == ["A"]
    assert [b["title"] for b in store.list_books()] == ["A", "B"]


def test_in_memory_database_works():
    store = BookStore(":memory:")
    try:
        store.create("Dune", "Frank Herbert", None, None)
        assert len(store.list_books()) == 1
    finally:
        store.close()
