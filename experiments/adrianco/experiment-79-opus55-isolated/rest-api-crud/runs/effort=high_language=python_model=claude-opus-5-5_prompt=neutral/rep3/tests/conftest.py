"""Shared fixtures: an in-process WSGI test client backed by a fresh database."""

from __future__ import annotations

import io
import json
from typing import Any, Optional
from wsgiref.util import setup_testing_defaults

import pytest

from books_api import BookRepository, BooksApp


class Response:
    def __init__(self, status: str, headers: list[tuple[str, str]], body: bytes) -> None:
        self.status = int(status.split(" ", 1)[0])
        self.headers = {name.lower(): value for name, value in headers}
        self.body = body

    def json(self) -> Any:
        return json.loads(self.body)


class Client:
    """Calls the WSGI app directly, without opening a socket."""

    def __init__(self, app: BooksApp) -> None:
        self.app = app

    def request(
        self,
        method: str,
        path: str,
        json_body: Any = None,
        raw_body: Optional[bytes] = None,
    ) -> Response:
        path, _, query = path.partition("?")
        body = raw_body
        if body is None:
            body = b"" if json_body is None else json.dumps(json_body).encode("utf-8")
        environ: dict[str, Any] = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "CONTENT_LENGTH": str(len(body)),
            "CONTENT_TYPE": "application/json",
            "wsgi.input": io.BytesIO(body),
        }
        return self.request_environ(environ)

    def request_environ(self, environ: dict[str, Any]) -> Response:
        """Send a hand-built WSGI environ, for cases ``request`` cannot express."""
        setup_testing_defaults(environ)

        captured: dict[str, Any] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            captured["status"] = status
            captured["headers"] = headers

        chunks = self.app(environ, start_response)
        return Response(captured["status"], captured["headers"], b"".join(chunks))

    def get(self, path: str) -> Response:
        return self.request("GET", path)

    def post(self, path: str, json_body: Any = None, **kwargs: Any) -> Response:
        return self.request("POST", path, json_body, **kwargs)

    def put(self, path: str, json_body: Any = None, **kwargs: Any) -> Response:
        return self.request("PUT", path, json_body, **kwargs)

    def delete(self, path: str) -> Response:
        return self.request("DELETE", path)


@pytest.fixture
def repository():
    repo = BookRepository(":memory:")
    yield repo
    repo.close()


@pytest.fixture
def client(repository: BookRepository) -> Client:
    return Client(BooksApp(repository))


@pytest.fixture
def dune() -> dict[str, Any]:
    return {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "978-0441172719",
    }
