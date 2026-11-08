"""A small SQLite-backed book collection API."""
import os
import sqlite3

from flask import Flask, g, jsonify, request


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
    def close_db(_error):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        get_db().execute(
            """CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )"""
        )
        get_db().commit()

    def validate_book():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return None, "Request body must be a JSON object"
        for field in ("title", "author"):
            if not isinstance(data.get(field), str) or not data[field].strip():
                return None, f"{field} is required and must be a non-empty string"
        year = data.get("year")
        if year is not None and (not isinstance(year, int) or isinstance(year, bool)):
            return None, "year must be an integer or null"
        isbn = data.get("isbn")
        if isbn is not None and not isinstance(isbn, str):
            return None, "isbn must be a string or null"
        return (data["title"].strip(), data["author"].strip(), year, isbn), None

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.route("/books", methods=["GET", "POST"])
    def books():
        db = get_db()
        if request.method == "GET":
            author = request.args.get("author")
            if author is None:
                rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
            else:
                rows = db.execute("SELECT * FROM books WHERE author = ? ORDER BY id", (author,)).fetchall()
            return jsonify([dict(row) for row in rows])
        values, error = validate_book()
        if error:
            return jsonify(error=error), 400
        cursor = db.execute("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", values)
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify(dict(row)), 201

    @app.route("/books/<int:book_id>", methods=["GET", "PUT", "DELETE"])
    def book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify(error="Book not found"), 404
        if request.method == "GET":
            return jsonify(dict(row))
        if request.method == "DELETE":
            db.execute("DELETE FROM books WHERE id = ?", (book_id,))
            db.commit()
            return jsonify(message="Book deleted")
        values, error = validate_book()
        if error:
            return jsonify(error=error), 400
        db.execute("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", (*values, book_id))
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(dict(row))

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(error="Not found"), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify(error="Method not allowed"), 405

    return app


if __name__ == "__main__":
    create_app().run()
