"""HTTP-level tests of the WSGI app, run in-process."""

import io
import json
from wsgiref.util import setup_testing_defaults

import pytest

from books_api import BooksApp

# -- health ---------------------------------------------------------------------


def test_health(client):
    response = client.get("/health")
    assert response.status == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.json == {"status": "ok", "database": "ok"}


def test_health_reports_unavailable_database(client, repository):
    repository.close()
    response = client.get("/health")
    assert response.status == 503
    assert response.json == {"status": "error", "database": "unavailable"}


# -- create -----------------------------------------------------------------------


def test_create_book(client):
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}
    response = client.post("/books", payload)

    assert response.status == 201
    body = response.json
    assert isinstance(body["id"], int)
    assert body == {"id": body["id"], **payload}
    assert response.headers["Location"] == f"/books/{body['id']}"


def test_create_with_only_required_fields(client):
    response = client.post("/books", {"title": "Dune", "author": "Frank Herbert"})
    assert response.status == 201
    assert response.json["year"] is None
    assert response.json["isbn"] is None


def test_created_book_is_retrievable(client, make_book):
    book = make_book()
    response = client.get(f"/books/{book['id']}")
    assert response.status == 200
    assert response.json == book


def test_location_includes_script_name_when_mounted_under_a_prefix(client):
    response = client.post(
        "/books", {"title": "Dune", "author": "Frank Herbert"}, environ={"SCRIPT_NAME": "/api"}
    )
    assert response.headers["Location"] == f"/api/books/{response.json['id']}"


@pytest.mark.parametrize(
    ("payload", "expected_details"),
    [
        ({"author": "Frank Herbert"}, {"title": "title is required"}),
        ({"title": "Dune"}, {"author": "author is required"}),
        ({}, {"title": "title is required", "author": "author is required"}),
        ({"title": "  ", "author": "Frank Herbert"}, {"title": "title must not be blank"}),
        ({"title": None, "author": "Frank Herbert"}, {"title": "title is required"}),
        ({"title": 42, "author": "Frank Herbert"}, {"title": "title must be a string"}),
        ({"title": "Dune", "author": "Frank Herbert", "year": "1965"}, {"year": "year must be an integer"}),
    ],
)
def test_create_rejects_invalid_payload(client, payload, expected_details):
    response = client.post("/books", payload)
    assert response.status == 400
    assert response.json == {"error": "Validation failed", "details": expected_details}
    assert client.get("/books").json == []


def test_create_rejects_invalid_isbn(client):
    response = client.post("/books", {"title": "Dune", "author": "Frank Herbert", "isbn": "not-an-isbn"})
    assert response.status == 400
    assert "isbn" in response.json["details"]


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (b"", "Request body must be a JSON object"),
        (b"   ", "Request body must be a JSON object"),
        (b"{not json", "Malformed JSON body"),
        (b"\xff\xfe\xfa", "Malformed JSON body"),
        (b"[" * 100_000, "Malformed JSON body"),
    ],
)
def test_create_rejects_unparseable_body(client, body, message):
    response = client.post("/books", data=body)
    assert response.status == 400
    assert response.json["error"].startswith(message)


@pytest.mark.parametrize("payload", [[], ["Dune"], "Dune", 1, None])
def test_create_rejects_non_object_json(client, payload):
    response = client.post("/books", data=json.dumps(payload).encode())
    assert response.status == 400
    assert response.json["details"] == {"body": "must be a JSON object"}


def test_create_rejects_oversized_body(repository, make_client):
    client = make_client(BooksApp(repository, max_body_bytes=100))
    response = client.post("/books", {"title": "x" * 200, "author": "A"})
    assert response.status == 413
    assert "error" in response.json


@pytest.mark.parametrize("content_length", ["abc", "-5"])
def test_invalid_content_length_is_a_bad_request(app, content_length):
    # wsgiref's validator itself rejects such an environ, so call the app directly.
    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/books",
        "SCRIPT_NAME": "",
        "CONTENT_LENGTH": content_length,
        "wsgi.input": io.BytesIO(b"{}"),
    }
    setup_testing_defaults(environ)
    captured = {}
    body = b"".join(app(environ, lambda status, headers: captured.setdefault("status", status)))
    assert captured["status"] == "400 Bad Request"
    assert json.loads(body) == {"error": "Invalid Content-Length header"}


def test_unicode_round_trip(client):
    payload = {"title": "Cien años de soledad", "author": "Gabriel García Márquez", "year": 1967}
    created = client.post("/books", payload).json
    assert client.get(f"/books/{created['id']}").json == {**payload, "id": created["id"], "isbn": None}


# -- list -------------------------------------------------------------------------


def test_list_empty(client):
    response = client.get("/books")
    assert response.status == 200
    assert response.json == []


def test_list_returns_all_books_in_creation_order(client, make_book):
    books = [
        make_book(title="Dune"),
        make_book(title="The Left Hand of Darkness", author="Ursula K. Le Guin", year=1969, isbn=None),
        make_book(title="Children of Dune", year=1976, isbn=None),
    ]
    response = client.get("/books")
    assert response.status == 200
    assert response.json == books


