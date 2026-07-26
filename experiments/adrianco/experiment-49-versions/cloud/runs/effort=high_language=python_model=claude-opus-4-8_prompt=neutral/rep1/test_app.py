"""Integration tests for the Book Collection API.

Each test runs against a temporary SQLite database so runs are isolated and
repeatable.
"""

import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    db_file = tmp_path / "test_books.db"
    app = create_app(db_path=str(db_file))
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def _sample_book(**overrides):
    book = {
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt",
        "year": 1999,
        "isbn": "978-0201616224",
    }
    book.update(overrides)
    return book


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    resp = client.post("/books", json=_sample_book())
    assert resp.status_code == 201
    created = resp.get_json()
    assert created["id"] > 0
    assert created["title"] == "The Pragmatic Programmer"
    assert created["author"] == "Andrew Hunt"

    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == created


def test_create_requires_title_and_author(client):
    # Missing author.
    resp = client.post("/books", json={"title": "No Author"})
    assert resp.status_code == 400

    # Blank title should also be rejected.
    resp = client.post("/books", json={"title": "   ", "author": "Someone"})
    assert resp.status_code == 400


def test_list_and_author_filter(client):
    client.post("/books", json=_sample_book(title="Book A", author="Alice"))
    client.post("/books", json=_sample_book(title="Book B", author="Bob"))
    client.post("/books", json=_sample_book(title="Book C", author="Alice"))

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    titles = sorted(b["title"] for b in resp.get_json())
    assert titles == ["Book A", "Book C"]


def test_update_book(client):
    created = client.post("/books", json=_sample_book()).get_json()

    resp = client.put(
        f"/books/{created['id']}",
        json=_sample_book(title="Updated Title", year=2019),
    )
    assert resp.status_code == 200
    updated = resp.get_json()
    assert updated["title"] == "Updated Title"
    assert updated["year"] == 2019
    assert updated["id"] == created["id"]


def test_delete_book(client):
    created = client.post("/books", json=_sample_book()).get_json()

    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 200

    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 404


def test_missing_book_returns_404(client):
    assert client.get("/books/9999").status_code == 404
    assert client.put("/books/9999", json=_sample_book()).status_code == 404
    assert client.delete("/books/9999").status_code == 404
