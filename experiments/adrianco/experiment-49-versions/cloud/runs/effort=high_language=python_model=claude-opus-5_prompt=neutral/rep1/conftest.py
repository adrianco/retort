"""Shared pytest fixtures.

Lives at the repository root so that ``bookapi`` is importable without any
installation step.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from http.client import HTTPConnection
from typing import Any, NamedTuple

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bookapi.server import make_http_server  # noqa: E402


class Response(NamedTuple):
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))


class Client:
    """Minimal HTTP client that talks to the API over a real socket."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    def request(
        self,
        method: str,
        path: str,
        body: Any = None,
        *,
        raw_body: bytes | None = None,
        content_type: str | None = "application/json",
    ) -> Response:
        payload = raw_body
        if payload is None and body is not None:
            payload = json.dumps(body).encode("utf-8")

        headers = {}
        if payload is not None and content_type is not None:
            headers["Content-Type"] = content_type

        conn = HTTPConnection(self.host, self.port, timeout=10)
        try:
            conn.request(method, path, body=payload, headers=headers)
            response = conn.getresponse()
            return Response(
                status=response.status,
                headers={k.lower(): v for k, v in response.getheaders()},
                body=response.read(),
            )
        finally:
            conn.close()

    def get(self, path: str, **kw) -> Response:
        return self.request("GET", path, **kw)

    def post(self, path: str, body: Any = None, **kw) -> Response:
        return self.request("POST", path, body, **kw)

    def put(self, path: str, body: Any = None, **kw) -> Response:
        return self.request("PUT", path, body, **kw)

    def delete(self, path: str, **kw) -> Response:
        return self.request("DELETE", path, **kw)


@pytest.fixture
def client(tmp_path) -> Client:
    """Run the real server on an ephemeral port against a temporary database."""
    server = make_http_server(
        "127.0.0.1", 0, str(tmp_path / "test-books.db"), quiet=True
    )
    # A short poll interval keeps fixture teardown from dominating the run time.
    thread = threading.Thread(target=server.serve_forever, args=(0.01,), daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        yield Client(host, port)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.fixture
def sample_book() -> dict[str, Any]:
    return {
        "title": "Nineteen Eighty-Four",
        "author": "George Orwell",
        "year": 1949,
        "isbn": "978-0-452-28423-4",
    }
