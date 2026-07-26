"""REST API for managing a book collection, backed by SQLite."""

import sqlite3

from flask import Flask, g, jsonify, request

DEFAULT_DB_PATH = "books.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    year   INTEGER,
    isbn   TEXT
);
"""


def create_app(db_path=DEFAULT_DB_PATH):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path

    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)

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

    def row_to_dict(row):
        return {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"],
        }

    def validate_payload(data, require_all=True):
        """Validate a book payload. Returns (fields, errors)."""
        errors = []
        if not isinstance(data, dict):
            return None, ["Request body must be a JSON object"]

        fields = {}

        for field in ("title", "author"):
            value = data.get(field)
            if value is None:
                if require_all or field in data:
                    errors.append(f"'{field}' is required")
            elif not isinstance(value, str) or not value.strip():
                errors.append(f"'{field}' must be a non-empty string")
            else:
                fields[field] = value.strip()

        if "year" in data and data["year"] is not None:
            year = data["year"]
            if not isinstance(year, int) or isinstance(year, bool):
                errors.append("'year' must be an integer")
            else:
                fields["year"] = year
        elif "year" in data:
            fields["year"] = None

        if "isbn" in data and data["isbn"] is not None:
            isbn = data["isbn"]
            if not isinstance(isbn, str):
                errors.append("'isbn' must be a string")
            else:
                fields["isbn"] = isbn.strip()
        elif "isbn" in data:
            fields["isbn"] = None

        return fields, errors

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request"}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Request body must be valid JSON"}), 400
        fields, errors = validate_payload(data, require_all=True)
        if errors:
            return jsonify({"errors": errors}), 400

        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (
                fields["title"],
                fields["author"],
                fields.get("year"),
                fields.get("isbn"),
            ),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(row_to_dict(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author is not None:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([row_to_dict(r) for r in rows])

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = get_db().execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": f"Book {book_id} not found"}), 404
        return jsonify(row_to_dict(row))

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": f"Book {book_id} not found"}), 404

        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Request body must be valid JSON"}), 400
        fields, errors = validate_payload(data, require_all=False)
        if errors:
            return jsonify({"errors": errors}), 400
        if not fields:
            return jsonify({"errors": ["No updatable fields provided"]}), 400

        assignments = ", ".join(f"{col} = ?" for col in fields)
        db.execute(
            f"UPDATE books SET {assignments} WHERE id = ?",
            (*fields.values(), book_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(row_to_dict(row))

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        if cur.rowcount == 0:
            return jsonify({"error": f"Book {book_id} not found"}), 404
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=True)
