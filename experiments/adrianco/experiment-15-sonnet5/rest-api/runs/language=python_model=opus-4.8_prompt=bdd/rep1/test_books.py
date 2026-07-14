"""BDD-style tests for the book collection API.

Each test follows the Given / When / Then structure and is named after an
observable behaviour rather than an implementation detail.
"""

import pytest
from fastapi.testclient import TestClient

from db import Database
from main import create_app


@pytest.fixture
def client():
    # Given a service backed by a fresh in-memory database
    db = Database(":memory:")
    app = create_app(db=db)
    yield TestClient(app)
    db.close()


def _make_book(**overrides):
    book = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "12345"}
    book.update(overrides)
    return book


def test_given_running_service_when_get_health_then_status_is_ok(client):
    # Given a running service
    # When the health endpoint is called
    response = client.get("/health")
    # Then it reports an ok status
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_given_valid_book_when_create_then_returns_201_with_id(client):
    # Given a valid book payload
    payload = _make_book()
    # When it is posted to the collection
    response = client.post("/books", json=payload)
    # Then the book is created with a generated id
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["title"] == "Dune"


def test_given_missing_title_when_create_then_returns_422(client):
    # Given a payload without a title
    payload = {"author": "Frank Herbert"}
    # When it is posted
    response = client.post("/books", json=payload)
    # Then validation rejects it
    assert response.status_code == 422


def test_given_empty_author_when_create_then_returns_422(client):
    # Given a payload with an empty author
    payload = _make_book(author="")
    # When it is posted
    response = client.post("/books", json=payload)
    # Then validation rejects it
    assert response.status_code == 422


def test_given_existing_book_when_get_by_id_then_returns_that_book(client):
    # Given an existing book
    created = client.post("/books", json=_make_book()).json()
    # When it is fetched by id
    response = client.get(f"/books/{created['id']}")
    # Then the same book is returned
    assert response.status_code == 200
    assert response.json()["title"] == "Dune"


def test_given_no_such_book_when_get_by_id_then_returns_404(client):
    # Given an id that does not exist
    # When it is fetched
    response = client.get("/books/999")
    # Then a not-found error is returned
    assert response.status_code == 404


def test_given_books_by_two_authors_when_list_filtered_then_returns_only_matches(client):
    # Given books written by two different authors
    client.post("/books", json=_make_book(author="Frank Herbert"))
    client.post("/books", json=_make_book(title="1984", author="George Orwell"))
    # When the list is filtered by one author
    response = client.get("/books", params={"author": "George Orwell"})
    # Then only that author's books are returned
    assert response.status_code == 200
    books = response.json()
    assert len(books) == 1
    assert books[0]["author"] == "George Orwell"


def test_given_multiple_books_when_list_without_filter_then_returns_all(client):
    # Given several books in the collection
    client.post("/books", json=_make_book())
    client.post("/books", json=_make_book(title="1984"))
    # When the full list is requested
    response = client.get("/books")
    # Then every book is returned
    assert len(response.json()) == 2


def test_given_existing_book_when_update_then_fields_are_changed(client):
    # Given an existing book
    created = client.post("/books", json=_make_book()).json()
    # When it is updated with new values
    response = client.put(
        f"/books/{created['id']}",
        json=_make_book(title="Dune Messiah", year=1969),
    )
    # Then the stored book reflects the changes
    assert response.status_code == 200
    assert response.json()["title"] == "Dune Messiah"
    assert response.json()["year"] == 1969


def test_given_no_such_book_when_update_then_returns_404(client):
    # Given an id that does not exist
    # When an update is attempted
    response = client.put("/books/999", json=_make_book())
    # Then a not-found error is returned
    assert response.status_code == 404


def test_given_existing_book_when_delete_then_it_is_gone(client):
    # Given an existing book
    created = client.post("/books", json=_make_book()).json()
    # When it is deleted
    delete_response = client.delete(f"/books/{created['id']}")
    # Then the deletion succeeds and the book can no longer be fetched
    assert delete_response.status_code == 204
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_given_no_such_book_when_delete_then_returns_404(client):
    # Given an id that does not exist
    # When a delete is attempted
    response = client.delete("/books/999")
    # Then a not-found error is returned
    assert response.status_code == 404
