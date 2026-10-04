import io
import json
import sqlite3
import threading
import urllib.error
import urllib.request
from wsgiref.simple_server import WSGIRequestHandler, make_server

import pytest

from app import MAX_BODY_BYTES, create_app

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
EMMA = {"title": "Emma", "author": "Jane Austen", "year": 1815, "isbn": "9780141439587"}


class Response:
    def __init__(self, status, headers, body):
        self.status = int(status.split(" ", 1)[0])
        self.headers = dict(headers)
        self.body = body

    @property
    def json(self):
        return json.loads(self.body)


class Client:
    """Minimal in-process WSGI test client."""

    def __init__(self, app):
        self.app = app

    def request(self, method, path, json_body=None, raw_body=None, headers=None):
        path, _, query = path.partition("?")
        body = raw_body if raw_body is not None else b""
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "CONTENT_LENGTH": str(len(body)),
            "CONTENT_TYPE": "application/json",
            "wsgi.input": io.BytesIO(body),
            "wsgi.errors": io.StringIO(),
        }
        environ.update(headers or {})
        captured = {}

        def start_response(status, response_headers):
            captured["status"] = status
            captured["headers"] = response_headers

        chunks = self.app(environ, start_response)
        return Response(captured["status"], captured["headers"], b"".join(chunks))

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, json_body=None, **kwargs):
        return self.request("POST", path, json_body, **kwargs)

    def put(self, path, json_body=None, **kwargs):
        return self.request("PUT", path, json_body, **kwargs)

    def delete(self, path):
        return self.request("DELETE", path)


@pytest.fixture
def app(tmp_path):
    application = create_app(str(tmp_path / "books.db"))
    yield application
    application.store.close()


@pytest.fixture
def client(app):
    return Client(app)


def test_health(client):
    res = client.get("/health")
    assert res.status == 200
    assert res.headers["Content-Type"] == "application/json"
    assert res.json == {"status": "ok"}


def test_create_book(client):
    res = client.post("/books", DUNE)
    assert res.status == 201
    assert res.json == {"id": 1, **DUNE}
    assert res.headers["Location"] == "/books/1"


def test_create_book_with_only_required_fields(client):
    res = client.post("/books", {"title": "Dune", "author": "Frank Herbert"})
    assert res.status == 201
    assert res.json == {"id": 1, "title": "Dune", "author": "Frank Herbert", "year": None, "isbn": None}


def test_create_trims_whitespace(client):
    res = client.post("/books", {"title": "  Dune ", "author": " Frank Herbert "})
    assert res.json["title"] == "Dune"
    assert res.json["author"] == "Frank Herbert"


@pytest.mark.parametrize(
    "payload, bad_fields",
    [
        ({}, {"title", "author"}),
        ({"title": "Dune"}, {"author"}),
        ({"author": "Frank Herbert"}, {"title"}),
        ({"title": "", "author": "   "}, {"title", "author"}),
        ({"title": None, "author": 42}, {"title", "author"}),
        ({"title": "Dune", "author": "Frank Herbert", "year": "1965"}, {"year"}),
        ({"title": "Dune", "author": "Frank Herbert", "year": True}, {"year"}),
        ({"title": "Dune", "author": "Frank Herbert", "year": 1965.5}, {"year"}),
        ({"title": "Dune", "author": "Frank Herbert", "year": 10**30}, {"year"}),
        ({"title": "Dune", "author": "Frank Herbert", "isbn": 123}, {"isbn"}),
        ({"title": "Dune", "author": "Frank Herbert", "isbn": ""}, {"isbn"}),
    ],
)
def test_create_validation_errors(client, payload, bad_fields):
    res = client.post("/books", payload)
    assert res.status == 400
    assert res.json["error"] == "Validation failed"
    assert set(res.json["details"]) == bad_fields
    assert client.get("/books").json == []


@pytest.mark.parametrize("raw", [b"", b"{not json", b"\xff\xfe", b"[1, 2]", b'"text"', b"null"])
def test_create_rejects_malformed_bodies(client, raw):
    res = client.post("/books", raw_body=raw)
    assert res.status == 400
    assert "error" in res.json


def test_create_rejects_oversized_body(client):
    res = client.post("/books", headers={"CONTENT_LENGTH": str(MAX_BODY_BYTES + 1)})
    assert res.status == 413


def test_create_rejects_bad_content_length(client):
    assert client.post("/books", headers={"CONTENT_LENGTH": "abc"}).status == 400
    assert client.post("/books", headers={"CONTENT_LENGTH": "-5"}).status == 400


def test_create_duplicate_isbn_conflicts(client):
    assert client.post("/books", DUNE).status == 201
    res = client.post("/books", {**EMMA, "isbn": DUNE["isbn"]})
    assert res.status == 409
    assert len(client.get("/books").json) == 1


def test_multiple_books_without_isbn_allowed(client):
    assert client.post("/books", {"title": "A", "author": "X"}).status == 201
    assert client.post("/books", {"title": "B", "author": "X"}).status == 201


def test_list_books(client):
    assert client.get("/books").json == []
    client.post("/books", DUNE)
    client.post("/books", EMMA)
    res = client.get("/books")
    assert res.status == 200
    assert [b["title"] for b in res.json] == ["Dune", "Emma"]


