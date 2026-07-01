import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_books.db")
    monkeypatch.setenv("BOOKS_DB_PATH", db_path)
    main.app.dependency_overrides[main.get_db_path] = lambda: db_path
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


def make_book(client, title="Dune", author="Frank Herbert", year=1965, isbn="9780441013593"):
    return client.post(
        "/books", json={"title": title, "author": author, "year": year, "isbn": isbn}
    )


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_get_book(client):
    create_response = make_book(client)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["title"] == "Dune"
    assert created["id"] is not None

    get_response = client.get(f"/books/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json() == created


def test_get_book_not_found(client):
    response = client.get("/books/999")
    assert response.status_code == 404


def test_create_book_missing_required_fields(client):
    response = client.post("/books", json={"title": "", "author": "Someone"})
    assert response.status_code == 422

    response = client.post("/books", json={"author": "Someone"})
    assert response.status_code == 422


def test_list_books_with_author_filter(client):
    make_book(client, title="Dune", author="Frank Herbert")
    make_book(client, title="Children of Dune", author="Frank Herbert")
    make_book(client, title="Foundation", author="Isaac Asimov")

    all_books = client.get("/books")
    assert all_books.status_code == 200
    assert len(all_books.json()) == 3

    filtered = client.get("/books", params={"author": "Herbert"})
    assert filtered.status_code == 200
    titles = {book["title"] for book in filtered.json()}
    assert titles == {"Dune", "Children of Dune"}


def test_update_book(client):
    created = make_book(client).json()
    response = client.put(
        f"/books/{created['id']}",
        json={"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969, "isbn": "123"},
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "Dune Messiah"
    assert updated["year"] == 1969


def test_update_book_not_found(client):
    response = client.put(
        "/books/999", json={"title": "Ghost", "author": "Nobody"}
    )
    assert response.status_code == 404


def test_delete_book(client):
    created = make_book(client).json()
    delete_response = client.delete(f"/books/{created['id']}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/books/{created['id']}")
    assert get_response.status_code == 404


def test_delete_book_not_found(client):
    response = client.delete("/books/999")
    assert response.status_code == 404
