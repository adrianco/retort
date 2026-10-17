"""End-to-end tests: real HTTP requests over a socket against a running server."""

import http.client
import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

from bookapi.server import MAX_BODY_BYTES

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}


def request(base, method, path, data=None):
    """Return (status, headers, raw_body) for a request, including error statuses."""
    body = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        base + path,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read()


def raw_request(base, method, path, headers):
    """Send only headers (no body) so the server's early rejections can be observed."""
    host = urlsplit(base)
    conn = http.client.HTTPConnection(host.hostname, host.port, timeout=5)
    conn.putrequest(method, path, skip_accept_encoding=True)
    for name, value in headers.items():
        conn.putheader(name, value)
    conn.endheaders()
    response = conn.getresponse()
    body = response.read()
    conn.close()
    return response, body


def test_full_book_lifecycle_over_http(live_server):
    status, headers, raw = request(live_server, "POST", "/books", DUNE)
    assert status == 201
    book = json.loads(raw)
    assert headers["Location"] == f"/books/{book['id']}"
    assert book == {"id": book["id"], **DUNE}

    status, _, raw = request(live_server, "GET", f"/books/{book['id']}")
    assert status == 200
    assert json.loads(raw) == book

    status, _, raw = request(live_server, "GET", "/books?author=frank%20herbert")
    assert status == 200
    assert json.loads(raw) == [book]

    status, _, raw = request(
        live_server, "PUT", f"/books/{book['id']}", {"title": "Dune", "author": "Frank Herbert"}
    )
    assert status == 200
    assert json.loads(raw) == {"id": book["id"], "title": "Dune", "author": "Frank Herbert", "year": None, "isbn": None}

    status, _, raw = request(live_server, "DELETE", f"/books/{book['id']}")
    assert status == 204
    assert raw == b""

    status, _, raw = request(live_server, "GET", f"/books/{book['id']}")
    assert status == 404
    assert json.loads(raw) == {"error": "Book not found"}


def test_health_endpoint_over_http(live_server):
    status, headers, raw = request(live_server, "GET", "/health")

    assert status == 200
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    assert json.loads(raw) == {"status": "ok"}


def test_validation_errors_are_returned_as_json_400(live_server):
    status, headers, raw = request(live_server, "POST", "/books", {"year": 1965})

    assert status == 400
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    assert json.loads(raw) == {
        "error": "Validation failed",
        "details": {"title": "is required", "author": "is required"},
    }


def test_no_content_response_has_no_body_or_content_length(live_server):
    created = json.loads(request(live_server, "POST", "/books", DUNE)[2])

    response, body = raw_request(
        live_server, "DELETE", f"/books/{created['id']}", {}
    )

    assert response.status == 204
    assert body == b""
    assert response.getheader("Content-Length") is None


def test_oversized_body_is_rejected_with_413(live_server):
    response, _ = raw_request(
        live_server,
        "POST",
        "/books",
        {"Content-Length": str(MAX_BODY_BYTES + 1), "Content-Type": "application/json"},
    )

    assert response.status == 413


def test_chunked_request_bodies_are_rejected_with_501(live_server):
    response, _ = raw_request(
        live_server, "POST", "/books", {"Transfer-Encoding": "chunked"}
    )

    assert response.status == 501


def test_non_numeric_content_length_is_rejected_with_400(live_server):
    response, _ = raw_request(live_server, "POST", "/books", {"Content-Length": "lots"})

    assert response.status == 400


def test_concurrent_writes_are_all_stored(live_server):
    def create(i):
        status, _, _ = request(live_server, "POST", "/books", {"title": f"Book {i}", "author": "Many"})
        return status

    with ThreadPoolExecutor(max_workers=10) as pool:
        statuses = list(pool.map(create, range(40)))

    assert statuses == [201] * 40
    _, _, raw = request(live_server, "GET", "/books?author=Many")
    assert len(json.loads(raw)) == 40
