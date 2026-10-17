"""HTTP-level tests for the book API.

Most tests call the WSGI app directly. The end-to-end test starts a real server
on a free port and talks to it with urllib.
"""

import io
import json
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from wsgiref.simple_server import make_server
from wsgiref.util import setup_testing_defaults

import pytest

from bookapi.app import BookApp
from bookapi.server import ThreadingWSGIServer
from bookapi.store import BookStore

VALID_BOOK = {
    "title": "Dune",
    "author": "Frank Herbert",
    "year": 1965,
    "isbn": "978-0-306-40615-7",
}


@dataclass
class Response:
    status: int
    headers: dict
    body: Any


class Client:
    """Drives the WSGI app without a socket."""

    def __init__(self, app):
        self.app = app

    def request(self, method, path, json_body=None, raw=None, content_type="application/json", query=""):
        if raw is not None:
            body = raw
        elif json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
        else:
            body = b""

        environ = {}
        setup_testing_defaults(environ)
        environ.update(
            {
                "REQUEST_METHOD": method,
                "PATH_INFO": path,
                "QUERY_STRING": query,
                "CONTENT_LENGTH": str(len(body)),
                "wsgi.input": io.BytesIO(body),
            }
        )
        if content_type is not None:
            environ["CONTENT_TYPE"] = content_type

        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = dict(headers)

        data = b"".join(self.app(environ, start_response))
        code = int(captured["status"].split()[0])
        payload = json.loads(data) if data else None
        return Response(code, captured["headers"], payload)

    def create(self, **overrides):
        book = {**VALID_BOOK, **overrides}
        response = self.request("POST", "/books", json_body=book)
        assert response.status == 201, response.body
        return response.body


@pytest.fixture
def store():
    book_store = BookStore(":memory:")
    yield book_store
    book_store.close()


@pytest.fixture
def client(store):
    return Client(BookApp(store))


# --- POST /books -----------------------------------------------------------

def test_create_book_returns_201_with_location_and_body(client):
    response = client.request("POST", "/books", json_body=VALID_BOOK)

    assert response.status == 201
    assert response.headers["Content-Type"] == "application/json; charset=utf-8"
    assert response.body == {"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780306406157"}
    assert response.headers["Location"] == "/books/1"


def test_create_trims_whitespace_and_ignores_client_supplied_id(client):
    response = client.request("POST", "/books", json_body={"id": 99, "title": "  Emma  ", "author": " Jane Austen "})

    assert response.status == 201
    assert response.body["id"] == 1
    assert response.body["title"] == "Emma"
    assert response.body["author"] == "Jane Austen"


def test_create_allows_year_and_isbn_to_be_omitted(client):
    response = client.request("POST", "/books", json_body={"title": "Untitled", "author": "Anon"})

    assert response.status == 201
    assert response.body["year"] is None
    assert response.body["isbn"] is None


@pytest.mark.parametrize("missing", ["title", "author"])
def test_create_requires_title_and_author(client, missing):
    body = {k: v for k, v in VALID_BOOK.items() if k != missing}

    response = client.request("POST", "/books", json_body=body)

    assert response.status == 400
    assert response.body["error"] == "validation failed"
    assert response.body["details"] == {missing: "is required"}


@pytest.mark.parametrize("field", ["title", "author"])
def test_create_rejects_blank_or_non_string_text(client, field):
    blank = client.request("POST", "/books", json_body={**VALID_BOOK, field: "   "})
    number = client.request("POST", "/books", json_body={**VALID_BOOK, field: 42})

    assert blank.status == 400
    assert blank.body["details"] == {field: "must not be blank"}
    assert number.status == 400
    assert number.body["details"] == {field: "must be a string"}


def test_create_rejects_overlong_title(client):
    response = client.request("POST", "/books", json_body={**VALID_BOOK, "title": "x" * 501})

    assert response.status == 400
    assert "title" in response.body["details"]


@pytest.mark.parametrize("year", ["1965", 1.5, True, 0, 10000])
def test_create_rejects_invalid_year(client, year):
    response = client.request("POST", "/books", json_body={**VALID_BOOK, "year": year})

    assert response.status == 400
    assert "year" in response.body["details"]


@pytest.mark.parametrize("isbn", ["1234567890", "9780306406158", "not-an-isbn", 9780306406157])
def test_create_rejects_invalid_isbn(client, isbn):
    response = client.request("POST", "/books", json_body={**VALID_BOOK, "isbn": isbn})

    assert response.status == 400
    assert "isbn" in response.body["details"]


def test_create_accepts_isbn10_with_x_check_digit(client):
    response = client.request("POST", "/books", json_body={**VALID_BOOK, "isbn": "0-8044-2957-X"})

    assert response.status == 201
    assert response.body["isbn"] == "080442957X"


def test_create_rejects_invalid_json(client):
    response = client.request("POST", "/books", raw=b"{not json")

    assert response.status == 400
    assert response.body == {"error": "request body is not valid JSON"}


def test_create_rejects_non_object_body(client):
    response = client.request("POST", "/books", json_body=["Dune", "Herbert"])

    assert response.status == 400
    assert response.body["details"] == {"body": "must be a JSON object"}


def test_create_requires_json_content_type(client):
    response = client.request("POST", "/books", raw=b"title=Dune", content_type="application/x-www-form-urlencoded")

    assert response.status == 415


def test_create_accepts_content_type_with_parameters(client):
    response = client.request(
        "POST", "/books", json_body=VALID_BOOK, content_type="application/json; charset=utf-8"
    )

    assert response.status == 201


