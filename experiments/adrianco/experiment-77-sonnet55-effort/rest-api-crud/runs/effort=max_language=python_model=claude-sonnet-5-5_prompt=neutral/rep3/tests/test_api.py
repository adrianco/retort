"""Tests of the HTTP API, driven in-process through the WSGI interface.

They are grouped by endpoint, in the order the requirements list them.
"""

from __future__ import annotations

import json
import os
import socket
from typing import Any

import pytest

from bookapi import BookApp
from bookapi.web import MAX_BODY_BYTES

JSON_TYPE = "application/json; charset=utf-8"

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"}
EMMA = {"title": "Emma", "author": "Jane Austen", "year": 1815, "isbn": "978-0-14-143958-7"}


def create_book(client: Any, **book: Any) -> dict[str, Any]:
    reply = client.post("/books", payload=book or DUNE)
    assert reply.status == 201, reply.body
    return reply.json()


# --- GET /health ------------------------------------------------------------------


def test_health_check_reports_ok(client):
    reply = client.get("/health")
    assert reply.status == 200
    assert reply.headers["content-type"] == JSON_TYPE
    assert reply.json() == {"status": "ok"}


def test_health_check_reports_503_when_the_database_is_unavailable(client, app: BookApp):
    app.repository.close()
    reply = client.get("/health")
    assert reply.status == 503
    assert reply.json() == {"status": "unavailable", "error": "Database unavailable"}


@pytest.mark.skipif(os.name != "posix", reason="overwrites a database file that is still open")
def test_health_check_notices_a_corrupted_database_file(file_client, tmp_path):
    create_book(file_client)
    assert file_client.get("/health").status == 200

    (tmp_path / "books.db").write_bytes(b"this is not an SQLite database " * 300)

    assert file_client.get("/health").status == 503
    assert file_client.get("/books").status == 500  # the health check agrees with what clients see


# --- POST /books ------------------------------------------------------------------


def test_create_book_returns_201_with_location_and_the_stored_book(client):
    reply = client.post("/books", payload=DUNE)

    assert reply.status == 201
    assert reply.headers["content-type"] == JSON_TYPE
    assert reply.headers["location"] == "/books/1"
    assert reply.json() == {"id": 1, **DUNE}
    assert client.get("/books/1").json() == reply.json()


def test_created_books_get_distinct_ids(client):
    assert [create_book(client, **DUNE)["id"], create_book(client, **EMMA)["id"]] == [1, 2]


def test_only_title_and_author_are_needed_to_create_a_book(client):
    reply = client.post("/books", payload={"title": "Untitled Notes", "author": "Anon"})
    assert reply.status == 201
    assert reply.json() == {"id": 1, "title": "Untitled Notes", "author": "Anon", "year": None, "isbn": None}


def test_text_fields_are_trimmed_and_unicode_is_preserved(client):
    reply = client.post("/books", payload={"title": "  Cien años de soledad ", "author": "Gabriel García Márquez"})
    assert reply.json()["title"] == "Cien años de soledad"
    assert reply.json()["author"] == "Gabriel García Márquez"
    assert b"Garc\xc3\xada" in reply.body  # sent as UTF-8, not \u-escaped


def test_client_cannot_choose_the_id(client):
    reply = client.post("/books", payload={**DUNE, "id": 999})
    assert reply.json()["id"] == 1


def test_location_header_honours_the_mount_point(client):
    reply = client.post("/books", payload=DUNE, environ={"SCRIPT_NAME": "/api"})
    assert reply.headers["location"] == "/api/books/1"


