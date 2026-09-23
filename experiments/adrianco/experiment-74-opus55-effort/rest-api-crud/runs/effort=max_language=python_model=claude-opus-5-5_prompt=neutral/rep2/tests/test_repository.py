"""Tests for the SQLite repository, below the HTTP layer."""

import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager

import pytest

from books_api import db
from books_api.db import BookRepository
from books_api.schemas import BookIn

_HOLD_WRITE_LOCK = """
import sqlite3, sys, time
conn = sqlite3.connect(sys.argv[1], isolation_level=None)
conn.execute("BEGIN IMMEDIATE")
print("locked", flush=True)
time.sleep(float(sys.argv[2]))
conn.execute("COMMIT")
"""


@contextmanager
def another_process_holding_the_write_lock(path, seconds):
    command = [sys.executable, "-c", _HOLD_WRITE_LOCK, str(path), str(seconds)]
    with subprocess.Popen(command, stdout=subprocess.PIPE, text=True) as holder:
        try:
            assert holder.stdout.readline() == "locked\n"
            yield
        finally:
            holder.kill()


@pytest.fixture
def repository(db_path):
    return BookRepository(db_path)


def test_create_get_replace_delete_round_trip(repository):
    created = repository.create(BookIn(title="Dune", author="Frank Herbert", year=1965))
    assert repository.get(created.id) == created

    replaced = repository.replace(created.id, BookIn(title="Dune", author="F. Herbert"))
    assert replaced is not None
    assert repository.get(created.id) == replaced

    assert repository.delete(created.id) is True
    assert repository.get(created.id) is None
    assert repository.delete(created.id) is False
    assert repository.replace(created.id, BookIn(title="Dune", author="F. Herbert")) is None


def test_creates_the_schema_on_first_use(repository, db_path):
    assert not db_path.exists()

    assert repository.list_books() == []
    assert db_path.exists()


def test_initialize_is_repeatable_and_keeps_existing_books(db_path):
    BookRepository(db_path).create(BookIn(title="Dune", author="Frank Herbert"))

    reopened = BookRepository(db_path)
    reopened.initialize()
    reopened.initialize()

    assert [book.title for book in reopened.list_books()] == ["Dune"]


def test_initialize_waits_while_another_process_holds_the_write_lock(db_path):
    # What happens when several server workers start on a new database at once.
    # SQLite refuses the switch to WAL immediately instead of waiting for the lock.
    with another_process_holding_the_write_lock(db_path, seconds=0.5):
        BookRepository(db_path).initialize()

    assert BookRepository(db_path).list_books() == []


def test_initialize_gives_up_if_the_lock_is_never_released(db_path, monkeypatch):
    monkeypatch.setattr(db, "_INIT_TIMEOUT_SECONDS", 0.2)

    with another_process_holding_the_write_lock(db_path, seconds=30):
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            BookRepository(db_path).initialize()


def test_uses_write_ahead_logging(repository, db_path):
    repository.initialize()

    with closing(sqlite3.connect(db_path)) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_database_rejects_blank_fields_that_bypass_validation(repository):
    # model_construct skips validation, standing in for a bug in a caller.
    invalid = BookIn.model_construct(title="", author="Frank Herbert", year=None, isbn=None)

    with pytest.raises(sqlite3.IntegrityError):
        repository.create(invalid)
    assert repository.list_books() == []


def test_concurrent_writers_each_get_a_distinct_id(repository):
    # The server runs requests on a thread pool; this starts from an
    # uninitialized repository so schema creation races too.
    def add(number):
        return repository.create(BookIn(title=f"Book {number}", author="Anonymous")).id

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(add, range(100)))

    assert len(set(ids)) == 100
    assert sorted(book.id for book in repository.list_books()) == sorted(ids)