def test_list_filters_by_author(client, make_book):
    dune = make_book(title="Dune")
    left_hand = make_book(title="The Left Hand of Darkness", author="Ursula K. Le Guin", isbn=None)
    messiah = make_book(title="Dune Messiah", isbn=None)

    assert client.get("/books", query="author=Frank+Herbert").json == [dune, messiah]
    assert client.get("/books", query="author=le%20guin").json == [left_hand]
    assert client.get("/books", query="author=HERBERT").json == [dune, messiah]
    assert client.get("/books", query="author=Tolkien").json == []
    # An empty filter is no filter.
    assert client.get("/books", query="author=").json == [dune, left_hand, messiah]


# -- get --------------------------------------------------------------------------


def test_get_missing_book_returns_404(client):
    response = client.get("/books/999")
    assert response.status == 404
    assert response.json == {"error": "Book 999 not found"}


@pytest.mark.parametrize("path", ["/books/abc", "/books/-1", "/books/1.5", "/books/" + "9" * 40, "/nope", "/"])
def test_unknown_paths_return_json_404(client, path):
    response = client.get(path)
    assert response.status == 404
    assert "error" in response.json


def test_trailing_slash_is_accepted(client, make_book):
    book = make_book()
    assert client.get("/books/").json == [book]
    assert client.get(f"/books/{book['id']}/").json == book


# -- update -----------------------------------------------------------------------


def test_update_book(client, make_book):
    book = make_book()
    changes = {"title": "Dune (40th Anniversary)", "author": "Frank Herbert", "year": 2005, "isbn": "0441013597"}

    response = client.put(f"/books/{book['id']}", changes)

    assert response.status == 200
    assert response.json == {"id": book["id"], **changes}
    assert client.get(f"/books/{book['id']}").json == {"id": book["id"], **changes}


def test_update_replaces_the_whole_book(client, make_book):
    book = make_book()
    response = client.put(f"/books/{book['id']}", {"title": "Dune", "author": "Frank Herbert"})
    assert response.status == 200
    assert response.json == {"id": book["id"], "title": "Dune", "author": "Frank Herbert", "year": None, "isbn": None}


def test_update_ignores_id_in_body(client, make_book):
    book = make_book()
    response = client.put(f"/books/{book['id']}", {**book, "id": 12345, "title": "Renamed"})
    assert response.status == 200
    assert response.json["id"] == book["id"]
    assert client.get("/books/12345").status == 404


def test_update_missing_book_returns_404(client):
    response = client.put("/books/999", {"title": "Dune", "author": "Frank Herbert"})
    assert response.status == 404
    assert response.json == {"error": "Book 999 not found"}


def test_update_with_invalid_payload_returns_400_and_changes_nothing(client, make_book):
    book = make_book()
    response = client.put(f"/books/{book['id']}", {"title": "", "year": 1966})
    assert response.status == 400
    assert response.json["details"] == {"title": "title must not be blank", "author": "author is required"}
    assert client.get(f"/books/{book['id']}").json == book


# -- delete -----------------------------------------------------------------------


def test_delete_book(client, make_book):
    book = make_book()
    other = make_book(title="Children of Dune")

    response = client.delete(f"/books/{book['id']}")

    assert response.status == 204
    assert response.body == b""
    assert "Content-Type" not in response.headers
    assert "Content-Length" not in response.headers
    assert client.get(f"/books/{book['id']}").status == 404
    assert client.get("/books").json == [other]


def test_delete_missing_book_returns_404(client):
    response = client.delete("/books/999")
    assert response.status == 404
    assert response.json == {"error": "Book 999 not found"}


def test_deleted_ids_are_not_reused(client, make_book):
    book = make_book()
    client.delete(f"/books/{book['id']}")
    assert make_book()["id"] != book["id"]


# -- protocol details -------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path", "allow"),
    [
        ("DELETE", "/books", "GET, HEAD, POST"),
        ("PUT", "/books", "GET, HEAD, POST"),
        ("PATCH", "/books/1", "DELETE, GET, HEAD, PUT"),
        ("POST", "/books/1", "DELETE, GET, HEAD, PUT"),
        ("POST", "/health", "GET, HEAD"),
    ],
)
def test_unsupported_method_returns_405_with_allow_header(client, method, path, allow):
    response = client.request(method, path)
    assert response.status == 405
    assert response.headers["Allow"] == allow
    assert "error" in response.json


def test_head_returns_headers_without_body(client, make_book):
    make_book()
    get = client.get("/books")
    head = client.request("HEAD", "/books")
    assert head.status == 200
    assert head.body == b""
    assert head.headers["Content-Length"] == get.headers["Content-Length"]


def test_unexpected_errors_return_json_500(client, repository, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(repository, "list_books", boom)
    response = client.get("/books")
    assert response.status == 500
    assert response.json == {"error": "Internal server error"}
