"""HTTP routes for the book collection service."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request, url_for

from . import repository
from .errors import ApiError
from .validation import validate_book

bp = Blueprint("api", __name__)


def _json_body() -> Any:
    """Return the parsed JSON body, or raise a helpful 4xx if it is unusable."""
    body = request.get_json(silent=True)
    if body is None:
        if not request.is_json:
            raise ApiError(
                415,
                "unsupported_media_type",
                "Request must be sent with Content-Type: application/json.",
            )
        raise ApiError(400, "invalid_json", "Request body is not valid JSON.")
    return body


def _book_or_404(book_id: int) -> dict[str, Any]:
    book = repository.get_book(book_id)
    if book is None:
        raise ApiError(404, "not_found", f"No book with id {book_id}.")
    return book


@bp.get("/health")
def health():
    try:
        repository.ping()
    except Exception:  # pragma: no cover - only reachable on a broken database
        return jsonify({"status": "unhealthy", "database": "unavailable"}), 503
    return jsonify({"status": "ok", "database": "ok"})


@bp.post("/books")
def create_book():
    book = repository.create_book(validate_book(_json_body()))
    return (
        jsonify(book),
        201,
        {"Location": url_for("api.get_book", book_id=book["id"])},
    )


@bp.get("/books")
def list_books():
    return jsonify(repository.list_books(author=request.args.get("author")))


@bp.get("/books/<int:book_id>")
def get_book(book_id: int):
    return jsonify(_book_or_404(book_id))


@bp.put("/books/<int:book_id>")
def replace_book(book_id: int):
    book = repository.replace_book(book_id, validate_book(_json_body()))
    if book is None:
        raise ApiError(404, "not_found", f"No book with id {book_id}.")
    return jsonify(book)


@bp.delete("/books/<int:book_id>")
def delete_book(book_id: int):
    if not repository.delete_book(book_id):
        raise ApiError(404, "not_found", f"No book with id {book_id}.")
    return "", 204
