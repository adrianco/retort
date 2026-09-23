"""A small multi-threaded HTTP server for the WSGI app (standard library only)."""

from __future__ import annotations

import logging
from socketserver import ThreadingMixIn
from typing import Any
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer
from wsgiref.simple_server import make_server as _make_server

logger = logging.getLogger("books_api.access")


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    """Handles each request in its own thread."""

    daemon_threads = True


class LoggingRequestHandler(WSGIRequestHandler):
    """Sends access logs to the ``logging`` module instead of raw stderr."""

    def log_message(self, format: str, *args: Any) -> None:
        logger.info("%s %s", self.address_string(), format % args)


def make_server(host: str, port: int, app: Any) -> ThreadingWSGIServer:
    """Bind a server to ``host:port`` (port 0 picks a free port)."""
    return _make_server(  # type: ignore[return-value]
        host, port, app, server_class=ThreadingWSGIServer, handler_class=LoggingRequestHandler
    )
