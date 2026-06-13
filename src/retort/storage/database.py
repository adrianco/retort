"""Database engine and session management."""

from __future__ import annotations

import time
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from retort.storage.models import Base


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable WAL, foreign keys, and a busy timeout for SQLite connections.

    The busy timeout matters for sharded/parallel runs (`retort run --shard` on a
    shared retort.db): without it SQLite fails a contended write *immediately*
    with "database is locked" instead of waiting briefly for the lock to clear,
    so concurrent shards lose run results.
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=30000")  # 30s: wait for the lock, don't fail
    cursor.close()


def get_engine(db_path: Path):
    """Create a SQLAlchemy engine for the given SQLite database path."""
    return create_engine(f"sqlite:///{db_path}", echo=False)


def create_tables(engine: Engine) -> None:
    """Create all tables from the ORM models (used for fresh databases).

    Safe under concurrent cold-start. When several ``retort run --shard``
    processes initialize the *same fresh* DB at once, ``create_all`` (checkfirst)
    can race — two processes both observe a table missing, both ``CREATE`` it, and
    one errors "table already exists". Retry a few times: ``checkfirst`` skips the
    tables a racing process already made, so this converges once the schema is in
    place. (Pre-creating the DB once, e.g. via ``retort init``, avoids the race
    entirely; this makes the cold-start path safe regardless.)
    """
    for attempt in range(5):
        try:
            Base.metadata.create_all(engine)
            return
        except OperationalError as exc:
            msg = str(exc).lower()
            if "already exists" not in msg and "database is locked" not in msg:
                raise
            if attempt == 4:
                raise
            time.sleep(0.2 * (attempt + 1))


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a session factory bound to the given engine."""
    return sessionmaker(bind=engine)


def get_session(engine: Engine) -> Session:
    """Create and return a new session bound to the given engine."""
    return get_session_factory(engine)()