@pytest.mark.parametrize(
    "payload, invalid_field",
    [
        pytest.param({"author": "Frank Herbert"}, "title", id="missing-title"),
        pytest.param({"title": "Dune"}, "author", id="missing-author"),
        pytest.param({"title": "", "author": "Frank Herbert"}, "title", id="empty-title"),
        pytest.param({"title": "Dune", "author": "   "}, "author", id="blank-author"),
        pytest.param({"title": None, "author": "Frank Herbert"}, "title", id="null-title"),
        pytest.param({"title": 1965, "author": "Frank Herbert"}, "title", id="numeric-title"),
        pytest.param({**DUNE, "year": "1965"}, "year", id="year-as-string"),
        pytest.param({**DUNE, "year": 19.65}, "year", id="fractional-year"),
        pytest.param({**DUNE, "year": 10000}, "year", id="year-out-of-range"),
        pytest.param({**DUNE, "isbn": 9780441172719}, "isbn", id="isbn-as-number"),
    ],
)
def test_invalid_book_is_rejected_with_400_naming_the_field(client, payload, invalid_field):
    reply = client.post("/books", payload=payload)

    assert reply.status == 400
    assert reply.headers["content-type"] == JSON_TYPE
    body = reply.json()
    assert body["error"] == "Validation failed"
    assert list(body["details"]) == [invalid_field]
    assert client.get("/books").json() == []  # nothing was stored


def test_all_validation_errors_are_reported_together(client):
    reply = client.post("/books", payload={"title": "", "year": "soon"})
    assert reply.status == 400
    assert reply.json()["details"] == {
        "title": "must not be blank",
        "author": "is required",
        "year": "must be an integer",
    }


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(b"", id="empty-body"),
        pytest.param(b"{not json", id="syntax-error"),
        pytest.param(b'{"title": "Dune", "author": ', id="truncated"),
        pytest.param(b"\xff\xfe\x00\x01", id="not-utf8"),
        pytest.param(b'{"title": "Dune", "author": "Frank Herbert", "year": NaN}', id="nan"),
    ],
)
def test_malformed_json_is_rejected_with_400(client, raw):
    reply = client.post("/books", raw=raw)
    assert reply.status == 400
    assert reply.json() == {"error": "Request body must be valid JSON"}


def test_deeply_nested_json_is_a_400_never_a_crash(client):
    # Python <= 3.11 raises RecursionError for this; newer versions parse it and then
    # find it is not an object. Either way the client must get a clean 400, not a 500.
    reply = client.post("/books", raw=b"[" * 10_000 + b"]" * 10_000)
    assert reply.status == 400
    assert reply.headers["content-type"] == JSON_TYPE


@pytest.mark.parametrize("raw", [b"[]", b'"Dune"', b"42", b"null", b"true"])
def test_json_that_is_not_an_object_is_rejected_with_400(client, raw):
    reply = client.post("/books", raw=raw)
    assert reply.status == 400
    assert reply.json() == {"error": "Request body must be a JSON object"}


def test_lone_surrogate_in_json_is_a_400_not_a_crash(client):
    reply = client.post("/books", raw=b'{"title": "bad \\ud800", "author": "Someone"}')
    assert reply.status == 400
    assert reply.json()["details"] == {"title": "must be valid Unicode text"}


def test_oversized_body_is_rejected_with_413(client):
    reply = client.post("/books", raw=b" " * (MAX_BODY_BYTES + 1))
    assert reply.status == 413
    assert "error" in reply.json()


@pytest.mark.parametrize("length", ["abc", "-5", "1e3", " 7"])
def test_invalid_content_length_is_rejected_with_400(client, length):
    reply = client.post("/books", raw=b"{}", environ={"CONTENT_LENGTH": length}, validate=False)
    assert reply.status == 400
    assert reply.json() == {"error": "Invalid Content-Length header"}


@pytest.mark.parametrize(
    "length",
    ["9" * 4301, "9" * 400, str(MAX_BODY_BYTES + 1), "0" * 5000 + str(MAX_BODY_BYTES + 1)],
    ids=["4301-digits", "400-digits", "one-byte-over", "zero-padded-over"],
)
def test_absurd_content_length_is_413_not_a_crash(client, length):
    # int() refuses digit strings longer than 4300 characters; that must not become a 500.
    reply = client.post("/books", raw=b"{}", environ={"CONTENT_LENGTH": length}, validate=False)
    assert reply.status == 413


def test_zero_padded_content_length_is_understood(client):
    body = json.dumps(DUNE).encode()
    padded = "0" * 5000 + str(len(body))
    assert client.post("/books", raw=body, environ={"CONTENT_LENGTH": padded}, validate=False).status == 201


