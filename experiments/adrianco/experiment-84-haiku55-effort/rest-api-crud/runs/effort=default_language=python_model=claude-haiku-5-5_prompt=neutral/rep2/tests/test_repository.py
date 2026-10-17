import pytest

from books_api import BookRepository, ConflictError


@pytest.fixture
def repo():
    repository = BookRepository(":memory:")
    yield repository
    repository.close()


def _book(**overrides):
    data = {"title": "Title", "author": "Author", "year": None, "isbn": None}
    data.update(overrides)
    return data


def test_create_assigns_increasing_ids(repo):
    first = repo.create(_book(title="First"))
    second = repo.create(_book(title="Second"))

    assert second["id"] > first["id"]
    assert repo.get(first["id"])["title"] == "First"


def test_get_missing_returns_none(repo):
    assert repo.get(42) is None


def test_update_missing_returns_none(repo):
    assert repo.update(42, _book()) is None


def test_delete_reports_whether_anything_was_removed(repo):
    created = repo.create(_book())

    assert repo.delete(created["id"]) is True
    assert repo.delete(created["id"]) is False


def test_find_filters_by_author(repo):
    repo.create(_book(title="A", author="Alice"))
    repo.create(_book(title="B", author="Bob"))

    assert [b["title"] for b in repo.find(author="alice")] == ["A"]
    assert len(repo.find()) == 2


def test_duplicate_isbn_raises_conflict(repo):
    repo.create(_book(isbn="9780306406157"))

    with pytest.raises(ConflictError):
        repo.create(_book(title="Other", isbn="9780306406157"))


def test_multiple_books_without_isbn_are_allowed(repo):
    repo.create(_book(title="A"))
    repo.create(_book(title="B"))

    assert len(repo.find()) == 2


def test_failed_update_leaves_original_unchanged(repo):
    repo.create(_book(title="Keep", isbn="9780306406157"))
    other = repo.create(_book(title="Other"))

    with pytest.raises(ConflictError):
        repo.update(other["id"], _book(title="Changed", isbn="9780306406157"))

    assert repo.get(other["id"])["title"] == "Other"


def test_data_persists_across_connections(tmp_path):
    db_file = tmp_path / "books.db"
    first = BookRepository(str(db_file))
    created = first.create(_book(title="Persisted"))
    first.close()

    second = BookRepository(str(db_file))
    try:
        assert second.get(created["id"])["title"] == "Persisted"
    finally:
        second.close()
