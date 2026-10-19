"""Book collection REST API service.

A small Flask service exposing CRUD endpoints for a book collection,
persisted in SQLite.

Run directly:
    python app.py            # serves on http://localhost:5000
"""

import os
import sqlite3

from flask import Flask, g, jsonify, request

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")

TEXT_FIELDS = ("title", "author")
OPTIONAL_FIELDS = ("year", "isbn")
ALL_FIELDS = TEXT_FIELDS + OPTIONAL_FIELDS


def create_app(db_path=None):
    """Application factory. ``db_path`` defaults to $BOOKS_DB or books.db."""
    app = Flask(__name__)
    app.config["DATABASE"] = db_path or os.environ.get("BOOKS_DB", DEFAULT_DB_PATH)

    # ------------------------------------------------------------------ db
    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(exc=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        db = get_db()
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )
            """
        )
        db.commit()

    # ------------------------------------------------------------- helpers
    def row_to_book(row):
        return {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }

    def error(message, status):
        return jsonify({"error": message}), status

    def parse_body():
        """Return (data, error_response); error_response is None on success."""
        data = request.get_json(silent=True)
        if data is None or not isinstance(data, dict):
            return None, error("Request body must be a JSON object", 400)
        return data, None

    def validate_text(value):
        """True if value is a non-empty (after strip) string."""
        return isinstance(value, str) and bool(value.strip())

    def validate_year(value):
        """Return (value, error_message)."""
        if value is None:
            return None, None
        if isinstance(value, bool) or not isinstance(value, int):
            return None, "'year' must be an integer"
        return value, None

    def validate_isbn(value):
        """Return (value, error_message)."""
        if value is None:
            return None, None
        if not isinstance(value, str) or not value.strip():
            return None, "'isbn' must be a non-empty string"
        return value, None

    # ----------------------------------------------------------- endpoints
    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/books")
    def create_book():
        data, err = parse_body()
        if err:
            return err

        errors = []
        for field in TEXT_FIELDS:
            value = data.get(field)
            if value is None:
                errors.append(f"'{field}' is required")
            elif not validate_text(value):
                errors.append(f"'{field}' must be a non-empty string")

        year, year_err = validate_year(data.get("year"))
        if year_err:
            errors.append(year_err)
        isbn, isbn_err = validate_isbn(data.get("isbn"))
        if isbn_err:
            errors.append(isbn_err)

        if errors:
            return error("; ".join(errors), 400)

        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"], data["author"], year, isbn),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return jsonify(row_to_book(row)), 201

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
        return jsonify([row_to_book(row) for row in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = get_db().execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return error("Book not found", 404)
        return jsonify(row_to_book(row))

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        data, err = parse_body()
        if err:
            return err

        if not data:
            return error("Request body must contain at least one field to update", 400)

        unknown = set(data) - set(ALL_FIELDS)
        if unknown:
            return error(f"Unknown fields: {', '.join(sorted(unknown))}", 400)

        errors = []
        for field in TEXT_FIELDS:
            if field in data and not validate_text(data[field]):
                errors.append(f"'{field}' must be a non-empty string")
        year, year_err = validate_year(data.get("year"))
        if year_err:
            errors.append(year_err)
        isbn, isbn_err = validate_isbn(data.get("isbn"))
        if isbn_err:
            errors.append(isbn_err)
        if errors:
            return error("; ".join(errors), 400)

        db = get_db()
        existing = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if existing is None:
            return error("Book not found", 404)

        sets = []
        params = []
        for field in ALL_FIELDS:
            if field in data:
                sets.append(f"{field} = ?")
                params.append(data[field])
        params.append(book_id)
        db.execute(f"UPDATE books SET {', '.join(sets)} WHERE id = ?", params)
        db.commit()

        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_book(row))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return error("Book not found", 404)
        return "", 204

    # ------------------------------------------------- JSON error handlers
    @app.errorhandler(404)
    def not_found(_exc):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_exc):
        return jsonify({"error": "Method not allowed"}), 405

    with app.app_context():
        init_db()
    return app


def main():
    application = create_app()
    port = int(os.environ.get("PORT", "5000"))
    application.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
