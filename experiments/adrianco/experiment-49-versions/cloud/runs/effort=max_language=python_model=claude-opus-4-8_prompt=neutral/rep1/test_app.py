"""Integration and unit tests for the book collection API.

Run with::

    pytest -v
"""

import os
import tempfile

import pytest

from app import create_app, validate_book_payload


@pytest.fixture
def client():
    """Yield a Flask test client backed by a throwaway temp SQLite file."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app = create_app(database=db_path)
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client
    os.close(db_fd)
    os.unlink(db_path)


def make_book(client, **overrides):
    """Helper: POST a book and return the parsed JSON response."""
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965,
               "isbn": "978-0441013593"}
    payload.update(overrides)
    resp = client.post("/books", json=payload)
    return resp


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
def test_create_book_returns_201_and_body(client):
    resp = make_book(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] >= 1
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "978-0441013593"


def test_create_book_minimal_fields(client):
    """Only title and author are required; year/isbn default to null."""
    resp = client.post("/books", json={"title": "Untitled", "author": "Anon"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["year"] is None
    assert body["isbn"] is None


def test_create_book_trims_whitespace(client):
    resp = client.post("/books", json={"title": "  Neuromancer  ",
                                       "author": "  Gibson  "})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["title"] == "Neuromancer"
    assert body["author"] == "Gibson"


def test_create_missing_title_returns_400(client):
    resp = client.post("/books", json={"author": "Nobody"})
    assert resp.status_code == 400
    assert "title" in " ".join(resp.get_json()["details"]).lower()


def test_create_missing_author_returns_400(client):
    resp = client.post("/books", json={"title": "Orphan"})
    assert resp.status_code == 400
    assert "author" in " ".join(resp.get_json()["details"]).lower()


def test_create_blank_title_returns_400(client):
    resp = client.post("/books", json={"title": "   ", "author": "X"})
    assert resp.status_code == 400


def test_create_invalid_year_returns_400(client):
    resp = client.post("/books", json={"title": "T", "author": "A",
                                       "year": "not-a-year"})
    assert resp.status_code == 400
    assert "year" in " ".join(resp.get_json()["details"]).lower()


def test_create_invalid_json_returns_400(client):
    resp = client.post("/books", data="this is not json",
                       content_type="application/json")
    assert resp.status_code == 400


def test_create_non_object_json_returns_400(client):
    resp = client.post("/books", json=["not", "an", "object"])
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------
def test_list_empty(client):
    resp = client.get("/books")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_returns_created_books(client):
    make_book(client, title="A", author="Author One")
    make_book(client, title="B", author="Author Two")
    resp = client.get("/books")
    assert resp.status_code == 200
    titles = [b["title"] for b in resp.get_json()]
    assert titles == ["A", "B"]


def test_list_author_filter(client):
    make_book(client, title="A", author="Ursula K. Le Guin")
    make_book(client, title="B", author="Isaac Asimov")
    make_book(client, title="C", author="Ursula K. Le Guin")
    resp = client.get("/books", query_string={"author": "Ursula K. Le Guin"})
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 2
    assert {b["title"] for b in books} == {"A", "C"}


def test_list_author_filter_is_case_insensitive(client):
    make_book(client, title="A", author="Terry Pratchett")
    resp = client.get("/books", query_string={"author": "terry pratchett"})
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1


def test_list_author_filter_no_match(client):
    make_book(client, title="A", author="Someone")
    resp = client.get("/books", query_string={"author": "Nobody"})
    assert resp.status_code == 200
    assert resp.get_json() == []


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------
def test_get_existing_book(client):
    created = make_book(client).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == created


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/999")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Book not found"


def test_get_non_integer_id_returns_404(client):
    resp = client.get("/books/not-a-number")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------
def test_update_book(client):
    created = make_book(client).get_json()
    resp = client.put(f"/books/{created['id']}", json={
        "title": "Dune Messiah", "author": "Frank Herbert", "year": 1969,
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "Dune Messiah"
    assert body["year"] == 1969
    # isbn was omitted on a full-replace PUT -> reset to null
    assert body["isbn"] is None
    assert body["id"] == created["id"]


def test_update_persists(client):
    created = make_book(client).get_json()
    client.put(f"/books/{created['id']}", json={"title": "New", "author": "New"})
    resp = client.get(f"/books/{created['id']}")
    assert resp.get_json()["title"] == "New"


def test_update_missing_book_returns_404(client):
    resp = client.put("/books/999", json={"title": "X", "author": "Y"})
    assert resp.status_code == 404


def test_update_invalid_payload_returns_400(client):
    created = make_book(client).get_json()
    resp = client.put(f"/books/{created['id']}", json={"author": "No title"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------
def test_delete_book(client):
    created = make_book(client).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204
    assert resp.data == b""
    # confirm it is gone
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_delete_missing_book_returns_404(client):
    resp = client.delete("/books/999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Routing / method handling
# ---------------------------------------------------------------------------
def test_unknown_route_returns_json_404(client):
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert resp.is_json
    assert resp.get_json()["error"] == "Not found"


def test_method_not_allowed_returns_json_405(client):
    resp = client.delete("/books")  # no collection-level DELETE
    assert resp.status_code == 405
    assert resp.is_json
    assert resp.get_json()["error"] == "Method not allowed"


# ---------------------------------------------------------------------------
# End-to-end lifecycle
# ---------------------------------------------------------------------------
def test_full_crud_lifecycle(client):
    # create
    book = client.post("/books", json={"title": "1984", "author": "Orwell",
                                       "year": 1949}).get_json()
    book_id = book["id"]
    # read
    assert client.get(f"/books/{book_id}").status_code == 200
    # update
    assert client.put(f"/books/{book_id}",
                      json={"title": "1984", "author": "George Orwell",
                            "year": 1949, "isbn": "978-0451524935"}
                      ).status_code == 200
    # list reflects update
    listed = client.get("/books").get_json()
    assert listed[0]["author"] == "George Orwell"
    # delete
    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get("/books").get_json() == []


# ---------------------------------------------------------------------------
# Pure unit tests for the validation helper
# ---------------------------------------------------------------------------
def test_validate_valid_payload():
    clean, errors = validate_book_payload(
        {"title": "T", "author": "A", "year": 2000, "isbn": "x"}
    )
    assert errors == []
    assert clean == {"title": "T", "author": "A", "year": 2000, "isbn": "x"}


def test_validate_missing_required_fields():
    clean, errors = validate_book_payload({})
    assert len(errors) == 2  # title and author


def test_validate_rejects_boolean_year():
    # bool is a subclass of int; ensure it is not accepted as a year.
    _clean, errors = validate_book_payload(
        {"title": "T", "author": "A", "year": True}
    )
    assert any("year" in e for e in errors)


def test_validate_rejects_out_of_range_year():
    _clean, errors = validate_book_payload(
        {"title": "T", "author": "A", "year": 99999}
    )
    assert any("year" in e for e in errors)


def test_validate_rejects_non_string_isbn():
    _clean, errors = validate_book_payload(
        {"title": "T", "author": "A", "isbn": 12345}
    )
    assert any("isbn" in e for e in errors)


def test_validate_optional_fields_default_to_none():
    clean, errors = validate_book_payload({"title": "T", "author": "A"})
    assert errors == []
    assert clean["year"] is None
    assert clean["isbn"] is None
