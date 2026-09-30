"""Minimal request/response helpers for the WSGI layer."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any, Callable
from urllib.parse import parse_qs

# Book payloads are tiny; anything larger is refused without being read.
MAX_BODY_BYTES = 64 * 1024

# Looked up by number because the enum member was renamed in Python 3.13.
PAYLOAD_TOO_LARGE = HTTPStatus(413)

Environ = dict[str, Any]
StartResponse = Callable[..., Any]
Headers = list[tuple[str, str]]


@dataclass
class Response:
    """A JSON response. ``body=None`` gives an empty body, as for ``204``."""

    status: HTTPStatus
    body: Any = None
    headers: Headers = field(default_factory=list)

    def send(self, start_response: StartResponse, *, head_only: bool = False) -> list[bytes]:
        """Start the WSGI response and return the body chunks.

        For ``HEAD`` the headers (including ``Content-Length``) are those of the
        equivalent ``GET`` but no body is sent.
        """
        headers = list(self.headers)
        payload = b""
        if self.body is not None:
            payload = json.dumps(self.body, ensure_ascii=False).encode("utf-8")
            headers.append(("Content-Type", "application/json"))
            headers.append(("Content-Length", str(len(payload))))
        start_response(f"{self.status.value} {self.status.phrase}", headers)
        return [payload] if payload and not head_only else []


class HTTPError(Exception):
    """An error that maps directly onto a JSON error response."""

    def __init__(
        self,
        status: HTTPStatus,
        message: str,
        *,
        details: dict[str, str] | None = None,
        headers: Headers | None = None,
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


class Request:
    """A read-only view of a WSGI ``environ``."""

    def __init__(self, environ: Environ) -> None:
        self.environ = environ
        self.method = environ.get("REQUEST_METHOD", "GET")  # case-sensitive, per RFC 9110
        # Where the app is mounted, if not at the root: needed to build absolute paths.
        self.script_name = environ.get("SCRIPT_NAME", "")
        # "/books/" and "/books" name the same resource.
        self.path = (environ.get("PATH_INFO") or "/").rstrip("/") or "/"

    def query_param(self, name: str) -> str | None:
        """First value of a query-string parameter; ``None`` if absent or blank."""
        values = parse_qs(_decode_query_string(self.environ.get("QUERY_STRING", ""))).get(name)
        if not values:
            return None
        return values[0].strip() or None

    def json_body(self) -> Any:
        """Read and decode the JSON request body.

        The ``Content-Type`` header is deliberately not enforced, so that
        ``curl -d '{...}'`` works without extra flags.
        """
        length = self._content_length()
        if length == 0:
            raise HTTPError(HTTPStatus.BAD_REQUEST, "Request body is required")
        try:
            raw = self.environ["wsgi.input"].read(length)
        except OSError:  # the client stalled (socket timeout) or hung up mid-body
            raise HTTPError(
                HTTPStatus.REQUEST_TIMEOUT, "The request body could not be read in time"
            ) from None
        try:
            return json.loads(raw)
        except (ValueError, RecursionError):  # bad JSON, bad UTF-8, or absurd nesting
            raise HTTPError(HTTPStatus.BAD_REQUEST, "Request body must be valid JSON") from None

    def _content_length(self) -> int:
        value = (self.environ.get("CONTENT_LENGTH") or "").strip()
        if not value:
            if "HTTP_TRANSFER_ENCODING" in self.environ:
                # WSGI gives no portable way to read a chunked body, so insist on a length.
                raise HTTPError(
                    HTTPStatus.LENGTH_REQUIRED,
                    "Chunked request bodies are not supported; send a Content-Length header",
                )
            return 0
        if not (value.isascii() and value.isdigit()):
            raise HTTPError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header")
        # Compare digit counts before converting: int() refuses absurdly long strings.
        digits = value.lstrip("0") or "0"
        if len(digits) > len(str(MAX_BODY_BYTES)) or int(digits) > MAX_BODY_BYTES:
            raise HTTPError(
                PAYLOAD_TOO_LARGE, f"Request body must not exceed {MAX_BODY_BYTES} bytes"
            )
        return int(digits)


def _decode_query_string(raw: str) -> str:
    """Undo PEP 3333's latin-1 view of the query string.

    WSGI hands the raw bytes over as latin-1 text, so a client that sends UTF-8
    without percent-encoding it (as ``curl`` does) would otherwise be mangled.
    """
    try:
        return raw.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return raw
