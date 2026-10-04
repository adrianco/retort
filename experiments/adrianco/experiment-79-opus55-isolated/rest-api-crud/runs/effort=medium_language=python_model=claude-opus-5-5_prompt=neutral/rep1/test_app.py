"""Integration tests: a real server on an ephemeral port, driven over HTTP."""

import json
import socket
import threading
import urllib.error
import urllib.request
from urllib.parse import urlsplit

import pytest

from app import BookStore, make_server, validate_book

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
EMMA = {"title": "Emma", "author": "Jane Austen", "year": 1815, "isbn": "9780141439587"}


class Client:
    def __init__(self, base_url):
        self.base_url = base_url

    def request(self, method, path, body=None, raw=None):
        data = raw if raw is not None else (
            json.dumps(body).encode() if body is not None else None
        )
        req = urllib.request.Request(self.base_url + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            resp = urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as exc:
            resp = exc
        with resp:
            text = resp.read()
            payload = json.loads(text) if text else None
            return resp.status, payload, resp.headers


@pytest.fixture
def client():
    server = make_server(port=0, db_path=":memory:", quiet=True)
    # A short poll interval keeps shutdown() from adding 0.5s to every test.
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    )
    thread.start()
    host, port = server.server_address[:2]
    yield Client(f"http://{host}:{port}")
    server.shutdown()
    server.server_close()
    server.store.close()
    thread.join(timeout=5)


def test_health(client):
    status, body, headers = client.request("GET", "/health")
    assert status == 200
    assert body == {"status": "ok"}
    assert headers["Content-Type"] == "application/json"


def test_create_book(client):
    status, body, headers = client.request("POST", "/books", DUNE)
    assert status == 201
    assert body == {"id": body["id"], **DUNE}
    assert headers["Location"] == f"/books/{body['id']}"


def test_create_book_with_only_required_fields(client):
    status, body, _ = client.request(
        "POST", "/books", {"title": "Untitled", "author": "Anon"}
    )
    assert status == 201
    assert body["year"] is None
    assert body["isbn"] is None


@pytest.mark.parametrize(
    "payload, expected_error",
    [
        ({"author": "Frank Herbert"}, "title is required"),
        ({"title": "Dune"}, "author is required"),
        ({"title": "   ", "author": "Frank Herbert"}, "title must not be empty"),
        ({"title": "Dune", "author": ""}, "author must not be empty"),
        ({"title": 42, "author": "Frank Herbert"}, "title must be a string"),
        ({**DUNE, "year": "1965"}, "year must be an integer"),
        ({**DUNE, "year": True}, "year must be an integer"),
        ({**DUNE, "year": 10**30}, "year must be between 0 and 9999"),
        ({**DUNE, "isbn": 9780441013593}, "isbn must be a string"),
        ([DUNE], "request body must be a JSON object"),
    ],
)
def test_create_book_validation(client, payload, expected_error):
    status, body, _ = client.request("POST", "/books", payload)
    assert status == 400
    assert body["error"] == "validation failed"
    assert expected_error in body["details"]
    assert client.request("GET", "/books")[1] == []


def test_create_book_reports_all_validation_errors(client):
    status, body, _ = client.request("POST", "/books", {})
    assert status == 400
    assert body["details"] == ["title is required", "author is required"]


@pytest.mark.parametrize("raw", [b"{not json", b""])
def test_create_book_invalid_json(client, raw):
    status, body, _ = client.request("POST", "/books", raw=raw)
    assert status == 400
    assert body == {"error": "request body must be valid JSON"}


def test_get_book(client):
    created = client.request("POST", "/books", DUNE)[1]
    status, body, _ = client.request("GET", f"/books/{created['id']}")
    assert status == 200
    assert body == created


@pytest.mark.parametrize("path", ["/books/999", "/books/abc", "/books/" + "9" * 30])
def test_get_missing_book(client, path):
    status, body, _ = client.request("GET", path)
    assert status == 404
    assert "error" in body


