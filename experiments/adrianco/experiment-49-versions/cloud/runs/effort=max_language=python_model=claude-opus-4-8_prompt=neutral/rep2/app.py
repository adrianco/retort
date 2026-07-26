"""A small REST API for managing a book collection.

Framework:  Flask (already available in the environment)
Storage:    SQLite via the standard-library ``sqlite3`` module

The application is built with the *application factory* pattern
(:func:`create_app`) so it can be instantiated against an isolated
database — this is what makes the test-suite hermetic.

Endpoints
---------
POST   /books          Create a book               -> 201
GET    /books          List books (?author= filter) -> 200
GET    /books/<id>     Fetch one book              -> 200 / 404
PUT    /books/<id>     Replace a book              -> 200 / 400 / 404
DELETE /books/<id>     Delete a book               -> 200 / 404
GET    /health         Liveness/DB health check    -> 200 / 500
"""

from __future__ import annotations

import os
import sqlite3

from flask import Flask, current_app, g, jsonify, request

DEFAULT_DB = "books.db"

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
def get_db() -> sqlite3.Connection:
    """Return a per-request SQLite connection, creating it on first use."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(exception=None) -> None:  # noqa: ARG001 - Flask teardown signature
    """Close the request-scoped connection, if one was opened."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app: Flask) -> None:
    """Ensure the ``books`` table exists for the configured database."""
    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA)
        db.commit()
        close_db()


# --------------------------------------------------------------------------- #
# Serialization & validation
# --------------------------------------------------------------------------- #
def book_to_dict(row: sqlite3.Row) -> dict:
    """Convert a DB row into a JSON-serializable dict."""
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def _is_int(value) -> bool:
    """True for genuine integers (``bool`` is intentionally excluded)."""
    return isinstance(value, int) and not isinstance(value, bool)


def validate_book(data) -> list[str]:
    """Validate a create/replace payload.

    ``title`` and ``author`` are required, non-empty strings.  ``year`` and
    ``isbn`` are optional but, when supplied, must be an integer and a string
    respectively.  Returns a (possibly empty) list of human-readable errors.
    """
    if not isinstance(data, dict):
        return ["Request body must be a JSON object."]

    errors: list[str] = []

    title = data.get("title")
    if title is None:
        errors.append("title is required.")
    elif not isinstance(title, str) or not title.strip():
        errors.append("title must be a non-empty string.")

    author = data.get("author")
    if author is None:
        errors.append("author is required.")
    elif not isinstance(author, str) or not author.strip():
        errors.append("author must be a non-empty string.")

    if data.get("year") is not None and not _is_int(data["year"]):
        errors.append("year must be an integer.")

    if data.get("isbn") is not None and not isinstance(data["isbn"], str):
        errors.append("isbn must be a string.")

    return errors


# --------------------------------------------------------------------------- #
# Application factory
# --------------------------------------------------------------------------- #
def create_app(database: str | None = None) -> Flask:
    """Build and configure a Flask application instance."""
    app = Flask(__name__)
    app.config["DATABASE"] = database or os.environ.get("BOOKS_DB", DEFAULT_DB)

    app.teardown_appcontext(close_db)
    init_db(app)

    # ----- Books collection ------------------------------------------------ #
    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        errors = validate_book(data)
        if errors:
            return jsonify({"errors": errors}), 400

        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (
                data["title"].strip(),
                data["author"].strip(),
                data.get("year"),
                data.get("isbn"),
            ),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        response = jsonify(book_to_dict(row))
        response.headers["Location"] = f"/books/{row['id']}"
        return response, 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author is not None:
            # Case-insensitive exact match on author.
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                (author,),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([book_to_dict(r) for r in rows]), 200

    # ----- Single book ----------------------------------------------------- #
    @app.get("/books/<int:book_id>")
    def get_book(book_id: int):
        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found."}), 404
        return jsonify(book_to_dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int):
        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found."}), 404

        data = request.get_json(silent=True)
        errors = validate_book(data)
        if errors:
            return jsonify({"errors": errors}), 400

        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? "
            "WHERE id = ?",
            (
                data["title"].strip(),
                data["author"].strip(),
                data.get("year"),
                data.get("isbn"),
                book_id,
            ),
        )
        db.commit()
        updated = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return jsonify(book_to_dict(updated)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int):
        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found."}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return jsonify({"deleted": True, "id": book_id}), 200

    # ----- Health ---------------------------------------------------------- #
    @app.get("/health")
    def health():
        try:
            get_db().execute("SELECT 1")
        except sqlite3.Error as exc:  # pragma: no cover - defensive
            return jsonify({"status": "error", "detail": str(exc)}), 500
        return jsonify({"status": "ok"}), 200

    # ----- JSON error handlers (so 404/405 stay JSON) ---------------------- #
    @app.errorhandler(404)
    def handle_404(_):
        return jsonify({"error": "Not found."}), 404

    @app.errorhandler(405)
    def handle_405(_):
        return jsonify({"error": "Method not allowed."}), 405

    return app


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
