import http.client
import json
import threading

import pytest

from books_api import create_server


@pytest.fixture
def server():
    """A real HTTP server on a free port, backed by an in-memory database."""
    srv = create_server("127.0.0.1", 0, ":memory:")
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()
    thread.join()


@pytest.fixture
def api(server):
    """Send a request to the server. Returns (status, headers, json_payload)."""
    host, port = server.server_address[:2]

    def request(method, path, body=None, raw=None):
        data = raw
        headers = {}
        if body is not None:
            data = json.dumps(body)
            headers["Content-Type"] = "application/json"
        conn = http.client.HTTPConnection(host, port, timeout=5)
        try:
            conn.request(method, path, body=data, headers=headers)
            resp = conn.getresponse()
            raw_body = resp.read()
            payload = json.loads(raw_body) if raw_body else None
            return resp.status, dict(resp.getheaders()), payload
        finally:
            conn.close()

    return request


@pytest.fixture
def sample_book():
    return {
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt",
        "year": 1999,
        "isbn": "0-201-61622-X",
    }
