"""Unit tests for the persistence layer and the validation models."""

from __future__ import annotations

import sqlite3

import pytest
from pydantic import ValidationError

import database
from models import BookCreate, BookPatch, max_year


# --------------------------------------------------------------------------- #
# Schema / repository
# --------------------------------------------------------------------------- #

def test_init_db_is_idempotent(tmp_path):
    path = str(tmp_path / "books.db")

    database.init_db(path)
    database.init_db(path)

    with database.get_connection(path) as conn:
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master")}
    assert "books" in tables


def test_create_and_read_round_trip(conn):
    created = database.create_book(
        conn, {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": None}
    )

    assert created["id"] > 0
    assert database.get_book(conn, created["id"]) == created


def test_get_book_returns_none_when_missing(conn):
    assert database.get_book(conn, 999) is None


def test_replace_book_returns_none_when_missing(conn):
    assert database.replace_book(conn, 999, {"title": "T", "author": "A"}) is None


def test_update_book_returns_none_when_missing(conn):
    assert database.update_book(conn, 999, {"title": "T"}) is None


def test_delete_book_reports_whether_a_row_was_removed(conn):
    book = database.create_book(conn, {"title": "T", "author": "A"})

    assert database.delete_book(conn, book["id"]) is True
    assert database.delete_book(conn, book["id"]) is False


def test_update_book_touches_only_the_given_columns(conn):
    book = database.create_book(
        conn, {"title": "T", "author": "A", "year": 2000, "isbn": "9780441478125"}
    )

    updated = database.update_book(conn, book["id"], {"year": 2001})

    assert updated == dict(book, year=2001)


def test_unique_isbn_is_enforced_by_the_database(conn):
    database.create_book(conn, {"title": "T", "author": "A", "isbn": "9780441478125"})

    with pytest.raises(sqlite3.IntegrityError):
        database.create_book(conn, {"title": "U", "author": "B", "isbn": "9780441478125"})


def test_missing_title_is_rejected_by_the_database(conn):
    with pytest.raises(sqlite3.IntegrityError):
        database.create_book(conn, {"title": None, "author": "A"})


def test_list_books_filter_and_pagination(conn):
    for index in range(4):
        database.create_book(conn, {"title": f"T{index}", "author": "Le Guin"})
    database.create_book(conn, {"title": "Dune", "author": "Herbert"})

    assert len(database.list_books(conn)) == 5
    assert len(database.list_books(conn, author="le guin")) == 4
    assert len(database.list_books(conn, limit=2)) == 2
    assert len(database.list_books(conn, offset=3)) == 2
    assert database.list_books(conn, author="nobody") == []


def test_db_path_comes_from_the_environment(monkeypatch):
    monkeypatch.delenv("BOOKS_DB_PATH", raising=False)
    assert database.get_db_path() == database.DEFAULT_DB_PATH

    monkeypatch.setenv("BOOKS_DB_PATH", "/tmp/somewhere.db")
    assert database.get_db_path() == "/tmp/somewhere.db"


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #

def test_strings_are_trimmed():
    book = BookCreate(title="  Dune  ", author="  Frank Herbert ")

    assert book.title == "Dune"
    assert book.author == "Frank Herbert"


@pytest.mark.parametrize(
    "isbn", ["9780441478125", "978-0-441-47812-5", "978 0 441 47812 5", "043942089X"]
)
def test_valid_isbns_are_normalised(isbn):
    assert BookCreate(title="T", author="A", isbn=isbn).isbn == isbn.replace("-", "").replace(" ", "")


@pytest.mark.parametrize("isbn", ["123", "abcdefghij", "97804414781256", "X780441478125"])
def test_invalid_isbns_are_rejected(isbn):
    with pytest.raises(ValidationError):
        BookCreate(title="T", author="A", isbn=isbn)


def test_blank_isbn_is_treated_as_absent():
    assert BookCreate(title="T", author="A", isbn="   ").isbn is None


def test_year_bounds():
    assert BookCreate(title="T", author="A", year=max_year()).year == max_year()
    with pytest.raises(ValidationError):
        BookCreate(title="T", author="A", year=max_year() + 1)
    with pytest.raises(ValidationError):
        BookCreate(title="T", author="A", year=999)


def test_patch_reports_only_the_fields_that_were_sent():
    patch = BookPatch.model_validate({"year": None})

    assert patch.changes() == {"year": None}


def test_patch_requires_at_least_one_field():
    with pytest.raises(ValidationError):
        BookPatch.model_validate({})