def test_chunked_uploads_are_refused_with_411(client):
    # The bundled server does not decode chunked bodies, so silently reading "nothing"
    # and complaining about invalid JSON would be misleading.
    reply = client.post(
        "/books",
        raw=json.dumps(DUNE).encode(),
        environ={"CONTENT_LENGTH": None, "HTTP_TRANSFER_ENCODING": "chunked"},
    )
    assert reply.status == 411
    assert "Content-Length" in reply.json()["error"]


def test_an_upload_that_stalls_is_a_408(client):
    class NeverDelivers:
        def read(self, size: int) -> bytes:
            raise socket.timeout("timed out")

    reply = client.post(
        "/books",
        raw=b"x",
        environ={"CONTENT_LENGTH": "100", "wsgi.input": NeverDelivers()},
        validate=False,
    )
    assert reply.status == 408
    assert reply.json() == {"error": "Timed out waiting for the request body"}


def test_body_is_read_as_json_whatever_the_content_type(client):
    # curl -d and many HTTP libraries default to form/text content types.
    body = json.dumps(DUNE).encode()
    reply = client.post("/books", raw=body, environ={"CONTENT_TYPE": "application/x-www-form-urlencoded"})
    assert reply.status == 201


def test_utf8_byte_order_mark_is_tolerated(client):
    reply = client.post("/books", raw=b"\xef\xbb\xbf" + json.dumps(DUNE).encode())
    assert reply.status == 201


# --- GET /books -------------------------------------------------------------------


def test_list_is_an_empty_array_when_there_are_no_books(client):
    reply = client.get("/books")
    assert reply.status == 200
    assert reply.headers["content-type"] == JSON_TYPE
    assert reply.json() == []


def test_list_returns_every_book_in_creation_order(client):
    dune, emma = create_book(client, **DUNE), create_book(client, **EMMA)
    assert client.get("/books").json() == [dune, emma]


def test_list_can_be_filtered_by_author(client):
    dune = create_book(client, **DUNE)
    messiah = create_book(client, **{**DUNE, "title": "Dune Messiah", "year": 1969})
    create_book(client, **EMMA)

    reply = client.get("/books?author=Frank%20Herbert")

    assert reply.status == 200
    assert reply.json() == [dune, messiah]


def test_author_filter_is_case_insensitive_and_needs_the_whole_name(client):
    create_book(client, **DUNE)
    assert len(client.get("/books?author=frank+HERBERT").json()) == 1
    assert client.get("/books?author=Herbert").json() == []
    assert client.get("/books?author=Nobody").json() == []


def test_author_filter_understands_percent_encoded_utf8(client):
    create_book(client, title="Cien años de soledad", author="Gabriel García Márquez")
    reply = client.get("/books?author=Gabriel%20Garc%C3%ADa%20M%C3%A1rquez")
    assert [book["title"] for book in reply.json()] == ["Cien años de soledad"]


def test_author_filter_understands_unescaped_utf8_in_the_query_string(client):
    # curl and friends send non-ASCII URL characters as raw UTF-8, which PEP 3333 servers
    # present to the application as latin-1 text.
    create_book(client, title="Cien años de soledad", author="Gabriel García Márquez")
    reply = client.get("/books?author=Gabriel%20García%20Márquez")
    assert [book["title"] for book in reply.json()] == ["Cien años de soledad"]


@pytest.mark.parametrize(
    "query, author",
    [
        pytest.param("author=Fran\xe7ois%20Zola", "François Zola", id="lone-latin1-byte"),
        pytest.param("author=Snow☃man", "Snow☃man", id="already-unicode"),
    ],
)
def test_query_strings_that_are_not_utf8_bytes_are_used_as_they_are(client, query, author):
    # A legacy client may send a bare latin-1 byte, and a non-conforming server may pass real Unicode.
    create_book(client, title="Anything", author=author)
    reply = client.get("/books", environ={"QUERY_STRING": query})
    assert [book["author"] for book in reply.json()] == [author]


def test_blank_author_filter_lists_everything(client):
    create_book(client, **DUNE)
    create_book(client, **EMMA)
    assert len(client.get("/books?author=").json()) == 2
    assert len(client.get("/books?author=%20%20").json()) == 2


