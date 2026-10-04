"""End-to-end test over a real HTTP socket."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from bookapi.server import create_server


@pytest.fixture
def base_url(store):
    server = create_server(store, "127.0.0.1", 0)  # port 0: pick any free port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def call(method, url, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_full_crud_lifecycle_over_http(base_url):
    assert call("GET", f"{base_url}/health") == (200, {"status": "ok"})

    status, book = call(
        "POST", f"{base_url}/books", {"title": "Dune", "author": "Frank Herbert"}
    )
    assert status == 201
    url = f"{base_url}/books/{book['id']}"

    assert call("GET", url) == (200, book)
    assert call("GET", f"{base_url}/books?author=Frank%20Herbert") == (200, [book])

    status, updated = call(
        "PUT", url, {"title": "Dune", "author": "Frank Herbert", "year": 1965}
    )
    assert (status, updated["year"]) == (200, 1965)

    assert call("DELETE", url) == (204, None)
    status, error = call("GET", url)
    assert status == 404
    assert "not found" in error["error"]

    status, error = call("POST", f"{base_url}/books", {"author": "Frank Herbert"})
    assert status == 400
    assert error["details"] == {"title": "is required"}
