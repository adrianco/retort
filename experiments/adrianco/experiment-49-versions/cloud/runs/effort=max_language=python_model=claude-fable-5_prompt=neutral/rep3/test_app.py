"""Integration tests for the book collection API."""

import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})


@pytest.fixture()
def client(app):
    return app.test_client()


def create_book(client, **overrides):
    payload = {
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt",
        "year": 1999,
        "isbn": "978-0201616224",
    }
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_create_book_returns_201_with_book_and_location(client):
    response = create_book(client)
    assert response.status_code == 201
    book = response.get_json()
    assert book["id"] == 1
    assert book["title"] == "The Pragmatic Programmer"
    assert book["author"] == "Andrew Hunt"
    assert book["year"] == 1999
    assert book["isbn"] == "978-0201616224"
    assert response.headers["Location"].endswith("/books/1")


def test_create_book_allows_optional_fields_to_be_omitted(client):
    response = client.post("/books", json={"title": "Sula", "author": "Toni Morrison"})
    assert response.status_code == 201
    book = response.get_json()
    assert book["year"] is None
    assert book["isbn"] is None


def test_create_book_requires_title_and_author(client):
    response = client.post("/books", json={"year": 2001})
    assert response.status_code == 400
    errors = response.get_json()["errors"]
    assert "title" in errors
    assert "author" in errors


def test_create_book_rejects_blank_title(client):
    response = create_book(client, title="   ")
    assert response.status_code == 400
    assert "title" in response.get_json()["errors"]


def test_create_book_rejects_non_integer_year(client):
    response = create_book(client, year="nineteen ninety-nine")
    assert response.status_code == 400
    assert "year" in response.get_json()["errors"]


def test_create_book_rejects_non_json_body(client):
    response = client.post("/books", data="not json", content_type="text/plain")
    assert response.status_code == 400
    assert "body" in response.get_json()["errors"]


def test_list_books_returns_all_books(client):
    create_book(client)
    create_book(client, title="Beloved", author="Toni Morrison", year=1987)
    response = client.get("/books")
    assert response.status_code == 200
    books = response.get_json()
    assert [book["title"] for book in books] == [
        "The Pragmatic Programmer",
        "Beloved",
    ]


def test_list_books_filters_by_author_case_insensitively(client):
    create_book(client)
    create_book(client, title="Beloved", author="Toni Morrison")
    create_book(client, title="Song of Solomon", author="Toni Morrison")

    response = client.get("/books", query_string={"author": "toni morrison"})
    assert response.status_code == 200
    books = response.get_json()
    assert len(books) == 2
    assert all(book["author"] == "Toni Morrison" for book in books)

    response = client.get("/books", query_string={"author": "Nobody"})
    assert response.get_json() == []


def test_get_book_by_id(client):
    created = create_book(client).get_json()
    response = client.get(f"/books/{created['id']}")
    assert response.status_code == 200
    assert response.get_json() == created


def test_get_missing_book_returns_404(client):
    response = client.get("/books/999")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_update_book_replaces_fields(client):
    created = create_book(client).get_json()
    response = client.put(
        f"/books/{created['id']}",
        json={"title": "The Pragmatic Programmer, 2nd Edition",
              "author": "Andrew Hunt and David Thomas",
              "year": 2019},
    )
    assert response.status_code == 200
    book = response.get_json()
    assert book["title"] == "The Pragmatic Programmer, 2nd Edition"
    assert book["year"] == 2019
    assert book["isbn"] is None  # omitted optional field is cleared on full update

    # The change is persisted.
    assert client.get(f"/books/{created['id']}").get_json() == book


def test_update_missing_book_returns_404(client):
    response = client.put("/books/999", json={"title": "X", "author": "Y"})
    assert response.status_code == 404


def test_update_book_validates_payload(client):
    created = create_book(client).get_json()
    response = client.put(f"/books/{created['id']}", json={"title": "No author"})
    assert response.status_code == 400
    assert "author" in response.get_json()["errors"]


def test_delete_book(client):
    created = create_book(client).get_json()
    response = client.delete(f"/books/{created['id']}")
    assert response.status_code == 204
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_delete_missing_book_returns_404(client):
    response = client.delete("/books/999")
    assert response.status_code == 404


def test_unknown_route_returns_json_404(client):
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.get_json() == {"error": "resource not found"}
