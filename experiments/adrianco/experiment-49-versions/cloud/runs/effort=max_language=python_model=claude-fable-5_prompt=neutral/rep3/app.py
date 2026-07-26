"""REST API for managing a book collection, backed by SQLite."""

import os

from flask import Blueprint, Flask, jsonify, request, url_for

from db import get_db, init_app

bp = Blueprint("books", __name__)


def to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book_payload(req):
    """Validate a create/update request body.

    Returns (data, errors): exactly one of the two is None. ``data`` holds the
    normalized fields; ``errors`` maps field names to human-readable messages.
    """
    payload = req.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, {"body": "request body must be a JSON object"}

    errors = {}

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        errors["title"] = "title is required and must be a non-empty string"

    author = payload.get("author")
    if not isinstance(author, str) or not author.strip():
        errors["author"] = "author is required and must be a non-empty string"

    year = payload.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors["year"] = "year must be an integer"

    isbn = payload.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors["isbn"] = "isbn must be a string"

    if errors:
        return None, errors

    return {
        "title": title.strip(),
        "author": author.strip(),
        "year": year,
        "isbn": isbn.strip() if isinstance(isbn, str) else None,
    }, None


@bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@bp.post("/books")
def create_book():
    data, errors = validate_book_payload(request)
    if errors:
        return jsonify({"errors": errors}), 400

    db = get_db()
    cursor = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (data["title"], data["author"], data["year"], data["isbn"]),
    )
    db.commit()

    row = db.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
    response = jsonify(to_dict(row))
    response.status_code = 201
    response.headers["Location"] = url_for("books.get_book", book_id=row["id"])
    return response


@bp.get("/books")
def list_books():
    author = request.args.get("author")
    db = get_db()
    if author is not None:
        rows = db.execute(
            "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
            (author,),
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM books ORDER BY id").fetchall()
    return jsonify([to_dict(row) for row in rows])


@bp.get("/books/<int:book_id>")
def get_book(book_id):
    row = get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": f"book {book_id} not found"}), 404
    return jsonify(to_dict(row))


@bp.put("/books/<int:book_id>")
def update_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": f"book {book_id} not found"}), 404

    data, errors = validate_book_payload(request)
    if errors:
        return jsonify({"errors": errors}), 400

    db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (data["title"], data["author"], data["year"], data["isbn"], book_id),
    )
    db.commit()

    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return jsonify(to_dict(row))


@bp.delete("/books/<int:book_id>")
def delete_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        return jsonify({"error": f"book {book_id} not found"}), 404

    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    return "", 204


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get(
            "BOOKS_DB",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db"),
        ),
    )
    if test_config:
        app.config.update(test_config)

    init_app(app)
    app.register_blueprint(bp)

    @app.errorhandler(404)
    def not_found(exc):
        return jsonify({"error": "resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(exc):
        return jsonify({"error": "method not allowed"}), 405

    @app.errorhandler(500)
    def internal_error(exc):
        return jsonify({"error": "internal server error"}), 500

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=True)
