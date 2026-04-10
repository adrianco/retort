"""Database engine and session management."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from retort.storage.models import Base


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable WAL mode and foreign keys for SQLite connections."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_engine(db_path: Path):
    """Create a SQLAlchemy engine for the given SQLite database path."""
    return create_engine(f"sqlite:///{db_path}", echo=False)


def create_tables(engine: Engine) -> None:
    """Create all tables from the ORM models (used for fresh databases)."""
    Base.metadata.create_all(engine)


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a session factory bound to the given engine."""
    return sessionmaker(bind=engine)
