"""REST API for managing a book collection (Flask + SQLite)."""

import os

from flask import Flask, g, jsonify, request

import db

DEFAULT_DATABASE = os.environ.get("BOOKS_DB", "books.db")


def validate_payload(data):
    """Return (cleaned, errors) for a create/update payload.

    title and author are required non-empty strings; year (int) and isbn
    (string) are optional and default to None.
    """
    if not isinstance(data, dict):
        return None, ["request body must be a JSON object"]

    errors = []
    cleaned = {"year": None, "isbn": None}

    for field in ("title", "author"):
        value = data.get(field)
        if value is None:
            errors.append(f"{field} is required")
        elif not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be a non-empty string")
        else:
            cleaned[field] = value.strip()

    year = data.get("year")
    if year is not None:
        if isinstance(year, bool) or not isinstance(year, int):
            errors.append("year must be an integer")
        else:
            cleaned["year"] = year

    isbn = data.get("isbn")
    if isbn is not None:
        if not isinstance(isbn, str) or not isbn.strip():
            errors.append("isbn must be a non-empty string")
        else:
            cleaned["isbn"] = isbn.strip()

    return cleaned, errors


def create_app(database=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database or DEFAULT_DATABASE
    db.init_db(app.config["DATABASE"])

    def get_conn():
        if "conn" not in g:
            g.conn = db.connect(app.config["DATABASE"])
        return g.conn

    @app.teardown_appcontext
    def close_conn(_exc):
        conn = g.pop("conn", None)
        if conn is not None:
            conn.close()

    @app.get("/health")
    def health():
        get_conn().execute("SELECT 1").fetchone()
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"errors": ["invalid or missing JSON body"]}), 400

        cleaned, errors = validate_payload(data)
        if errors:
            return jsonify({"errors": errors}), 400

        conn = get_conn()
        with conn:
            cur = conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (cleaned["title"], cleaned["author"], cleaned["year"], cleaned["isbn"]),
            )
        row = conn.execute(
            "SELECT * FROM books WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return jsonify(db.row_to_book(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        conn = get_conn()
        if author:
            rows = conn.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([db.row_to_book(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = get_conn().execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(db.row_to_book(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"errors": ["invalid or missing JSON body"]}), 400

        conn = get_conn()
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404

        cleaned, errors = validate_payload(data)
        if errors:
            return jsonify({"errors": errors}), 400

        with conn:
            conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (
                    cleaned["title"],
                    cleaned["author"],
                    cleaned["year"],
                    cleaned["isbn"],
                    book_id,
                ),
            )
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(db.row_to_book(row)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        conn = get_conn()
        with conn:
            cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        if cur.rowcount == 0:
            return jsonify({"error": "book not found"}), 404
        return "", 204

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(405)
    def not_allowed(_e):
        return jsonify({"error": "method not allowed"}), 405

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
