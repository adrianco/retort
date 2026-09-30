"""Small request/response helpers for the WSGI application."""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any, Iterable, Mapping, Optional
from urllib.parse import parse_qs

# A book is a handful of short strings, so anything bigger is not a valid request.
MAX_BODY_BYTES = 64 * 1024

JSON_CONTENT_TYPE = "application/json; charset=utf-8"

Headers = list[tuple[str, str]]


@dataclass
class Response:
    """An HTTP response, ready to be handed to ``start_response``."""

    status: HTTPStatus
    body: bytes = b""
    headers: Headers = field(default_factory=list)

    @property
    def status_line(self) -> str:
        return f"{self.status.value} {self.status.phrase}"

    def without_body(self) -> Response:
        """The same response minus its body, as required for HEAD requests."""
        return Response(self.status, b"", self.headers)


def json_response(status: HTTPStatus, payload: Any, headers: Iterable[tuple[str, str]] = ()) -> Response:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return Response(
        status,
        body,
        [("Content-Type", JSON_CONTENT_TYPE), ("Content-Length", str(len(body))), *headers],
    )


class HTTPError(Exception):
    """Raised to abort request handling with a JSON error response.

    The body is ``{"error": message}``, plus ``"details"`` when given.
    """

    def __init__(
        self,
        status: HTTPStatus,
        message: str,
        *,
        details: Optional[Mapping[str, str]] = None,
        headers: Iterable[tuple[str, str]] = (),
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details
        self.headers = list(headers)

    def response(self) -> Response:
        payload: dict[str, Any] = {"error": self.message}
        if self.details:
            payload["details"] = self.details
        return json_response(self.status, payload, self.headers)


def _reject_constant(name: str) -> Any:
    """``json`` accepts NaN/Infinity by default; they are not valid JSON."""
    raise ValueError(f"{name} is not valid JSON")


def _decode_query_string(raw: str) -> str:
    """Recover the UTF-8 text of a query string that PEP 3333 presents as latin-1.

    Well-behaved clients percent-encode non-ASCII characters (which ``parse_qs`` decodes as
    UTF-8), but curl and friends send them raw, and those arrive here as mojibake.
    """
    try:
        return raw.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return raw


class Request:
    """Read-only view of a WSGI ``environ`` offering what the handlers need."""

    def __init__(self, environ: Mapping[str, Any]) -> None:
        self.environ = environ
        self.method: str = environ.get("REQUEST_METHOD", "GET")  # methods are case-sensitive
        self.path: str = environ.get("PATH_INFO") or "/"
        self.script_name: str = environ.get("SCRIPT_NAME", "")
        self._query = parse_qs(_decode_query_string(environ.get("QUERY_STRING", "")), keep_blank_values=True)

    def query_param(self, name: str) -> Optional[str]:
        """The trimmed first value of query parameter ``name``; ``None`` if absent or blank."""
        values = self._query.get(name)
        return (values[0].strip() or None) if values else None

    def json_object(self) -> dict[str, Any]:
        """The request body parsed as a JSON object.

        Raises :class:`HTTPError` if the body cannot be read in full (400 for a bad
        ``Content-Length``, 408 if the client stalls, 411 if there is no ``Content-Length``,
        413 if it is too large) or is not valid UTF-8 JSON describing an object (400).
        """
        raw = self._read_body()
        try:
            payload = json.loads(raw.decode("utf-8-sig"), parse_constant=_reject_constant)
        except (ValueError, RecursionError):  # includes JSONDecodeError and UnicodeDecodeError
            raise HTTPError(HTTPStatus.BAD_REQUEST, "Request body must be valid JSON") from None
        if not isinstance(payload, dict):
            raise HTTPError(HTTPStatus.BAD_REQUEST, "Request body must be a JSON object")
        return payload

    def _read_body(self) -> bytes:
        # PEP 3333: a missing CONTENT_LENGTH means there is no body, and the
        # application must not read past it.
        raw_length = self.environ.get("CONTENT_LENGTH") or ""
        if not raw_length and self.environ.get("HTTP_TRANSFER_ENCODING"):
            raise HTTPError(
                HTTPStatus.LENGTH_REQUIRED,
                "Content-Length header is required (chunked request bodies are not supported)",
            )
        raw_length = raw_length or "0"
        if not (raw_length.isascii() and raw_length.isdigit()):
            raise HTTPError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header")
        digits = raw_length.lstrip("0")
        # Compare digit counts before int(), which refuses very long digit strings (ValueError).
        if len(digits) > len(str(MAX_BODY_BYTES)) or (digits and int(digits) > MAX_BODY_BYTES):
            raise HTTPError(HTTPStatus(413), f"Request body must not exceed {MAX_BODY_BYTES} bytes")
        length = int(digits) if digits else 0
        if not length:
            return b""
        try:
            return self.environ["wsgi.input"].read(length)
        except socket.timeout:  # the client promised more bytes than it sent
            raise HTTPError(HTTPStatus.REQUEST_TIMEOUT, "Timed out waiting for the request body") from None
