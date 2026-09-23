import sqlite3
import threading

import pytest

from books_api import BookRepository

from .samples import ANIMAL_FARM, HUXLEY, ORWELL


def test_create_and_get(repo):
    book = repo.create_book(ORWELL)
    assert book == {"id": book["id"], **ORWELL}
    assert repo.get_book(book["id"]) == book


def test_optional_fields_default_to_null(repo):
    book = repo.create_book({"title": "Untitled", "author": "Anonymous"})
    assert book["year"] is None and book["isbn"] is None


def test_get_missing_book_returns_none(repo):
    assert repo.get_book(12345) is None


def test_list_is_ordered_by_id(repo):
    ids = [repo.create_book(b)["id"] for b in (ORWELL, HUXLEY, ANIMAL_FARM)]
    assert [b["id"] for b in repo.list_books()] == ids


def test_author_filter_is_case_insensitive_substring(repo):
    repo.create_book(ORWELL)
    repo.create_book(HUXLEY)
    repo.create_book(ANIMAL_FARM)
    assert {b["title"] for b in repo.list_books(author="george orwell")} == {"1984", "Animal Farm"}
    assert {b["title"] for b in repo.list_books(author="ORWELL")} == {"1984", "Animal Farm"}
    assert [b["title"] for b in repo.list_books(author="huxley")] == ["Brave New World"]
    assert repo.list_books(author="Tolstoy") == []


def test_author_filter_folds_non_ascii_case(repo):
    # SQLite's lower()/LIKE only fold ASCII letters.
    repo.create_book({"title": "Die Blechtrommel", "author": "Günter Grass"})
    repo.create_book({"title": "Der Richter und sein Henker", "author": "Friedrich Dürrenmatt"})
    assert [b["author"] for b in repo.list_books(author="GÜNTER")] == ["Günter Grass"]
    assert [b["author"] for b in repo.list_books(author="DÜRRENMATT")] == ["Friedrich Dürrenmatt"]


def test_author_filter_treats_wildcards_literally(repo):
    repo.create_book({"title": "A", "author": "100% Human"})
    repo.create_book({"title": "B", "author": "Jane Doe"})
    assert [b["title"] for b in repo.list_books(author="%")] == ["A"]
    assert repo.list_books(author="_") == []


def test_update_changes_only_given_fields(repo):
    book = repo.create_book(ORWELL)
    updated = repo.update_book(book["id"], {"title": "Nineteen Eighty-Four", "isbn": None})
    assert updated == {**book, "title": "Nineteen Eighty-Four", "isbn": None}
    assert repo.get_book(book["id"]) == updated


def test_update_missing_book_returns_none(repo):
    assert repo.update_book(999, {"title": "x"}) is None
    assert repo.update_book(999, {}) is None


def test_update_rejects_unknown_columns(repo):
    book = repo.create_book(ORWELL)
    with pytest.raises(ValueError):
        repo.update_book(book["id"], {"id": 5})
    with pytest.raises(ValueError):
        repo.update_book(book["id"], {"title = 'x'; --": "y"})


def test_delete(repo):
    book = repo.create_book(ORWELL)
    assert repo.delete_book(book["id"]) is True
    assert repo.get_book(book["id"]) is None
    assert repo.delete_book(book["id"]) is False


def test_ids_of_deleted_books_are_not_reused(repo):
    first = repo.create_book(ORWELL)
    repo.delete_book(first["id"])
    assert repo.create_book(HUXLEY)["id"] > first["id"]


def test_data_persists_in_file_database(tmp_path):
    db_path = tmp_path / "nested" / "dir" / "books.db"  # parent directories are created
    with BookRepository(db_path) as repository:
        book = repository.create_book(ORWELL)
    with BookRepository(db_path) as repository:
        assert repository.list_books() == [book]


def test_ping_fails_once_closed():
    repository = BookRepository()
    repository.ping()
    repository.close()
    with pytest.raises(sqlite3.Error):
        repository.ping()


def test_concurrent_writes_from_many_threads(repo):
    def worker(n):
        for i in range(25):
            repo.create_book({"title": f"Book {n}-{i}", "author": f"Author {n}"})

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    books = repo.list_books()
    assert len(books) == 200
    assert len({b["id"] for b in books}) == 200
    assert len(repo.list_books(author="Author 3")) == 25
