"""Unit tests for the SQLite repository."""

from __future__ import annotations

import sqlite3
import threading

import pytest

from bookapi.models import Book, BookInput
from bookapi.repository import BookRepository

DUNE = BookInput("Dune", "Frank Herbert", 1965, "9780441172719")
EMMA = BookInput("Emma", "Jane Austen")


def test_create_returns_the_stored_book_with_a_generated_id(repository):
    assert repository.create(DUNE) == Book(1, "Dune", "Frank Herbert", 1965, "9780441172719")


def test_ids_increase(repository):
    assert [repository.create(DUNE).id, repository.create(EMMA).id] == [1, 2]


def test_get_returns_what_was_stored(repository):
    created = repository.create(DUNE)
    assert repository.get(created.id) == created


def test_optional_fields_round_trip_as_none(repository):
    book = repository.get(repository.create(EMMA).id)
    assert (book.year, book.isbn) == (None, None)


def test_get_unknown_id_returns_none(repository):
    assert repository.get(1) is None


@pytest.mark.parametrize("book_id", [0, -1, 2**63, 10**40])
def test_ids_no_row_can_have_are_simply_not_found(repository, book_id):
    # 2**63 and beyond do not fit a SQLite INTEGER; that must not blow up.
    repository.create(DUNE)
    assert repository.get(book_id) is None
    assert repository.update(book_id, EMMA) is None
    assert repository.delete(book_id) is False


def test_list_is_empty_initially(repository):
    assert repository.list_books() == []


def test_list_returns_every_book_in_id_order(repository):
    first, second, third = (repository.create(b) for b in (DUNE, EMMA, DUNE))
    assert repository.list_books() == [first, second, third]


class TestAuthorFilter:
    @pytest.fixture(autouse=True)
    def books(self, repository):
        self.dune = repository.create(DUNE)
        self.messiah = repository.create(BookInput("Dune Messiah", "Frank Herbert"))
        self.emma = repository.create(EMMA)
        self.repository = repository

    def test_returns_only_that_authors_books(self):
        assert self.repository.list_books("Frank Herbert") == [self.dune, self.messiah]

    def test_ignores_case(self):
        assert self.repository.list_books("fRANK hERBERT") == [self.dune, self.messiah]

    def test_no_match_gives_an_empty_list(self):
        assert self.repository.list_books("Nobody") == []

    def test_match_is_exact_not_a_substring(self):
        assert self.repository.list_books("Herbert") == []
        assert self.repository.list_books("Frank") == []

    def test_sql_wildcards_and_quotes_are_literal(self):
        assert self.repository.list_books("%") == []
        assert self.repository.list_books("_") == []
        assert self.repository.list_books("' OR '1'='1") == []

    @pytest.mark.parametrize(
        ("stored", "query"),
        [
            ("Émile Zola", "émile zola"),  # SQLite's own NOCASE/lower() only fold ASCII
            ("Émile Zola", "ÉMILE ZOLA"),
            ("Straße Verlag", "STRASSE VERLAG"),
            ("Ὀδυσσεύς", "ὀδυσσεύς"),
        ],
    )
    def test_case_folding_covers_all_of_unicode(self, repository, stored, query):
        book = repository.create(BookInput("Some Title", stored))
        assert repository.list_books(query) == [book]

    @pytest.mark.parametrize(
        ("stored", "query"),
        [
            # e-diaeresis stored as one character, asked as "e" + a combining mark...
            ("Zo\xeb", "Zoe\N{COMBINING DIAERESIS}"),
            # ...and the other way round
            ("Zoe\N{COMBINING DIAERESIS}", "Zo\xeb"),
            # composition and case at once
            ("\xc9mile Zola", "e\N{COMBINING ACUTE ACCENT}MILE zola"),
        ],
        ids=ascii,
    )
    def test_accents_match_however_they_are_composed(self, repository, stored, query):
        book = repository.create(BookInput("Some Title", stored))
        assert repository.list_books(query) == [book]
        assert repository.get(book.id).author == stored  # stored exactly as given

    def test_text_sqlite_cannot_store_matches_nothing(self, repository):
        repository.create(DUNE)
        assert repository.list_books("bad \udcff text") == []


def test_update_replaces_every_field(repository):
    created = repository.create(DUNE)
    updated = repository.update(created.id, BookInput("Emma", "Jane Austen", None, None))
    assert updated == Book(created.id, "Emma", "Jane Austen", None, None)
    assert repository.get(created.id) == updated


def test_update_touches_only_the_addressed_book(repository):
    first, second = repository.create(DUNE), repository.create(EMMA)
    repository.update(first.id, BookInput("Changed", "Someone"))
    assert repository.get(second.id) == second


def test_update_with_identical_data_still_counts_as_found(repository):
    created = repository.create(DUNE)
    assert repository.update(created.id, DUNE) == created


def test_update_unknown_id_returns_none(repository):
    assert repository.update(5, DUNE) is None


def test_delete_removes_the_book(repository):
    created = repository.create(DUNE)
    assert repository.delete(created.id) is True
    assert repository.get(created.id) is None
    assert repository.list_books() == []


def test_delete_unknown_id_returns_false(repository):
    assert repository.delete(5) is False


def test_deleted_ids_are_never_reused(repository):
    first = repository.create(DUNE)
    repository.delete(first.id)
    assert repository.create(EMMA).id == first.id + 1


def test_data_survives_reopening_the_database_file(tmp_path):
    path = tmp_path / "books.db"
    first = BookRepository(path)
    created = first.create(DUNE)
    first.close()

    second = BookRepository(path)
    try:
        assert second.list_books() == [created]
        assert second.create(EMMA).id == created.id + 1
    finally:
        second.close()


def test_ping_succeeds_on_a_healthy_database(repository):
    repository.ping()


def test_ping_fails_once_closed(repository):
    repository.close()
    with pytest.raises(sqlite3.Error):
        repository.ping()


def test_closing_twice_is_harmless(repository):
    repository.close()
    repository.close()


def test_an_empty_database_path_is_refused():
    # sqlite3 would silently open a throwaway temporary database instead.
    with pytest.raises(ValueError, match="must not be empty"):
        BookRepository("")


def test_a_file_that_is_not_a_database_is_rejected(tmp_path):
    path = tmp_path / "garbage.db"
    path.write_bytes(b"this is definitely not a sqlite database" * 20)
    with pytest.raises(sqlite3.DatabaseError):
        BookRepository(path)


def test_concurrent_writers_never_lose_or_duplicate_a_row(repository):
    threads, per_thread = 8, 25
    created: list[int] = []
    guard = threading.Lock()

    def worker(n: int) -> None:
        for i in range(per_thread):
            book = repository.create(BookInput(f"Book {n}-{i}", f"Author {n}"))
            with guard:
                created.append(book.id)

    pool = [threading.Thread(target=worker, args=(n,)) for n in range(threads)]
    for thread in pool:
        thread.start()
    for thread in pool:
        thread.join()

    assert sorted(created) == list(range(1, threads * per_thread + 1))
    assert len(repository.list_books()) == threads * per_thread
