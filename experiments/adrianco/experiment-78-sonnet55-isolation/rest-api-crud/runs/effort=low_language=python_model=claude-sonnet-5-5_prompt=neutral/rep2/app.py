import os
import sqlite3

from flask import Flask, jsonify, request

FIELDS = ("title", "author", "year", "isbn")


def create_app(db_path=None):
    app = Flask(__name__)
    db_path = db_path or os.environ.get("BOOKS_DB", "books.db")

    def db():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    with db() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)"
        )

    def validate(data):
        if not isinstance(data, dict):
            return None, "body must be a JSON object"
        for f in ("title", "author"):
            v = data.get(f)
            if not isinstance(v, str) or not v.strip():
                return None, f"{f} is required"
        year = data.get("year")
        if year is not None and (not isinstance(year, int) or isinstance(year, bool)):
            return None, "year must be an integer"
        isbn = data.get("isbn")
        if isbn is not None and not isinstance(isbn, str):
            return None, "isbn must be a string"
        return {f: data.get(f) for f in FIELDS}, None

    def get_book(conn, book_id):
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return dict(row) if row else None

    def not_found():
        return jsonify(error="book not found"), 404

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/books")
    def create():
        book, err = validate(request.get_json(silent=True))
        if err:
            return jsonify(error=err), 400
        with db() as conn:
            cur = conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                tuple(book[f] for f in FIELDS),
            )
            return jsonify(get_book(conn, cur.lastrowid)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        with db() as conn:
            if author:
                rows = conn.execute(
                    "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
                )
            else:
                rows = conn.execute("SELECT * FROM books ORDER BY id")
            return jsonify([dict(r) for r in rows])

    @app.get("/books/<int:book_id>")
    def get_one(book_id):
        with db() as conn:
            book = get_book(conn, book_id)
        return jsonify(book) if book else not_found()

    @app.put("/books/<int:book_id>")
    def update(book_id):
        book, err = validate(request.get_json(silent=True))
        if err:
            return jsonify(error=err), 400
        with db() as conn:
            if not get_book(conn, book_id):
                return not_found()
            conn.execute(
                "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                (*(book[f] for f in FIELDS), book_id),
            )
            return jsonify(get_book(conn, book_id))

    @app.delete("/books/<int:book_id>")
    def delete(book_id):
        with db() as conn:
            cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return ("", 204) if cur.rowcount else not_found()

    return app


if __name__ == "__main__":
    create_app().run(port=int(os.environ.get("PORT", 5000)))
