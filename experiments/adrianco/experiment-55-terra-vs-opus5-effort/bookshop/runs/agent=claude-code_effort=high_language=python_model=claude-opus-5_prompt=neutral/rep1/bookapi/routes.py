"""HTTP routes for the book collection API."""

from __future__ import annotations

import sqlite3
from typing import Any

from flask import Blueprint, jsonify, request, url_for

from .db import get_db
from .validation import validate_book_payload

bp = Blueprint("books", __name__)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _serialize(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _error(message: str, status: int, details: dict[str, str] | None = None):
    body: dict[str, Any] = {"error": message}
    if details:
        body["details"] = details
    return jsonify(body), status


def _not_found(book_id: int):
    return _error(f"Book {book_id} not found", 404)


def _fetch(book_id: int) -> sqlite3.Row | None:
    return get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()


def _json_body() -> tuple[Any, tuple | None]:
    """Decode the request body, tolerating a missing/incorrect Content-Type.

    ``force=True`` parses the body as JSON even when the client omitted
    ``Content-Type: application/json``, which is a common oversight; a body
    that is not JSON at all still yields a 400 rather than a 415.

    Returns ``(payload, error_response)``; exactly one is meaningful.
    """
    payload = request.get_json(silent=True, force=True)
    if payload is None:
        return None, _error("Request body must be valid JSON", 400)
    return payload, None


def _is_isbn_conflict(exc: sqlite3.IntegrityError) -> bool:
    return "isbn" in str(exc).lower()


# --------------------------------------------------------------------------- #
# health
# --------------------------------------------------------------------------- #

@bp.get("/health")
def health():
    """Liveness/readiness probe: also verifies the database is reachable."""
    try:
        get_db().execute("SELECT 1 FROM books LIMIT 1").fetchall()
    except sqlite3.Error as exc:
        return jsonify({"status": "error", "database": "unavailable", "detail": str(exc)}), 503
    return jsonify({"status": "ok", "database": "ok"}), 200


# --------------------------------------------------------------------------- #
# collection
# --------------------------------------------------------------------------- #

@bp.post("/books")
def create_book():
    payload, error = _json_body()
    if error:
        return error

    values, errors = validate_book_payload(payload)
    if errors:
        return _error("Validation failed", 400, errors)

    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (values["title"], values["author"], values["year"], values["isbn"]),
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        db.rollback()
        if _is_isbn_conflict(exc):
            return _error("A book with this ISBN already exists", 409)
        raise

    book = _fetch(cur.lastrowid)
    response = jsonify(_serialize(book))
    response.status_code = 201
    response.headers["Location"] = url_for(".get_book", book_id=book["id"])
    return response


@bp.get("/books")
def list_books():
    """List books, newest last.

    Supported query parameters:
        author  case-insensitive substring match on the author name
        year    exact publication year
    """
    sql = "SELECT * FROM books"
    clauses: list[str] = []
    params: list[Any] = []

    author = request.args.get("author")
    if author is not None and author.strip():
        clauses.append("author LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(author.strip())}%")

    year = request.args.get("year")
    if year is not None and year.strip():
        if not year.strip().lstrip("-").isdigit():
            return _error("Validation failed", 400, {"year": "'year' must be an integer"})
        clauses.append("year = ?")
        params.append(int(year.strip()))

    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id"

    rows = get_db().execute(sql, params).fetchall()
    return jsonify([_serialize(row) for row in rows]), 200


def _escape_like(value: str) -> str:
    """Neutralise LIKE wildcards so a filter of ``%`` matches literally."""
    for char in ("\\", "%", "_"):
        value = value.replace(char, "\\" + char)
    return value


# --------------------------------------------------------------------------- #
# single resource
# --------------------------------------------------------------------------- #

@bp.get("/books/<int:book_id>")
def get_book(book_id: int):
    book = _fetch(book_id)
    if book is None:
        return _not_found(book_id)
    return jsonify(_serialize(book)), 200


@bp.put("/books/<int:book_id>")
def replace_book(book_id: int):
    """Full update: ``title`` and ``author`` are required, others are cleared."""
    return _update(book_id, partial=False)


@bp.patch("/books/<int:book_id>")
def update_book(book_id: int):
    """Partial update: only the supplied fields change."""
    return _update(book_id, partial=True)


def _update(book_id: int, *, partial: bool):
    payload, error = _json_body()
    if error:
        return error

    values, errors = validate_book_payload(payload, partial=partial)
    if errors:
        return _error("Validation failed", 400, errors)

    db = get_db()
    if _fetch(book_id) is None:
        return _not_found(book_id)

    assignments = ", ".join(f"{field} = ?" for field in values)
    params = list(values.values()) + [book_id]
    try:
        db.execute(
            f"UPDATE books SET {assignments}, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            params,
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        db.rollback()
        if _is_isbn_conflict(exc):
            return _error("A book with this ISBN already exists", 409)
        raise

    return jsonify(_serialize(_fetch(book_id))), 200


@bp.delete("/books/<int:book_id>")
def delete_book(book_id: int):
    db = get_db()
    cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    if cur.rowcount == 0:
        return _not_found(book_id)
    return "", 204
