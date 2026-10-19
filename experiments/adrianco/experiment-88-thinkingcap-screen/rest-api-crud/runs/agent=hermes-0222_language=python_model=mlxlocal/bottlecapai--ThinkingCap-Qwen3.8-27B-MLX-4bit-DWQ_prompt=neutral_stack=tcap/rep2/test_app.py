"""Integration tests for the book collection REST API.

Run with: pytest -q
"""

import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(db_path=str(tmp_path / "test_books.db"))
    app.config["TESTING"] = True
    return app.test_client()


def _create(client, **fields):
    return client.post("/books", json=fields)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /books
# ---------------------------------------------------------------------------

def test_create_book_full(client):
    res = _create(
        client,
        title="The Hobbit",
        author="J.R.R. Tolkien",
        year=1937,
        isbn="978-0547928227",
    )
    assert res.status_code == 201
    body = res.get_json()
    assert body["title"] == "The Hobbit"
    assert body["author"] == "J.R.R. Tolkien"
    assert body["year"] == 1937
    assert body["isbn"] == "978-0547928227"
    assert isinstance(body["id"], int)


def test_create_book_minimal_fields(client):
    res = _create(client, title="Dune", author="Frank Herbert")
    assert res.status_code == 201
    body = res.get_json()
    assert body["year"] is None
    assert body["isbn"] is None


def test_create_book_missing_title(client):
    res = _create(client, author="Frank Herbert")
    assert res.status_code == 400
    assert "title" in res.get_json()["error"]


def test_create_book_missing_author(client):
    res = _create(client, title="Dune")
    assert res.status_code == 400
    assert "author" in res.get_json()["error"]


def test_create_book_empty_title(client):
    res = _create(client, title="   ", author="Someone")
    assert res.status_code == 400


def test_create_book_invalid_year(client):
    res = _create(client, title="Dune", author="Frank Herbert", year="not-a-year")
    assert res.status_code == 400
    assert "year" in res.get_json()["error"]


def test_create_book_non_json_body(client):
    res = client.post("/books", data="not json", content_type="text/plain")
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# GET /books
# ---------------------------------------------------------------------------

def test_list_books_empty(client):
    res = client.get("/books")
    assert res.status_code == 200
    assert res.get_json() == []


def test_list_books_returns_all(client):
    _create(client, title="Book A", author="Alice", year=2001)
    _create(client, title="Book B", author="Bob", year=2002)
    res = client.get("/books")
    assert res.status_code == 200
    titles = [b["title"] for b in res.get_json()]
    assert titles == ["Book A", "Book B"]


def test_list_books_filter_by_author(client):
    _create(client, title="Book A", author="Alice")
    _create(client, title="Book B", author="Bob")
    _create(client, title="Book C", author="Alice")

    res = client.get("/books?author=Alice")
    assert res.status_code == 200
    books = res.get_json()
    assert [b["title"] for b in books] == ["Book A", "Book C"]

    res = client.get("/books?author=Nobody")
    assert res.status_code == 200
    assert res.get_json() == []


# ---------------------------------------------------------------------------
# GET /books/<id>
# ---------------------------------------------------------------------------

def test_get_book_by_id(client):
    created = _create(client, title="1984", author="George Orwell", year=1949)
    book_id = created.get_json()["id"]

    res = client.get(f"/books/{book_id}")
    assert res.status_code == 200
    assert res.get_json()["title"] == "1984"


def test_get_book_not_found(client):
    res = client.get("/books/9999")
    assert res.status_code == 404
    assert res.get_json()["error"] == "Book not found"


# ---------------------------------------------------------------------------
# PUT /books/<id>
# ---------------------------------------------------------------------------

def test_update_book_partial(client):
    created = _create(client, title="Old Title", author="Author", year=1999)
    book_id = created.get_json()["id"]

    res = client.put(f"/books/{book_id}", json={"title": "New Title", "year": 2020})
    assert res.status_code == 200
    body = res.get_json()
    assert body["title"] == "New Title"
    assert body["year"] == 2020
    assert body["author"] == "Author"  # untouched

    # persisted
    assert client.get(f"/books/{book_id}").get_json()["title"] == "New Title"


def test_update_book_clears_year_with_null(client):
    created = _create(client, title="T", author="A", year=1999)
    book_id = created.get_json()["id"]

    res = client.put(f"/books/{book_id}", json={"year": None})
    assert res.status_code == 200
    assert res.get_json()["year"] is None


def test_update_book_not_found(client):
    res = client.put("/books/9999", json={"title": "X"})
    assert res.status_code == 404


def test_update_book_empty_title_rejected(client):
    created = _create(client, title="T", author="A")
    book_id = created.get_json()["id"]
    res = client.put(f"/books/{book_id}", json={"title": ""})
    assert res.status_code == 400


def test_update_book_no_fields(client):
    created = _create(client, title="T", author="A")
    book_id = created.get_json()["id"]
    res = client.put(f"/books/{book_id}", json={})
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /books/<id>
# ---------------------------------------------------------------------------

def test_delete_book(client):
    created = _create(client, title="T", author="A")
    book_id = created.get_json()["id"]

    res = client.delete(f"/books/{book_id}")
    assert res.status_code == 200

    assert client.get(f"/books/{book_id}").status_code == 404
    assert client.get("/books").get_json() == []


def test_delete_book_not_found(client):
    res = client.delete("/books/9999")
    assert res.status_code == 404


def test_delete_is_idempotent_404(client):
    created = _create(client, title="T", author="A")
    book_id = created.get_json()["id"]
    assert client.delete(f"/books/{book_id}").status_code == 200
    assert client.delete(f"/books/{book_id}").status_code == 404
