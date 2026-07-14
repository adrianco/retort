import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app import app, Base, engine
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_book(client):
    r = client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-17271-9"})
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Dune"
    assert data["author"] == "Frank Herbert"
    assert data["id"] is not None


def test_create_book_missing_required_fields(client):
    r = client.post("/books", json={"year": 2000})
    assert r.status_code == 422


def test_create_book_missing_author(client):
    r = client.post("/books", json={"title": "No Author"})
    assert r.status_code == 422


def test_list_books(client):
    client.post("/books", json={"title": "Book A", "author": "Alice"})
    client.post("/books", json={"title": "Book B", "author": "Bob"})
    r = client.get("/books")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_books_filter_by_author(client):
    client.post("/books", json={"title": "Book A", "author": "Alice"})
    client.post("/books", json={"title": "Book B", "author": "Bob"})
    r = client.get("/books?author=Alice")
    assert r.status_code == 200
    books = r.json()
    assert len(books) == 1
    assert books[0]["author"] == "Alice"


def test_get_book(client):
    created = client.post("/books", json={"title": "Foundation", "author": "Isaac Asimov"}).json()
    r = client.get(f"/books/{created['id']}")
    assert r.status_code == 200
    assert r.json()["title"] == "Foundation"


def test_get_book_not_found(client):
    r = client.get("/books/9999")
    assert r.status_code == 404


def test_update_book(client):
    created = client.post("/books", json={"title": "Old Title", "author": "Author"}).json()
    r = client.put(f"/books/{created['id']}", json={"title": "New Title", "author": "Author"})
    assert r.status_code == 200
    assert r.json()["title"] == "New Title"


def test_update_book_not_found(client):
    r = client.put("/books/9999", json={"title": "X", "author": "Y"})
    assert r.status_code == 404


def test_delete_book(client):
    created = client.post("/books", json={"title": "To Delete", "author": "Author"}).json()
    r = client.delete(f"/books/{created['id']}")
    assert r.status_code == 204
    r2 = client.get(f"/books/{created['id']}")
    assert r2.status_code == 404


def test_delete_book_not_found(client):
    r = client.delete("/books/9999")
    assert r.status_code == 404
