import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from books_api import create_app  # noqa: E402


class Response:
    def __init__(self, status, headers, body):
        self.status = status
        self.headers = headers
        self.body = body

    def json(self):
        return json.loads(self.body)


class WsgiClient:
    """Calls the WSGI app in-process, without a network socket."""

    def __init__(self, app):
        self.app = app

    def request(self, method, path, body=None, raw=None):
        path, _, query = path.partition("?")
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else b"")
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "CONTENT_LENGTH": str(len(data)),
            "CONTENT_TYPE": "application/json",
            "wsgi.input": io.BytesIO(data),
        }
        captured = {}

        def start_response(status, headers):
            captured["status"] = int(status.split()[0])
            captured["headers"] = dict(headers)

        chunks = self.app(environ, start_response)
        return Response(captured["status"], captured["headers"], b"".join(chunks))

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, body=None, raw=None):
        return self.request("POST", path, body, raw)

    def put(self, path, body=None, raw=None):
        return self.request("PUT", path, body, raw)

    def delete(self, path):
        return self.request("DELETE", path)


@pytest.fixture
def app():
    application = create_app(":memory:")
    yield application
    application.repo.close()


@pytest.fixture
def client(app):
    return WsgiClient(app)


@pytest.fixture
def sample_book():
    return {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}
