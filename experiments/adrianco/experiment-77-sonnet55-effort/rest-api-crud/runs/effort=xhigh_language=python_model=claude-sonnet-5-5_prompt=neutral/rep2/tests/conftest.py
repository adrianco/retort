import io
import json as jsonlib
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import pytest

from bookapi.app import BookApp
from bookapi.db import BookStore


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return jsonlib.loads(self.body)


class Client:
    """Calls the WSGI app in-process, without sockets."""

    def __init__(self, app: BookApp) -> None:
        self.app = app

    def request(
        self,
        method: str,
        url: str,
        *,
        json: Any = None,
        data: bytes | None = None,
        content_length: str | None = None,
    ) -> Response:
        if json is not None:
            data = jsonlib.dumps(json).encode()
        data = data or b""
        parts = urlsplit(url)
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": parts.path,
            "QUERY_STRING": parts.query,
            "CONTENT_LENGTH": content_length if content_length is not None else str(len(data)),
            "wsgi.input": io.BytesIO(data),
        }
        captured: dict[str, Any] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            captured["status"] = int(status.split(" ", 1)[0])
            captured["headers"] = dict(headers)

        body = b"".join(self.app(environ, start_response))
        return Response(captured["status"], captured["headers"], body)

    def get(self, url: str) -> Response:
        return self.request("GET", url)

    def post(self, url: str, **kwargs: Any) -> Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> Response:
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str) -> Response:
        return self.request("DELETE", url)


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "books.db")


@pytest.fixture
def store(db_path):
    store = BookStore(db_path)
    yield store
    store.close()


@pytest.fixture
def client(store):
    return Client(BookApp(store))


@pytest.fixture
def make_client():
    """Build a Client around an arbitrary store."""
    return lambda store: Client(BookApp(store))


@pytest.fixture
def make_book(client):
    def _make(**overrides: Any) -> dict[str, Any]:
        payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
        payload.update(overrides)
        resp = client.post("/books", json=payload)
        assert resp.status == 201, resp.body
        return resp.json()

    return _make
