import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(database=str(tmp_path / "test.db"))
    app.testing = True
    return app.test_client()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    resp = client.post("/books", json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"})
    assert resp.status_code == 201
    book = resp.get_json()
    assert book["title"] == "Dune"
    assert book["id"] == 1

    resp = client.get("/books/1")
    assert resp.status_code == 200
    assert resp.get_json()["author"] == "Frank Herbert"


def test_validation_errors(client):
    resp = client.post("/books", json={"author": "No Title"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["errors"]

    resp = client.post("/books", json={"title": "X", "author": "Y", "year": "not-a-year"})
    assert resp.status_code == 400


def test_list_and_filter_by_author(client):
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})
    client.post("/books", json={"title": "C", "author": "Alice"})

    all_books = client.get("/books").get_json()
    assert len(all_books) == 3

    alice = client.get("/books?author=Alice").get_json()
    assert len(alice) == 2
    assert all(b["author"] == "Alice" for b in alice)


def test_update_book(client):
    client.post("/books", json={"title": "Old", "author": "Author"})
    resp = client.put("/books/1", json={"title": "New"})
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "New"
    assert resp.get_json()["author"] == "Author"

    resp = client.put("/books/999", json={"title": "X"})
    assert resp.status_code == 404

    resp = client.put("/books/1", json={"title": ""})
    assert resp.status_code == 400


def test_delete_book(client):
    client.post("/books", json={"title": "T", "author": "A"})
    resp = client.delete("/books/1")
    assert resp.status_code == 204
    assert client.get("/books/1").status_code == 404
    assert client.delete("/books/1").status_code == 404
