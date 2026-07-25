"""SQLite connection handling and schema management."""

from __future__ import annotations

import sqlite3

import click
from flask import current_app, g

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


def get_db() -> sqlite3.Connection:
    """Return the connection for the current app context, opening it if needed."""
    if "db" not in g:
        connection = sqlite3.connect(
            current_app.config["DATABASE"],
            isolation_level=None,  # autocommit; we manage transactions explicitly
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


def close_db(exc: BaseException | None = None) -> None:
    """Close the connection attached to the current app context, if any."""
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db() -> None:
    """Create the schema if it does not already exist."""
    get_db().executescript(SCHEMA)


@click.command("init-db")
def init_db_command() -> None:
    """Flask CLI command: `flask --app app init-db`."""
    init_db()
    click.echo(f"Initialised database at {current_app.config['DATABASE']}")


def register(app) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
