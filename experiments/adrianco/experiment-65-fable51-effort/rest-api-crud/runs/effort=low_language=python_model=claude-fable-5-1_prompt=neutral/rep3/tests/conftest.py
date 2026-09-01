import json
import threading
import urllib.error
import urllib.request

import pytest

from src.app import create_server


class Client:
    def __init__(self, base):
        self.base = base

    def request(self, method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read()
                return resp.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            raw = e.read()
            return e.code, (json.loads(raw) if raw else None)


@pytest.fixture
def client(tmp_path):
    server = create_server(str(tmp_path / "test.db"), "127.0.0.1", 0, quiet=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield Client(f"http://{host}:{port}")
    server.shutdown()
    server.server_close()
    server.repo.close()
