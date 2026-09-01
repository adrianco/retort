"""Book collection REST API built with Flask and SQLite."""

import os
import sqlite3

from flask import Flask, g, jsonify, request

DEFAULT_DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")


def create_app(db_path=None):
    """Application factory. Accepts a database path for testing."""
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or DEFAULT_DB_PATH

    def get_db():
        if "db" not in g:
            conn = sqlite3.connect(app.config["DB_PATH"])
            conn.row_factory = sqlite3.Row
            g.db = conn
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        conn = sqlite3.connect(app.config["DB_PATH"])
        try:
            conn.execute(
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
            conn.commit()
        finally:
            conn.close()

    init_db()

    def row_to_dict(row):
        return {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }

    def validate_book(data, partial=False):
        """Validate and normalise a book payload.

        Returns (clean_dict, errors). With partial=True, missing fields are
        allowed (used by PUT to support partial updates); present fields are
        still validated.
        """
        errors = {}
        clean = {}
        if not isinstance(data, dict):
            return None, {"body": "JSON object expected"}

        for field in ("title", "author"):
            if field in data:
                value = data[field]
                if not isinstance(value, str) or not value.strip():
                    errors[field] = f"{field} must be a non-empty string"
                else:
                    clean[field] = value.strip()
            elif not partial:
                errors[field] = f"{field} is required"

        if "year" in data:
            year = data["year"]
            if year is None:
                clean["year"] = None
            elif isinstance(year, bool) or not isinstance(year, int):
                errors["year"] = "year must be an integer"
            elif year < 0 or year > 9999:
                errors["year"] = "year must be between 0 and 9999"
            else:
                clean["year"] = year

        if "isbn" in data:
            isbn = data["isbn"]
            if isbn is None:
                clean["isbn"] = None
            elif not isinstance(isbn, str):
                errors["isbn"] = "isbn must be a string"
            else:
                isbn = isbn.strip()
                digits = isbn.replace("-", "").replace(" ", "")
                if len(digits) not in (10, 13) or not (
                    digits[:-1].isdigit() and (digits[-1].isdigit() or digits[-1] in "Xx")
                ):
                    errors["isbn"] = "isbn must be a 10 or 13 character ISBN"
                else:
                    clean["isbn"] = isbn

        return clean, errors

    def error(status, message, details=None):
        body = {"error": message}
        if details:
            body["details"] = details
        return jsonify(body), status

    def get_json_or_error():
        data = request.get_json(silent=True)
        if data is None:
            return None, error(400, "Request body must be valid JSON")
        return data, None

    @app.get("/health")
    def health():
        try:
            get_db().execute("SELECT 1")
            return jsonify({"status": "ok"}), 200
        except sqlite3.Error:
            return jsonify({"status": "error"}), 503

    @app.post("/books")
    def create_book():
        data, err = get_json_or_error()
        if err:
            return err
        clean, errors = validate_book(data)
        if errors:
            return error(400, "Validation failed", errors)
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (clean["title"], clean["author"], clean.get("year"), clean.get("isbn")),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(row_to_dict(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                (author.strip(),),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([row_to_dict(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return error(404, "Book not found")
        return jsonify(row_to_dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return error(404, "Book not found")
        data, err = get_json_or_error()
        if err:
            return err
        clean, errors = validate_book(data, partial=True)
        if errors:
            return error(400, "Validation failed", errors)
        if not clean:
            return error(400, "No updatable fields provided")
        assignments = ", ".join(f"{k} = ?" for k in clean)
        db.execute(
            f"UPDATE books SET {assignments} WHERE id = ?",
            (*clean.values(), book_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_dict(row)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return error(404, "Book not found")
        return "", 204

    @app.errorhandler(404)
    def not_found(_e):
        return error(404, "Resource not found")

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return error(405, "Method not allowed")

    @app.errorhandler(500)
    def server_error(_e):
        return error(500, "Internal server error")

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