def test_list_books_filtered_by_author(client):
    client.post("/books", DUNE)
    client.post("/books", EMMA)
    client.post("/books", {"title": "Persuasion", "author": "Jane Austen"})

    res = client.get("/books?author=Jane%20Austen")
    assert res.status == 200
    assert [b["title"] for b in res.json] == ["Emma", "Persuasion"]

    assert [b["title"] for b in client.get("/books?author=jane+austen").json] == ["Emma", "Persuasion"]
    assert client.get("/books?author=Nobody").json == []
    # Partial names do not match, and SQL metacharacters are treated literally.
    assert client.get("/books?author=Jane").json == []
    assert client.get("/books?author=%25").json == []
    assert client.get("/books?author=x'%20OR%20'1'='1").json == []


def test_get_book(client):
    client.post("/books", DUNE)
    res = client.get("/books/1")
    assert res.status == 200
    assert res.json == {"id": 1, **DUNE}


@pytest.mark.parametrize("path", ["/books/999", "/books/abc", "/books/-1", "/books/1.5", "/books/" + "9" * 40])
def test_get_missing_book(client, path):
    res = client.get(path)
    assert res.status == 404
    assert res.json == {"error": "Book not found"}


def test_update_book(client):
    client.post("/books", DUNE)
    updated = {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": "9780593098233"}
    res = client.put("/books/1", updated)
    assert res.status == 200
    assert res.json == {"id": 1, **updated}
    assert client.get("/books/1").json == {"id": 1, **updated}


def test_update_replaces_omitted_optional_fields(client):
    client.post("/books", DUNE)
    res = client.put("/books/1", {"title": "Dune", "author": "Frank Herbert"})
    assert res.status == 200
    assert res.json["year"] is None
    assert res.json["isbn"] is None


def test_update_can_keep_own_isbn(client):
    client.post("/books", DUNE)
    assert client.put("/books/1", {**DUNE, "year": 1966}).status == 200


def test_update_validation_error_leaves_book_unchanged(client):
    client.post("/books", DUNE)
    res = client.put("/books/1", {"title": "", "year": 1969})
    assert res.status == 400
    assert set(res.json["details"]) == {"title", "author"}
    assert client.get("/books/1").json == {"id": 1, **DUNE}


def test_update_missing_book(client):
    assert client.put("/books/999", DUNE).status == 404


def test_update_duplicate_isbn_conflicts(client):
    client.post("/books", DUNE)
    client.post("/books", EMMA)
    res = client.put("/books/2", {**EMMA, "isbn": DUNE["isbn"]})
    assert res.status == 409
    assert client.get("/books/2").json["isbn"] == EMMA["isbn"]


def test_delete_book(client):
    client.post("/books", DUNE)
    res = client.delete("/books/1")
    assert res.status == 204
    assert res.body == b""
    assert client.get("/books/1").status == 404
    assert client.delete("/books/1").status == 404


def test_ids_are_not_reused_after_delete(client):
    client.post("/books", DUNE)
    client.delete("/books/1")
    assert client.post("/books", EMMA).json["id"] == 2


def test_unknown_route(client):
    res = client.get("/nope")
    assert res.status == 404
    assert res.json == {"error": "Not found"}


@pytest.mark.parametrize(
    "method, path, allow",
    [
        ("DELETE", "/books", "GET, POST"),
        ("PUT", "/books", "GET, POST"),
        ("POST", "/books/1", "GET, PUT, DELETE"),
        ("POST", "/health", "GET"),
    ],
)
def test_method_not_allowed(client, method, path, allow):
    res = client.request(method, path)
    assert res.status == 405
    assert res.headers["Allow"] == allow


def test_unexpected_errors_return_json_500(client, app, monkeypatch):
    def boom(author=None):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(app.store, "list", boom)
    res = client.get("/books")
    assert res.status == 500
    assert res.json == {"error": "Internal server error"}


def test_data_persists_across_app_instances(tmp_path):
    db_path = str(tmp_path / "books.db")
    first = create_app(db_path)
    Client(first).post("/books", DUNE)
    first.store.close()

    second = create_app(db_path)
    try:
        assert Client(second).get("/books/1").json == {"id": 1, **DUNE}
    finally:
        second.store.close()


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


def test_full_crud_over_real_http(app):
    """End-to-end check through an actual socket, as a deployed client would see it."""
    server = make_server("127.0.0.1", 0, app, handler_class=QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"

    def call(method, path, payload=None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(base + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                raw = res.read()
                return res.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read())

    try:
        assert call("GET", "/health") == (200, {"status": "ok"})
        assert call("POST", "/books", DUNE) == (201, {"id": 1, **DUNE})
        assert call("GET", "/books?author=Frank%20Herbert") == (200, [{"id": 1, **DUNE}])
        assert call("PUT", "/books/1", {**DUNE, "year": 1966}) == (200, {"id": 1, **DUNE, "year": 1966})
        assert call("POST", "/books", {"title": "No author"})[0] == 400
        assert call("DELETE", "/books/1") == (204, None)
        assert call("GET", "/books/1") == (404, {"error": "Book not found"})
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
