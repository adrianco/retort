import io
import json
import threading
import urllib.error
import urllib.request
from wsgiref.simple_server import WSGIRequestHandler, make_server
from wsgiref.util import setup_testing_defaults

import pytest

from app import BookAPI, ThreadingWSGIServer

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}


class Client:
    """Calls the WSGI app directly, without a network socket."""

    def __init__(self, app):
        self.app = app

    def request(self, method, path, body=None, raw=None):
        path, _, query = path.partition("?")
        data = raw if raw is not None else (b"" if body is None else json.dumps(body).encode())
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "CONTENT_LENGTH": str(len(data)),
            "wsgi.input": io.BytesIO(data),
            "wsgi.errors": io.StringIO(),
        }
        setup_testing_defaults(environ)
        result = {}

        def start_response(status, headers):
            result["status"] = int(status.split()[0])
            result["headers"] = dict(headers)

        payload = b"".join(self.app(environ, start_response))
        return result["status"], (json.loads(payload) if payload else None), result["headers"]

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, body):
        return self.request("POST", path, body)

    def put(self, path, body):
        return self.request("PUT", path, body)

    def delete(self, path):
        return self.request("DELETE", path)


@pytest.fixture
def app(tmp_path):
    return BookAPI(tmp_path / "books.db")


@pytest.fixture
def client(app):
    return Client(app)


def test_health(client):
    status, body, headers = client.get("/health")
    assert status == 200
    assert body == {"status": "ok"}
    assert headers["Content-Type"] == "application/json"


def test_create_book(client):
    status, body, headers = client.post("/books", DUNE)
    assert status == 201
    assert body == {"id": 1, **DUNE}
    assert headers["Location"] == "/books/1"


def test_create_with_only_required_fields(client):
    status, body, _ = client.post("/books", {"title": "Emma", "author": "Jane Austen"})
    assert status == 201
    assert body == {"id": 1, "title": "Emma", "author": "Jane Austen", "year": None, "isbn": None}


@pytest.mark.parametrize(
    "payload, bad_fields",
    [
        ({"author": "Frank Herbert"}, {"title"}),
        ({"title": "Dune"}, {"author"}),
        ({}, {"title", "author"}),
        ({"title": "   ", "author": ""}, {"title", "author"}),
        ({"title": None, "author": 7}, {"title", "author"}),
        ({**DUNE, "year": "1965"}, {"year"}),
        ({**DUNE, "year": True}, {"year"}),
        ({**DUNE, "year": 1965.5}, {"year"}),
        ({**DUNE, "isbn": 9780441172719}, {"isbn"}),
    ],
)
def test_create_validation_errors(client, payload, bad_fields):
    status, body, _ = client.post("/books", payload)
    assert status == 400
    assert body["error"] == "Validation failed"
    assert set(body["details"]) == bad_fields
    assert client.get("/books")[1] == []


@pytest.mark.parametrize("raw", [b"", b"{not json", b"[1, 2]", b'"text"', b"\xff\xfe"])
def test_create_rejects_bad_bodies(client, raw):
    status, body, _ = client.request("POST", "/books", raw=raw)
    assert status == 400
    assert "error" in body


def test_create_rejects_oversized_body(client):
    raw = json.dumps({**DUNE, "title": "x" * (1024 * 1024)}).encode()
    assert client.request("POST", "/books", raw=raw)[0] == 413


def test_create_duplicate_isbn_conflicts(client):
    client.post("/books", DUNE)
    status, body, _ = client.post("/books", {**DUNE, "title": "Dune again"})
    assert status == 409
    assert "isbn" in body["error"]


def test_books_without_isbn_do_not_conflict(client):
    assert client.post("/books", {"title": "A", "author": "X"})[0] == 201
    assert client.post("/books", {"title": "B", "author": "X", "isbn": ""})[0] == 201


def test_get_book(client):
    client.post("/books", DUNE)
    status, body, _ = client.get("/books/1")
    assert status == 200
    assert body == {"id": 1, **DUNE}


@pytest.mark.parametrize("path", ["/books/999", "/books/abc", "/books/1/extra", "/nope", "/"])
def test_not_found(client, path):
    status, body, _ = client.get(path)
    assert status == 404
    assert "error" in body


