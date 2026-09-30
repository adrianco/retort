import io
import json
import threading
from wsgiref.simple_server import WSGIRequestHandler, make_server
from urllib import request as urlrequest
from urllib.error import HTTPError

import pytest

from books_api import BookStore, create_app
from books_api.__main__ import ThreadingWSGIServer


class Client:
    """Minimal in-process WSGI test client."""

    def __init__(self, app):
        self.app = app

    def call(self, method, path, body=None, raw=None):
        path, _, query = path.partition("?")
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else b"")
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "CONTENT_LENGTH": str(len(data)),
            "wsgi.input": io.BytesIO(data),
        }
        captured = {}

        def start_response(status, headers):
            captured["status"] = int(status.split()[0])
            captured["headers"] = dict(headers)

        out = b"".join(self.app(environ, start_response))
        return captured["status"], (json.loads(out) if out else None), captured["headers"]


@pytest.fixture
def client():
    return Client(create_app(BookStore(":memory:")))


BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}


def test_health(client):
    status, body, _ = client.call("GET", "/health")
    assert (status, body) == (200, {"status": "ok"})


def test_create_and_get(client):
    status, created, headers = client.call("POST", "/books", BOOK)
    assert status == 201
    assert headers["Content-Type"] == "application/json"
    assert created == {"id": 1, **BOOK}
    assert client.call("GET", "/books/1")[:2] == (200, created)


def test_create_minimal_book(client):
    status, book, _ = client.call("POST", "/books", {"title": "T", "author": "A"})
    assert status == 201
    assert book["year"] is None and book["isbn"] is None


@pytest.mark.parametrize(
    "payload, bad_field",
    [
        ({"author": "A"}, "title"),
        ({"title": "T"}, "author"),
        ({"title": "  ", "author": "A"}, "title"),
        ({"title": "T", "author": 5}, "author"),
        ({"title": "T", "author": "A", "year": "1999"}, "year"),
        ({"title": "T", "author": "A", "year": True}, "year"),
        ({"title": "T", "author": "A", "isbn": 123}, "isbn"),
    ],
)
def test_validation_errors(client, payload, bad_field):
    status, body, _ = client.call("POST", "/books", payload)
    assert status == 422
    assert bad_field in body["details"]
    assert client.call("GET", "/books")[1] == []


def test_invalid_json_and_non_object(client):
    assert client.call("POST", "/books", raw=b"{not json")[0] == 400
    assert client.call("POST", "/books", raw=b"[1, 2]")[0] == 400
    assert client.call("POST", "/books")[0] == 400  # empty body


def test_duplicate_isbn_conflict(client):
    client.call("POST", "/books", BOOK)
    status, _, _ = client.call("POST", "/books", {**BOOK, "title": "Other"})
    assert status == 409


def test_list_and_author_filter(client):
    client.call("POST", "/books", BOOK)
    client.call("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    client.call("POST", "/books", {"title": "Persuasion", "author": "Jane Austen"})

    assert len(client.call("GET", "/books")[1]) == 3
    titles = [b["title"] for b in client.call("GET", "/books?author=Jane%20Austen")[1]]
    assert titles == ["Emma", "Persuasion"]
    assert client.call("GET", "/books?author=jane+austen")[1] == client.call(
        "GET", "/books?author=Jane%20Austen"
    )[1]
    assert client.call("GET", "/books?author=Nobody")[1] == []


def test_update(client):
    client.call("POST", "/books", BOOK)
    status, updated, _ = client.call(
        "PUT", "/books/1", {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}
    )
    assert status == 200
    assert updated == {"id": 1, "title": "Dune Messiah", "author": "Frank Herbert",
                       "year": 1969, "isbn": None}
    assert client.call("GET", "/books/1")[1] == updated


def test_update_validation_and_conflict(client):
    client.call("POST", "/books", BOOK)
    client.call("POST", "/books", {"title": "B", "author": "A", "isbn": "X"})
    assert client.call("PUT", "/books/2", {"title": "", "author": "A"})[0] == 422
    assert client.call("PUT", "/books/2", {"title": "B", "author": "A", "isbn": BOOK["isbn"]})[0] == 409
    # A book may keep its own ISBN on update.
    assert client.call("PUT", "/books/2", {"title": "B2", "author": "A", "isbn": "X"})[0] == 200


def test_delete(client):
    client.call("POST", "/books", BOOK)
    status, body, _ = client.call("DELETE", "/books/1")
    assert (status, body) == (204, None)
    assert client.call("GET", "/books/1")[0] == 404
    assert client.call("DELETE", "/books/1")[0] == 404


def test_not_found_and_method_errors(client):
    assert client.call("GET", "/books/99")[0] == 404
    assert client.call("PUT", "/books/99", {"title": "T", "author": "A"})[0] == 404
    assert client.call("GET", "/nope")[0] == 404
    assert client.call("GET", "/books/abc")[0] == 404
    assert client.call("PATCH", "/books/1")[0] == 405
    assert client.call("DELETE", "/books")[0] == 405
    assert client.call("POST", "/health")[0] == 405


def test_persistence_across_store_instances(tmp_path):
    db = str(tmp_path / "books.db")
    store = BookStore(db)
    Client(create_app(store)).call("POST", "/books", BOOK)
    store.close()

    reopened = Client(create_app(BookStore(db)))
    status, body, _ = reopened.call("GET", "/books")
    assert status == 200 and body[0]["title"] == "Dune"


def test_real_http_server_round_trip():
    """End to end over a real socket using the threaded server."""

    class Quiet(WSGIRequestHandler):
        def log_message(self, *args):
            pass

    srv = make_server("127.0.0.1", 0, create_app(BookStore()), ThreadingWSGIServer, Quiet)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{srv.server_port}"
    try:
        req = urlrequest.Request(
            base + "/books", data=json.dumps(BOOK).encode(), method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urlrequest.urlopen(req) as resp:
            assert resp.status == 201
            assert json.load(resp)["id"] == 1
        with urlrequest.urlopen(base + "/health") as resp:
            assert json.load(resp) == {"status": "ok"}
        with pytest.raises(HTTPError) as exc:
            urlrequest.urlopen(base + "/books/42")
        assert exc.value.code == 404
    finally:
        srv.shutdown()
        srv.server_close()
