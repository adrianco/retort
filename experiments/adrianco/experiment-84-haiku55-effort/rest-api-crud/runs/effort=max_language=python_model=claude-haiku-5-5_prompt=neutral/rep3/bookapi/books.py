"""HTTP routes for the /books collection."""

from flask import Blueprint, jsonify, request, url_for

from . import repository
from .db import get_db
from .errors import ApiError
from .validation import validate_author_filter, validate_book

bp = Blueprint("books", __name__, url_prefix="/books")


@bp.post("")
def create_book():
    fields = validate_book(_json_body())
    book_id = repository.insert_book(get_db(), fields)
    location = url_for("books.get_book", book_id=book_id)
    return jsonify({"id": book_id, **fields}), 201, {"Location": location}


@bp.get("")
def list_books():
    author = validate_author_filter(request.args.get("author"))
    rows = repository.list_books(get_db(), author)
    return jsonify([dict(row) for row in rows])


@bp.get("/<int:book_id>")
def get_book(book_id: int):
    row = repository.get_book(get_db(), book_id)
    if row is None:
        raise _not_found(book_id)
    return jsonify(dict(row))


@bp.put("/<int:book_id>")
def update_book(book_id: int):
    fields = validate_book(_json_body())
    if not repository.update_book(get_db(), book_id, fields):
        raise _not_found(book_id)
    return jsonify({"id": book_id, **fields})


@bp.delete("/<int:book_id>")
def delete_book(book_id: int):
    if not repository.delete_book(get_db(), book_id):
        raise _not_found(book_id)
    return "", 204


def _json_body() -> dict:
    # force=True parses the body even without a JSON content type.
    # silent=True turns a body that is not valid JSON into None.
    body = request.get_json(force=True, silent=True)
    if not isinstance(body, dict):
        raise ApiError(400, "Request body must be a JSON object")
    return body


def _not_found(book_id: int) -> ApiError:
    return ApiError(404, f"Book {book_id} not found")
