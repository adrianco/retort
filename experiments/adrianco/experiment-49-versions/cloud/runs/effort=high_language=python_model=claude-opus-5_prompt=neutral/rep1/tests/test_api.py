"""Integration tests: every request goes over a real socket to a real server."""

from __future__ import annotations

import pytest


# -- health -------------------------------------------------------------


def test_health_reports_ok(client):
    response = client.get("/health")

    assert response.status == 200
    assert response.json() == {"status": "ok", "database": "ok"}


# -- create -------------------------------------------------------------


def test_create_book_returns_201_with_the_stored_record(client, sample_book):
    response = client.post("/books", sample_book)

    assert response.status == 201
    book = response.json()
    assert isinstance(book["id"], int)
    assert book["title"] == sample_book["title"]
    assert book["author"] == sample_book["author"]
    assert book["year"] == sample_book["year"]
    assert book["isbn"] == sample_book["isbn"]
    assert book["created_at"] and book["updated_at"]
    assert response.headers["location"] == f"/books/{book['id']}"
    assert response.headers["content-type"].startswith("application/json")


def test_create_book_without_optional_fields(client):
    response = client.post("/books", {"title": "Untitled", "author": "Anon"})

    assert response.status == 201
    book = response.json()
    assert book["year"] is None
    assert book["isbn"] is None


def test_create_trims_whitespace_and_ignores_unknown_fields(client):
    response = client.post(
        "/books",
        {"title": "  Dune  ", "author": " Frank Herbert ", "id": 999, "sneaky": True},
    )

    assert response.status == 201
    book = response.json()
    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"
    assert book["id"] != 999  # client-supplied id is ignored
    assert "sneaky" not in book


def test_ids_are_unique_across_books(client, sample_book):
    ids = {client.post("/books", sample_book).json()["id"] for _ in range(5)}

    assert len(ids) == 5


@pytest.mark.parametrize(
    "payload, bad_field",
    [
        ({"author": "Anon"}, "title"),
        ({"title": "Untitled"}, "author"),
        ({"title": "   ", "author": "Anon"}, "title"),
        ({"title": "Untitled", "author": ""}, "author"),
        ({"title": None, "author": "Anon"}, "title"),
        ({"title": 42, "author": "Anon"}, "title"),
        ({"title": "T", "author": "A", "year": "not-a-year"}, "year"),
        ({"title": "T", "author": "A", "year": 12345}, "year"),
        ({"title": "T", "author": "A", "isbn": "nope"}, "isbn"),
    ],
)
def test_create_rejects_invalid_payloads(client, payload, bad_field):
    response = client.post("/books", payload)

    assert response.status == 400
    body = response.json()
    assert body["error"] == "Validation failed"
    assert bad_field in body["details"]


def test_create_reports_every_invalid_field_at_once(client):
    response = client.post("/books", {"year": "soon", "isbn": "nope"})

    assert response.status == 400
    assert set(response.json()["details"]) == {"title", "author", "year", "isbn"}


def test_create_rejects_malformed_json(client):
    response = client.post("/books", raw_body=b"{not json")

    assert response.status == 400
    assert "not valid JSON" in response.json()["error"]


def test_create_rejects_empty_body(client):
    response = client.post("/books", raw_body=b"")

    assert response.status == 400


def test_create_rejects_non_object_json(client):
    response = client.post("/books", ["a list is not a book"])

    assert response.status == 400
    assert "body" in response.json()["details"]


def test_create_rejects_non_json_content_type(client, sample_book):
    response = client.post("/books", sample_book, content_type="text/plain")

    assert response.status == 415


# -- list ---------------------------------------------------------------


def test_list_is_empty_initially(client):
    response = client.get("/books")

    assert response.status == 200
    assert response.json() == []


def test_list_returns_all_books(client, sample_book):
    client.post("/books", sample_book)
    client.post("/books", {"title": "Dune", "author": "Frank Herbert"})

    response = client.get("/books")

    assert response.status == 200
    titles = {book["title"] for book in response.json()}
    assert titles == {"Nineteen Eighty-Four", "Dune"}


def test_list_filters_by_author(client, sample_book):
    client.post("/books", sample_book)
    client.post("/books", {"title": "Animal Farm", "author": "George Orwell"})
    client.post("/books", {"title": "Dune", "author": "Frank Herbert"})

    response = client.get("/books?author=George%20Orwell")

    assert response.status == 200
    books = response.json()
    assert len(books) == 2
    assert {book["title"] for book in books} == {"Nineteen Eighty-Four", "Animal Farm"}


