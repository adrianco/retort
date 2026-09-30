"""Small WSGI helpers: request parsing, JSON responses and HTTP errors."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs

MAX_BODY_BYTES = 1024 * 1024  # request bodies larger than this are rejected with 413
JSON_CONTENT_TYPE = "application/json"

StartResponse = Callable[..., Any]


def _from_latin1(text: str) -> str:
    """Re-read text that PEP 3333 servers decode as latin-1 as the UTF-8 it really is.

    A client that sends raw UTF-8 in the URL (``curl '.../books?author=García'``) would
    otherwise arrive as mojibake. Text that is not valid UTF-8 is returned unchanged.
    """
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


class HTTPError(Exception):
    """An error that maps directly onto a JSON error response."""

    def __init__(
        self,
        status: int,
        message: str,
        *,
        details: dict[str, str] | None = None,
        headers: list[tuple[str, str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details
        self.headers = headers or []

    def to_response(self) -> Response:
        body: dict[str, Any] = {"error": self.message}
        if self.details:
            body["details"] = self.details
        return Response(self.status, body, self.headers)


@dataclass
class Response:
    """A response with an optional JSON body (``None`` means no body at all)."""

    status: int
    body: Any = None
    headers: list[tuple[str, str]] = field(default_factory=list)

    def send(self, start_response: StartResponse, *, head_only: bool = False) -> list[bytes]:
        """Start the WSGI response and return the body chunks.

        For HEAD the headers (including Content-Length) describe the body a GET would
        have produced, but no body is sent.
        """
        headers = [*self.headers, ("X-Content-Type-Options", "nosniff")]
        payload = b""
        if self.body is not None:
            payload = json.dumps(self.body, ensure_ascii=False).encode("utf-8")
            headers += [
                ("Content-Type", JSON_CONTENT_TYPE),
                ("Content-Length", str(len(payload))),
            ]
        start_response(f"{self.status} {HTTPStatus(self.status).phrase}", headers)
        return [] if head_only or not payload else [payload]


class Request:
    """The parts of a WSGI request that the handlers care about."""

    def __init__(self, environ: dict[str, Any]) -> None:
        self._environ = environ
        self.method: str = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO") or "/"
        # "/books/" and "/books" are the same resource.
        self.path = path[:-1] if len(path) > 1 and path.endswith("/") else path
        self.query = parse_qs(_from_latin1(environ.get("QUERY_STRING", "")), keep_blank_values=True)

    def json_object(self) -> dict[str, Any]:
        """The request body parsed as a JSON object.

        The Content-Type header is not consulted: any body that parses as a JSON object is
        accepted, which keeps ``curl -d`` and hand-rolled clients working.
        """
        raw = self._read_body()
        if not raw.strip():
            raise HTTPError(400, "Request body is required")
        try:
            payload = json.loads(raw.decode("utf-8-sig"))
        except (ValueError, RecursionError):  # bad UTF-8, bad JSON, absurd nesting or number
            raise HTTPError(400, "Request body must be valid JSON") from None
        if not isinstance(payload, dict):
            raise HTTPError(400, "Request body must be a JSON object")
        return payload

    def _read_body(self) -> bytes:
        if "chunked" in str(self._environ.get("HTTP_TRANSFER_ENCODING", "")).lower():
            # WSGI gives no portable way to read an unbounded stream, so insist on a length.
            raise HTTPError(411, "Chunked request bodies are not supported; send Content-Length")
        text = str(self._environ.get("CONTENT_LENGTH") or "").strip()
        if not text:
            return b""
        if not (text.isascii() and text.isdigit()):
            raise HTTPError(400, "Invalid Content-Length header")
        # Anything longer than 18 digits is far over the limit (and int() stays cheap and safe).
        length = int(text) if len(text) <= 18 else MAX_BODY_BYTES + 1
        if length > MAX_BODY_BYTES:
            raise HTTPError(413, f"Request body must not exceed {MAX_BODY_BYTES} bytes")
        try:
            data: bytes = self._environ["wsgi.input"].read(length)
        except OSError:  # includes socket timeouts and connections dropped mid-body
            raise HTTPError(408, "Could not read the request body") from None
        return data
