"""Book collection REST API service.

Flask + SQLite (stdlib sqlite3).

Endpoints:
    GET    /health        -> {"status": "ok"}
    POST   /books         -> create a book (title, author required; year, isbn optional)
    GET    /books         -> list books (optional ?author= filter)
    GET    /books/<id>    -> fetch one book
    PUT    /books/<id>    -> update a book (partial updates supported)
    DELETE /books/<id>    -> delete a book
"""

import os
import sqlite3

from flask import Flask, current_app, g, jsonify, request

DEFAULT_DB_FILENAME = "books.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
"""


# ---------------------------------------------------------------------------
# App factory / database plumbing
# ---------------------------------------------------------------------------

def create_app(db_path=None):
    """Create and configure the Flask app.

    db_path: path to the SQLite file. Defaults to $BOOKS_DB or ./books.db.
    """
    app = Flask(__name__)
    app.config["DATABASE"] = db_path or os.environ.get("BOOKS_DB", DEFAULT_DB_FILENAME)
    app.teardown_appcontext(close_db)
    _init_db(app.config["DATABASE"])
    _register_routes(app)
    return app


def _init_db(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def get_db():
    """Per-request SQLite connection (row factory: sqlite3.Row)."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _book_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def _error(message, status):
    return jsonify({"error": message}), status


def _clean_str(value):
    """Return a stripped string, or None if value is not a string."""
    if isinstance(value, str):
        return value.strip()
    return None


def _parse_year(value):
    """Return an int year, or None if value is None.

    Accepts ints and digit strings. Anything else is invalid (returns None
    for a non-None input, which callers must distinguish).
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _year_is_valid(value):
    """True when `value` is a legitimate year input (int, digit string, or null)."""
    if value is None or isinstance(value, int) and not isinstance(value, bool):
        return True
    return isinstance(value, str) and value.strip().isdigit()


def _string_field(data, key, required):
    """Validate a string field. Returns (value, error_message).

    required=True  -> missing/empty/non-string is an error.
    required=False -> missing/null is fine (None); empty string becomes None;
                      non-string is an error.
    """
    if key not in data or data[key] is None:
        if required:
            return None, f"'{key}' is required"
        return None, None
    value = _clean_str(data[key])
    if value is None:
        return None, f"'{key}' must be a string"
    if not value:
        if required:
            return None, f"'{key}' must be a non-empty string"
        return None, None
    return value, None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def _register_routes(app):
    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _error("Request body must be a JSON object", 400)

        title, err = _string_field(data, "title", required=True)
        if err:
            return _error(err, 400)
        author, err = _string_field(data, "author", required=True)
        if err:
            return _error(err, 400)

        if "year" in data and not _year_is_valid(data["year"]):
            return _error("'year' must be an integer", 400)
        year = _parse_year(data.get("year"))

        isbn, err = _string_field(data, "isbn", required=False)
        if err:
            return _error(err, 400)

        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (title, author, year, isbn),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(_book_to_dict(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([_book_to_dict(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = get_db().execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return _error("Book not found", 404)
        return jsonify(_book_to_dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _error("Request body must be a JSON object", 400)

        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return _error("Book not found", 404)

        updates = {}
        if "title" in data:
            value, err = _string_field(data, "title", required=True)
            if err:
                return _error(err, 400)
            updates["title"] = value
        if "author" in data:
            value, err = _string_field(data, "author", required=True)
            if err:
                return _error(err, 400)
            updates["author"] = value
        if "year" in data:
            if not _year_is_valid(data["year"]):
                return _error("'year' must be an integer", 400)
            updates["year"] = _parse_year(data["year"])
        if "isbn" in data:
            value, err = _string_field(data, "isbn", required=False)
            if err:
                return _error(err, 400)
            updates["isbn"] = value

        if not updates:
            return _error("No fields to update", 400)

        set_clause = ", ".join(f"{col} = ?" for col in updates)
        db.execute(
            f"UPDATE books SET {set_clause} WHERE id = ?",
            (*updates.values(), book_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(_book_to_dict(row)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return _error("Book not found", 404)
        return jsonify({"message": "Book deleted"}), 200


# Module-level app so `flask run` and `python app.py` both work.
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
