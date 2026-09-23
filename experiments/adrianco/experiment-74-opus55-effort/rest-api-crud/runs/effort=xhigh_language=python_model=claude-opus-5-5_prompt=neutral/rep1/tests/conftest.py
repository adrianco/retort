from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from typing import Any
from wsgiref.util import setup_testing_defaults
from wsgiref.validate import validator

import pytest

from books_api import BookRepository, BooksApp


@dataclass
class Result:
    status: int
    headers: dict[str, str]
    body: bytes
    raw_headers: list[tuple[str, str]] = field(default_factory=list)

    @property
    def json(self) -> Any:
        return json.loads(self.body)


class WSGIClient:
    """Calls the WSGI app in-process, checking every exchange with wsgiref's validator."""

    def __init__(self, app: BooksApp) -> None:
        self.app = validator(app)

    def request(
        self,
        method: str,
        path: str,
        json_body: Any = None,
        *,
        data: bytes | None = None,
        query: str = "",
        environ: dict[str, str] | None = None,
    ) -> Result:
        body = data if data is not None else b""
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
        env: dict[str, Any] = {
            "REQUEST_METHOD": method,
            "SCRIPT_NAME": "",
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
        }
        env.update(environ or {})
        setup_testing_defaults(env)

        captured: dict[str, Any] = {}

        def start_response(status: str, headers: list[tuple[str, str]], exc_info: Any = None):
            captured["status"] = int(status.split(" ", 1)[0])
            captured["headers"] = headers
            return lambda chunk: None

        iterable = self.app(env, start_response)
        try:
            payload = b"".join(iterable)
        finally:
            iterable.close()
        headers = captured["headers"]
        return Result(captured["status"], dict(headers), payload, headers)

    def get(self, path: str, **kwargs: Any) -> Result:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, json_body: Any = None, **kwargs: Any) -> Result:
        return self.request("POST", path, json_body, **kwargs)

    def put(self, path: str, json_body: Any = None, **kwargs: Any) -> Result:
        return self.request("PUT", path, json_body, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Result:
        return self.request("DELETE", path, **kwargs)


@pytest.fixture
def repository(tmp_path):
    repo = BookRepository(tmp_path / "books.db")
    yield repo
    repo.close()


@pytest.fixture
def app(repository):
    return BooksApp(repository)


@pytest.fixture
def make_client():
    """Factory for clients of custom-configured apps."""
    return WSGIClient


@pytest.fixture
def client(app):
    return WSGIClient(app)


@pytest.fixture
def make_book(client):
    """Create a book through the API and return its JSON representation."""

    def _make(**overrides: Any) -> dict[str, Any]:
        payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}
        payload.update(overrides)
        response = client.post("/books", payload)
        assert response.status == 201, response.body
        return response.json

    return _make
