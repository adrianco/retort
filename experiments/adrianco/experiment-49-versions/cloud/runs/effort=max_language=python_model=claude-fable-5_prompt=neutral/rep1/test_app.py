"""Integration tests for the book API, run against a temp SQLite database."""

import pytest

from app import create_app

BOOK = {
    "title": "The Dispossessed",
    "author": "Ursula K. Le Guin",
    "year": 1974,
    "isbn": "978-0061054884",
}


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "books.db"


@pytest.fixture()
def app(db_path):
    app = create_app(db_path)
    app.config.update(TESTING=True)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def create_book(client, **overrides):
    return client.post("/books", json={**BOOK, **overrides})


# --- health -----------------------------------------------------------------


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


# --- create -----------------------------------------------------------------


def test_create_book_returns_201_and_persists(client):
    response = create_book(client)
    assert response.status_code == 201

    book = response.get_json()
    assert book["id"] == 1
    assert {k: book[k] for k in BOOK} == BOOK
    assert response.headers["Location"].endswith("/books/1")

    fetched = client.get("/books/1")
    assert fetched.status_code == 200
    assert fetched.get_json() == book


def test_create_book_optional_fields_default_to_null(client):
    response = client.post("/books", json={"title": "Kindred", "author": "Octavia Butler"})
    assert response.status_code == 201
    book = response.get_json()
    assert book["year"] is None
    assert book["isbn"] is None


@pytest.mark.parametrize("missing", ["title", "author"])
def test_create_book_requires_title_and_author(client, missing):
    payload = {k: v for k, v in BOOK.items() if k != missing}
    response = client.post("/books", json=payload)
    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "validation failed"
    assert body["details"][missing] == "is required"


def test_create_book_rejects_blank_title(client):
    response = create_book(client, title="   ")
    assert response.status_code == 400
    assert "title" in response.get_json()["details"]


def test_create_book_rejects_non_integer_year(client):
    response = create_book(client, year="1974")
    assert response.status_code == 400
    assert response.get_json()["details"]["year"] == "must be an integer"


def test_create_book_rejects_unknown_fields(client):
    response = create_book(client, publisher="Harper")
    assert response.status_code == 400
    assert response.get_json()["details"]["publisher"] == "unknown field"


def test_create_book_rejects_non_json_body(client):
    response = client.post("/books", data="not json", content_type="text/plain")
    assert response.status_code == 400
    assert response.get_json()["error"] == "request body must be a JSON object"


# --- list & filter ----------------------------------------------------------


def test_list_books_returns_all_in_insertion_order(client):
    create_book(client)
    create_book(client, title="Parable of the Sower", author="Octavia Butler", year=1993)

    response = client.get("/books")
    assert response.status_code == 200
    books = response.get_json()
    assert [b["title"] for b in books] == ["The Dispossessed", "Parable of the Sower"]


def test_list_books_filters_by_author_case_insensitively(client):
    create_book(client)
    create_book(client, title="Parable of the Sower", author="Octavia Butler", year=1993)

    response = client.get("/books", query_string={"author": "octavia butler"})
    books = response.get_json()
    assert len(books) == 1
    assert books[0]["title"] == "Parable of the Sower"

    assert client.get("/books", query_string={"author": "Nobody"}).get_json() == []


# --- get one ----------------------------------------------------------------


def test_get_missing_book_returns_404(client):
    response = client.get("/books/999")
    assert response.status_code == 404
    assert response.get_json()["error"] == "book 999 not found"


# --- update -----------------------------------------------------------------


def test_put_replaces_book(client):
    book_id = create_book(client).get_json()["id"]

    response = client.put(
        f"/books/{book_id}",
        json={"title": "The Left Hand of Darkness", "author": "Ursula K. Le Guin", "year": 1969},
    )
    assert response.status_code == 200
    book = response.get_json()
    assert book["title"] == "The Left Hand of Darkness"
    assert book["year"] == 1969
    assert book["isbn"] is None  # PUT is a full replace: omitted fields reset


def test_put_missing_book_returns_404(client):
    response = client.put("/books/999", json=BOOK)
    assert response.status_code == 404


def test_put_invalid_payload_returns_400(client):
    book_id = create_book(client).get_json()["id"]
    response = client.put(f"/books/{book_id}", json={"title": "No Author"})
    assert response.status_code == 400
    assert response.get_json()["details"]["author"] == "is required"


# --- delete -----------------------------------------------------------------


def test_delete_book_then_it_is_gone(client):
    book_id = create_book(client).get_json()["id"]

    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204
    assert response.data == b""

    assert client.get(f"/books/{book_id}").status_code == 404
    assert client.get("/books").get_json() == []


def test_delete_missing_book_returns_404(client):
    assert client.delete("/books/999").status_code == 404


# --- framework errors are JSON too ------------------------------------------


def test_unknown_route_returns_json_404(client):
    response = client.get("/no-such-route")
    assert response.status_code == 404
    assert response.get_json() == {"error": "not found"}


def test_wrong_method_returns_json_405(client):
    response = client.delete("/books")
    assert response.status_code == 405
    assert response.get_json() == {"error": "method not allowed"}


# --- persistence ------------------------------------------------------------


def test_data_persists_across_app_instances(db_path):
    first = create_app(db_path).test_client()
    created = first.post("/books", json=BOOK).get_json()

    second = create_app(db_path).test_client()
    books = second.get("/books").get_json()
    assert books == [created]
