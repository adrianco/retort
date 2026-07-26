"""A small REST API for managing a book collection.

Framework : Flask
Storage   : SQLite, via the standard-library ``sqlite3`` module (no ORM).

The application is built with an *app factory* (:func:`create_app`) so that a
fresh, isolated database can be wired in for tests while production code uses
the default on-disk database.
"""

import os
import sqlite3

from flask import Flask, current_app, g, jsonify, request

# Default location of the SQLite database file. Overridable via env var so the
# same code can run against different databases without edits.
DEFAULT_DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    author TEXT    NOT NULL,
    year   INTEGER,
    isbn   TEXT
);
"""


# --------------------------------------------------------------------------- #
# Database helpers
# --------------------------------------------------------------------------- #
def get_db():
    """Return a per-request SQLite connection, opening one on first use."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DB_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(exc=None):
    """Close the request-scoped connection, if one was opened."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(db_path):
    """Create the ``books`` table if it does not already exist."""
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def book_to_dict(row):
    """Convert a ``sqlite3.Row`` into a plain, JSON-serialisable dict."""
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def validate_payload(data):
    """Validate an incoming book payload.

    Returns ``(values, errors)`` where ``values`` is a dict of cleaned book
    fields (or ``None`` when invalid) and ``errors`` is a list of human-readable
    messages (empty when the payload is valid).

    Rules:
      * ``title``  — required, non-empty string.
      * ``author`` — required, non-empty string.
      * ``year``   — optional; if present must be an integer.
      * ``isbn``   — optional; if present must be a string.
    """
    if not isinstance(data, dict):
        return None, ["Request body must be a JSON object"]

    errors = []

    title = data.get("title")
    if not isinstance(title, str) or title.strip() == "":
        errors.append("title is required and must be a non-empty string")

    author = data.get("author")
    if not isinstance(author, str) or author.strip() == "":
        errors.append("author is required and must be a non-empty string")

    year = data.get("year")
    # bool is a subclass of int, so reject it explicitly (True/False aren't years).
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors.append("year must be an integer")

    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors.append("isbn must be a string")

    if errors:
        return None, errors

    values = {
        "title": title.strip(),
        "author": author.strip(),
        "year": year,
        "isbn": isbn.strip() if isinstance(isbn, str) else isbn,
    }
    return values, []


def _json_body():
    """Return the parsed JSON body, or ``None`` if absent/malformed."""
    return request.get_json(silent=True)


# --------------------------------------------------------------------------- #
# Application factory
# --------------------------------------------------------------------------- #
def create_app(db_path=None):
    """Build and configure a Flask application instance."""
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or DEFAULT_DB_PATH

    init_db(app.config["DB_PATH"])
    app.teardown_appcontext(close_db)

    # ----------------------------- Health ---------------------------------- #
    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    # ----------------------------- Create ---------------------------------- #
    @app.post("/books")
    def create_book():
        data = _json_body()
        if data is None:
            return jsonify({"error": "Request body must be valid JSON"}), 400

        values, errors = validate_payload(data)
        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400

        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (values["title"], values["author"], values["year"], values["isbn"]),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return jsonify(book_to_dict(row)), 201

    # ------------------------------ List ----------------------------------- #
    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author:
            # Case-insensitive exact match on author.
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                (author,),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([book_to_dict(r) for r in rows]), 200

    # --------------------------- Retrieve one ------------------------------ #
    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": f"Book {book_id} not found"}), 404
        return jsonify(book_to_dict(row)), 200

    # ----------------------------- Update ---------------------------------- #
    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": f"Book {book_id} not found"}), 404

        data = _json_body()
        if data is None:
            return jsonify({"error": "Request body must be valid JSON"}), 400

        values, errors = validate_payload(data)
        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400

        # PUT replaces the full resource (year/isbn reset to null when omitted).
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (
                values["title"],
                values["author"],
                values["year"],
                values["isbn"],
                book_id,
            ),
        )
        db.commit()
        updated = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return jsonify(book_to_dict(updated)), 200

    # ----------------------------- Delete ---------------------------------- #
    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": f"Book {book_id} not found"}), 404

        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return jsonify({"message": f"Book {book_id} deleted"}), 200

    # ------------------------- JSON error handlers ------------------------- #
    # Ensure clients always receive JSON, even for framework-level errors.
    @app.errorhandler(400)
    def bad_request(_e):
        return jsonify({"error": "Bad request"}), 400

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def server_error(_e):
        return jsonify({"error": "Internal server error"}), 500

    return app


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    create_app().run(host=host, port=port, debug=False)
