"""End-to-end tests of the REST API, calling the WSGI app in-process."""

import pytest

from bookapi.app import MAX_BODY_BYTES
from bookapi.db import BookStore


# -- health ----------------------------------------------------------------


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status == 200
    assert resp.headers["Content-Type"] == "application/json"
    assert resp.json() == {"status": "ok"}


def test_health_reports_unavailable_when_db_is_closed(db_path, make_client):
    store = BookStore(db_path)
    client = make_client(store)
    store.close()

    resp = client.get("/health")
    assert resp.status == 503
    assert resp.json() == {"status": "unavailable"}


# -- create ----------------------------------------------------------------


def test_create_book(client):
    resp = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"},
    )
    assert resp.status == 201
    book = resp.json()
    assert book == {
        "id": 1,
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "9780441172719",
    }
    assert resp.headers["Location"] == "/books/1"
    assert resp.headers["Content-Type"] == "application/json"


def test_create_with_only_required_fields(client):
    resp = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    assert resp.status == 201
    assert resp.json()["year"] is None
    assert resp.json()["isbn"] is None


def test_create_trims_whitespace(client):
    resp = client.post("/books", json={"title": "  Dune ", "author": " Frank Herbert  "})
    assert resp.json()["title"] == "Dune"
    assert resp.json()["author"] == "Frank Herbert"


def test_create_ignores_client_supplied_id(client):
    resp = client.post("/books", json={"id": 99, "title": "Dune", "author": "Frank Herbert"})
    assert resp.json()["id"] == 1


@pytest.mark.parametrize(
    "payload, field",
    [
        ({"author": "A"}, "title"),
        ({"title": "T"}, "author"),
        ({"title": "", "author": "A"}, "title"),
        ({"title": "T", "author": "   "}, "author"),
        ({"title": None, "author": "A"}, "title"),
        ({"title": 123, "author": "A"}, "title"),
        ({"title": "T", "author": ["A"]}, "author"),
        ({"title": "T", "author": "A", "year": "1999"}, "year"),
        ({"title": "T", "author": "A", "year": 19.5}, "year"),
        ({"title": "T", "author": "A", "year": True}, "year"),
        ({"title": "T", "author": "A", "year": 10000}, "year"),
        ({"title": "T", "author": "A", "year": -1}, "year"),
        ({"title": "T", "author": "A", "isbn": 9780441172719}, "isbn"),
        ({"title": "T" * 501, "author": "A"}, "title"),
    ],
)
def test_create_validation_errors(client, payload, field):
    resp = client.post("/books", json=payload)
    assert resp.status == 400
    body = resp.json()
    assert body["error"] == "validation failed"
    assert field in body["details"]
    assert client.get("/books").json() == []


def test_create_reports_all_invalid_fields_at_once(client):
    resp = client.post("/books", json={"year": "x"})
    assert set(resp.json()["details"]) == {"title", "author", "year"}


@pytest.mark.parametrize("raw", [b"", b"not json", b"{", b"\xff\xfe", b"[1, 2]", b'"str"', b"null", b"42"])
def test_create_rejects_bad_bodies(client, raw):
    resp = client.post("/books", data=raw)
    assert resp.status == 400
    assert "error" in resp.json()


def test_create_rejects_oversized_body(client):
    resp = client.post("/books", data=b"x", content_length=str(MAX_BODY_BYTES + 1))
    assert resp.status == 413


@pytest.mark.parametrize("length", ["abc", "-5"])
def test_create_rejects_bad_content_length(client, length):
    resp = client.post("/books", data=b"{}", content_length=length)
    assert resp.status == 400


def test_create_rejects_deeply_nested_json(client):
    resp = client.post("/books", data=b"[" * 100_000 + b"]" * 100_000)
    assert resp.status == 400


def test_unicode_round_trip(client):
    resp = client.post("/books", json={"title": "Les Misérables", "author": "Victor Hugo 雨果"})
    book_id = resp.json()["id"]
    assert client.get(f"/books/{book_id}").json()["title"] == "Les Misérables"
    assert client.get(f"/books/{book_id}").json()["author"] == "Victor Hugo 雨果"


# -- list / filter ---------------------------------------------------------


def test_list_empty(client):
    resp = client.get("/books")
    assert resp.status == 200
    assert resp.json() == []


def test_list_returns_all_books_in_id_order(client, make_book):
    make_book(title="A", author="X")
    make_book(title="B", author="Y")
    make_book(title="C", author="X")
    resp = client.get("/books")
    assert resp.status == 200
    assert [b["title"] for b in resp.json()] == ["A", "B", "C"]


def test_list_filter_by_author(client, make_book):
    make_book(title="A", author="Ursula K. Le Guin")
    make_book(title="B", author="Frank Herbert")
    make_book(title="C", author="Ursula K. Le Guin")
    resp = client.get("/books?author=Ursula%20K.%20Le%20Guin")
    assert resp.status == 200
    assert [b["title"] for b in resp.json()] == ["A", "C"]


def test_list_filter_is_case_insensitive_and_supports_plus_encoding(client, make_book):
    make_book(title="A", author="Frank Herbert")
    assert len(client.get("/books?author=frank+herbert").json()) == 1
    assert len(client.get("/books?author=FRANK%20HERBERT").json()) == 1


def test_list_filter_case_insensitive_beyond_ascii(client, make_book):
    make_book(title="A", author="Émile Zola")
    assert len(client.get("/books?author=%C3%A9mile%20zola").json()) == 1


def test_list_filter_is_exact_not_substring(client, make_book):
    make_book(author="Frank Herbert")
    assert client.get("/books?author=Frank").json() == []


def test_list_filter_no_match(client, make_book):
    make_book()
    resp = client.get("/books?author=Nobody")
    assert resp.status == 200
    assert resp.json() == []


