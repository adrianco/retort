"""Unit tests for the SQLite repository."""

import sqlite3

import pytest

from bookapi.models import Book, BookData
from bookapi.repository import MAX_ID, BookRepository

DUNE = BookData("Dune", "Frank Herbert", 1965, "978-0441013593")


def test_create_returns_the_stored_book(repository):
    book = repository.create(DUNE)

    assert book == Book(1, "Dune", "Frank Herbert", 1965, "978-0441013593")
    assert repository.get(book.id) == book


def test_optional_fields_round_trip_as_none(repository):
    book = repository.create(BookData("Dune", "Frank Herbert"))
    assert repository.get(book.id) == Book(book.id, "Dune", "Frank Herbert", None, None)


def test_ids_increase(repository):
    ids = [repository.create(DUNE).id for _ in range(3)]
    assert ids == sorted(set(ids)) and len(ids) == 3


def test_get_unknown_id_returns_none(repository):
    assert repository.get(42) is None


def test_list_is_ordered_by_id(repository):
    created = [repository.create(BookData(f"Book {n}", "Someone")) for n in range(5)]
    assert repository.list_books() == created


class TestAuthorFilter:
    @pytest.fixture(autouse=True)
    def _books(self, repository):
        self.orwell = repository.create(BookData("1984", "George Orwell"))
        self.farm = repository.create(BookData("Animal Farm", "George Orwell"))
        self.dune = repository.create(BookData("Dune", "Frank Herbert"))
        self.garcia = repository.create(BookData("Cien años de soledad", "Gabriel García Márquez"))
        self.strasse = repository.create(BookData("Ein Buch", "Hans Straße"))

    def test_exact_match(self, repository):
        assert repository.list_books("George Orwell") == [self.orwell, self.farm]

    def test_is_case_insensitive(self, repository):
        assert repository.list_books("gEORGE oRWELL") == [self.orwell, self.farm]

    def test_case_folding_covers_non_ascii_letters(self, repository):
        assert repository.list_books("GABRIEL GARCÍA MÁRQUEZ") == [self.garcia]
        assert repository.list_books("HANS STRASSE") == [self.strasse]  # ß folds to ss

    def test_partial_names_do_not_match(self, repository):
        assert repository.list_books("Orwell") == []
        assert repository.list_books("George") == []

    def test_wildcards_are_literal(self, repository):
        assert repository.list_books("%") == []
        assert repository.list_books("George _rwell") == []

    def test_none_means_no_filter(self, repository):
        assert len(repository.list_books(None)) == 5


def test_update_replaces_every_field(repository):
    book = repository.create(DUNE)

    updated = repository.update(book.id, BookData("Dune Messiah", "Frank Herbert"))

    assert updated == Book(book.id, "Dune Messiah", "Frank Herbert", None, None)
    assert repository.get(book.id) == updated


def test_update_only_touches_the_addressed_book(repository):
    first, second = repository.create(DUNE), repository.create(DUNE)
    repository.update(first.id, BookData("Other", "Someone"))
    assert repository.get(second.id) == second


def test_update_unknown_id_returns_none(repository):
    assert repository.update(42, DUNE) is None
    assert repository.list_books() == []


def test_delete_reports_whether_the_book_existed(repository):
    book = repository.create(DUNE)
    assert repository.delete(book.id) is True
    assert repository.delete(book.id) is False
    assert repository.get(book.id) is None


def test_ids_are_never_reused(repository):
    first = repository.create(DUNE)
    repository.delete(first.id)
    assert repository.create(DUNE).id > first.id


@pytest.mark.parametrize("book_id", [0, -1, MAX_ID + 1, 2**64, 10**30])
def test_ids_outside_the_storable_range_are_simply_not_found(repository, book_id):
    # sqlite3 raises OverflowError when binding such integers; the repository must not.
    assert repository.get(book_id) is None
    assert repository.update(book_id, DUNE) is None
    assert repository.delete(book_id) is False


def test_the_largest_storable_id_is_valid_to_look_up(repository):
    assert repository.get(MAX_ID) is None


def test_data_persists_across_connections(tmp_path):
    path = tmp_path / "books.db"
    with BookRepository(path) as first:
        created = first.create(DUNE)
    with BookRepository(path) as second:
        assert second.get(created.id) == created
        assert second.create(DUNE).id > created.id


def test_opening_an_existing_database_is_idempotent(tmp_path):
    path = tmp_path / "books.db"
    for _ in range(3):
        with BookRepository(path) as repo:
            repo.list_books()


def test_database_refuses_blank_text_even_if_validation_is_bypassed(tmp_path):
    path = tmp_path / "books.db"
    with BookRepository(path):
        pass
    raw = sqlite3.connect(path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            raw.execute("INSERT INTO books (title, author) VALUES ('   ', 'Someone')")
        with pytest.raises(sqlite3.IntegrityError):
            raw.execute("INSERT INTO books (title, author) VALUES ('Title', NULL)")
    finally:
        raw.close()


def test_ping_succeeds_while_open_and_fails_once_closed():
    repo = BookRepository(":memory:")
    repo.ping()
    repo.close()
    with pytest.raises(sqlite3.ProgrammingError):
        repo.ping()


def test_close_is_idempotent():
    repo = BookRepository(":memory:")
    repo.close()
    repo.close()


def test_a_file_that_is_not_a_database_is_reported_and_not_leaked(tmp_path):
    path = tmp_path / "junk.db"
    path.write_bytes(b"this is definitely not an sqlite database" * 10)
    with pytest.raises(sqlite3.DatabaseError):
        BookRepository(path)


def test_concurrent_readers_and_writers_do_not_lose_rows_or_deadlock(run_concurrently):
    # Deliberately mixes writes with filtered reads: the filter calls back into Python from
    # inside SQLite, which is exactly where unsynchronised sharing of the connection
    # deadlocks. A private repository, so a stuck one is never touched again.
    repo = BookRepository(":memory:")
    workers, per_worker = 8, 40
    ids = []

    def worker(n):
        for i in range(per_worker):
            ids.append(repo.create(BookData(f"Book {n}-{i}", "Someone")).id)
            repo.list_books("someone")

    run_concurrently(worker, workers)

    try:
        assert len(set(ids)) == workers * per_worker
        assert len(repo.list_books()) == workers * per_worker
    finally:
        repo.close()
