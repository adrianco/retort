import threading

from books_api import Book, BookData, BookRepository

DUNE = BookData(title="Dune", author="Frank Herbert", year=1965, isbn="9780441172719")


def test_create_and_get(repository):
    book = repository.create(DUNE)
    assert book == Book(id=book.id, title="Dune", author="Frank Herbert", year=1965, isbn="9780441172719")
    assert repository.get(book.id) == book


def test_get_missing_and_out_of_range_ids(repository):
    assert repository.get(1) is None
    assert repository.get(0) is None
    assert repository.get(-1) is None
    # Larger than SQLite's INTEGER range: must not raise OverflowError.
    assert repository.get(2**64) is None
    assert repository.delete(2**64) is False
    assert repository.update(2**64, DUNE) is None


def test_update_replaces_all_fields(repository):
    book = repository.create(DUNE)
    updated = repository.update(book.id, BookData(title="Dune Messiah", author="Frank Herbert"))
    assert updated == Book(id=book.id, title="Dune Messiah", author="Frank Herbert", year=None, isbn=None)
    assert repository.get(book.id) == updated
    assert repository.update(book.id + 1, DUNE) is None


def test_delete(repository):
    book = repository.create(DUNE)
    assert repository.delete(book.id) is True
    assert repository.get(book.id) is None
    assert repository.delete(book.id) is False


def test_ids_are_not_reused_after_delete(repository):
    first = repository.create(DUNE)
    repository.delete(first.id)
    second = repository.create(DUNE)
    assert second.id > first.id


def test_list_is_ordered_by_id_and_filters_by_author(repository):
    herbert = repository.create(DUNE)
    le_guin = repository.create(BookData(title="The Dispossessed", author="Ursula K. Le Guin"))
    herbert_2 = repository.create(BookData(title="Children of Dune", author="Frank Herbert"))

    assert repository.list_books() == [herbert, le_guin, herbert_2]
    assert repository.list_books(author="frank herbert") == [herbert, herbert_2]
    assert repository.list_books(author="GUIN") == [le_guin]
    assert repository.list_books(author="Tolkien") == []


def test_author_filter_is_unicode_case_insensitive_and_literal(repository):
    marquez = repository.create(BookData(title="Cien años de soledad", author="Gabriel García Márquez"))
    repository.create(BookData(title="Other", author="100% Author_Name"))
    assert repository.list_books(author="GARCÍA MÁRQUEZ") == [marquez]
    # LIKE wildcards have no special meaning.
    assert repository.list_books(author="%") == repository.list_books(author="100%")
    assert len(repository.list_books(author="_")) == 1


def test_data_persists_across_connections(tmp_path):
    path = tmp_path / "persist.db"
    repo = BookRepository(path)
    book = repo.create(DUNE)
    repo.close()

    reopened = BookRepository(path)
    try:
        assert reopened.get(book.id) == book
    finally:
        reopened.close()


def test_ping_reports_database_health(tmp_path):
    repo = BookRepository(tmp_path / "ping.db")
    assert repo.ping() is True
    repo.close()
    assert repo.ping() is False


def test_concurrent_writes_from_many_threads():
    repo = BookRepository(":memory:")
    errors = []

    def worker(n):
        try:
            for i in range(20):
                repo.create(BookData(title=f"Book {n}-{i}", author=f"Author {n}"))
        except Exception as exc:  # pragma: no cover - only on failure
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    books = repo.list_books()
    assert len(books) == 160
    assert len({book.id for book in books}) == 160
    repo.close()
