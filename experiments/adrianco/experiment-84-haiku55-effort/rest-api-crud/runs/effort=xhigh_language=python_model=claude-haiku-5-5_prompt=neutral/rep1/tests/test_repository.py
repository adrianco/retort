from book_api import BookRepository
from book_api.models import BookFields


def make_fields(**overrides) -> BookFields:
    values = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": None}
    values.update(overrides)
    return BookFields(**values)


def test_create_assigns_ids_and_round_trips(repository):
    first = repository.create(make_fields(title="Dune"))
    second = repository.create(make_fields(title="Emma", author="Jane Austen", year=None))

    assert second.id > first.id
    assert repository.get(first.id) == first
    assert repository.get(second.id).year is None


def test_get_missing_book_returns_none(repository):
    assert repository.get(999) is None


def test_list_books_is_ordered_by_id(repository):
    titles = ["C", "A", "B"]
    for title in titles:
        repository.create(make_fields(title=title))

    assert [book.title for book in repository.list_books()] == titles


def test_list_books_filters_by_author_ignoring_case(repository):
    repository.create(make_fields(title="Dune", author="Frank Herbert"))
    repository.create(make_fields(title="Emma", author="Jane Austen"))
    repository.create(make_fields(title="Children of Dune", author="frank herbert"))
    repository.create(make_fields(title="Other", author="Frank Herbert Jr."))

    matches = repository.list_books(author="FRANK HERBERT")

    assert [book.title for book in matches] == ["Dune", "Children of Dune"]


def test_update_replaces_fields_and_reports_missing_books(repository):
    book = repository.create(make_fields())

    updated = repository.update(book.id, make_fields(title="Dune Messiah", year=None, isbn="9780441172696"))

    assert updated.id == book.id
    assert repository.get(book.id) == updated
    assert repository.update(999, make_fields()) is None


def test_delete_removes_book_and_reports_missing_books(repository):
    book = repository.create(make_fields())

    assert repository.delete(book.id) is True
    assert repository.get(book.id) is None
    assert repository.delete(book.id) is False


def test_data_survives_reopening_the_database_file(tmp_path):
    db_file = str(tmp_path / "books.db")
    first = BookRepository(db_file)
    created = first.create(make_fields())
    first.close()

    second = BookRepository(db_file)
    try:
        assert second.get(created.id) == created
    finally:
        second.close()


def test_ping_is_true_while_open_and_false_once_closed():
    repo = BookRepository(":memory:")
    assert repo.ping() is True

    repo.close()
    assert repo.ping() is False
