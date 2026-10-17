from bookapi.store import BookStore


def new_book(**overrides):
    book = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": None}
    book.update(overrides)
    return book


def test_create_assigns_increasing_ids(store):
    first = store.create(new_book())
    second = store.create(new_book(title="Emma"))
    assert second["id"] > first["id"]
    assert store.get(first["id"]) == first


def test_list_filters_by_author_case_insensitively(store):
    store.create(new_book(author="Frank Herbert"))
    store.create(new_book(title="Emma", author="Jane Austen"))
    assert [b["title"] for b in store.list_books("frank herbert")] == ["Dune"]
    assert store.list_books("Nobody") == []
    assert len(store.list_books()) == 2


def test_update_replaces_all_fields(store):
    created = store.create(new_book())
    updated = store.update(created["id"], new_book(title="Dune Messiah", year=None))
    assert updated == {"id": created["id"], "title": "Dune Messiah", "author": "Frank Herbert",
                       "year": None, "isbn": None}


def test_update_and_delete_return_none_or_false_for_missing_book(store):
    assert store.update(999, new_book()) is None
    assert store.delete(999) is False


def test_delete_removes_book(store):
    created = store.create(new_book())
    assert store.delete(created["id"]) is True
    assert store.get(created["id"]) is None


def test_data_persists_across_connections(tmp_path):
    path = str(tmp_path / "books.db")
    first = BookStore(path)
    created = first.create(new_book())
    first.close()

    second = BookStore(path)
    try:
        assert second.get(created["id"]) == created
    finally:
        second.close()