def test_list_filter_is_not_injectable(client, make_book):
    make_book()
    assert client.get("/books?author=%27%20OR%20%271%27%3D%271").json() == []
    assert len(client.get("/books").json()) == 1


def test_list_empty_author_param_means_no_filter(client, make_book):
    make_book()
    assert len(client.get("/books?author=").json()) == 1


# -- get -------------------------------------------------------------------


def test_get_book(client, make_book):
    created = make_book()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status == 200
    assert resp.json() == created


@pytest.mark.parametrize("book_id", ["999", "0", "abc", "-1", "1.5", "99999999999999999999999"])
def test_get_unknown_or_malformed_id_is_404(client, book_id):
    resp = client.get(f"/books/{book_id}")
    assert resp.status == 404
    assert "error" in resp.json()


# -- update ----------------------------------------------------------------


def test_update_book(client, make_book):
    created = make_book()
    resp = client.put(
        f"/books/{created['id']}",
        json={"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": "9780593098233"},
    )
    assert resp.status == 200
    assert resp.json() == {
        "id": created["id"],
        "title": "Dune Messiah",
        "author": "Frank Herbert",
        "year": 1969,
        "isbn": "9780593098233",
    }
    assert client.get(f"/books/{created['id']}").json() == resp.json()


def test_update_only_changes_supplied_fields(client, make_book):
    created = make_book()
    resp = client.put(f"/books/{created['id']}", json={"year": 1966})
    assert resp.status == 200
    assert resp.json() == {**created, "year": 1966}


def test_update_can_clear_optional_fields(client, make_book):
    created = make_book()
    resp = client.put(f"/books/{created['id']}", json={"year": None, "isbn": None})
    assert resp.json()["year"] is None
    assert resp.json()["isbn"] is None


def test_update_cannot_change_id(client, make_book):
    created = make_book()
    resp = client.put(f"/books/{created['id']}", json={"id": 50, "title": "New"})
    assert resp.json()["id"] == created["id"]
    assert client.get("/books/50").status == 404


@pytest.mark.parametrize(
    "payload, field",
    [
        ({"title": ""}, "title"),
        ({"author": None}, "author"),
        ({"year": "1999"}, "year"),
        ({"isbn": 5}, "isbn"),
    ],
)
def test_update_validation_errors_leave_book_unchanged(client, make_book, payload, field):
    created = make_book()
    resp = client.put(f"/books/{created['id']}", json=payload)
    assert resp.status == 400
    assert field in resp.json()["details"]
    assert client.get(f"/books/{created['id']}").json() == created


@pytest.mark.parametrize("payload", [{}, {"unrelated": 1}, [], "x"])
def test_update_requires_something_to_update(client, make_book, payload):
    created = make_book()
    assert client.put(f"/books/{created['id']}", json=payload).status == 400


def test_update_invalid_json(client, make_book):
    created = make_book()
    assert client.put(f"/books/{created['id']}", data=b"{nope").status == 400


@pytest.mark.parametrize("book_id", ["42", "0", "99999999999999999999999"])
def test_update_unknown_book_is_404(client, book_id):
    resp = client.put(f"/books/{book_id}", json={"title": "T", "author": "A"})
    assert resp.status == 404


# -- delete ----------------------------------------------------------------


def test_delete_book(client, make_book):
    created = make_book()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status == 204
    assert resp.body == b""
    assert client.get(f"/books/{created['id']}").status == 404
    assert client.get("/books").json() == []


@pytest.mark.parametrize("book_id", ["42", "0", "99999999999999999999999"])
def test_delete_unknown_book_is_404(client, book_id):
    assert client.delete(f"/books/{book_id}").status == 404


def test_delete_twice_is_404_the_second_time(client, make_book):
    created = make_book()
    assert client.delete(f"/books/{created['id']}").status == 204
    assert client.delete(f"/books/{created['id']}").status == 404


def test_ids_are_not_reused_after_delete(client, make_book):
    first = make_book()
    client.delete(f"/books/{first['id']}")
    second = make_book()
    assert second["id"] > first["id"]


# -- routing ---------------------------------------------------------------


def test_unknown_path_is_404_json(client):
    resp = client.get("/nope")
    assert resp.status == 404
    assert resp.json() == {"error": "not found"}


@pytest.mark.parametrize(
    "method, path, allow",
    [
        ("DELETE", "/books", "GET, POST"),
        ("PUT", "/books", "GET, POST"),
        ("POST", "/books/1", "GET, PUT, DELETE"),
        ("PATCH", "/books/1", "GET, PUT, DELETE"),
        ("POST", "/health", "GET"),
    ],
)
def test_method_not_allowed(client, method, path, allow):
    resp = client.request(method, path)
    assert resp.status == 405
    assert resp.headers["Allow"] == allow
    assert "error" in resp.json()


def test_trailing_slash_is_accepted(client, make_book):
    created = make_book()
    assert client.get("/books/").status == 200
    assert client.get(f"/books/{created['id']}/").status == 200
    assert client.get("/health/").status == 200


# -- persistence & robustness ---------------------------------------------


def test_data_persists_across_store_instances(db_path, make_client):
    first = BookStore(db_path)
    created = make_client(first).post("/books", json={"title": "Dune", "author": "Frank Herbert"}).json()
    first.close()

    second = BookStore(db_path)
    try:
        assert make_client(second).get(f"/books/{created['id']}").json() == created
    finally:
        second.close()


def test_unexpected_error_returns_500_json_without_leaking_details(client, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(client.app.store, "list_books", boom)
    resp = client.get("/books")
    assert resp.status == 500
    assert resp.json() == {"error": "internal server error"}
    assert b"secret" not in resp.body
