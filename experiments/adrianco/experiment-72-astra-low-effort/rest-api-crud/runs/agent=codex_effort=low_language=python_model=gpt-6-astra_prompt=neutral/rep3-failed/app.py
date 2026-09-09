"""SQLite-backed book collection REST API."""
import os
import sqlite3

from flask import Flask, g, jsonify, request, url_for
from werkzeug.exceptions import HTTPException


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(DATABASE=os.environ.get("BOOKS_DATABASE", "books.sqlite3"))
    if test_config:
        app.config.update(test_config)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        db = get_db()
        db.execute("""CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL CHECK(length(trim(title)) > 0),
            author TEXT NOT NULL CHECK(length(trim(author)) > 0),
            year INTEGER,
            isbn TEXT
        )""")
        db.commit()

    @app.errorhandler(HTTPException)
    def http_error(error):
        response = error.get_response()
        response.data = app.json.dumps({"error": error.description})
        response.content_type = "application/json"
        return response

    def payload():
        from werkzeug.exceptions import BadRequest
        data = request.get_json()
        if not isinstance(data, dict):
            raise BadRequest("Body must be a JSON object.")
        unknown = data.keys() - {"title", "author", "year", "isbn"}
        if unknown:
            raise BadRequest("Unknown fields: " + ", ".join(sorted(unknown)))
        for field in ("title", "author"):
            if not isinstance(data.get(field), str) or not data[field].strip():
                raise BadRequest(f"{field} must be a non-empty string.")
        year = data.get("year")
        if year is not None and (type(year) is not int or not -9223372036854775808 <= year <= 9223372036854775807):
            raise BadRequest("year must be an integer within SQLite's signed 64-bit range or null.")
        isbn = data.get("isbn")
        if isbn is not None and (not isinstance(isbn, str) or not isbn.strip()):
            raise BadRequest("isbn must be a non-empty string or null.")
        return (data["title"].strip(), data["author"].strip(), year,
                isbn.strip() if isbn is not None else None)

    def book_by_id(book_id):
        from werkzeug.exceptions import NotFound
        # SQLite cannot bind Python integers outside its signed 64-bit range.
        if book_id > 9223372036854775807:
            raise NotFound("Book not found.")
        book = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if book is None:
            raise NotFound("Book not found.")
        return dict(book)

    @app.get("/health")
    def health():
        get_db().execute("SELECT 1")
        return jsonify(status="ok")

    @app.post("/books")
    def create_book():
        values = payload()
        db = get_db()
        with db:
            cursor = db.execute("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", values)
        book = book_by_id(cursor.lastrowid)
        return jsonify(book), 201, {"Location": url_for("get_book", book_id=book["id"])}

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        if author is None:
            rows = get_db().execute("SELECT * FROM books ORDER BY id").fetchall()
        else:
            rows = get_db().execute("SELECT * FROM books WHERE author = ? ORDER BY id", (author,)).fetchall()
        return jsonify([dict(row) for row in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        return jsonify(book_by_id(book_id))

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        book_by_id(book_id)
        values = payload()
        db = get_db()
        with db:
            db.execute("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", (*values, book_id))
        return jsonify(book_by_id(book_id))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        book_by_id(book_id)
        db = get_db()
        with db:
            db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)
