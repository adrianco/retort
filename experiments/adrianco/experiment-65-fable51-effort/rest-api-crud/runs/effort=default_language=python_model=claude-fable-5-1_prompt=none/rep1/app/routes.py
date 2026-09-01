"""HTTP routes for /health and /books."""
from __future__ import annotations

import sqlite3

from flask import Blueprint, jsonify, request

from .db import get_db

bp = Blueprint("books", __name__)

FIELDS = ("title", "author", "year", "isbn")


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in ("id", *FIELDS)}


def _validate(payload, *, partial: bool) -> tuple[dict, list[str]]:
    """Validate a create/update payload.

    Returns (clean_fields, errors). For partial updates, missing fields are
    simply omitted; for full creates, title and author are required.
    """
    errors: list[str] = []
    if not isinstance(payload, dict):
        return {}, ["request body must be a JSON object"]

    unknown = sorted(set(payload) - set(FIELDS))
    if unknown:
        errors.append(f"unknown field(s): {', '.join(unknown)}")

    clean: dict = {}

    for name in ("title", "author"):
        if name in payload:
            value = payload[name]
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{name} must be a non-empty string")
            else:
                clean[name] = value.strip()
        elif not partial:
            errors.append(f"{name} is required")

    if "year" in payload:
        value = payload["year"]
        if value is None:
            clean["year"] = None
        elif isinstance(value, bool) or not isinstance(value, int):
            errors.append("year must be an integer")
        elif not (0 <= value <= 9999):
            errors.append("year must be between 0 and 9999")
        else:
            clean["year"] = value

    if "isbn" in payload:
        value = payload["isbn"]
        if value is None:
            clean["isbn"] = None
        elif not isinstance(value, str):
            errors.append("isbn must be a string")
        else:
            digits = value.replace("-", "").replace(" ", "")
            if not (len(digits) in (10, 13) and digits[:-1].isdigit()
                    and (digits[-1].isdigit() or digits[-1] in "xX")):
                errors.append("isbn must be a valid 10- or 13-character ISBN")
            else:
                clean["isbn"] = digits.upper()

    return clean, errors


def _json_body():
    """Parse the JSON body, returning (data, error_response)."""
    data = request.get_json(silent=True)
    if data is None:
        return None, (jsonify(error="request body must be valid JSON"), 400)
    return data, None


def _fetch(book_id: int):
    return get_db().execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()


@bp.get("/health")
def health():
    try:
        get_db().execute("SELECT 1").fetchone()
        db_status = "ok"
        code = 200
    except sqlite3.Error:
        db_status = "error"
        code = 503
    return jsonify(status="ok" if code == 200 else "degraded", database=db_status), code


@bp.post("/books")
def create_book():
    data, err = _json_body()
    if err:
        return err
    clean, errors = _validate(data, partial=False)
    if errors:
        return jsonify(error="validation failed", details=errors), 400

    db = get_db()
    cur = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (clean["title"], clean["author"], clean.get("year"), clean.get("isbn")),
    )
    db.commit()
    row = _fetch(cur.lastrowid)
    resp = jsonify(_row_to_dict(row))
    resp.status_code = 201
    resp.headers["Location"] = f"/books/{row['id']}"
    return resp


@bp.get("/books")
def list_books():
    author = request.args.get("author")
    sql = "SELECT * FROM books"
    params: tuple = ()
    if author is not None:
        sql += " WHERE author = ? COLLATE NOCASE"
        params = (author.strip(),)
    sql += " ORDER BY id"
    rows = get_db().execute(sql, params).fetchall()
    return jsonify([_row_to_dict(r) for r in rows])


@bp.get("/books/<int:book_id>")
def get_book(book_id: int):
    row = _fetch(book_id)
    if row is None:
        return jsonify(error="book not found"), 404
    return jsonify(_row_to_dict(row))


@bp.put("/books/<int:book_id>")
def update_book(book_id: int):
    if _fetch(book_id) is None:
        return jsonify(error="book not found"), 404
    data, err = _json_body()
    if err:
        return err
    clean, errors = _validate(data, partial=True)
    if errors:
        return jsonify(error="validation failed", details=errors), 400
    if not clean:
        return jsonify(error="validation failed",
                       details=["no updatable fields supplied"]), 400

    assignments = ", ".join(f"{k} = ?" for k in clean)
    db = get_db()
    db.execute(f"UPDATE books SET {assignments} WHERE id = ?",
               (*clean.values(), book_id))
    db.commit()
    return jsonify(_row_to_dict(_fetch(book_id)))


@bp.delete("/books/<int:book_id>")
def delete_book(book_id: int):
    db = get_db()
    cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify(error="book not found"), 404
    return "", 204
