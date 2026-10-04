import io
import json
from wsgiref.util import setup_testing_defaults

import pytest

from bookapi import create_app


class Response:
    def __init__(self, status, headers, body):
        self.status = int(status.split(" ", 1)[0])
        self.headers = {name.lower(): value for name, value in headers}
        self.body = body

    def json(self):
        return json.loads(self.body)


class Client:
    """Calls the WSGI app in-process, without opening a socket."""

    def __init__(self, app):
        self.app = app

    def request(self, method, url, json_body=None, body=None):
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
        body = body or b""
        path, _, query = url.partition("?")

        environ = {}
        setup_testing_defaults(environ)
        environ.update(
            REQUEST_METHOD=method,
            PATH_INFO=path,
            QUERY_STRING=query,
            CONTENT_TYPE="application/json",
            CONTENT_LENGTH=str(len(body)),
        )
        environ["wsgi.input"] = io.BytesIO(body)
        environ["wsgi.errors"] = io.StringIO()

        captured = {}

        def start_response(status, headers, exc_info=None):
            captured["status"] = status
            captured["headers"] = headers

        chunks = self.app(environ, start_response)
        return Response(captured["status"], captured["headers"], b"".join(chunks))

    def get(self, url):
        return self.request("GET", url)

    def post(self, url, json_body=None, body=None):
        return self.request("POST", url, json_body, body)

    def put(self, url, json_body=None, body=None):
        return self.request("PUT", url, json_body, body)

    def delete(self, url):
        return self.request("DELETE", url)


@pytest.fixture
def app():
    app = create_app(":memory:")
    yield app
    app.store.close()


@pytest.fixture
def client(app):
    return Client(app)
