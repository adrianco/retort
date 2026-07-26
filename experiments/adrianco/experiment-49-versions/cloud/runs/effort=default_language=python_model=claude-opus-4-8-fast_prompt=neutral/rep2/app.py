"""REST API service for managing a book collection.

Endpoints:
    POST   /books        Create a new book
    GET    /books        List all books (optional ?author= filter)
    GET    /books/<id>   Get a single book
    PUT    /books/<id>   Update a book
    DELETE /books/<id>   Delete a book
    GET    /health        Health check
"""

from flask import Flask, request, jsonify, g

from db import DEFAULT_DB_PATH, get_connection, init_db


def _row_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def _validate_book(data, partial=False):
    """Validate an incoming book payload.

    Returns a tuple (cleaned_dict, errors_list). For a full (non-partial)
    payload, title and author are required. ``year`` must be an integer if
    provided. Only known fields are kept.
    """
    errors = []
    if not isinstance(data, dict):
        return None, ["request body must be a JSON object"]

    cleaned = {}

    # title / author are required strings (required only for full payloads).
    for field in ("title", "author"):
        if field in data:
            value = data[field]
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{field} must be a non-empty string")
            else:
                cleaned[field] = value.strip()
        elif not partial:
            errors.append(f"{field} is required")

    # year is optional but must be an integer when present.
    if "year" in data and data["year"] is not None:
        value = data["year"]
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append("year must be an integer")
        else:
            cleaned["year"] = value
    elif "year" in data:
        cleaned["year"] = None

    # isbn is optional but must be a string when present.
    if "isbn" in data and data["isbn"] is not None:
        value = data["isbn"]
        if not isinstance(value, str):
            errors.append("isbn must be a string")
        else:
            cleaned["isbn"] = value.strip()
    elif "isbn" in data:
        cleaned["isbn"] = None

    return cleaned, errors


def create_app(db_path=DEFAULT_DB_PATH):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path
    init_db(db_path)

    def get_db():
        if "db" not in g:
            g.db = get_connection(app.config["DB_PATH"])
        return g.db

    @app.teardown_appcontext
    def close_db(exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        data = request.get_json(silent=True)
        cleaned, errors = _validate_book(data or {}, partial=False)
        if errors:
            return jsonify({"errors": errors}), 400

        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (
                cleaned["title"],
                cleaned["author"],
                cleaned.get("year"),
                cleaned.get("isbn"),
            ),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return jsonify(_row_to_dict(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        db = get_db()
        if author:
            rows = db.execute(
                "SELECT * FROM books WHERE author = ? ORDER BY id", (author,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([_row_to_dict(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(_row_to_dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404

        data = request.get_json(silent=True)
        cleaned, errors = _validate_book(data or {}, partial=True)
        if errors:
            return jsonify({"errors": errors}), 400
        if not cleaned:
            return jsonify({"errors": ["no valid fields to update"]}), 400

        # Merge provided fields over the existing record.
        merged = _row_to_dict(row)
        merged.update(cleaned)
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (merged["title"], merged["author"], merged["year"], merged["isbn"], book_id),
        )
        db.commit()
        updated = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        return jsonify(_row_to_dict(updated)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id):
        db = get_db()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        db.commit()
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=True)
