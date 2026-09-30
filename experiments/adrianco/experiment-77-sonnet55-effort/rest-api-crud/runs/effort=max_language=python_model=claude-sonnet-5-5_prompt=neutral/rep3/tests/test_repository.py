"""Tests for the SQLite repository."""

from __future__ import annotations

import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterator

import pytest

from bookapi.repository import Book, BookRepository
from bookapi.validation import BookFields


def fields(
    title: str = "Dune",
    author: str = "Frank Herbert",
    year: int = 1965,
    isbn: str = "978-0-441-17271-9",
) -> BookFields:
    return BookFields(title=title, author=author, year=year, isbn=isbn)


def titles(books: list[Book]) -> list[str]:
    return [book["title"] for book in books]


@pytest.fixture
def repo() -> Iterator[BookRepository]:
    repository = BookRepository(":memory:")
    yield repository
    repository.close()


# --- create / get -----------------------------------------------------------------


def test_create_assigns_sequential_ids_and_returns_the_book(repo: BookRepository):
    first = repo.create_book(fields(title="Dune"))
    second = repo.create_book(fields(title="Emma"))
    assert first == {"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}
    assert second["id"] == 2


def test_get_returns_what_was_stored(repo: BookRepository):
    created = repo.create_book(fields())
    assert repo.get_book(created["id"]) == created


def test_optional_fields_round_trip_as_null(repo: BookRepository):
    created = repo.create_book(BookFields(title="Dune", author="Frank Herbert", year=None, isbn=None))
    stored = repo.get_book(created["id"])
    assert stored is not None
    assert (stored["year"], stored["isbn"]) == (None, None)


def test_get_unknown_id_returns_none(repo: BookRepository):
    assert repo.get_book(1) is None


@pytest.mark.parametrize("book_id", [0, -1, 2**63, 10**30])
def test_impossible_ids_are_simply_not_found(repo: BookRepository, book_id: int):
    # 2**63 and up cannot be bound to an SQLite INTEGER; they must not raise OverflowError.
    assert repo.get_book(book_id) is None
    assert repo.update_book(book_id, fields()) is None
    assert repo.delete_book(book_id) is False


# --- list -------------------------------------------------------------------------


def test_list_is_empty_for_a_new_database(repo: BookRepository):
    assert repo.list_books() == []


def test_list_returns_books_in_insertion_order(repo: BookRepository):
    for title in ("Zebra", "Apple", "Mango"):
        repo.create_book(fields(title=title))
    assert titles(repo.list_books()) == ["Zebra", "Apple", "Mango"]


def test_author_filter_is_an_exact_case_insensitive_match(repo: BookRepository):
    repo.create_book(fields(title="Dune", author="Frank Herbert"))
    repo.create_book(fields(title="Emma", author="Jane Austen"))
    repo.create_book(fields(title="Dune Messiah", author="Frank Herbert"))

    assert titles(repo.list_books(author="Frank Herbert")) == ["Dune", "Dune Messiah"]
    assert titles(repo.list_books(author="fRaNk hErBeRt")) == ["Dune", "Dune Messiah"]
    assert repo.list_books(author="Herbert") == []  # a substring is not a match
    assert repo.list_books(author="Nobody") == []


def test_author_filter_ignores_case_of_non_ascii_letters(repo: BookRepository):
    repo.create_book(fields(author="Émile Zola"))
    assert len(repo.list_books(author="ÉMILE ZOLA")) == 1
    assert len(repo.list_books(author="émile zola")) == 1
    assert len(repo.list_books(author="Émile Zola")) == 1  # "É" written as E + combining accent


# --- update / delete --------------------------------------------------------------


def test_update_replaces_every_editable_field(repo: BookRepository):
    created = repo.create_book(fields())
    replacement = BookFields(title="Emma", author="Jane Austen", year=None, isbn=None)

    updated = repo.update_book(created["id"], replacement)

    assert updated == {"id": created["id"], **replacement}
    assert repo.get_book(created["id"]) == updated


def test_update_leaves_other_books_alone(repo: BookRepository):
    target = repo.create_book(fields(title="Dune"))
    bystander = repo.create_book(fields(title="Emma"))
    repo.update_book(target["id"], fields(title="Changed"))
    assert repo.get_book(bystander["id"]) == bystander


def test_update_unknown_id_returns_none(repo: BookRepository):
    assert repo.update_book(1, fields()) is None
    assert repo.list_books() == []  # and it did not create anything


def test_delete_removes_only_the_addressed_book(repo: BookRepository):
    doomed = repo.create_book(fields(title="Dune"))
    survivor = repo.create_book(fields(title="Emma"))

    assert repo.delete_book(doomed["id"]) is True
    assert repo.delete_book(doomed["id"]) is False
    assert repo.list_books() == [survivor]


def test_ids_are_never_reused_after_a_delete(repo: BookRepository):
    first = repo.create_book(fields())
    repo.delete_book(first["id"])
    assert repo.create_book(fields())["id"] > first["id"]


# --- storage ----------------------------------------------------------------------


def test_values_are_bound_as_data_never_interpreted_as_sql(repo: BookRepository):
    nasty = "Robert'); DROP TABLE books;--"
    repo.create_book(fields(title=nasty, author=nasty))
    assert titles(repo.list_books()) == [nasty]
    assert len(repo.list_books(author=nasty)) == 1
    assert repo.list_books(author="' OR '1'='1") == []


def test_data_persists_in_the_database_file(tmp_path: Path):
    path = tmp_path / "library" / "books.db"  # the directory does not exist yet
    first = BookRepository(path)
    created = first.create_book(fields())
    first.close()

    second = BookRepository(str(path))
    try:
        assert second.get_book(created["id"]) == created
    finally:
        second.close()


def test_schema_itself_refuses_blank_titles_and_authors(tmp_path: Path):
    path = tmp_path / "books.db"
    BookRepository(path).close()
    connection = sqlite3.connect(path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO books (title, author) VALUES ('  ', 'Someone')")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO books (title, author) VALUES ('Something', '')")
    finally:
        connection.close()


def test_concurrent_writers_share_the_connection_safely(repo: BookRepository):
    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(lambda n: repo.create_book(fields(title=f"Book {n}"))["id"], range(200)))
    assert len(set(ids)) == 200
    assert len(repo.list_books()) == 200


def test_ping_succeeds_while_open_and_fails_once_closed():
    repository = BookRepository(":memory:")
    repository.ping()
    repository.close()
    with pytest.raises(sqlite3.Error):
        repository.ping()


@pytest.mark.skipif(os.name != "posix", reason="overwrites a database file that is still open")
def test_ping_really_reads_the_database_file(tmp_path: Path):
    path = tmp_path / "books.db"
    repository = BookRepository(path)
    try:
        repository.create_book(fields())
        repository.ping()

        path.write_bytes(b"this is not an SQLite database " * 300)

        with pytest.raises(sqlite3.Error):
            repository.ping()
    finally:
        repository.close()


def test_opening_something_that_is_not_a_database_fails_and_releases_the_file(tmp_path: Path, monkeypatch):
    bogus = tmp_path / "bogus.db"
    bogus.write_bytes(b"this is not an SQLite database " * 300)
    opened = []
    real_connect = sqlite3.connect

    def recording_connect(*args, **kwargs):
        connection = real_connect(*args, **kwargs)
        opened.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", recording_connect)

    with pytest.raises(sqlite3.DatabaseError):
        BookRepository(bogus)

    assert len(opened) == 1
    with pytest.raises(sqlite3.ProgrammingError):  # "Cannot operate on a closed database"
        opened[0].execute("SELECT 1")
