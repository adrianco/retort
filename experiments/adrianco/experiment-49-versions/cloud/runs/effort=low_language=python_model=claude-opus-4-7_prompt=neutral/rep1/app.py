import os
import sqlite3
from flask import Flask, request, jsonify, g


DEFAULT_DB = os.path.join(os.path.dirname(__file__), "books.db")


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.environ.get("BOOKS_DB", DEFAULT_DB)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB_PATH"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        get_db().executescript(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            );
            """
        )
        get_db().commit()

    def row_to_dict(row):
        return {k: row[k] for k in row.keys()}

    def validate(data, partial=False):
        if not isinstance(data, dict):
            return "request body must be a JSON object"
        if not partial:
            if not data.get("title") or not str(data.get("title")).strip():
                return "title is required"
            if not data.get("author") or not str(data.get("author")).strip():
                return "author is required"
        if "year" in data and data["year"] is not None:
            try:
                int(data["year"])
            except (ValueError, TypeError):
                return "year must be an integer"
        return None

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/books", methods=["POST"])
    def create_book():
        data = request.get_json(silent=True) or {}
        err = validate(data)
        if err:
            return jsonify({"error": err}), 400
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (
                data["title"].strip(),
                data["author"].strip(),
                int(data["year"]) if data.get("year") is not None else None,
                data.get("isbn"),
            ),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id=?", (cur.lastrowid,)).fetchone()
        return jsonify(row_to_dict(row)), 201

    @app.route("/books", methods=["GET"])
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author:
            rows = db.execute("SELECT * FROM books WHERE author=?", (author,)).fetchall()
        else:
            rows = db.execute("SELECT * FROM books").fetchall()
        return jsonify([row_to_dict(r) for r in rows]), 200

    @app.route("/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        row = get_db().execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(row_to_dict(row)), 200

    @app.route("/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id):
        data = request.get_json(silent=True) or {}
        err = validate(data, partial=True)
        if err:
            return jsonify({"error": err}), 400
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        current = row_to_dict(row)
        title = data.get("title", current["title"])
        author = data.get("author", current["author"])
        if not str(title).strip():
            return jsonify({"error": "title cannot be empty"}), 400
        if not str(author).strip():
            return jsonify({"error": "author cannot be empty"}), 400
        year = data.get("year", current["year"])
        isbn = data.get("isbn", current["isbn"])
        db.execute(
            "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
            (title, author, int(year) if year is not None else None, isbn, book_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        return jsonify(row_to_dict(row)), 200

    @app.route("/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        db.execute("DELETE FROM books WHERE id=?", (book_id,))
        db.commit()
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
