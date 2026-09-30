import os
import sqlite3

from flask import Flask, g, jsonify, request

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
)
"""


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.environ.get("BOOKS_DB", "books.db")

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB_PATH"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        get_db().execute(SCHEMA)
        get_db().commit()

    def error(msg, code):
        return jsonify({"error": msg}), code

    def validate(data):
        """Return (clean_dict, error_message)."""
        if not isinstance(data, dict):
            return None, "JSON object body required"
        clean = {}
        for f in ("title", "author"):
            v = data.get(f)
            if not isinstance(v, str) or not v.strip():
                return None, f"{f} is required and must be a non-empty string"
            clean[f] = v.strip()
        year = data.get("year")
        if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
            return None, "year must be an integer"
        isbn = data.get("isbn")
        if isbn is not None and not isinstance(isbn, str):
            return None, "isbn must be a string"
        clean["year"], clean["isbn"] = year, isbn
        return clean, None

    def fetch(book_id):
        return get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/books")
    def create_book():
        clean, err = validate(request.get_json(silent=True))
        if err:
            return error(err, 400)
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (clean["title"], clean["author"], clean["year"], clean["isbn"]),
        )
        db.commit()
        return jsonify(dict(fetch(cur.lastrowid))), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        if author:
            rows = get_db().execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = get_db().execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = fetch(book_id)
        if row is None:
            return error("book not found", 404)
        return jsonify(dict(row))

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        if fetch(book_id) is None:
            return error("book not found", 404)
        clean, err = validate(request.get_json(silent=True))
        if err:
            return error(err, 400)
        db = get_db()
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (clean["title"], clean["author"], clean["year"], clean["isbn"], book_id),
        )
        db.commit()
        return jsonify(dict(fetch(book_id)))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return error("book not found", 404)
        return "", 204

    @app.errorhandler(404)
    def not_found(_e):
        return error("not found", 404)

    @app.errorhandler(405)
    def bad_method(_e):
        return error("method not allowed", 405)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
