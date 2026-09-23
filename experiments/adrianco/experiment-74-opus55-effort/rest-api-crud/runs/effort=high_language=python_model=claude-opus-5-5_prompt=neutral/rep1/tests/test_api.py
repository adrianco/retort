"""Endpoint tests run against the WSGI app in-process."""

import pytest


def test_health(client):
    resp = client.get("/health")
    assert resp.status == 200
    assert resp.json() == {"status": "ok", "database": "ok"}
    assert resp.headers["Content-Type"] == "application/json"


def test_create_book(client, sample_book):
    resp = client.post("/books", sample_book)
    assert resp.status == 201
    book = resp.json()
    assert book["id"] >= 1
    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"
    assert book["year"] == 1965
    assert book["isbn"] == "9780441172719"  # hyphens stripped
    assert resp.headers["Location"] == f"/books/{book['id']}"


def test_create_book_with_only_required_fields(client):
    resp = client.post("/books", {"title": "Untitled", "author": "Anon"})
    assert resp.status == 201
    assert resp.json()["year"] is None
    assert resp.json()["isbn"] is None


@pytest.mark.parametrize(
    "payload, field",
    [
        ({"author": "Someone"}, "title"),
        ({"title": "Something"}, "author"),
        ({"title": "   ", "author": "Someone"}, "title"),
        ({"title": "Something", "author": ""}, "author"),
        ({"title": 42, "author": "Someone"}, "title"),
        ({"title": "T", "author": "A", "year": "1999"}, "year"),
        ({"title": "T", "author": "A", "year": True}, "year"),
        ({"title": "T", "author": "A", "year": 99999}, "year"),
        ({"title": "T", "author": "A", "isbn": "not-an-isbn"}, "isbn"),
        ({"title": "T", "author": "A", "isbn": 12345}, "isbn"),
        ({"title": "T", "author": "A", "publisher": "X"}, "publisher"),
    ],
)
def test_create_book_validation_errors(client, payload, field):
    resp = client.post("/books", payload)
    assert resp.status == 400
    body = resp.json()
    assert body["error"] == "validation failed"
    assert field in body["details"]
    assert client.get("/books").json() == []


def test_create_book_missing_title_and_author_reports_both(client):
    resp = client.post("/books", {"year": 2000})
    assert resp.status == 400
    assert set(resp.json()["details"]) == {"title", "author"}


@pytest.mark.parametrize("raw", [b"", b"{not json", b"[1, 2]", b'"a string"', b"\xff\xfe"])
def test_create_book_rejects_bad_bodies(client, raw):
    resp = client.post("/books", raw=raw)
    assert resp.status == 400
    assert "error" in resp.json()


def test_duplicate_isbn_conflict(client, sample_book):
    assert client.post("/books", sample_book).status == 201
    dup = dict(sample_book, title="Dune (reprint)", isbn="9780441172719")
    resp = client.post("/books", dup)
    assert resp.status == 409


def test_list_books(client, sample_book):
    assert client.get("/books").json() == []
    client.post("/books", sample_book)
    client.post("/books", {"title": "Neuromancer", "author": "William Gibson", "year": 1984})
    resp = client.get("/books")
    assert resp.status == 200
    titles = [b["title"] for b in resp.json()]
    assert titles == ["Dune", "Neuromancer"]


def test_list_books_author_filter(client):
    client.post("/books", {"title": "Dune", "author": "Frank Herbert"})
    client.post("/books", {"title": "Dune Messiah", "author": "Frank Herbert"})
    client.post("/books", {"title": "Neuromancer", "author": "William Gibson"})

    resp = client.get("/books?author=Frank%20Herbert")
    assert resp.status == 200
    assert [b["title"] for b in resp.json()] == ["Dune", "Dune Messiah"]

    # case-insensitive match
    assert len(client.get("/books?author=frank+herbert").json()) == 2
    # no match
    assert client.get("/books?author=Nobody").json() == []
    # empty filter means no filter
    assert len(client.get("/books?author=").json()) == 3


def test_get_book(client, sample_book):
    created = client.post("/books", sample_book).json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status == 200
    assert resp.json() == created


@pytest.mark.parametrize("path", ["/books/999", "/books/abc", "/books/0", "/books/-1"])
def test_get_book_not_found(client, path):
    resp = client.get(path)
    assert resp.status == 404
    assert "error" in resp.json()


def test_update_book(client, sample_book):
    created = client.post("/books", sample_book).json()
    update = {"title": "Dune", "author": "Frank Herbert", "year": 1966, "isbn": "0441172717"}
    resp = client.put(f"/books/{created['id']}", update)
    assert resp.status == 200
    updated = resp.json()
    assert updated == {"id": created["id"], **update}
    assert client.get(f"/books/{created['id']}").json() == updated


def test_update_book_validation(client, sample_book):
    created = client.post("/books", sample_book).json()
    resp = client.put(f"/books/{created['id']}", {"title": "", "year": 2000})
    assert resp.status == 400
    assert {"title", "author"} <= set(resp.json()["details"])
    # unchanged
    assert client.get(f"/books/{created['id']}").json() == created


def test_update_book_not_found(client):
    resp = client.put("/books/42", {"title": "T", "author": "A"})
    assert resp.status == 404


def test_update_book_isbn_conflict(client, sample_book):
    client.post("/books", sample_book)
    other = client.post("/books", {"title": "Other", "author": "A", "isbn": "0441172717"}).json()
    resp = client.put(f"/books/{other['id']}", {"title": "Other", "author": "A", "isbn": sample_book["isbn"]})
    assert resp.status == 409


def test_delete_book(client, sample_book):
    created = client.post("/books", sample_book).json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status == 204
    assert resp.body == b""
    assert client.get(f"/books/{created['id']}").status == 404
    assert client.delete(f"/books/{created['id']}").status == 404


def test_unknown_route_and_method(client):
    assert client.get("/nope").status == 404
    resp = client.request("PATCH", "/books")
    assert resp.status == 405
    assert resp.headers["Allow"] == "GET, POST"
    assert client.request("POST", "/books/1").status == 405
    assert client.request("DELETE", "/health").status == 405


def test_trailing_slash_is_accepted(client, sample_book):
    assert client.post("/books/", sample_book).status == 201
    assert len(client.get("/books/").json()) == 1
