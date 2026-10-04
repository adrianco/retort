"""Persistence behaviour of BookStore."""

import threading

from bookapi import BookStore

BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": None}


def test_books_survive_reopening_the_database(tmp_path):
    path = str(tmp_path / "books.db")
    first = BookStore(path)
    created = first.create(BOOK)
    first.close()

    second = BookStore(path)
    try:
        assert second.get(created["id"]) == created
    finally:
        second.close()


def test_in_memory_database_is_supported():
    store = BookStore(":memory:")
    try:
        created = store.create(BOOK)
        assert store.list() == [created]
    finally:
        store.close()


def test_concurrent_writers_do_not_lose_books(store):
    per_thread, thread_count = 25, 8
    errors = []

    def work():
        try:
            for _ in range(per_thread):
                store.create(BOOK)
        except Exception as exc:  # surfaced through the assertion below
            errors.append(exc)

    threads = [threading.Thread(target=work) for _ in range(thread_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    ids = [book["id"] for book in store.list()]
    assert len(ids) == len(set(ids)) == per_thread * thread_count
