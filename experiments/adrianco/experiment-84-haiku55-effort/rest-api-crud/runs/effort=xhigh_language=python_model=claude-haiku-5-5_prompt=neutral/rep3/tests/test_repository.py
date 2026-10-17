from bookapi import BookFields, BookRepository

DUNE = BookFields(title="Dune", author="Frank Herbert", year=1965, isbn="9780441172719")
EMMA = BookFields(title="Emma", author="Jane Austen", year=1815)


def test_create_assigns_increasing_ids_and_round_trips(repository):
    first = repository.create(DUNE)
    second = repository.create(EMMA)

    assert second.id > first.id
    assert repository.get(first.id) == first
    assert first.to_dict() == {
        "id": first.id,
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "9780441172719",
    }


def test_optional_fields_are_stored_as_null(repository):
    book = repository.create(BookFields(title="Untitled", author="Anon"))

    assert repository.get(book.id).year is None
    assert repository.get(book.id).isbn is None


def test_get_unknown_id_returns_none(repository):
    assert repository.get(12345) is None


def test_list_returns_all_books_in_insertion_order(repository):
    dune = repository.create(DUNE)
    emma = repository.create(EMMA)

    assert repository.list() == [dune, emma]


def test_list_filters_by_author_ignoring_case(repository):
    dune = repository.create(DUNE)
    repository.create(EMMA)

    assert repository.list("frank herbert") == [dune]
    assert repository.list("Nobody") == []


def test_update_replaces_every_attribute(repository):
    book = repository.create(DUNE)

    updated = repository.update(book.id, BookFields(title="Emma", author="Jane Austen"))

    assert updated.id == book.id
    assert (updated.title, updated.author, updated.year, updated.isbn) == (
        "Emma",
        "Jane Austen",
        None,
        None,
    )
    assert repository.get(book.id) == updated


def test_update_unknown_id_returns_none(repository):
    assert repository.update(999, EMMA) is None


def test_delete_removes_the_book(repository):
    book = repository.create(DUNE)

    assert repository.delete(book.id) is True
    assert repository.get(book.id) is None


def test_delete_unknown_id_returns_false(repository):
    assert repository.delete(999) is False


def test_ping_succeeds_on_open_database(repository):
    repository.ping()


def test_data_survives_reopening_a_file_database(tmp_path):
    path = str(tmp_path / "books.db")
    repo = BookRepository(path)
    book = repo.create(DUNE)
    repo.close()

    reopened = BookRepository(path)
    try:
        assert reopened.get(book.id) == book
    finally:
        reopened.close()