def test_list_books(client):
    assert client.get("/books") == (200, [], client.get("/books")[2])
    client.post("/books", DUNE)
    client.post("/books", {"title": "Emma", "author": "Jane Austen"})
    status, body, _ = client.get("/books")
    assert status == 200
    assert [b["title"] for b in body] == ["Dune", "Emma"]


def test_list_filtered_by_author(client):
    client.post("/books", DUNE)
    client.post("/books", {"title": "Emma", "author": "Jane Austen"})
    client.post("/books", {"title": "Persuasion", "author": "Jane Austen"})

    status, body, _ = client.get("/books?author=Jane%20Austen")
    assert status == 200
    assert [b["title"] for b in body] == ["Emma", "Persuasion"]

    assert [b["title"] for b in client.get("/books?author=frank+herbert")[1]] == ["Dune"]
    assert client.get("/books?author=Nobody")[1] == []


def test_author_filter_is_not_injectable(client):
    client.post("/books", DUNE)
    assert client.get("/books?author=x'%20OR%20'1'='1")[1] == []


def test_update_book(client):
    client.post("/books", DUNE)
    updated = {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": "9780441172696"}
    status, body, _ = client.put("/books/1", updated)
    assert status == 200
    assert body == {"id": 1, **updated}
    assert client.get("/books/1")[1] == {"id": 1, **updated}


def test_update_can_keep_own_isbn(client):
    client.post("/books", DUNE)
    assert client.put("/books/1", {**DUNE, "year": 1966})[0] == 200


def test_update_validation_and_missing(client):
    client.post("/books", DUNE)
    status, body, _ = client.put("/books/1", {"title": "No author"})
    assert status == 400
    assert set(body["details"]) == {"author"}
    assert client.get("/books/1")[1]["title"] == "Dune"

    assert client.put("/books/999", DUNE)[0] == 404


def test_update_duplicate_isbn_conflicts(client):
    client.post("/books", DUNE)
    client.post("/books", {"title": "Emma", "author": "Jane Austen", "isbn": "111"})
    assert client.put("/books/2", {"title": "Emma", "author": "Jane Austen", "isbn": DUNE["isbn"]})[0] == 409


def test_delete_book(client):
    client.post("/books", DUNE)
    status, body, _ = client.delete("/books/1")
    assert status == 204
    assert body is None
    assert client.get("/books/1")[0] == 404
    assert client.delete("/books/1")[0] == 404


def test_method_not_allowed(client):
    status, _, headers = client.request("DELETE", "/books")
    assert status == 405
    assert headers["Allow"] == "GET, POST"
    assert client.request("POST", "/books/1", {})[0] == 405
    assert client.request("POST", "/health")[0] == 405


def test_data_persists_across_app_instances(tmp_path):
    path = tmp_path / "books.db"
    Client(BookAPI(path)).post("/books", DUNE)
    assert Client(BookAPI(path)).get("/books/1")[1]["title"] == "Dune"


def test_unicode_round_trip(client):
    book = {"title": "Cien años de soledad", "author": "Gabriel García Márquez"}
    client.post("/books", book)
    status, body, _ = client.get("/books?author=Gabriel%20Garc%C3%ADa%20M%C3%A1rquez")
    assert status == 200
    assert body[0]["title"] == book["title"]


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture
def base_url(app):
    server = make_server(
        "127.0.0.1", 0, app, server_class=ThreadingWSGIServer, handler_class=QuietHandler
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join()


def http(method, url, body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = response.read()
            return response.status, json.loads(payload) if payload else None
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_full_lifecycle_over_http(base_url):
    assert http("GET", f"{base_url}/health") == (200, {"status": "ok"})

    status, created = http("POST", f"{base_url}/books", DUNE)
    assert status == 201
    url = f"{base_url}/books/{created['id']}"

    assert http("GET", url) == (200, created)
    assert http("GET", f"{base_url}/books?author=Frank%20Herbert") == (200, [created])
    assert http("PUT", url, {**DUNE, "year": 1966}) == (200, {**created, "year": 1966})
    assert http("POST", f"{base_url}/books", {"title": "x"})[0] == 400
    assert http("DELETE", url) == (204, None)
    assert http("GET", url)[0] == 404
