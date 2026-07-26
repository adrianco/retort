"""REST API for managing a book collection.

Run with:  python app.py     (or: flask --app app run)
"""

import os

from flask import Flask, jsonify, request

from db import get_db, init_db


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


def _validate(payload, partial=False):
    """Validate an incoming book payload, returning cleaned field values.

    With partial=True (PUT of a subset) only the supplied fields are checked,
    but a supplied title/author still may not be blank.
    """
    if not isinstance(payload, dict):
        raise ValidationError(["request body must be a JSON object"])

    errors = []
    cleaned = {}

    for field in ("title", "author"):
        if field in payload:
            value = payload[field]
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{field} must be a non-empty string")
            else:
                cleaned[field] = value.strip()
        elif not partial:
            errors.append(f"{field} is required")

    if "year" in payload and payload["year"] is not None:
        value = payload["year"]
        # bool is a subclass of int, so reject it explicitly.
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append("year must be an integer")
        elif not 0 <= value <= 2200:
            errors.append("year must be between 0 and 2200")
        else:
            cleaned["year"] = value
    elif "year" in payload:
        cleaned["year"] = None

    if "isbn" in payload and payload["isbn"] is not None:
        value = payload["isbn"]
        if not isinstance(value, str):
            errors.append("isbn must be a string")
        else:
            cleaned["isbn"] = value.strip() or None
    elif "isbn" in payload:
        cleaned["isbn"] = None

    if errors:
        raise ValidationError(errors)
    return cleaned


def _row_to_book(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def create_app(database=None):
    app = Flask(__name__)
    app.config["DATABASE"] = database or os.environ.get("DATABASE", "books.db")
    init_db(app)

    @app.errorhandler(ValidationError)
    def _handle_validation_error(exc):
        return jsonify({"error": "validation failed", "details": exc.errors}), 400

    @app.errorhandler(404)
    def _handle_404(_exc):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(405)
    def _handle_405(_exc):
        return jsonify({"error": "method not allowed"}), 405

    def _json_body():
        body = request.get_json(silent=True)
        if body is None:
            raise ValidationError(["request body must be valid JSON"])
        return body

    @app.get("/health")
    def health():
        get_db().execute("SELECT 1").fetchone()
        return jsonify({"status": "ok"}), 200

    @app.post("/books")
    def create_book():
        data = _validate(_json_body())
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data["title"], data["author"], data.get("year"), data.get("isbn")),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM books WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return jsonify(_row_to_book(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        if author:
            rows = get_db().execute(
                "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                (author.strip(),),
            ).fetchall()
        else:
            rows = get_db().execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([_row_to_book(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id):
        row = get_db().execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404
        return jsonify(_row_to_book(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id):
        body = _json_body()
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify({"error": "book not found"}), 404

        data = _validate(body, partial=True)
        if not data:
            raise ValidationError(["no updatable fields supplied"])

        assignments = ", ".join(f"{field} = ?" for field in data)
        db.execute(
            f"UPDATE books SET {assignments} WHERE id = ?",
            (*data.values(), book_id),
        )
        db.commit()
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(_row_to_book(row)), 200

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
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
