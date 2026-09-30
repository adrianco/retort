"""HTTP server wiring: serves the WSGI app with the standard library."""

from __future__ import annotations

import logging
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from .app import BookApp
from .db import BookStore


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class QuietHandler(WSGIRequestHandler):
    """Request handler that logs one line per request through ``logging``."""

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        logging.getLogger("bookapi.access").info("%s - %s", self.address_string(), format % args)


def create_server(host: str, port: int, db_path: str) -> tuple[ThreadingWSGIServer, BookStore]:
    """Build (but do not start) a server. Pass port 0 to pick a free port."""
    store = BookStore(db_path)
    try:
        httpd = make_server(
            host, port, BookApp(store), server_class=ThreadingWSGIServer, handler_class=QuietHandler
        )
    except Exception:
        store.close()
        raise
    return httpd, store
