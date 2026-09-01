"""Book collection REST API backed by SQLite (Flask)."""
import os
import sqlite3

from flask import Flask, g, jsonify, request

DEFAULT_DB = os.environ.get("BOOKS_DB", "books.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
"""


def create_app(db_path: str = DEFAULT_DB) -> Flask:
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path

    def get_db() -> sqlite3.Connection:
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB_PATH"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)

    def row_to_dict(row) -> dict:
        return {k: row[k] for k in row.keys()}

    def validate(payload, partial=False):
        """Return (clean_data, errors)."""
        if not isinstance(payload, dict):
            return None, ["Request body must be a JSON object"]
        errors = []
        data = {}
        for field in ("title", "author"):
            if field in payload or not partial:
                value = payload.get(field)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"'{field}' is required and must be a non-empty string")
                else:
                    data[field] = value.strip()
        if "year" in payload:
            year = payload["year"]
            if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
                errors.append("'year' must be an integer")
            else:
                data["year"] = year
        if "isbn" in payload:
            isbn = payload["isbn"]
            if isbn is not None and not isinstance(isbn, str):
                errors.append("'isbn' must be a string")
            else:
                data["isbn"] = isbn
        return data, errors

    def fetch_book(book_id: int):
        row = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return row_to_dict(row) if row else None

    @app.get("/health")
    def health():
        get_db().execute("SELECT 1")
        return jsonify({"status": "ok"})

    @app.post("/books")
    def create_book():
        data, errors = validate(request.get_json(silent=True))
        if errors:
            return jsonify({"errors": errors}), 400
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"], data["author"], data.get("year"), data.get("isbn")),
        )
        db.commit()
        return jsonify(fetch_book(cur.lastrowid)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        if author:
            rows = get_db().execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = get_db().execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([row_to_dict(r) for r in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        book = fetch_book(book_id)
        if book is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(book)

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        if fetch_book(book_id) is None:
            return jsonify({"error": "Book not found"}), 404
        data, errors = validate(request.get_json(silent=True), partial=True)
        if errors:
            return jsonify({"errors": errors}), 400
        if not data:
            return jsonify({"errors": ["No updatable fields provided"]}), 400
        sets = ", ".join(f"{k} = ?" for k in data)
        db = get_db()
        db.execute(f"UPDATE books SET {sets} WHERE id = ?", (*data.values(), book_id))
        db.commit()
        return jsonify(fetch_book(book_id))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Book not found"}), 404
        return "", 204

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return jsonify({"error": "Method not allowed"}), 405

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
