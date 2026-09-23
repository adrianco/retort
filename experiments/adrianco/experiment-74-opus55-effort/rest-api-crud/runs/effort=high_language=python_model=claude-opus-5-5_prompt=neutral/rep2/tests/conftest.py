import http.client
import json
import threading

import pytest

from books_api import create_server


class Client:
    def __init__(self, host, port):
        self.host, self.port = host, port

    def request(self, method, path, body=None, raw=None, headers=None):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        headers = dict(headers or {})
        data = raw
        if body is not None:
            data = json.dumps(body).encode()
            headers.setdefault("Content-Type", "application/json")
        conn.request(method, path, body=data, headers=headers)
        resp = conn.getresponse()
        payload = resp.read()
        conn.close()
        parsed = json.loads(payload) if payload else None
        return resp.status, parsed, resp


@pytest.fixture
def server(tmp_path):
    srv = create_server("127.0.0.1", 0, str(tmp_path / "test.db"), quiet=True)
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()
    srv.store.close()


@pytest.fixture
def client(server):
    host, port = server.server_address[:2]
    return Client(host, port)


@pytest.fixture
def book():
    return {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}
