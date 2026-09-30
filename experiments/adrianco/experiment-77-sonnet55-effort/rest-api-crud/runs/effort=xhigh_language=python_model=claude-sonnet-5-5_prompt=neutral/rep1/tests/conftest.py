import io
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import pytest

from bookapi import create_app


@dataclass
class Reply:
    status: int
    headers: dict[str, str]
    raw: bytes

    @property
    def json(self) -> Any:
        return json.loads(self.raw)


class Client:
    """Calls the WSGI app directly, so no sockets or extra packages are needed."""

    def __init__(self, app) -> None:
        self.app = app

    def request(
        self,
        method: str,
        url: str,
        body: Any = None,
        *,
        raw: bytes | None = None,
        environ_extra: dict[str, Any] | None = None,
    ) -> Reply:
        if raw is None:
            raw = b"" if body is None else json.dumps(body).encode()
        parts = urlsplit(url)
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": parts.path,
            "QUERY_STRING": parts.query,
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(raw)),
            "wsgi.input": io.BytesIO(raw),
            **(environ_extra or {}),
        }
        captured: dict[str, Any] = {}

        def start_response(status, headers):
            captured["status"] = int(status.split()[0])
            captured["headers"] = dict(headers)

        chunks = self.app(environ, start_response)
        return Reply(captured["status"], captured["headers"], b"".join(chunks))

    def get(self, url: str) -> Reply:
        return self.request("GET", url)

    def post(self, url: str, body: Any = None, **kwargs) -> Reply:
        return self.request("POST", url, body, **kwargs)

    def put(self, url: str, body: Any = None, **kwargs) -> Reply:
        return self.request("PUT", url, body, **kwargs)

    def delete(self, url: str) -> Reply:
        return self.request("DELETE", url)


@pytest.fixture
def app():
    app = create_app(":memory:")
    yield app
    app.close()


@pytest.fixture
def client(app) -> Client:
    return Client(app)


@pytest.fixture
def make_book(client):
    """Create a book through the API and return its JSON."""

    def _make(**overrides) -> dict[str, Any]:
        payload = {
            "title": "Nineteen Eighty-Four",
            "author": "George Orwell",
            "year": 1949,
            "isbn": "978-0451524935",
            **overrides,
        }
        reply = client.post("/books", payload)
        assert reply.status == 201, reply.raw
        return reply.json

    return _make
