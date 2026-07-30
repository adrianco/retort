"""SQLite connection management.

One connection is opened per request and stored on Flask's ``g``, so handlers
share a connection (and therefore a transaction scope) but threads never do.
"""

from __future__ import annotations

import os
import sqlite3

import click
from flask import Flask, current_app, g
from flask.cli import with_appcontext

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    author     TEXT NOT NULL,
    year       INTEGER,
    isbn       TEXT UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_books_author ON books (author COLLATE NOCASE);
"""


def connect(database: str) -> sqlite3.Connection:
    """Open a configured connection to ``database``, creating its directory."""
    on_disk = database != ":memory:" and not database.startswith("file:")
    if on_disk:
        parent = os.path.dirname(os.path.abspath(database))
        if parent:
            os.makedirs(parent, exist_ok=True)

    conn = sqlite3.connect(database, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if on_disk:
        # WAL keeps readers from blocking the writer; harmless if unsupported.
        try:
            conn.execute("PRAGMA journal_mode = WAL")
        except sqlite3.DatabaseError:  # pragma: no cover - filesystem dependent
            pass
    return conn


def get_db() -> sqlite3.Connection:
    """Return this request's connection, opening one on first use."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(exc: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app: Flask | None = None) -> None:
    """Create the schema if it is not already there."""
    config = (app or current_app).config
    conn = connect(config["DATABASE"])
    try:
        with conn:
            conn.executescript(SCHEMA)
    finally:
        conn.close()


@click.command("init-db")
@with_appcontext
def init_db_command() -> None:
    """Create the books table in the configured database."""
    init_db()
    click.echo(f"Initialised {current_app.config['DATABASE']}")


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
