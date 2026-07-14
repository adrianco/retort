import os
import tempfile
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def tmp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DB_PATH"] = path
    yield path
    os.unlink(path)


@pytest.fixture(autouse=True)
def reset_db(tmp_db):
    import database
    import sqlite3
    conn = sqlite3.connect(tmp_db)
    conn.execute("DROP TABLE IF EXISTS books")
    conn.commit()
    conn.close()
    database.init_db()


@pytest.fixture(scope="session")
def client(tmp_db):
    import database  # noqa: ensure env var is set first
    from main import app
    with TestClient(app) as c:
        yield c


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_book(client):
    response = client.post(
        "/books", json={"title": "Clean Code", "author": "Robert Martin", "year": 2008}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Clean Code"
    assert data["author"] == "Robert Martin"
    assert data["year"] == 2008
    assert "id" in data


def test_create_book_missing_required_fields(client):
    response = client.post("/books", json={"title": "No Author"})
    assert response.status_code == 422

    response = client.post("/books", json={"author": "No Title"})
    assert response.status_code == 422


def test_create_book_blank_fields(client):
    response = client.post("/books", json={"title": "  ", "author": "Someone"})
    assert response.status_code == 422


def test_list_books(client):
    client.post("/books", json={"title": "Book A", "author": "Alice"})
    client.post("/books", json={"title": "Book B", "author": "Bob"})

    response = client.get("/books")
    assert response.status_code == 200
    books = response.json()
    assert len(books) >= 2


def test_list_books_filter_by_author(client):
    client.post("/books", json={"title": "Python Tricks", "author": "Dan Bader"})
    client.post("/books", json={"title": "Fluent Python", "author": "Luciano Ramalho"})

    response = client.get("/books?author=Dan")
    assert response.status_code == 200
    books = response.json()
    assert all("Dan" in b["author"] for b in books)


def test_get_book(client):
    create_resp = client.post("/books", json={"title": "SICP", "author": "Abelson"})
    book_id = create_resp.json()["id"]

    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "SICP"


def test_get_book_not_found(client):
    response = client.get("/books/99999")
    assert response.status_code == 404


def test_update_book(client):
    create_resp = client.post("/books", json={"title": "Old Title", "author": "Author"})
    book_id = create_resp.json()["id"]

    response = client.put(f"/books/{book_id}", json={"title": "New Title"})
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"
    assert response.json()["author"] == "Author"


def test_update_book_not_found(client):
    response = client.put("/books/99999", json={"title": "Ghost"})
    assert response.status_code == 404


def test_delete_book(client):
    create_resp = client.post("/books", json={"title": "To Delete", "author": "Author"})
    book_id = create_resp.json()["id"]

    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204

    response = client.get(f"/books/{book_id}")
    assert response.status_code == 404


def test_delete_book_not_found(client):
    response = client.delete("/books/99999")
    assert response.status_code == 404
