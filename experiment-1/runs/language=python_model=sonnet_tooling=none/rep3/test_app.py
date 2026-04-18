import os
import tempfile
import pytest
from app import app, init_db


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.environ["DATABASE"] = db_path
    app.config["TESTING"] = True

    # Reinitialize DB for this test
    import app as app_module
    app_module.DATABASE = db_path
    init_db()

    with app.test_client() as client:
        yield client

    os.close(db_fd)
    os.unlink(db_path)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book(client):
    resp = client.post("/books", json={"title": "1984", "author": "Orwell", "year": 1949, "isbn": "978-0451524935"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["title"] == "1984"
    assert data["author"] == "Orwell"
    assert data["year"] == 1949
    assert data["isbn"] == "978-0451524935"
    assert "id" in data


def test_create_book_missing_title(client):
    resp = client.post("/books", json={"author": "Orwell"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"].lower()


def test_create_book_missing_author(client):
    resp = client.post("/books", json={"title": "1984"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"].lower()


def test_list_books(client):
    client.post("/books", json={"title": "1984", "author": "Orwell"})
    client.post("/books", json={"title": "Brave New World", "author": "Huxley"})

    resp = client.get("/books")
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 2


def test_list_books_filter_by_author(client):
    client.post("/books", json={"title": "1984", "author": "Orwell"})
    client.post("/books", json={"title": "Brave New World", "author": "Huxley"})

    resp = client.get("/books?author=Orwell")
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 1
    assert books[0]["author"] == "Orwell"


def test_get_book(client):
    created = client.post("/books", json={"title": "1984", "author": "Orwell"}).get_json()
    book_id = created["id"]

    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "1984"


def test_get_book_not_found(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404


def test_update_book(client):
    created = client.post("/books", json={"title": "1984", "author": "Orwell"}).get_json()
    book_id = created["id"]

    resp = client.put(f"/books/{book_id}", json={"title": "Nineteen Eighty-Four", "year": 1949})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "Nineteen Eighty-Four"
    assert data["author"] == "Orwell"  # unchanged
    assert data["year"] == 1949


def test_update_book_not_found(client):
    resp = client.put("/books/9999", json={"title": "X", "author": "Y"})
    assert resp.status_code == 404


def test_delete_book(client):
    created = client.post("/books", json={"title": "1984", "author": "Orwell"}).get_json()
    book_id = created["id"]

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204

    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 404


def test_delete_book_not_found(client):
    resp = client.delete("/books/9999")
    assert resp.status_code == 404
