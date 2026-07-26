import os
import sqlite3

from flask import Flask, g, jsonify, request

DATABASE = os.environ.get("BOOKS_DB", "books.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
"""


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DATABASE"] = db_path or DATABASE

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        db = sqlite3.connect(app.config["DATABASE"])
        db.executescript(SCHEMA)
        db.close()

    def row_to_dict(row):
        return {k: row[k] for k in row.keys()}

    def validate(data, partial=False):
        errors = []
        if not isinstance(data, dict):
            return ["JSON object body required"]
        for field in ("title", "author"):
            if field in data:
                if not isinstance(data[field], str) or not data[field].strip():
                    errors.append(f"{field} must be a non-empty string")
            elif not partial:
                errors.append(f"{field} is required")
        if "year" in data and data["year"] is not None and not isinstance(data["year"], int):
            errors.append("year must be an integer")
        if "isbn" in data and data["isbn"] is not None and not isinstance(data["isbn"], str):
            errors.append("isbn must be a string")
        return errors

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        errors = validate(data)
        if errors:
            return jsonify({"errors": errors}), 400
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"].strip(), data["author"].strip(), data.get("year"), data.get("isbn")),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(row_to_dict(row)), 201

    @app.get("/books")
    def list_books():
        db = get_db()
        author = request.args.get("author")
        if author:
            rows = db.execute("SELECT * FROM books WHERE author = ?", (author,)).fetchall()
        else:
            rows = db.execute("SELECT * FROM books").fetchall()
        return jsonify([row_to_dict(r) for r in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(row_to_dict(row))

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        data = request.get_json(silent=True)
        errors = validate(data, partial=True)
        if errors:
            return jsonify({"errors": errors}), 400
        current = row_to_dict(row)
        for field in ("title", "author", "year", "isbn"):
            if field in data:
                current[field] = data[field].strip() if field in ("title", "author") else data[field]
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (current["title"], current["author"], current["year"], current["isbn"], book_id),
        )
        db.commit()
        return jsonify(current)

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "book not found"}), 404
        return "", 204

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
