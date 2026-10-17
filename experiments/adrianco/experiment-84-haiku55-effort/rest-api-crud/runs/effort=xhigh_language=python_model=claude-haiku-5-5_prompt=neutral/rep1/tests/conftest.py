"""Shared fixtures: an in-memory repository and a live HTTP server on a free port."""

import json
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from email.message import Message
from typing import Any
from urllib import error, request

import pytest

from book_api import BookRepository, create_server


@pytest.fixture
def repository() -> Iterator[BookRepository]:
    repo = BookRepository(":memory:")
    yield repo
    repo.close()


@pytest.fixture
def server(repository: BookRepository):
    httpd = create_server(repository, "127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=5)


@dataclass
class HttpResult:
    status: int
    headers: Message
    body: Any  # Parsed JSON, or None when the response has no body.


class ApiClient:
    """Minimal JSON client. Never fails on 4xx/5xx; the tests assert on the status."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        # An empty proxy map stops urllib from routing localhost calls through a configured proxy.
        self._opener = request.build_opener(request.ProxyHandler({}))

    def request(
        self,
        method: str,
        path: str,
        json_body: Any = None,
        raw_body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResult:
        all_headers = dict(headers or {})
        data = raw_body
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            all_headers.setdefault("Content-Type", "application/json")
        req = request.Request(self.base_url + path, data=data, method=method, headers=all_headers)
        try:
            with self._opener.open(req) as resp:
                return _result(resp.status, resp.headers, resp.read())
        except error.HTTPError as exc:
            return _result(exc.code, exc.headers, exc.read())

    def get(self, path: str) -> HttpResult:
        return self.request("GET", path)

    def post(self, path: str, **kwargs: Any) -> HttpResult:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> HttpResult:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str) -> HttpResult:
        return self.request("DELETE", path)


def _result(status: int, headers: Message, raw: bytes) -> HttpResult:
    return HttpResult(status=status, headers=headers, body=json.loads(raw) if raw else None)


@pytest.fixture
def api(server) -> ApiClient:
    host, port = server.server_address[:2]
    return ApiClient(f"http://{host}:{port}")