def test_list_books(client):
    assert client.request("GET", "/books")[:2] == (200, [])
    first = client.request("POST", "/books", DUNE)[1]
    second = client.request("POST", "/books", EMMA)[1]
    status, body, _ = client.request("GET", "/books")
    assert status == 200
    assert body == [first, second]


def test_list_books_filtered_by_author(client):
    dune = client.request("POST", "/books", DUNE)[1]
    client.request("POST", "/books", EMMA)
    messiah = client.request(
        "POST", "/books", {"title": "Dune Messiah", "author": "Frank Herbert"}
    )[1]

    status, body, _ = client.request("GET", "/books?author=Frank%20Herbert")
    assert status == 200
    assert body == [dune, messiah]

    # The filter is case-insensitive but matches the whole name.
    assert client.request("GET", "/books?author=frank+herbert")[1] == [dune, messiah]
    assert client.request("GET", "/books?author=Frank")[1] == []
    assert client.request("GET", "/books?author=Nobody")[1] == []


def test_update_book(client):
    created = client.request("POST", "/books", DUNE)[1]
    changes = {"title": "Dune (Revised)", "author": "Frank Herbert", "year": 1966}
    status, body, _ = client.request("PUT", f"/books/{created['id']}", changes)
    assert status == 200
    # PUT replaces the whole resource, so the omitted isbn is cleared.
    assert body == {"id": created["id"], **changes, "isbn": None}
    assert client.request("GET", f"/books/{created['id']}")[1] == body


def test_update_book_validation(client):
    created = client.request("POST", "/books", DUNE)[1]
    status, body, _ = client.request(
        "PUT", f"/books/{created['id']}", {"title": "No Author"}
    )
    assert status == 400
    assert body["details"] == ["author is required"]
    assert client.request("GET", f"/books/{created['id']}")[1] == created


def test_update_missing_book(client):
    status, body, _ = client.request("PUT", "/books/999", DUNE)
    assert status == 404
    assert body == {"error": "book not found"}


def test_delete_book(client):
    created = client.request("POST", "/books", DUNE)[1]
    status, body, _ = client.request("DELETE", f"/books/{created['id']}")
    assert status == 204
    assert body is None
    assert client.request("GET", f"/books/{created['id']}")[0] == 404
    assert client.request("DELETE", f"/books/{created['id']}")[0] == 404


def test_unknown_route_and_method(client):
    assert client.request("GET", "/nope")[0] == 404
    assert client.request("DELETE", "/books")[0] == 405
    assert client.request("POST", "/books/1", DUNE)[0] == 405
    assert client.request("POST", "/health", {})[0] == 405


def test_oversized_body_rejected(client):
    # The server rejects on the declared length without reading the body, so
    # send only the headers rather than racing a large upload against the reply.
    url = urlsplit(client.base_url)
    with socket.create_connection((url.hostname, url.port), timeout=5) as sock:
        sock.sendall(
            b"POST /books HTTP/1.1\r\n"
            b"Host: test\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: 1048577\r\n\r\n"
        )
        response = b""
        while chunk := sock.recv(4096):
            response += chunk
    head, _, body = response.partition(b"\r\n\r\n")
    assert head.split(b"\r\n")[0].split()[1] == b"413"
    assert json.loads(body) == {"error": "request body too large"}


def test_books_persist_across_store_instances(tmp_path):
    db_path = str(tmp_path / "books.db")
    store = BookStore(db_path)
    created = store.create(validate_book(DUNE)[0])
    store.close()

    reopened = BookStore(db_path)
    assert reopened.get(created["id"]) == created
    reopened.close()


def test_validate_book_normalises_whitespace():
    book, errors = validate_book({"title": "  Dune ", "author": " Frank Herbert "})
    assert errors == []
    assert book == {"title": "Dune", "author": "Frank Herbert", "year": None, "isbn": None}
