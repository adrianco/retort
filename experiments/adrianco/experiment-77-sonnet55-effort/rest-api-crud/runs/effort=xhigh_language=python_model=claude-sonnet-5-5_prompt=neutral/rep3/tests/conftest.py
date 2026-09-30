from __future__ import annotations

import io
import json
from urllib.parse import urlsplit

import pytest

from bookapi import BookApp, BookStore


class Response:
    def __init__(self, status: str, headers: list, body: bytes) -> None:
        self.status_code = int(status.split(" ", 1)[0])
        self.headers = {name.lower(): value for name, value in headers}
        self.body = body

    def json(self):
        return json.loads(self.body.decode("utf-8"))


class Client:
    """Minimal in-process WSGI test client (no sockets)."""

    def __init__(self, app) -> None:
        self.app = app

    def request(self, method: str, url: str, json_body=None, raw_body: bytes | None = None,
                headers: dict | None = None) -> Response:
        parts = urlsplit(url)
        body = raw_body if raw_body is not None else (
            b"" if json_body is None else json.dumps(json_body).encode("utf-8"))
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": parts.path,
            "QUERY_STRING": parts.query,
            "CONTENT_LENGTH": str(len(body)),
            "CONTENT_TYPE": "application/json",
            "wsgi.input": io.BytesIO(body),
            "SERVER_NAME": "testserver",
            "SERVER_PORT": "80",
            "wsgi.url_scheme": "http",
        }
        environ.update(headers or {})
        captured = {}

        def start_response(status, response_headers):
            captured["status"], captured["headers"] = status, response_headers

        chunks = self.app(environ, start_response)
        return Response(captured["status"], captured["headers"], b"".join(chunks))

    def get(self, url, **kw):
        return self.request("GET", url, **kw)

    def post(self, url, json=None, **kw):
        return self.request("POST", url, json_body=json, **kw)

    def put(self, url, json=None, **kw):
        return self.request("PUT", url, json_body=json, **kw)

    def delete(self, url, **kw):
        return self.request("DELETE", url, **kw)


@pytest.fixture
def store():
    store = BookStore(":memory:")
    yield store
    store.close()


@pytest.fixture
def client(store):
    return Client(BookApp(store))


@pytest.fixture
def book_payload():
    return {"title": "Nineteen Eighty-Four", "author": "George Orwell",
            "year": 1949, "isbn": "978-0-452-28423-4"}
