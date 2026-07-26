"""Integration tests for the book collection API."""

import pytest

from app import create_app


@pytest.fixture()
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture()
def app(db_path):
    application = create_app(db_path=db_path)
    application.config.update(TESTING=True)
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def create_book(client, **overrides):
    payload = {
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "year": 1937,
        "isbn": "978-0547928227",
    }
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_create_book_returns_201_with_created_book(client):
    response = create_book(client)
    assert response.status_code == 201
    book = response.get_json()
    assert book["id"] == 1
    assert book["title"] == "The Hobbit"
    assert book["author"] == "J.R.R. Tolkien"
    assert book["year"] == 1937
    assert book["isbn"] == "978-0547928227"
    assert response.headers["Location"].endswith("/books/1")


def test_create_book_optional_fields_default_to_null(client):
    response = client.post("/books", json={"title": "Sula", "author": "Toni Morrison"})
    assert response.status_code == 201
    book = response.get_json()
    assert book["year"] is None
    assert book["isbn"] is None


def test_create_book_requires_title_and_author(client):
    response = client.post("/books", json={"year": 2001})
    assert response.status_code == 400
    details = response.get_json()["details"]
    assert "title" in details
    assert "author" in details

    # Blank / whitespace-only strings are rejected too.
    response = create_book(client, title="   ")
    assert response.status_code == 400
    assert "title" in response.get_json()["details"]


def test_create_book_rejects_bad_field_types(client):
    response = create_book(client, year="nineteen thirty-seven")
    assert response.status_code == 400
    assert "year" in response.get_json()["details"]

    response = create_book(client, year=True)
    assert response.status_code == 400
    assert "year" in response.get_json()["details"]

    response = create_book(client, isbn=12345)
    assert response.status_code == 400
    assert "isbn" in response.get_json()["details"]


def test_create_book_rejects_non_json_body(client):
    response = client.post("/books", data="not json", content_type="text/plain")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_list_books_returns_all_books(client):
    create_book(client)
    create_book(client, title="Beloved", author="Toni Morrison", year=1987, isbn=None)

    response = client.get("/books")
    assert response.status_code == 200
    books = response.get_json()
    assert [b["title"] for b in books] == ["The Hobbit", "Beloved"]


def test_list_books_filters_by_author_case_insensitively(client):
    create_book(client)
    create_book(client, title="Beloved", author="Toni Morrison")
    create_book(client, title="Song of Solomon", author="Toni Morrison")

    response = client.get("/books", query_string={"author": "toni morrison"})
    assert response.status_code == 200
    books = response.get_json()
    assert len(books) == 2
    assert {b["title"] for b in books} == {"Beloved", "Song of Solomon"}

    response = client.get("/books", query_string={"author": "Nobody"})
    assert response.get_json() == []


def test_get_book_by_id(client):
    created = create_book(client).get_json()
    response = client.get(f"/books/{created['id']}")
    assert response.status_code == 200
    assert response.get_json() == created


def test_get_missing_or_malformed_id_returns_json_404(client):
    response = client.get("/books/999")
    assert response.status_code == 404
    assert "error" in response.get_json()

    response = client.get("/books/not-a-number")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_update_book_replaces_all_fields(client):
    book_id = create_book(client).get_json()["id"]
    response = client.put(
        f"/books/{book_id}",
        json={"title": "The Silmarillion", "author": "J.R.R. Tolkien", "year": 1977},
    )
    assert response.status_code == 200
    book = response.get_json()
    assert book["id"] == book_id
    assert book["title"] == "The Silmarillion"
    assert book["year"] == 1977
    assert book["isbn"] is None  # PUT is a full replacement; omitted fields reset


def test_update_book_validates_payload(client):
    book_id = create_book(client).get_json()["id"]
    response = client.put(f"/books/{book_id}", json={"title": "No Author"})
    assert response.status_code == 400
    assert "author" in response.get_json()["details"]


def test_update_missing_book_returns_404(client):
    response = client.put(
        "/books/42", json={"title": "Ghost", "author": "Nobody"}
    )
    assert response.status_code == 404


def test_delete_book(client):
    book_id = create_book(client).get_json()["id"]

    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204
    assert response.data == b""

    assert client.get(f"/books/{book_id}").status_code == 404
    assert client.delete(f"/books/{book_id}").status_code == 404


def test_unknown_route_returns_json_404(client):
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.content_type.startswith("application/json")
    assert "error" in response.get_json()


def test_data_persists_across_app_instances(db_path):
    first = create_app(db_path=db_path)
    with first.test_client() as client:
        created = create_book(client).get_json()

    second = create_app(db_path=db_path)
    with second.test_client() as client:
        response = client.get(f"/books/{created['id']}")
        assert response.status_code == 200
        assert response.get_json() == created
