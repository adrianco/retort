"""WSGI application exposing the books REST API."""

import json
import re
from http import HTTPStatus
from urllib.parse import parse_qs

from books_api.db import BookRepository, DuplicateIsbnError
from books_api.validation import validate_book

MAX_BODY_BYTES = 1024 * 1024
_BOOK_PATH = re.compile(r"^/books/(?P<id>[^/]+)$")


class HttpError(Exception):
    def __init__(self, status, message, details=None, headers=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details
        self.headers = headers or []


class BooksApp:
    """A minimal WSGI app with routing for /health and /books."""

    def __init__(self, repository):
        self.repo = repository

    def __call__(self, environ, start_response):
        try:
            status, body, headers = self._dispatch(environ)
        except HttpError as err:
            payload = {"error": err.message}
            if err.details:
                payload["details"] = err.details
            status, body, headers = err.status, payload, err.headers
        except Exception:  # pragma: no cover - defensive catch-all
            status, body, headers = HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "internal server error"}, []

        if body is None:
            data = b""
        else:
            data = json.dumps(body).encode("utf-8")
            headers = [("Content-Type", "application/json")] + headers
        headers.append(("Content-Length", str(len(data))))
        start_response(f"{status.value} {status.phrase}", headers)
        return [data]

    # -- routing ---------------------------------------------------------

    def _dispatch(self, environ):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "") or "/"
        if len(path) > 1:
            path = path.rstrip("/")

        if path == "/health":
            self._require_method(method, ("GET",))
            return self.health()

        if path == "/books":
            self._require_method(method, ("GET", "POST"))
            if method == "GET":
                return self.list_books(parse_qs(environ.get("QUERY_STRING", "")))
            return self.create_book(self._read_json(environ))

        match = _BOOK_PATH.match(path)
        if match:
            self._require_method(method, ("GET", "PUT", "DELETE"))
            book_id = self._parse_id(match.group("id"))
            if method == "GET":
                return self.get_book(book_id)
            if method == "PUT":
                return self.update_book(book_id, self._read_json(environ))
            return self.delete_book(book_id)

        raise HttpError(HTTPStatus.NOT_FOUND, "resource not found")

    @staticmethod
    def _require_method(method, allowed):
        if method not in allowed:
            raise HttpError(
                HTTPStatus.METHOD_NOT_ALLOWED,
                f"method {method} not allowed",
                headers=[("Allow", ", ".join(allowed))],
            )

    @staticmethod
    def _parse_id(raw):
        if not raw.isdigit() or int(raw) < 1:
            raise HttpError(HTTPStatus.NOT_FOUND, "book not found")
        return int(raw)

    @staticmethod
    def _read_json(environ):
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            raise HttpError(HTTPStatus.BAD_REQUEST, "invalid Content-Length header")
        if length > MAX_BODY_BYTES:
            raise HttpError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body too large")
        raw = environ["wsgi.input"].read(length) if length > 0 else b""
        if not raw.strip():
            raise HttpError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise HttpError(HTTPStatus.BAD_REQUEST, "request body is not valid JSON")

    # -- handlers --------------------------------------------------------

    def health(self):
        try:
            self.repo.ping()
        except Exception:
            return HTTPStatus.SERVICE_UNAVAILABLE, {"status": "error", "database": "unavailable"}, []
        return HTTPStatus.OK, {"status": "ok", "database": "ok"}, []

    def list_books(self, query):
        author = query.get("author", [None])[0]
        if author is not None:
            author = author.strip()
        return HTTPStatus.OK, self.repo.list(author=author or None), []

    def create_book(self, payload):
        book = self._validated(payload)
        try:
            created = self.repo.create(book)
        except DuplicateIsbnError:
            raise HttpError(HTTPStatus.CONFLICT, "a book with this isbn already exists")
        return HTTPStatus.CREATED, created, [("Location", f"/books/{created['id']}")]

    def get_book(self, book_id):
        book = self.repo.get(book_id)
        if book is None:
            raise HttpError(HTTPStatus.NOT_FOUND, "book not found")
        return HTTPStatus.OK, book, []

    def update_book(self, book_id, payload):
        book = self._validated(payload)
        try:
            updated = self.repo.update(book_id, book)
        except DuplicateIsbnError:
            raise HttpError(HTTPStatus.CONFLICT, "a book with this isbn already exists")
        if updated is None:
            raise HttpError(HTTPStatus.NOT_FOUND, "book not found")
        return HTTPStatus.OK, updated, []

    def delete_book(self, book_id):
        if not self.repo.delete(book_id):
            raise HttpError(HTTPStatus.NOT_FOUND, "book not found")
        return HTTPStatus.NO_CONTENT, None, []

    @staticmethod
    def _validated(payload):
        book, errors = validate_book(payload)
        if errors:
            raise HttpError(HTTPStatus.BAD_REQUEST, "validation failed", details=errors)
        return book


def create_app(db_path=":memory:"):
    return BooksApp(BookRepository(db_path))
