"""Integration tests for the book-collection REST API.

Each test runs against a fresh, isolated SQLite database created in a pytest
temporary directory, so tests never touch the real ``books.db`` and never
interfere with one another.
"""

import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    """Yield a Flask test client backed by a throwaway SQLite database."""
    db_path = str(tmp_path / "test_books.db")
    app = create_app(db_path=db_path)
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


def _make_book(client, **overrides):
    """Helper: create a book and return its JSON body."""
    payload = {
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "year": 1937,
        "isbn": "978-0261102217",
    }
    payload.update(overrides)
    resp = client.post("/books", json=payload)
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return resp.get_json()


# --------------------------------------------------------------------------- #
# Health check
# --------------------------------------------------------------------------- #
def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


# --------------------------------------------------------------------------- #
# Create
# --------------------------------------------------------------------------- #
def test_create_book_returns_201_with_id(client):
    book = _make_book(client)
    assert book["id"] >= 1
    assert book["title"] == "The Hobbit"
    assert book["author"] == "J.R.R. Tolkien"
    assert book["year"] == 1937
    assert book["isbn"] == "978-0261102217"


def test_create_book_trims_whitespace(client):
    book = _make_book(client, title="  Dune  ", author="  Frank Herbert  ")
    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"


def test_create_book_with_only_required_fields(client):
    resp = client.post("/books", json={"title": "Minimal", "author": "Someone"})
    assert resp.status_code == 201
    book = resp.get_json()
    assert book["year"] is None
    assert book["isbn"] is None


def test_create_book_missing_title_returns_400(client):
    resp = client.post("/books", json={"author": "Nobody"})
    assert resp.status_code == 400
    assert "title" in " ".join(resp.get_json()["details"]).lower()


def test_create_book_missing_author_returns_400(client):
    resp = client.post("/books", json={"title": "Untitled"})
    assert resp.status_code == 400
    assert "author" in " ".join(resp.get_json()["details"]).lower()


def test_create_book_blank_title_returns_400(client):
    resp = client.post("/books", json={"title": "   ", "author": "Someone"})
    assert resp.status_code == 400


def test_create_book_bad_year_type_returns_400(client):
    resp = client.post(
        "/books", json={"title": "T", "author": "A", "year": "not-a-year"}
    )
    assert resp.status_code == 400
    assert "year" in " ".join(resp.get_json()["details"]).lower()


def test_create_book_malformed_json_returns_400(client):
    resp = client.post(
        "/books", data="{not valid json", content_type="application/json"
    )
    assert resp.status_code == 400


# --------------------------------------------------------------------------- #
# List (and author filter)
# --------------------------------------------------------------------------- #
def test_list_books_empty(client):
    resp = client.get("/books")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_books_returns_all(client):
    _make_book(client, title="A", author="Author One")
    _make_book(client, title="B", author="Author Two")
    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2


def test_list_books_filter_by_author(client):
    _make_book(client, title="A", author="George Orwell")
    _make_book(client, title="B", author="Aldous Huxley")
    _make_book(client, title="C", author="George Orwell")

    resp = client.get("/books?author=George Orwell")
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 2
    assert {b["title"] for b in books} == {"A", "C"}


def test_list_books_filter_by_author_is_case_insensitive(client):
    _make_book(client, title="A", author="George Orwell")
    resp = client.get("/books?author=george orwell")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1


def test_list_books_filter_no_match(client):
    _make_book(client, author="Real Author")
    resp = client.get("/books?author=Nonexistent")
    assert resp.status_code == 200
    assert resp.get_json() == []


# --------------------------------------------------------------------------- #
# Retrieve one
# --------------------------------------------------------------------------- #
def test_get_single_book(client):
    created = _make_book(client)
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == created


def test_get_single_book_not_found(client):
    resp = client.get("/books/99999")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


# --------------------------------------------------------------------------- #
# Update
# --------------------------------------------------------------------------- #
def test_update_book(client):
    created = _make_book(client)
    resp = client.put(
        f"/books/{created['id']}",
        json={
            "title": "The Hobbit (Revised)",
            "author": "J.R.R. Tolkien",
            "year": 1951,
            "isbn": "978-0261102217",
        },
    )
    assert resp.status_code == 200
    updated = resp.get_json()
    assert updated["id"] == created["id"]
    assert updated["title"] == "The Hobbit (Revised)"
    assert updated["year"] == 1951

    # Confirm the change persisted.
    again = client.get(f"/books/{created['id']}").get_json()
    assert again["title"] == "The Hobbit (Revised)"


def test_update_book_full_replacement_clears_optional_fields(client):
    created = _make_book(client)  # has year + isbn
    resp = client.put(
        f"/books/{created['id']}", json={"title": "T", "author": "A"}
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["year"] is None
    assert body["isbn"] is None


def test_update_book_not_found(client):
    resp = client.put("/books/99999", json={"title": "X", "author": "Y"})
    assert resp.status_code == 404


def test_update_book_invalid_payload_returns_400(client):
    created = _make_book(client)
    resp = client.put(f"/books/{created['id']}", json={"title": "No author"})
    assert resp.status_code == 400


# --------------------------------------------------------------------------- #
# Delete
# --------------------------------------------------------------------------- #
def test_delete_book(client):
    created = _make_book(client)
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 200

    # It should now be gone.
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_delete_book_not_found(client):
    resp = client.delete("/books/99999")
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# Misc / framework behaviour
# --------------------------------------------------------------------------- #
def test_unknown_route_returns_json_404(client):
    resp = client.get("/does-not-exist")
    assert resp.status_code == 404
    assert resp.is_json
    assert "error" in resp.get_json()


def test_method_not_allowed_returns_json_405(client):
    resp = client.patch("/books")
    assert resp.status_code == 405
    assert resp.is_json