def test_create_rejects_oversized_body(client):
    response = client.request("POST", "/books", raw=b" " * 1_000_001)

    assert response.status == 413


# --- GET /books ------------------------------------------------------------

def test_list_returns_empty_array_when_no_books(client):
    response = client.request("GET", "/books")

    assert response.status == 200
    assert response.body == []


def test_list_returns_all_books_in_id_order(client):
    client.create(title="A")
    client.create(title="B")

    response = client.request("GET", "/books")

    assert response.status == 200
    assert [book["title"] for book in response.body] == ["A", "B"]


def test_list_filters_by_author_case_insensitively(client):
    client.create(title="Dune", author="Frank Herbert")
    client.create(title="Emma", author="Jane Austen")
    client.create(title="Children of Dune", author="frank herbert")

    response = client.request("GET", "/books", query="author=FRANK%20HERBERT")

    assert response.status == 200
    assert [book["title"] for book in response.body] == ["Dune", "Children of Dune"]


def test_list_author_filter_requires_exact_match(client):
    client.create(author="Frank Herbert")

    response = client.request("GET", "/books", query="author=Frank")

    assert response.status == 200
    assert response.body == []


def test_list_rejects_empty_author_filter(client):
    response = client.request("GET", "/books", query="author=%20")

    assert response.status == 400


# --- GET /books/{id} -------------------------------------------------------

def test_get_book_by_id(client):
    created = client.create()

    response = client.request("GET", f"/books/{created['id']}")

    assert response.status == 200
    assert response.body == created


def test_get_missing_book_returns_404(client):
    response = client.request("GET", "/books/42")

    assert response.status == 404
    assert response.body == {"error": "book not found"}


@pytest.mark.parametrize("bad_id", ["abc", "1.5", "-1"])
def test_get_malformed_id_returns_400(client, bad_id):
    response = client.request("GET", f"/books/{bad_id}")

    assert response.status == 400


def test_get_id_beyond_sqlite_range_returns_404_not_500(client):
    response = client.request("GET", f"/books/{2**70}")

    assert response.status == 404


# --- PUT /books/{id} -------------------------------------------------------

def test_put_replaces_book(client):
    created = client.create()
    replacement = {"title": "Dune Messiah", "author": "Frank Herbert"}

    response = client.request("PUT", f"/books/{created['id']}", json_body=replacement)

    assert response.status == 200
    assert response.body == {"id": created["id"], "title": "Dune Messiah", "author": "Frank Herbert", "year": None, "isbn": None}
    assert client.request("GET", f"/books/{created['id']}").body == response.body


def test_put_validates_body(client):
    created = client.create()

    response = client.request("PUT", f"/books/{created['id']}", json_body={"author": "Someone"})

    assert response.status == 400
    assert response.body["details"] == {"title": "is required"}


def test_put_missing_book_returns_404(client):
    response = client.request("PUT", "/books/7", json_body=VALID_BOOK)

    assert response.status == 404


# --- DELETE /books/{id} ----------------------------------------------------

def test_delete_book_then_it_is_gone(client):
    created = client.create()

    response = client.request("DELETE", f"/books/{created['id']}")

    assert response.status == 204
    assert response.body is None
    assert client.request("GET", f"/books/{created['id']}").status == 404


def test_delete_missing_book_returns_404(client):
    response = client.request("DELETE", "/books/7")

    assert response.status == 404


# --- Health, routing and misc ----------------------------------------------

def test_health_check_reports_ok(client):
    response = client.request("GET", "/health")

    assert response.status == 200
    assert response.body == {"status": "ok"}


def test_health_check_reports_unavailable_when_database_is_closed(store, client):
    store.close()

    response = client.request("GET", "/health")

    assert response.status == 503
    assert response.body == {"status": "unavailable"}


def test_unknown_route_returns_404(client):
    assert client.request("GET", "/authors").status == 404


def test_wrong_method_returns_405_with_allow_header(client):
    response = client.request("PATCH", "/books/1", json_body=VALID_BOOK)

    assert response.status == 405
    assert response.headers["Allow"] == "DELETE, GET, PUT"


def test_trailing_slash_is_accepted(client):
    client.create()

    assert client.request("GET", "/books/").status == 200


def test_data_persists_across_store_instances(tmp_path):
    db_path = str(tmp_path / "books.db")
    first = BookStore(db_path)
    Client(BookApp(first)).create(title="Persisted")
    first.close()

    second = BookStore(db_path)
    try:
        response = Client(BookApp(second)).request("GET", "/books")
    finally:
        second.close()

    assert [book["title"] for book in response.body] == ["Persisted"]


# --- End to end over a real socket -----------------------------------------

def test_full_crud_over_real_http(store):
    server = make_server("127.0.0.1", 0, BookApp(store), server_class=ThreadingWSGIServer)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"

    def call(method, path, body=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        request = urllib.request.Request(base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request) as resp:
                raw = resp.read()
                return resp.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read())

    try:
        assert call("GET", "/health") == (200, {"status": "ok"})

        status, created = call("POST", "/books", VALID_BOOK)
        assert status == 201
        book_path = f"/books/{created['id']}"

        assert call("GET", book_path) == (200, created)
        assert call("GET", "/books?author=Frank%20Herbert") == (200, [created])
        assert call("GET", "/books?author=Nobody") == (200, [])

        status, updated = call("PUT", book_path, {"title": "Dune Messiah", "author": "Frank Herbert"})
        assert status == 200
        assert updated["title"] == "Dune Messiah"

        assert call("DELETE", book_path) == (204, None)
        assert call("GET", book_path) == (404, {"error": "book not found"})
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
