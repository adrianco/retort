"""A small REST API for managing a book collection.

Built with Flask and the standard-library ``sqlite3`` module. Create the WSGI
application with :func:`create_app`; pass ``db_path=":memory:"`` for tests.
"""

import sqlite3

from flask import Flask, g, jsonify, request


def _connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db(conn):
    conn.execute(
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
    conn.commit()


def _book_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def _validate(payload):
    """Return (cleaned, error). ``error`` is None when the payload is valid."""
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object"

    title = payload.get("title")
    author = payload.get("author")

    if not isinstance(title, str) or not title.strip():
        return None, "title is required and must be a non-empty string"
    if not isinstance(author, str) or not author.strip():
        return None, "author is required and must be a non-empty string"

    year = payload.get("year")
    if year is not None and not isinstance(year, int):
        return None, "year must be an integer"

    isbn = payload.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        return None, "isbn must be a string"

    return {
        "title": title.strip(),
        "author": author.strip(),
        "year": year,
        "isbn": isbn,
    }, None


def create_app(db_path="books.db"):
    app = Flask(__name__)

    # A shared in-memory database must reuse one connection for the app's life,
    # otherwise each connection gets its own empty database.
    shared_conn = None
    if db_path == ":memory:":
        shared_conn = _connect(db_path)
        _init_db(shared_conn)
    else:
        init_conn = _connect(db_path)
        _init_db(init_conn)
        init_conn.close()

    def get_db():
        if shared_conn is not None:
            return shared_conn
        if "db" not in g:
            g.db = _connect(db_path)
        return g.db

    @app.teardown_appcontext
    def close_db(exception):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        cleaned, error = _validate(request.get_json(silent=True))
        if error:
            return jsonify({"error": error}), 400

        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (cleaned["title"], cleaned["author"], cleaned["year"], cleaned["isbn"]),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return jsonify(_book_to_dict(row)), 201

    @app.get("/books")
    def list_books():
        db = get_db()
        author = request.args.get("author")
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([_book_to_dict(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(_book_to_dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Book not found"}), 404

        cleaned, error = _validate(request.get_json(silent=True))
        if error:
            return jsonify({"error": error}), 400

        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (
                cleaned["title"],
                cleaned["author"],
                cleaned["year"],
                cleaned["isbn"],
                book_id,
            ),
        )
        db.commit()
        updated = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return jsonify(_book_to_dict(updated)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Book not found"}), 404
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=True)
