"""Book collection REST API (Flask + SQLite)."""
import os
import sqlite3

from flask import Flask, g, jsonify, request

FIELDS = ("title", "author", "year", "isbn")


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
        get_db().execute(
            "CREATE TABLE IF NOT EXISTS books ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, "
            "author TEXT NOT NULL, year INTEGER, isbn TEXT)"
        )
        get_db().commit()

    def validate(data):
        if not isinstance(data, dict):
            return None, "Request body must be a JSON object"
        errors = []
        for f in ("title", "author"):
            v = data.get(f)
            if not isinstance(v, str) or not v.strip():
                errors.append(f"'{f}' is required and must be a non-empty string")
        year = data.get("year")
        if year is not None and (not isinstance(year, int) or isinstance(year, bool)):
            errors.append("'year' must be an integer")
        isbn = data.get("isbn")
        if isbn is not None and not isinstance(isbn, str):
            errors.append("'isbn' must be a string")
        if errors:
            return None, "; ".join(errors)
        return {f: (data.get(f).strip() if f in ("title", "author") else data.get(f)) for f in FIELDS}, None

    def to_dict(row):
        return {k: row[k] for k in ("id",) + FIELDS}

    def find(book_id):
        return get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

    def not_found():
        return jsonify(error="Book not found"), 404

    @app.get("/health")
    def health():
        get_db().execute("SELECT 1")
        return jsonify(status="ok")

    @app.post("/books")
    def create_book():
        book, err = validate(request.get_json(silent=True))
        if err:
            return jsonify(error=err), 400
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            tuple(book[f] for f in FIELDS),
        )
        db.commit()
        return jsonify(to_dict(find(cur.lastrowid))), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        if author:
            rows = get_db().execute(
                "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = get_db().execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([to_dict(r) for r in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = find(book_id)
        return jsonify(to_dict(row)) if row else not_found()

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        if not find(book_id):
            return not_found()
        book, err = validate(request.get_json(silent=True))
        if err:
            return jsonify(error=err), 400
        db = get_db()
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            tuple(book[f] for f in FIELDS) + (book_id,),
        )
        db.commit()
        return jsonify(to_dict(find(book_id)))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        if not find(book_id):
            return not_found()
        db = get_db()
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
