import io
import json
from dataclasses import dataclass
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from bookapi import BookAPI, BookStore


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body)


class Client:
    """Minimal in-process WSGI client: calls the app without opening a socket."""

    def __init__(self, app: BookAPI) -> None:
        self._app = app

    def request(
        self,
        method: str,
        path: str,
        json_body: Any = None,
        raw_body: bytes | None = None,
        environ: dict[str, Any] | None = None,
    ) -> Response:
        path, _, query = path.partition("?")
        body = raw_body if raw_body is not None else b""
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")

        env: dict[str, Any] = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "CONTENT_LENGTH": str(len(body)),
            "CONTENT_TYPE": "application/json",
            "wsgi.input": io.BytesIO(body),
        }
        env.update(environ or {})
        setup_testing_defaults(env)

        captured: dict[str, Any] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            captured["status"] = int(status.split(" ", 1)[0])
            captured["headers"] = dict(headers)

        chunks = self._app(env, start_response)
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
def store(tmp_path):
    store = BookStore(str(tmp_path / "books.db"))
    yield store
    store.close()


@pytest.fixture
def client(store):
    return Client(BookAPI(store))


@pytest.fixture
def dune(client):
    """A book that already exists in the collection."""
    response = client.post(
        "/books",
        {
            "title": "Dune",
            "author": "Frank Herbert",
            "year": 1965,
            "isbn": "978-0441172719",
        },
    )
    assert response.status == 201
    return response.json()