def test_other_query_parameters_are_ignored(client):
    create_book(client, **DUNE)
    assert len(client.get("/books?colour=red").json()) == 1


def test_author_filter_cannot_be_used_for_sql_injection(client):
    create_book(client, **DUNE)
    assert client.get("/books?author=%27%20OR%20%271%27%3D%271").json() == []


# --- GET /books/{id} --------------------------------------------------------------


def test_get_book_returns_it(client):
    book = create_book(client)
    reply = client.get(f"/books/{book['id']}")
    assert reply.status == 200
    assert reply.headers["content-type"] == JSON_TYPE
    assert reply.json() == book


def test_get_unknown_book_is_404(client):
    reply = client.get("/books/42")
    assert reply.status == 404
    assert reply.headers["content-type"] == JSON_TYPE
    assert reply.json() == {"error": "Book 42 not found"}


@pytest.mark.parametrize(
    "path",
    [
        "/books/abc",
        "/books/1.5",
        "/books/-1",
        "/books/0",
        "/books/007",  # ids are canonical, so a book has exactly one URL
        "/books/9223372036854775808",  # 2**63: too big for an SQLite integer
        "/books/" + "9" * 5000,  # would blow int()'s digit limit if it were converted
    ],
)
def test_ids_that_cannot_exist_are_404_not_errors(client, path):
    reply = client.get(path)
    assert reply.status == 404
    assert reply.headers["content-type"] == JSON_TYPE


def test_a_book_has_exactly_one_url(client):
    book = create_book(client)
    assert client.get(f"/books/{book['id']}").status == 200
    for alias in (f"/books/0{book['id']}", f"/books/00{book['id']}"):
        assert client.get(alias).status == 404
        assert client.put(alias, payload=DUNE).status == 404
        assert client.delete(alias).status == 404
    assert client.get(f"/books/{book['id']}").json() == book  # untouched by the aliased writes


def test_only_ascii_digits_can_name_a_book(client):
    # A server that passes PATH_INFO as real Unicode could deliver "३" (Devanagari 3),
    # which int() would happily accept.
    reply = client.get("/anything", environ={"PATH_INFO": "/books/३"})
    assert reply.status == 404


def test_trailing_slashes_are_accepted(client):
    book = create_book(client)
    assert client.get(f"/books/{book['id']}/").json() == book
    assert client.get("/books/").json() == [book]
    assert client.get("/health/").status == 200


# --- PUT /books/{id} --------------------------------------------------------------


