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
    def close_db(_):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with sqlite3.connect(app.config["DB_PATH"]) as c:
        c.execute(
            "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)"
        )

    def error(msg, code):
        return jsonify(error=msg), code

    def validate(data):
        if not isinstance(data, dict):
            return None, "JSON object body required"
        for f in ("title", "author"):
            v = data.get(f)
            if not isinstance(v, str) or not v.strip():
                return None, f"{f} is required"
        year = data.get("year")
        if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
            return None, "year must be an integer"
        isbn = data.get("isbn")
        if isbn is not None and not isinstance(isbn, str):
            return None, "isbn must be a string"
        return {"title": data["title"].strip(), "author": data["author"].strip(),
                "year": year, "isbn": isbn}, None

    def fetch(book_id):
        row = get_db().execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        return dict(row) if row else None

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/books")
    def create():
        book, err = validate(request.get_json(silent=True))
        if err:
            return error(err, 400)
        db = get_db()
        cur = db.execute("INSERT INTO books (title, author, year, isbn) VALUES (?,?,?,?)",
                         tuple(book[f] for f in FIELDS))
        db.commit()
        return jsonify(fetch(cur.lastrowid)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        if author:
            rows = get_db().execute("SELECT * FROM books WHERE author=? ORDER BY id", (author,))
        else:
            rows = get_db().execute("SELECT * FROM books ORDER BY id")
        return jsonify([dict(r) for r in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        book = fetch(book_id)
        return jsonify(book) if book else error("book not found", 404)

    @app.put("/books/<int:book_id>")
    def update(book_id):
        if not fetch(book_id):
            return error("book not found", 404)
        book, err = validate(request.get_json(silent=True))
        if err:
            return error(err, 400)
        db = get_db()
        db.execute("UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
                   (*(book[f] for f in FIELDS), book_id))
        db.commit()
        return jsonify(fetch(book_id))

    @app.delete("/books/<int:book_id>")
    def delete(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id=?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return error("book not found", 404)
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(port=int(os.environ.get("PORT", 5000)))
