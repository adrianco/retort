from __future__ import annotations

import io
import json
from typing import Any
from wsgiref.util import setup_testing_defaults
from wsgiref.validate import validator

import pytest

from books_api.app import BookAPI
from books_api.storage import BookRepository

_NO_BODY = object()


class WSGIResponse:
    def __init__(self, status: str, headers: list[tuple[str, str]], body: bytes) -> None:
        self.status_code = int(status.split(" ", 1)[0])
        self.headers = {name.lower(): value for name, value in headers}
        self.body = body

    def json(self) -> Any:
        return json.loads(self.body)


class WSGIClient:
    """Calls a WSGI app in-process.

    The app is wrapped in wsgiref's validator, so every request also checks
    that the app follows the WSGI spec (PEP 3333).
    """

    def __init__(self, app: Any, *, validate: bool = True) -> None:
        self.app = validator(app) if validate else app

    def request(
        self,
        method: str,
        url: str,
        *,
        json_body: Any = _NO_BODY,
        data: bytes | None = None,
        content_type: str | None = "application/json",
        environ_overrides: dict[str, Any] | None = None,
    ) -> WSGIResponse:
        path, _, query = url.partition("?")
        if json_body is not _NO_BODY:
            data = json.dumps(json_body).encode("utf-8")
        environ: dict[str, Any] = {
            "REQUEST_METHOD": method,
            "SCRIPT_NAME": "",
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "wsgi.input": io.BytesIO(data or b""),
        }
        if data is not None:
            environ["CONTENT_LENGTH"] = str(len(data))
            if content_type is not None:
                environ["CONTENT_TYPE"] = content_type
        environ.update(environ_overrides or {})
        setup_testing_defaults(environ)

        captured: dict[str, Any] = {}

        def start_response(status, headers, exc_info=None):
            captured["status"], captured["headers"] = status, headers
            return lambda chunk: None

        result = self.app(environ, start_response)
        try:
            body = b"".join(result)
        finally:
            if hasattr(result, "close"):
                result.close()
        return WSGIResponse(captured["status"], captured["headers"], body)

    def get(self, url: str, **kwargs: Any) -> WSGIResponse:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, json_body: Any = _NO_BODY, **kwargs: Any) -> WSGIResponse:
        return self.request("POST", url, json_body=json_body, **kwargs)

    def put(self, url: str, json_body: Any = _NO_BODY, **kwargs: Any) -> WSGIResponse:
        return self.request("PUT", url, json_body=json_body, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> WSGIResponse:
        return self.request("DELETE", url, **kwargs)


@pytest.fixture
def repository():
    repo = BookRepository(":memory:")
    yield repo
    repo.close()


@pytest.fixture
def app(repository):
    return BookAPI(repository)


@pytest.fixture
def client(app):
    return WSGIClient(app)


@pytest.fixture
def unvalidated_client(app):
    """For malformed requests that wsgiref's validator would refuse to send."""
    return WSGIClient(app, validate=False)