def test_author_filter_is_case_insensitive_and_partial(client, sample_book):
    client.post("/books", sample_book)

    assert len(client.get("/books?author=orwell").json()) == 1
    assert len(client.get("/books?author=GEORGE").json()) == 1


def test_author_filter_with_no_match_returns_empty_list(client, sample_book):
    client.post("/books", sample_book)

    response = client.get("/books?author=Nobody")

    assert response.status == 200
    assert response.json() == []


def test_author_filter_does_not_treat_wildcards_as_patterns(client, sample_book):
    client.post("/books", sample_book)

    assert client.get("/books?author=%25").json() == []


def test_empty_author_filter_returns_everything(client, sample_book):
    client.post("/books", sample_book)

    assert len(client.get("/books?author=").json()) == 1


# -- read ---------------------------------------------------------------


def test_get_single_book(client, sample_book):
    created = client.post("/books", sample_book).json()

    response = client.get(f"/books/{created['id']}")

    assert response.status == 200
    assert response.json() == created


def test_get_unknown_book_returns_404(client):
    response = client.get("/books/424242")

    assert response.status == 404
    assert "error" in response.json()


def test_get_non_numeric_id_returns_404(client):
    assert client.get("/books/abc").status == 404


# -- update -------------------------------------------------------------


def test_update_replaces_the_book(client, sample_book):
    created = client.post("/books", sample_book).json()

    response = client.put(
        f"/books/{created['id']}",
        {"title": "1984", "author": "Eric Blair", "year": 1950},
    )

    assert response.status == 200
    updated = response.json()
    assert updated["id"] == created["id"]
    assert updated["title"] == "1984"
    assert updated["author"] == "Eric Blair"
    assert updated["year"] == 1950
    assert updated["isbn"] is None  # PUT replaces: omitted fields are cleared
    assert updated["created_at"] == created["created_at"]

    assert client.get(f"/books/{created['id']}").json() == updated


def test_update_validates_the_payload(client, sample_book):
    created = client.post("/books", sample_book).json()

    response = client.put(f"/books/{created['id']}", {"author": "Nobody"})

    assert response.status == 400
    assert "title" in response.json()["details"]
    # The stored record is untouched.
    assert client.get(f"/books/{created['id']}").json() == created


def test_update_unknown_book_returns_404(client, sample_book):
    response = client.put("/books/424242", sample_book)

    assert response.status == 404


# -- delete -------------------------------------------------------------


def test_delete_removes_the_book(client, sample_book):
    created = client.post("/books", sample_book).json()

    response = client.delete(f"/books/{created['id']}")

    assert response.status == 204
    assert response.body == b""
    assert client.get(f"/books/{created['id']}").status == 404
    assert client.get("/books").json() == []


def test_delete_is_not_idempotent_for_unknown_ids(client, sample_book):
    created = client.post("/books", sample_book).json()
    client.delete(f"/books/{created['id']}")

    assert client.delete(f"/books/{created['id']}").status == 404


# -- routing ------------------------------------------------------------


def test_unknown_route_returns_404(client):
    response = client.get("/nope")

    assert response.status == 404
    assert "error" in response.json()


@pytest.mark.parametrize(
    "method, path, allowed",
    [
        ("DELETE", "/books", "GET, POST"),
        ("POST", "/books/1", "GET, PUT, DELETE"),
        ("POST", "/health", "GET, HEAD"),
    ],
)
def test_wrong_method_returns_405_with_allow_header(client, method, path, allowed):
    response = client.request(method, path, body={})

    assert response.status == 405
    assert response.headers["allow"] == allowed


def test_trailing_slash_is_accepted(client, sample_book):
    created = client.post("/books/", sample_book)

    assert created.status == 201
    assert client.get("/books/").status == 200
    assert client.get(f"/books/{created.json()['id']}/").status == 200


def test_data_survives_a_server_restart(tmp_path, sample_book):
    """The database is real storage, not an in-process dict."""
    import threading

    from bookapi.server import make_http_server
    from conftest import Client

    db_path = str(tmp_path / "persist.db")
    ids = []

    for _ in range(2):
        server = make_http_server("127.0.0.1", 0, db_path, quiet=True)
        thread = threading.Thread(target=server.serve_forever, args=(0.01,), daemon=True)
        thread.start()
        try:
            api = Client(*server.server_address[:2])
            ids.append(api.post("/books", sample_book).json()["id"])
            listed = api.get("/books").json()
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

    assert len(listed) == 2  # the second server saw the first server's book
    assert ids[0] != ids[1]
