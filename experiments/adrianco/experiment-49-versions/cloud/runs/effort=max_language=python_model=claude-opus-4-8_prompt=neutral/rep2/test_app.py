"""Integration tests for the book-collection API.

Each test runs against a fresh, isolated SQLite file created under pytest's
``tmp_path`` fixture, so tests never touch the real ``books.db`` and never
interfere with one another.
"""

import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    """A Flask test client backed by a throwaway database file."""
    db_path = tmp_path / "test_books.db"
    app = create_app(database=str(db_path))
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def _make_book(client, **overrides):
    """Helper: POST a book and return the parsed JSON body."""
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965,
               "isbn": "978-0441013593"}
    payload.update(overrides)
    resp = client.post("/books", json=payload)
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return resp.get_json()


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


# --------------------------------------------------------------------------- #
# Create
# --------------------------------------------------------------------------- #
def test_create_book(client):
    resp = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965,
              "isbn": "978-0441013593"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] == 1
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "978-0441013593"
    # A Location header should point at the new resource.
    assert resp.headers["Location"].endswith("/books/1")


def test_create_book_minimal(client):
    """Only title + author are required; year/isbn default to null."""
    resp = client.post("/books", json={"title": "Untitled", "author": "Anon"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["year"] is None
    assert body["isbn"] is None


def test_create_book_trims_whitespace(client):
    body = _make_book(client, title="  Spaced Out  ", author="  Writer  ")
    assert body["title"] == "Spaced Out"
    assert body["author"] == "Writer"


@pytest.mark.parametrize(
    "payload",
    [
        {"author": "No Title"},              # missing title
        {"title": "No Author"},              # missing author
        {"title": "", "author": "x"},        # empty title
        {"title": "x", "author": "   "},     # whitespace-only author
        {"title": "x", "author": "y", "year": "old"},  # bad year type
    ],
)
def test_create_book_validation_errors(client, payload):
    resp = client.post("/books", json=payload)
    assert resp.status_code == 400
    assert "errors" in resp.get_json()


def test_create_book_rejects_non_json(client):
    resp = client.post("/books", data="not json",
                       content_type="application/json")
    assert resp.status_code == 400


# --------------------------------------------------------------------------- #
# List (+ author filter)
# --------------------------------------------------------------------------- #
def test_list_books_empty(client):
    resp = client.get("/books")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_and_filter_by_author(client):
    _make_book(client, title="Dune", author="Frank Herbert")
    _make_book(client, title="Neuromancer", author="William Gibson")
    _make_book(client, title="Count Zero", author="William Gibson")

    # No filter -> all three.
    all_books = client.get("/books").get_json()
    assert len(all_books) == 3

    # Filtered -> only Gibson's two (case-insensitive match).
    gibson = client.get("/books?author=william gibson").get_json()
    assert len(gibson) == 2
    assert {b["title"] for b in gibson} == {"Neuromancer", "Count Zero"}

    # Unknown author -> empty list, still 200.
    none = client.get("/books?author=Nobody")
    assert none.status_code == 200
    assert none.get_json() == []


# --------------------------------------------------------------------------- #
# Retrieve one
# --------------------------------------------------------------------------- #
def test_get_book(client):
    created = _make_book(client)
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == created


def test_get_book_not_found(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


# --------------------------------------------------------------------------- #
# Update
# --------------------------------------------------------------------------- #
def test_update_book(client):
    created = _make_book(client)
    resp = client.put(
        f"/books/{created['id']}",
        json={"title": "Dune Messiah", "author": "Frank Herbert",
              "year": 1969, "isbn": "978-0593098233"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == created["id"]
    assert body["title"] == "Dune Messiah"
    assert body["year"] == 1969

    # Persisted?
    assert client.get(f"/books/{created['id']}").get_json()["title"] == \
        "Dune Messiah"


def test_update_book_not_found(client):
    resp = client.put("/books/9999",
                      json={"title": "x", "author": "y"})
    assert resp.status_code == 404


def test_update_book_validation(client):
    created = _make_book(client)
    resp = client.put(f"/books/{created['id']}", json={"title": "only title"})
    assert resp.status_code == 400
    assert "errors" in resp.get_json()


# --------------------------------------------------------------------------- #
# Delete
# --------------------------------------------------------------------------- #
def test_delete_book(client):
    created = _make_book(client)
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["deleted"] is True

    # Gone afterwards.
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_delete_book_not_found(client):
    resp = client.delete("/books/9999")
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# Misc / routing
# --------------------------------------------------------------------------- #
def test_unknown_route_returns_json_404(client):
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert resp.is_json
    assert "error" in resp.get_json()


def test_method_not_allowed_returns_json_405(client):
    resp = client.patch("/books")
    assert resp.status_code == 405
    assert resp.is_json
