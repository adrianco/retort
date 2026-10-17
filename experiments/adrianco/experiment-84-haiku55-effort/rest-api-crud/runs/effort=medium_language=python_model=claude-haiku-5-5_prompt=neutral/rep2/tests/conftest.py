import io
import json
import threading
from collections import namedtuple

import pytest

from books.app import BooksApp, make_books_server
from books.db import BookStore

Response = namedtuple("Response", "status headers json")


class Client:
    """Drives the WSGI app directly, without a socket."""

    def __init__(self, app):
        self.app = app

    def request(self, method, path, body=None, raw=None, query=""):
        if raw is None and body is not None:
            raw = json.dumps(body).encode()
        raw = raw or b""
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "CONTENT_LENGTH": str(len(raw)),
            "CONTENT_TYPE": "application/json",
            "wsgi.input": io.BytesIO(raw),
        }
        captured = {}

        def start_response(status, headers):
            captured["status"] = int(status.split()[0])
            captured["headers"] = dict(headers)

        data = b"".join(self.app(environ, start_response))
        payload = json.loads(data) if data else None
        return Response(captured["status"], captured["headers"], payload)

    def get(self, path, query=""):
        return self.request("GET", path, query=query)

    def post(self, path, body=None, raw=None):
        return self.request("POST", path, body=body, raw=raw)

    def put(self, path, body=None):
        return self.request("PUT", path, body=body)

    def delete(self, path):
        return self.request("DELETE", path)


VALID_BOOK = {
    "title": "Dune",
    "author": "Frank Herbert",
    "year": 1965,
    "isbn": "978-0-306-40615-7",
}


@pytest.fixture
def store():
    s = BookStore(":memory:")
    yield s
    s.close()


@pytest.fixture
def client(store):
    return Client(BooksApp(store))


@pytest.fixture
def live_server(store):
    server = make_books_server(BooksApp(store))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