def test_put_replaces_the_book(client):
    book = create_book(client)
    replacement = {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": "978-0-593-09864-4"}

    reply = client.put(f"/books/{book['id']}", payload=replacement)

    assert reply.status == 200
    assert reply.headers["content-type"] == JSON_TYPE
    assert reply.json() == {"id": book["id"], **replacement}
    assert client.get(f"/books/{book['id']}").json() == reply.json()


def test_put_is_a_full_replacement_so_omitted_optional_fields_are_cleared(client):
    book = create_book(client)
    reply = client.put(f"/books/{book['id']}", payload={"title": "Dune", "author": "Frank Herbert"})
    assert reply.status == 200
    assert reply.json() == {"id": book["id"], "title": "Dune", "author": "Frank Herbert", "year": None, "isbn": None}


def test_put_only_changes_the_addressed_book(client):
    dune, emma = create_book(client, **DUNE), create_book(client, **EMMA)
    client.put(f"/books/{dune['id']}", payload={**DUNE, "title": "Changed"})
    assert client.get(f"/books/{emma['id']}").json() == emma


def test_put_cannot_change_the_id(client):
    book = create_book(client)
    reply = client.put(f"/books/{book['id']}", payload={**DUNE, "id": 500})
    assert reply.json()["id"] == book["id"]
    assert client.get("/books/500").status == 404


def test_put_unknown_book_is_404_and_does_not_create_it(client):
    reply = client.put("/books/7", payload=DUNE)
    assert reply.status == 404
    assert reply.json() == {"error": "Book 7 not found"}
    assert client.get("/books").json() == []


@pytest.mark.parametrize(
    "payload",
    [{"author": "Frank Herbert"}, {"title": "Dune", "author": ""}, {**DUNE, "year": "1965"}],
    ids=["missing-title", "blank-author", "bad-year"],
)
def test_put_validates_like_post_and_leaves_the_book_untouched(client, payload):
    book = create_book(client)
    reply = client.put(f"/books/{book['id']}", payload=payload)
    assert reply.status == 400
    assert reply.json()["error"] == "Validation failed"
    assert client.get(f"/books/{book['id']}").json() == book


def test_put_rejects_malformed_json(client):
    book = create_book(client)
    reply = client.put(f"/books/{book['id']}", raw=b"{oops")
    assert reply.status == 400
    assert client.get(f"/books/{book['id']}").json() == book


# --- DELETE /books/{id} -----------------------------------------------------------


def test_delete_removes_the_book_and_returns_204_without_a_body(client):
    book = create_book(client)

    reply = client.delete(f"/books/{book['id']}")

    assert reply.status == 204
    assert reply.body == b""
    assert "content-type" not in reply.headers
    assert client.get(f"/books/{book['id']}").status == 404
    assert client.get("/books").json() == []


def test_deleting_twice_is_404_the_second_time(client):
    book = create_book(client)
    assert client.delete(f"/books/{book['id']}").status == 204
    second = client.delete(f"/books/{book['id']}")
    assert second.status == 404
    assert second.json() == {"error": f"Book {book['id']} not found"}


def test_delete_only_removes_the_addressed_book(client):
    dune, emma = create_book(client, **DUNE), create_book(client, **EMMA)
    client.delete(f"/books/{dune['id']}")
    assert client.get("/books").json() == [emma]


def test_a_deleted_id_is_not_handed_out_again(client):
    first = create_book(client)
    client.delete(f"/books/{first['id']}")
    assert create_book(client)["id"] != first["id"]


# --- routing, methods and error handling ------------------------------------------


@pytest.mark.parametrize("path", ["/", "/nope", "/books/1/extra", "/health/deep", "/BOOKS"])
def test_unknown_paths_are_404_json(client, path):
    reply = client.get(path)
    assert reply.status == 404
    assert reply.headers["content-type"] == JSON_TYPE
    assert reply.json() == {"error": "Not found"}


@pytest.mark.parametrize(
    "method, path, allowed",
    [
        ("DELETE", "/books", "GET, HEAD, POST"),
        ("PUT", "/books", "GET, HEAD, POST"),
        ("POST", "/books/1", "DELETE, GET, HEAD, PUT"),
        ("PATCH", "/books/1", "DELETE, GET, HEAD, PUT"),
        ("POST", "/health", "GET, HEAD"),
        ("OPTIONS", "/health", "GET, HEAD"),
    ],
)
def test_unsupported_methods_are_405_and_list_the_allowed_ones(client, method, path, allowed):
    reply = client.request(method, path)
    assert reply.status == 405
    assert reply.headers["allow"] == allowed
    assert reply.json() == {"error": "Method not allowed"}


def test_http_methods_are_case_sensitive(client):
    reply = client.request("get", "/books", validate=False)  # the PEP 3333 validator warns about this method
    assert reply.status == 405
    assert reply.headers["allow"] == "GET, HEAD, POST"


def test_head_behaves_like_get_without_the_body(client):
    create_book(client)
    for path in ("/health", "/books", "/books/1", "/books/99", "/nope"):
        got, head = client.get(path), client.head(path)
        assert head.status == got.status
        assert head.body == b""
        assert head.headers["content-length"] == got.headers["content-length"] != "0"
        assert head.headers["content-type"] == JSON_TYPE


def test_unexpected_errors_become_a_generic_500_and_are_logged(client, app: BookApp, monkeypatch, caplog):
    def explode(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(app.repository, "list_books", explode)

    reply = client.get("/books")

    assert reply.status == 500
    assert reply.headers["content-type"] == JSON_TYPE
    assert reply.json() == {"error": "Internal server error"}
    assert b"secret" not in reply.body  # nothing internal leaks to the client...
    assert "secret internal detail" in caplog.text  # ...but the operator can see it
    assert client.get("/health").status == 200  # and the app keeps serving
