"""Book collection REST API built on Flask + SQLite."""

import os
from typing import Any, Optional

from flask import Flask, jsonify, request

import db

FIELDS = ("title", "author", "year", "isbn")


def create_app(test_config: Optional[dict[str, Any]] = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("BOOKS_DB", os.path.join(app.root_path, "books.db")),
        JSON_SORT_KEYS=False,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    register_routes(app)
    register_error_handlers(app)
    return app


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #

def _clean_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("must be a string")
    value = value.strip()
    return value or None


def validate_book(payload: Any, partial: bool = False) -> tuple[dict[str, Any], dict[str, str]]:
    """Validate a request body and return (cleaned_fields, errors).

    With partial=False (create / full update) title and author are required.
    With partial=True only the supplied fields are validated.
    """
    errors: dict[str, str] = {}
    if not isinstance(payload, dict):
        return {}, {"body": "JSON object expected"}

    unknown = set(payload) - set(FIELDS)
    if unknown:
        errors["body"] = f"unknown fields: {', '.join(sorted(unknown))}"

    cleaned: dict[str, Any] = {}

    for field in ("title", "author"):
        if field in payload or not partial:
            try:
                value = _clean_str(payload.get(field))
            except ValueError as exc:
                errors[field] = str(exc)
                continue
            if value is None:
                errors[field] = "is required"
            else:
                cleaned[field] = value

    if "year" in payload:
        year = payload["year"]
        if year is None:
            cleaned["year"] = None
        elif isinstance(year, bool) or not isinstance(year, int):
            errors["year"] = "must be an integer"
        elif not 0 <= year <= 9999:
            errors["year"] = "must be between 0 and 9999"
        else:
            cleaned["year"] = year
    elif not partial:
        cleaned["year"] = None

    if "isbn" in payload:
        try:
            isbn = _clean_str(payload["isbn"])
        except ValueError as exc:
            errors["isbn"] = str(exc)
        else:
            if isbn is not None:
                digits = isbn.replace("-", "").replace(" ", "")
                if len(digits) not in (10, 13) or not digits[:-1].isdigit() or not (
                    digits[-1].isdigit() or digits[-1].upper() == "X"
                ):
                    errors["isbn"] = "must be a valid ISBN-10 or ISBN-13"
            cleaned["isbn"] = isbn
    elif not partial:
        cleaned["isbn"] = None

    return cleaned, errors


def _json_body() -> Any:
    body = request.get_json(silent=True)
    if body is None:
        return None
    return body


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

def register_routes(app: Flask) -> None:
    @app.get("/health")
    def health():
        try:
            db.get_db().execute("SELECT 1").fetchone()
            return jsonify(status="ok", database="ok"), 200
        except Exception as exc:  # pragma: no cover - defensive
            return jsonify(status="error", database=str(exc)), 503

    @app.post("/books")
    def create_book():
        body = _json_body()
        if body is None:
            return jsonify(error="request body must be valid JSON"), 400
        fields, errors = validate_book(body)
        if errors:
            return jsonify(error="validation failed", details=errors), 400

        conn = db.get_db()
        cur = conn.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (fields["title"], fields["author"], fields["year"], fields["isbn"]),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(db.row_to_dict(row)), 201

    @app.get("/books")
    def list_books():
        author = request.args.get("author")
        conn = db.get_db()
        if author is not None and author.strip():
            rows = conn.execute(
                "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
                (author.strip(),),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
        return jsonify([db.row_to_dict(r) for r in rows]), 200

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int):
        row = db.get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return jsonify(error=f"book {book_id} not found"), 404
        return jsonify(db.row_to_dict(row)), 200

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int):
        body = _json_body()
        if body is None:
            return jsonify(error="request body must be valid JSON"), 400
        fields, errors = validate_book(body)
        if errors:
            return jsonify(error="validation failed", details=errors), 400

        conn = db.get_db()
        cur = conn.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (fields["title"], fields["author"], fields["year"], fields["isbn"], book_id),
        )
        if cur.rowcount == 0:
            return jsonify(error=f"book {book_id} not found"), 404
        conn.commit()
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(db.row_to_dict(row)), 200

    @app.patch("/books/<int:book_id>")
    def patch_book(book_id: int):
        body = _json_body()
        if body is None:
            return jsonify(error="request body must be valid JSON"), 400
        fields, errors = validate_book(body, partial=True)
        if errors:
            return jsonify(error="validation failed", details=errors), 400
        if not fields:
            return jsonify(error="no updatable fields supplied"), 400

        conn = db.get_db()
        assignments = ", ".join(f"{k} = ?" for k in fields)
        cur = conn.execute(
            f"UPDATE books SET {assignments} WHERE id = ?",
            (*fields.values(), book_id),
        )
        if cur.rowcount == 0:
            return jsonify(error=f"book {book_id} not found"), 404
        conn.commit()
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return jsonify(db.row_to_dict(row)), 200

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int):
        conn = db.get_db()
        cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        if cur.rowcount == 0:
            return jsonify(error=f"book {book_id} not found"), 404
        conn.commit()
        return "", 204


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(_e):
        return jsonify(error="resource not found"), 404

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return jsonify(error="method not allowed"), 405

    @app.errorhandler(415)
    def unsupported_media(_e):
        return jsonify(error="content-type must be application/json"), 415

    @app.errorhandler(500)
    def server_error(_e):
        return jsonify(error="internal server error"), 500


if __name__ == "__main__":
    create_app().run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
    )
