"""HTTP routes for the book collection service."""

import sqlite3

from flask import Blueprint, jsonify, request, url_for

from .db import get_db
from .validation import ValidationError, validate_book

bp = Blueprint("api", __name__)


def error(message: str, status: int, details: dict | None = None):
    body = {"error": message}
    if details:
        body["details"] = details
    return jsonify(body), status


def serialize(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def read_json():
    """Return the decoded JSON body, or raise a 400 for malformed input."""
    if not request.is_json:
        raise ValidationError({"body": "Content-Type must be application/json"})
    payload = request.get_json(silent=True)
    if payload is None:
        raise ValidationError({"body": "request body must be valid JSON"})
    return payload


def fetch_book(book_id: int):
    return get_db().execute(
        "SELECT * FROM books WHERE id = ?", (book_id,)
    ).fetchone()


@bp.get("/health")
def health():
    try:
        get_db().execute("SELECT 1").fetchone()
    except sqlite3.Error as exc:  # pragma: no cover - only on a broken DB file
        return jsonify({"status": "error", "database": str(exc)}), 503
    return jsonify({"status": "ok", "database": "ok"}), 200


@bp.post("/books")
def create_book():
    book = validate_book(read_json())
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (book["title"], book["author"], book["year"], book["isbn"]),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return error(
            "Conflict", 409, {"isbn": "a book with this ISBN already exists"}
        )
    created = fetch_book(cursor.lastrowid)
    response = jsonify(serialize(created))
    response.headers["Location"] = url_for("api.get_book", book_id=created["id"])
    return response, 201


@bp.get("/books")
def list_books():
    author = request.args.get("author")
    sql = "SELECT * FROM books"
    params: tuple = ()
    if author is not None:
        # Case-insensitive exact match on the author name.
        sql += " WHERE author = ? COLLATE NOCASE"
        params = (author.strip(),)
    sql += " ORDER BY id"
    rows = get_db().execute(sql, params).fetchall()
    return jsonify({"books": [serialize(row) for row in rows], "count": len(rows)}), 200


@bp.get("/books/<int:book_id>")
def get_book(book_id: int):
    row = fetch_book(book_id)
    if row is None:
        return error(f"Book {book_id} not found", 404)
    return jsonify(serialize(row)), 200


@bp.put("/books/<int:book_id>")
def update_book(book_id: int):
    book = validate_book(read_json())
    db = get_db()
    if fetch_book(book_id) is None:
        return error(f"Book {book_id} not found", 404)
    try:
        db.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (book["title"], book["author"], book["year"], book["isbn"], book_id),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return error(
            "Conflict", 409, {"isbn": "a book with this ISBN already exists"}
        )
    return jsonify(serialize(fetch_book(book_id))), 200


@bp.delete("/books/<int:book_id>")
def delete_book(book_id: int):
    db = get_db()
    cursor = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    if cursor.rowcount == 0:
        return error(f"Book {book_id} not found", 404)
    return "", 204
