import http.client
import json
import socket
import threading

import pytest

from bookapi import create_server
from bookapi.api import MAX_BODY_BYTES

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965}


@pytest.fixture
def server():
    srv = create_server("127.0.0.1", 0, ":memory:")
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()
    thread.join(timeout=5)


def request(server, method, path, payload=None, headers=None):
    """Send a real HTTP request and return (status, headers, decoded JSON or None)."""
    host, port = server.server_address[:2]
    conn = http.client.HTTPConnection(host, port, timeout=5)
    body = None if payload is None else json.dumps(payload)
    conn.request(method, path, body=body, headers=headers or {"Content-Type": "application/json"})
    response = conn.getresponse()
    raw = response.read()
    conn.close()
    headers = {name: value for name, value in response.getheaders()}
    return response.status, headers, (json.loads(raw) if raw else None)


def test_book_lifecycle_over_http(server):
    status, headers, book = request(server, "POST", "/books", DUNE)
    assert status == 201
    assert headers["Content-Type"] == "application/json"
    book_path = headers["Location"]

    status, _, fetched = request(server, "GET", book_path)
    assert status == 200 and fetched == book

    status, _, listing = request(server, "GET", "/books?author=herbert")
    assert status == 200 and [item["id"] for item in listing] == [book["id"]]

    status, _, updated = request(server, "PUT", book_path, {**DUNE, "year": 1966})
    assert status == 200 and updated["year"] == 1966

    status, headers, body = request(server, "DELETE", book_path)
    assert status == 204 and body is None
    assert "Content-Length" not in headers

    status, _, body = request(server, "GET", book_path)
    assert status == 404 and body == {"error": "Book not found"}


def test_validation_errors_are_reported_as_json_over_http(server):
    status, _, body = request(server, "POST", "/books", {"year": 1965})

    assert status == 400
    assert body["details"] == {"title": "is required", "author": "is required"}


def test_invalid_json_over_http_returns_400(server):
    host, port = server.server_address[:2]
    conn = http.client.HTTPConnection(host, port, timeout=5)
    conn.request("POST", "/books", body="{oops", headers={"Content-Type": "application/json"})
    response = conn.getresponse()
    body = json.loads(response.read())
    conn.close()

    assert response.status == 400
    assert body == {"error": "Request body must be valid JSON"}


def test_health_check_over_http(server):
    status, _, body = request(server, "GET", "/health")

    assert status == 200
    assert body == {"status": "ok"}


def test_oversized_body_is_rejected_without_being_read(server):
    headers = {"Content-Type": "application/json", "Content-Length": str(MAX_BODY_BYTES + 1)}

    status, _, body = request(server, "POST", "/books", headers=headers)

    assert status == 413
    assert body == {"error": "Request body too large"}


def test_raw_utf8_in_query_string_matches_author_filter(server):
    # http.client refuses non-ASCII request lines, so send the bytes directly.
    request(server, "POST", "/books", {"title": "Cien años", "author": "Gabriel García Márquez"})
    host, port = server.server_address[:2]
    with socket.create_connection((host, port), timeout=5) as sock:
        sock.sendall("GET /books?author=garcía HTTP/1.0\r\nHost: test\r\n\r\n".encode("utf-8"))
        raw = b""
        while chunk := sock.recv(4096):
            raw += chunk
    body = json.loads(raw.split(b"\r\n\r\n", 1)[1])

    assert [book["title"] for book in body] == ["Cien años"]


def test_invalid_content_length_returns_400(server):
    status, _, body = request(server, "POST", "/books", headers={"Content-Length": "lots"})

    assert status == 400
    assert body == {"error": "Invalid Content-Length header"}
