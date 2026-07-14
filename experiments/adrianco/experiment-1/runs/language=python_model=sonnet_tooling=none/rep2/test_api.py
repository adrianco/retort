import pytest
from fastapi.testclient import TestClient
from main import app, DATABASE, init_db
import os


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_books.db")
    monkeypatch.setattr("main.DATABASE", db_path)
    init_db()
    yield
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_book(client):
    payload = {"title": "1984", "author": "George Orwell", "year": 1949, "isbn": "978-0451524935"}
    response = client.post("/books", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "1984"
    assert data["author"] == "George Orwell"
    assert data["year"] == 1949
    assert data["isbn"] == "978-0451524935"
    assert "id" in data


def test_create_book_missing_required_fields(client):
    response = client.post("/books", json={"title": "No Author"})
    assert response.status_code == 422

    response = client.post("/books", json={"author": "No Title"})
    assert response.status_code == 422


def test_create_book_empty_title(client):
    response = client.post("/books", json={"title": "  ", "author": "Someone"})
    assert response.status_code == 422


def test_list_books(client):
    client.post("/books", json={"title": "Book A", "author": "Alice"})
    client.post("/books", json={"title": "Book B", "author": "Bob"})
    response = client.get("/books")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_list_books_filter_by_author(client):
    client.post("/books", json={"title": "Book A", "author": "Alice"})
    client.post("/books", json={"title": "Book B", "author": "Bob"})
    response = client.get("/books?author=Alice")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["author"] == "Alice"


def test_get_book(client):
    created = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"}).json()
    book_id = created["id"]
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Dune"


def test_get_book_not_found(client):
    response = client.get("/books/9999")
    assert response.status_code == 404


def test_update_book(client):
    created = client.post("/books", json={"title": "Old Title", "author": "Author"}).json()
    book_id = created["id"]
    response = client.put(f"/books/{book_id}", json={"title": "New Title"})
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"
    assert response.json()["author"] == "Author"


def test_update_book_not_found(client):
    response = client.put("/books/9999", json={"title": "Anything"})
    assert response.status_code == 404


def test_delete_book(client):
    created = client.post("/books", json={"title": "To Delete", "author": "Author"}).json()
    book_id = created["id"]
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_delete_book_not_found(client):
    response = client.delete("/books/9999")
    assert response.status_code == 404
