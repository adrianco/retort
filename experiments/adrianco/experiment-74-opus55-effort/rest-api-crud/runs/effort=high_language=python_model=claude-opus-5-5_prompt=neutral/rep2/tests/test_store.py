import pytest

from books_api.store import BookStore, DuplicateISBNError


@pytest.fixture
def store():
    s = BookStore(":memory:")
    yield s
    s.close()


def _book(**overrides):
    return {"title": "T", "author": "A", "year": None, "isbn": None, **overrides}


def test_crud_roundtrip(store):
    created = store.create(_book(title="Emma", author="Jane Austen"))
    assert store.get(created["id"]) == created
    updated = store.update(created["id"], _book(title="Persuasion", author="Jane Austen"))
    assert store.get(created["id"])["title"] == "Persuasion" == updated["title"]
    assert store.delete(created["id"]) is True
    assert store.get(created["id"]) is None
    assert store.delete(created["id"]) is False


def test_author_filter_is_case_insensitive(store):
    store.create(_book(author="Jane Austen"))
    store.create(_book(author="Mark Twain"))
    assert [b["author"] for b in store.list(author="jane austen")] == ["Jane Austen"]
    assert len(store.list()) == 2


def test_duplicate_isbn_rejected_but_null_isbns_allowed(store):
    store.create(_book(isbn="0441013597"))
    store.create(_book())
    store.create(_book())
    with pytest.raises(DuplicateISBNError):
        store.create(_book(isbn="0441013597"))


def test_persists_to_file(tmp_path):
    path = str(tmp_path / "books.db")
    s = BookStore(path)
    created = s.create(_book(title="Kept"))
    s.close()
    s = BookStore(path)
    assert s.get(created["id"])["title"] == "Kept"
    s.close()
