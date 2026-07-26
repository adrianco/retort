"""A small REST API for managing a book collection.

Built with Flask and backed by SQLite. The application is exposed through the
``create_app`` factory so that tests (and multiple environments) can supply
their own database file.

Run locally::

    python app.py                # serves on http://127.0.0.1:5000
    flask --app app run          # alternative, uses the create_app factory

Endpoints:
    GET    /health          -> service + database health check
    POST   /books           -> create a book
    GET    /books           -> list books (optional ?author= filter)
    GET    /books/<id>      -> fetch a single book
    PUT    /books/<id>      -> replace a book
    DELETE /books/<id>      -> delete a book
"""

import os
import sqlite3

from flask import Flask, current_app, g, jsonify, request

DEFAULT_DB = "books.db"

# Year sanity bounds. Wide enough to accept genuinely old works while
# rejecting obvious nonsense.
MIN_YEAR = 0
MAX_YEAR = 9999


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    """Return the SQLite connection for the current request/app context.

    A fresh connection is created per context and stored on ``flask.g`` so it
    is reused within the same request and closed automatically on teardown.
    """
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(exception=None):
    """Close the connection stored on ``flask.g`` (registered as teardown)."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the ``books`` table if it does not already exist."""
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL,
            year   INTEGER,
            isbn   TEXT
        )
        """
    )
    db.commit()


def get_book_row(db, book_id):
    """Return the row for ``book_id`` or ``None`` when it does not exist."""
    return db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()


def book_to_dict(row):
    """Serialize a ``sqlite3.Row`` into a plain JSON-friendly dict."""
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_book_payload(data):
    """Validate and normalize an incoming book payload.

    ``title`` and ``author`` are required non-empty strings. ``year`` and
    ``isbn`` are optional; when supplied they must be an integer and a string
    respectively. Omitted optional fields default to ``None``.

    Returns a tuple ``(clean, errors)`` where ``clean`` is the normalized
    payload and ``errors`` is a list of human-readable messages (empty when the
    payload is valid).
    """
    errors = []
    clean = {}

    # --- required: title ---
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append("title is required and must be a non-empty string")
    else:
        clean["title"] = title.strip()

    # --- required: author ---
    author = data.get("author")
    if not isinstance(author, str) or not author.strip():
        errors.append("author is required and must be a non-empty string")
    else:
        clean["author"] = author.strip()

    # --- optional: year ---
    year = data.get("year")
    if year is None:
        clean["year"] = None
    elif isinstance(year, bool) or not isinstance(year, int):
        # bool is a subclass of int in Python; reject True/False explicitly.
        errors.append("year must be an integer")
    elif not (MIN_YEAR <= year <= MAX_YEAR):
        errors.append(f"year must be between {MIN_YEAR} and {MAX_YEAR}")
    else:
        clean["year"] = year

    # --- optional: isbn ---
    isbn = data.get("isbn")
    if isbn is None:
        clean["isbn"] = None
    elif not isinstance(isbn, str):
        errors.append("isbn must be a string")
    else:
        clean["isbn"] = isbn.strip()

    return clean, errors


def _json_body():
    """Return the request body as a dict, or ``None`` if it is not a JSON object.

    Using ``silent=True`` means malformed JSON (or a missing/incorrect
    Content-Type) yields ``None`` rather than raising, which we translate into a
    clean 400 response at the call site.
    """
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
def create_app(database=None):
    """Create and configure the Flask application.

    ``database`` overrides the SQLite file path (falling back to the ``BOOKS_DB``
    environment variable and finally :data:`DEFAULT_DB`). Passing an explicit
    path is what makes the app trivially testable against a temp database.
    """
    app = Flask(__name__)
    app.config["DATABASE"] = database or os.environ.get("BOOKS_DB", DEFAULT_DB)
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    # ---- Health check ----------------------------------------------------
    @app.get("/health")
    def health():
        try:
            get_db().execute("SELECT 1")
            return jsonify(status="ok", database="connected"), 200
        except sqlite3.Error:
            return jsonify(status="error", database="disconnected"), 503

    # ---- Create ----------------------------------------------------------
    @app.post("/books")
    def create_book():
        data = _json_body()
        if data is None:
            return jsonify(error="Request body must be a JSON object"), 400

        clean, errors = validate_book_payload(data)
        if errors:
            return jsonify(error="Validation failed", details=errors), 400

        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (clean["title"], clean["author"], clean["year"], clean["isbn"]),
        )
        db.commit()
        row = get_book_row(db, cur.lastrowid)
        return jsonify(book_to_dict(row)), 201

    # ---- List (with optional author filter) ------------------------------
    @app.get("/books")
    def list_books():
        db = get_db()
        author = request.args.get("author")
        if author:
            # Exact match, case-insensitive, so ?author=tolkien finds "Tolkien".
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                (author,),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([book_to_dict(r) for r in rows]), 200

    # ---- Read ------------------------------------------------------------
    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = get_book_row(get_db(), book_id)
        if row is None:
            return jsonify(error="Book not found"), 404
        return jsonify(book_to_dict(row)), 200

    # ---- Update (full replace) ------------------------------------------
    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        data = _json_body()
        if data is None:
            return jsonify(error="Request body must be a JSON object"), 400

        db = get_db()
        if get_book_row(db, book_id) is None:
            return jsonify(error="Book not found"), 404

        clean, errors = validate_book_payload(data)
        if errors:
            return jsonify(error="Validation failed", details=errors), 400

        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (clean["title"], clean["author"], clean["year"], clean["isbn"], book_id),
        )
        db.commit()
        return jsonify(book_to_dict(get_book_row(db, book_id))), 200

    # ---- Delete ----------------------------------------------------------
    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        if get_book_row(db, book_id) is None:
            return jsonify(error="Book not found"), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    # ---- JSON error handlers --------------------------------------------
    @app.errorhandler(404)
    def handle_404(_error):
        return jsonify(error="Not found"), 404

    @app.errorhandler(405)
    def handle_405(_error):
        return jsonify(error="Method not allowed"), 405

    @app.errorhandler(500)
    def handle_500(_error):  # pragma: no cover - defensive
        return jsonify(error="Internal server error"), 500

    return app


if __name__ == "__main__":
    # `python app.py` -> development server.
    create_app().run(host="127.0.0.1", port=5000, debug=True)
