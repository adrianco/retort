"""Integration tests: a real server on an ephemeral port, real HTTP requests."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from app import BookStore, ValidationError, create_server, validate_book

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}


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
            with urllib.request.urlopen(req, timeout=5) as resp:
                return self._unpack(resp)
        except urllib.error.HTTPError as err:
            with err:
                return self._unpack(err)

    @staticmethod
    def _unpack(resp):
        text = resp.read()
        return resp.status, (json.loads(text) if text else None), resp.headers

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, body):
        return self.request("POST", path, body)

    def put(self, path, body):
        return self.request("PUT", path, body)

    def delete(self, path):
        return self.request("DELETE", path)


def start(db_path):
    server = create_server(port=0, db_path=str(db_path), quiet=True)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    )
    thread.start()
    return server, thread


def stop(server, thread):
    server.shutdown()
    thread.join()
    server.server_close()
    server.store.close()


@pytest.fixture
def client(tmp_path):
    server, thread = start(tmp_path / "books.db")
    yield Client(f"http://127.0.0.1:{server.server_address[1]}")
    stop(server, thread)


# -- health -----------------------------------------------------------


def test_health(client):
    status, body, headers = client.get("/health")
    assert status == 200
    assert body == {"status": "ok"}
    assert headers["Content-Type"] == "application/json"


# -- create -----------------------------------------------------------


def test_create_book(client):
    status, body, headers = client.post("/books", DUNE)
    assert status == 201
    assert body == {"id": body["id"], **DUNE}
    assert isinstance(body["id"], int)
    assert headers["Location"] == f"/books/{body['id']}"


def test_create_book_with_only_required_fields(client):
    status, body, _ = client.post("/books", {"title": "Emma", "author": "Jane Austen"})
    assert status == 201
    assert body["year"] is None
    assert body["isbn"] is None


@pytest.mark.parametrize(
    "payload, bad_fields",
    [
        ({"author": "Frank Herbert"}, {"title"}),
        ({"title": "Dune"}, {"author"}),
        ({}, {"title", "author"}),
        ({"title": "", "author": "   "}, {"title", "author"}),
        ({"title": None, "author": 7}, {"title", "author"}),
        ({**DUNE, "year": "1965"}, {"year"}),
        ({**DUNE, "year": True}, {"year"}),
        ({**DUNE, "year": 1965.5}, {"year"}),
        ({**DUNE, "isbn": 9780441172719}, {"isbn"}),
    ],
)
def test_create_rejects_invalid_fields(client, payload, bad_fields):
    status, body, _ = client.post("/books", payload)
    assert status == 400
    assert set(body["details"]) == bad_fields
    assert client.get("/books")[1] == []


def test_create_rejects_malformed_json(client):
    status, body, _ = client.request("POST", "/books", raw=b"{not json")
    assert status == 400
    assert "error" in body


def test_create_rejects_empty_body(client):
    status, _, _ = client.request("POST", "/books", raw=b"")
    assert status == 400


def test_create_rejects_non_object_json(client):
    status, body, _ = client.post("/books", ["Dune"])
    assert status == 400
    assert "body" in body["details"]


# -- list -------------------------------------------------------------


def test_list_books_empty(client):
    assert client.get("/books")[:2] == (200, [])


def test_list_books(client):
    client.post("/books", DUNE)
    client.post("/books", {"title": "Emma", "author": "Jane Austen"})
    status, body, _ = client.get("/books")
    assert status == 200
    assert [b["title"] for b in body] == ["Dune", "Emma"]


def test_list_books_filtered_by_author(client):
    client.post("/books", DUNE)
    client.post("/books", {"title": "Children of Dune", "author": "Frank Herbert"})
    client.post("/books", {"title": "Emma", "author": "Jane Austen"})

    status, body, _ = client.get("/books?author=Frank%20Herbert")
    assert status == 200
    assert [b["title"] for b in body] == ["Dune", "Children of Dune"]

    assert len(client.get("/books?author=jane+austen")[1]) == 1
    assert client.get("/books?author=Nobody")[:2] == (200, [])
    # A partial name is not a match.
    assert client.get("/books?author=Frank")[1] == []


# -- get --------------------------------------------------------------


def test_get_book(client):
    created = client.post("/books", DUNE)[1]
    status, body, _ = client.get(f"/books/{created['id']}")
    assert status == 200
    assert body == created


@pytest.mark.parametrize("book_id", ["999", "abc", "-1", "1.5", "9" * 40])
def test_get_unknown_book(client, book_id):
    status, body, _ = client.get(f"/books/{book_id}")
    assert status == 404
    assert "error" in body


# -- update -----------------------------------------------------------


def test_update_book(client):
    book_id = client.post("/books", DUNE)[1]["id"]
    changed = {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}
    status, body, _ = client.put(f"/books/{book_id}", changed)
    assert status == 200
    # PUT replaces the whole book, so the omitted isbn is cleared.
    assert body == {"id": book_id, **changed, "isbn": None}
    assert client.get(f"/books/{book_id}")[1] == body


def test_update_ignores_id_in_body(client):
    book_id = client.post("/books", DUNE)[1]["id"]
    status, body, _ = client.put(f"/books/{book_id}", {**DUNE, "id": book_id + 50})
    assert status == 200
    assert body["id"] == book_id


def test_update_rejects_invalid_book(client):
    created = client.post("/books", DUNE)[1]
    status, body, _ = client.put(f"/books/{created['id']}", {"title": "No Author"})
    assert status == 400
    assert set(body["details"]) == {"author"}
    assert client.get(f"/books/{created['id']}")[1] == created


def test_update_unknown_book(client):
    assert client.put("/books/999", DUNE)[0] == 404


# -- delete -----------------------------------------------------------


def test_delete_book(client):
    book_id = client.post("/books", DUNE)[1]["id"]
    status, body, _ = client.delete(f"/books/{book_id}")
    assert status == 204
    assert body is None
    assert client.get(f"/books/{book_id}")[0] == 404
    assert client.delete(f"/books/{book_id}")[0] == 404


def test_ids_are_not_reused_after_delete(client):
    first = client.post("/books", DUNE)[1]["id"]
    client.delete(f"/books/{first}")
    assert client.post("/books", DUNE)[1]["id"] != first


# -- routing ----------------------------------------------------------


def test_unknown_route(client):
    status, body, _ = client.get("/nope")
    assert status == 404
    assert "error" in body


@pytest.mark.parametrize(
    "method, path, allow",
    [
        ("DELETE", "/books", "GET, POST"),
        ("POST", "/books/1", "GET, PUT, DELETE"),
        ("POST", "/health", "GET"),
    ],
)
def test_method_not_allowed(client, method, path, allow):
    status, body, headers = client.request(method, path, body={})
    assert status == 405
    assert headers["Allow"] == allow
    assert "error" in body


# -- storage ----------------------------------------------------------


def test_books_persist_across_restarts(tmp_path):
    db_path = tmp_path / "books.db"

    server, thread = start(db_path)
    created = Client(f"http://127.0.0.1:{server.server_address[1]}").post("/books", DUNE)[1]
    stop(server, thread)

    server, thread = start(db_path)
    try:
        listed = Client(f"http://127.0.0.1:{server.server_address[1]}").get("/books")[1]
    finally:
        stop(server, thread)
    assert listed == [created]


def test_sql_injection_is_stored_as_plain_text(client):
    evil = "x'); DROP TABLE books; --"
    client.post("/books", {"title": evil, "author": evil})
    status, body, _ = client.get("/books")
    assert status == 200
    assert body[0]["title"] == evil


def test_store_in_memory():
    store = BookStore(":memory:")
    book = store.create(validate_book(DUNE))
    assert store.get(book["id"]) == book
    assert store.delete(book["id"]) is True
    assert store.delete(book["id"]) is False
    store.close()


def test_validate_book_strips_whitespace():
    book = validate_book({"title": "  Dune ", "author": " Frank Herbert ", "isbn": " 1 "})
    assert book == {"title": "Dune", "author": "Frank Herbert", "year": None, "isbn": "1"}


def test_validate_book_reports_every_problem():
    with pytest.raises(ValidationError) as exc:
        validate_book({"year": "x", "isbn": 1})
    assert set(exc.value.details) == {"title", "author", "year", "isbn"}
