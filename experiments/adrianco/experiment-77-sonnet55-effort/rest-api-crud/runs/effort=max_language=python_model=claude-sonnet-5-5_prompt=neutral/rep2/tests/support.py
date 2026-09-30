"""Helpers shared by the test modules."""

from __future__ import annotations

import io
import json as jsonlib
import time
from dataclasses import dataclass
from typing import Any, Callable
from wsgiref.util import setup_testing_defaults
from wsgiref.validate import validator

_UNSET: Any = object()


def book_payload(**overrides: Any) -> dict[str, Any]:
    """A valid request body for creating a book; keyword arguments override fields."""
    payload = {
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt",
        "year": 1999,
        "isbn": "978-0201616224",
    }
    payload.update(overrides)
    return payload


@dataclass
class ApiResponse:
    status: int
    headers: dict[str, str]  # names lower-cased
    body: bytes

    def json(self) -> Any:
        return jsonlib.loads(self.body)


class WSGIClient:
    """Calls a WSGI application in-process, without any sockets.

    Unless ``validate=False``, every request and response is checked against
    PEP 3333 by :mod:`wsgiref.validate` (status line format, header types, no
    ``Content-Type`` on a 204, iterators closed, ...).
    """

    def __init__(self, app: Callable[..., Any], *, validate: bool = True) -> None:
        self._app = validator(app) if validate else app

    def request(
        self,
        method: str,
        target: str,
        *,
        json: Any = _UNSET,
        data: bytes | None = None,
        environ: dict[str, Any] | None = None,
    ) -> ApiResponse:
        """Send a request. ``target`` is the path plus an optional raw query string."""
        path, _, query = target.partition("?")
        body = b""
        if json is not _UNSET:
            body = jsonlib.dumps(json).encode("utf-8")
        elif data is not None:
            body = data

        env: dict[str, Any] = {
            "REQUEST_METHOD": method,
            "SCRIPT_NAME": "",  # real servers always send it; the validator requires it
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "wsgi.input": io.BytesIO(body),
        }
        if body:
            env["CONTENT_LENGTH"] = str(len(body))
            env["CONTENT_TYPE"] = "application/json"
        env.update(environ or {})
        setup_testing_defaults(env)

        captured: dict[str, Any] = {}

        def start_response(status: str, headers: list[tuple[str, str]], exc_info: Any = None):
            captured["status"] = status
            captured["headers"] = headers

        result = self._app(env, start_response)
        try:
            payload = b"".join(result)
        finally:
            close = getattr(result, "close", None)
            if close is not None:
                close()

        return ApiResponse(
            status=int(captured["status"].split(" ", 1)[0]),
            headers={name.lower(): value for name, value in captured["headers"]},
            body=payload,
        )

    def get(self, target: str, **kwargs: Any) -> ApiResponse:
        return self.request("GET", target, **kwargs)

    def post(self, target: str, **kwargs: Any) -> ApiResponse:
        return self.request("POST", target, **kwargs)

    def put(self, target: str, **kwargs: Any) -> ApiResponse:
        return self.request("PUT", target, **kwargs)

    def delete(self, target: str, **kwargs: Any) -> ApiResponse:
        return self.request("DELETE", target, **kwargs)


def wait_for(condition: Callable[[], bool], timeout: float = 5.0) -> bool:
    """Poll until ``condition()`` is true; return whether it became true in time."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.01)
    return condition()
