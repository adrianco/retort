"""Shared fixtures.

``client`` drives the WSGI application in-process (fast, no sockets) and passes every
call through ``wsgiref.validate.validator``, so any PEP 3333 violation fails the test.
``live_server`` / ``start_server`` run the real threaded HTTP server on a loopback port.
"""

from __future__ import annotations

import http.client
import io
import json
import socket
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Optional
from urllib.parse import unquote, urlsplit
from wsgiref.simple_server import make_server
from wsgiref.util import setup_testing_defaults
from wsgiref.validate import validator

import pytest

from bookapi import BookApp, create_app
from bookapi.server import RequestHandler, ThreadingWSGIServer

_NO_PAYLOAD = object()


@dataclass
class Reply:
    """What came back for a request, whichever way it was sent."""

    status: int
    headers: dict[str, str]  # names lower-cased
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body)

    @classmethod
    def parse(cls, raw_response: bytes) -> Reply:
        """Split the bytes of an HTTP/1.x response into status, headers and body."""
        head, _, body = raw_response.partition(b"\r\n\r\n")
        status_line, *header_lines = head.decode("latin-1").split("\r\n")
        headers = {}
        for line in header_lines:
            name, _, value = line.partition(":")
            headers[name.strip().lower()] = value.strip()
        return cls(int(status_line.split()[1]), headers, body)


def _build_body(payload: Any, raw: Optional[bytes]) -> Optional[bytes]:
    if raw is not None:
        return raw
    if payload is not _NO_PAYLOAD:
        return json.dumps(payload).encode("utf-8")
    return None


class Client:
    """Calls the WSGI application directly."""

    def __init__(self, app: BookApp) -> None:
        self.app = app

    def request(
        self,
        method: str,
        target: str,
        *,
        payload: Any = _NO_PAYLOAD,
        raw: Optional[bytes] = None,
        environ: Optional[dict[str, Any]] = None,
        validate: bool = True,
    ) -> Reply:
        """Send a request; ``payload`` is JSON-encoded, ``raw`` is sent as-is.

        ``environ`` overrides WSGI variables (a value of ``None`` removes one). Pass
        ``validate=False`` to send values (such as a garbage CONTENT_LENGTH) that the
        PEP 3333 validator would refuse.
        """
        # PEP 3333 hands the request bytes to the application as latin-1 text, so a raw "í"
        # (UTF-8 bytes C3 AD) in the target arrives as "Ã\xad". Emulate what servers do.
        parts = urlsplit(target.encode("utf-8").decode("latin-1"))
        body = _build_body(payload, raw)
        env: dict[str, Any] = {}
        setup_testing_defaults(env)
        env.update(
            REQUEST_METHOD=method,
            PATH_INFO=unquote(parts.path, encoding="latin-1"),
            QUERY_STRING=parts.query,
        )
        if body is not None:
            env.update({"CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)})
            if payload is not _NO_PAYLOAD:
                env["CONTENT_TYPE"] = "application/json"
        for name, value in (environ or {}).items():
            if value is None:
                env.pop(name, None)
            else:
                env[name] = value

        captured: dict[str, Any] = {}

        def start_response(status: str, headers: list[tuple[str, str]], exc_info: Any = None) -> None:
            captured["status"], captured["headers"] = status, headers

        app = validator(self.app) if validate else self.app
        result = app(env, start_response)
        try:
            content = b"".join(result)
        finally:
            close = getattr(result, "close", None)
            if close is not None:
                close()
        return Reply(
            int(captured["status"].split()[0]),
            {name.lower(): value for name, value in captured["headers"]},
            content,
        )

    def get(self, target: str, **kwargs: Any) -> Reply:
        return self.request("GET", target, **kwargs)

    def head(self, target: str, **kwargs: Any) -> Reply:
        return self.request("HEAD", target, **kwargs)

    def post(self, target: str, **kwargs: Any) -> Reply:
        return self.request("POST", target, **kwargs)

    def put(self, target: str, **kwargs: Any) -> Reply:
        return self.request("PUT", target, **kwargs)

    def delete(self, target: str, **kwargs: Any) -> Reply:
        return self.request("DELETE", target, **kwargs)


class LiveServer:
    """The real HTTP server, running in a background thread on a free loopback port."""

    def __init__(self, database: Any, handler_class: type = RequestHandler) -> None:
        self.app = create_app(database)
        self._server = make_server("127.0.0.1", 0, self.app, ThreadingWSGIServer, handler_class)
        self.port: int = self._server.server_port
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self._stopped = False

    def request(self, method: str, path: str, *, payload: Any = _NO_PAYLOAD, raw: Optional[bytes] = None) -> Reply:
        body = _build_body(payload, raw)
        headers = {"Content-Type": "application/json"} if payload is not _NO_PAYLOAD else {}
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return Reply(
                response.status,
                {name.lower(): value for name, value in response.getheaders()},
                response.read(),
            )
        finally:
            connection.close()

    def exchange(self, raw_request: bytes) -> Reply:
        """``send_raw`` for a request that is expected to produce a well-formed response."""
        return Reply.parse(self.send_raw(raw_request))

    def send_raw(self, raw_request: bytes, *, timeout: float = 10) -> bytes:
        """Send raw bytes and return everything the server writes until it closes the connection.

        For requests that ``http.client`` would refuse to build (raw UTF-8 in the URL,
        absurd headers, a body that never arrives, ...).
        """
        chunks = []
        with socket.create_connection(("127.0.0.1", self.port), timeout=timeout) as sock:
            sock.sendall(raw_request)
            while True:
                try:
                    data = sock.recv(65536)
                except ConnectionResetError:
                    break
                if not data:
                    break
                chunks.append(data)
        return b"".join(chunks)

    def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
        self.app.close()


@pytest.fixture
def app() -> Iterator[BookApp]:
    application = create_app(":memory:")
    yield application
    application.close()


@pytest.fixture
def client(app: BookApp) -> Client:
    return Client(app)


@pytest.fixture
def file_app(tmp_path: Path) -> Iterator[BookApp]:
    """An application backed by ``tmp_path / "books.db"``, for tests that touch the file itself."""
    application = create_app(tmp_path / "books.db")
    yield application
    application.close()


@pytest.fixture
def file_client(file_app: BookApp) -> Client:
    return Client(file_app)


@pytest.fixture(scope="session")
def loopback() -> None:
    """Skip the requesting test if this environment forbids binding a loopback socket."""
    try:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
    except OSError as exc:
        pytest.skip(f"cannot bind a loopback socket here: {exc}")


@pytest.fixture
def start_server(tmp_path: Path, loopback: None) -> Iterator[Callable[..., LiveServer]]:
    """Factory for live servers (default database: a fresh file); all are stopped afterwards."""
    servers: list[LiveServer] = []

    def start(database: Any = None, *, timeout: Optional[float] = None) -> LiveServer:
        """``timeout`` replaces the handler's socket timeout, to test stalled clients quickly."""
        handler = RequestHandler
        if timeout is not None:
            handler = type("ShortTimeoutHandler", (RequestHandler,), {"timeout": timeout})
        server = LiveServer(database if database is not None else tmp_path / "books.db", handler)
        servers.append(server)
        return server

    yield start
    for server in servers:
        server.stop()


@pytest.fixture
def live_server(start_server: Callable[..., LiveServer]) -> LiveServer:
    return start_server()
