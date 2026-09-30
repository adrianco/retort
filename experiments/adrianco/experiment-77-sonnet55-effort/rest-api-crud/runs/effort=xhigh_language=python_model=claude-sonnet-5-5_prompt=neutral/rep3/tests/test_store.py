"""Unit tests for the SQLite store and the validation rules."""

import pytest

from bookapi import BookStore, ValidationError, validate_book

BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}


def test_create_then_get_roundtrip(store):
    created = store.create(BOOK)
    assert created == {"id": created["id"], **BOOK}
    assert store.get(created["id"]) == created


def test_get_missing_returns_none(store):
    assert store.get(1) is None
    assert store.get(2**70) is None


def test_update_and_delete_missing_report_absence(store):
    assert store.update(1, BOOK) is None
    assert store.update(2**70, BOOK) is None
    assert store.delete(1) is False
    assert store.delete(2**70) is False


def test_list_filters_case_insensitively_with_unicode(store):
    store.create({**BOOK, "author": "Émile Zola"})
    store.create({**BOOK, "author": "Frank Herbert"})
    assert [b["author"] for b in store.list_books("émile zola")] == ["Émile Zola"]
    assert [b["author"] for b in store.list_books("ÉMILE ZOLA")] == ["Émile Zola"]
    assert len(store.list_books()) == 2


def test_data_persists_across_connections(tmp_path):
    path = str(tmp_path / "books.db")
    first = BookStore(path)
    created = first.create(BOOK)
    first.close()

    second = BookStore(path)
    try:
        assert second.get(created["id"]) == created
    finally:
        second.close()


def test_store_is_usable_from_multiple_threads(store):
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda i: store.create({**BOOK, "title": f"Book {i}"}), range(50)))
    assert len(store.list_books()) == 50


def test_validate_book_returns_cleaned_fields():
    assert validate_book({"title": " T ", "author": " A ", "extra": "ignored"}) == {
        "title": "T", "author": "A", "year": None, "isbn": None}


def test_validate_book_blank_isbn_becomes_none():
    assert validate_book({"title": "T", "author": "A", "isbn": "  "})["isbn"] is None


def test_validate_book_collects_all_errors():
    with pytest.raises(ValidationError) as excinfo:
        validate_book({"title": "", "year": "x"})
    assert set(excinfo.value.errors) == {"title", "author", "year"}


def test_validate_book_rejects_non_object():
    with pytest.raises(ValidationError) as excinfo:
        validate_book(["not", "an", "object"])
    assert "body" in excinfo.value.errors
