import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app(database=":memory:")
    app.config["TESTING"] = True
    with app.app_context():
        with app.test_client() as client:
            yield client


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book(client):
    resp = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "123"},
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["id"] > 0
    assert data["title"] == "Dune"
    assert data["author"] == "Frank Herbert"
    assert data["year"] == 1965
    assert data["isbn"] == "123"


def test_create_book_missing_required_fields(client):
    resp = client.post("/books", json={"title": "No Author"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]

    resp = client.post("/books", json={"author": "No Title"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]

    resp = client.post("/books", json={"title": "  ", "author": "x"})
    assert resp.status_code == 400


def test_get_book(client):
    created = client.post(
        "/books", json={"title": "1984", "author": "George Orwell"}
    ).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "1984"


def test_get_book_not_found(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404


def test_list_books_and_author_filter(client):
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})
    client.post("/books", json={"title": "C", "author": "Alice"})

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2
    assert all(b["author"] == "Alice" for b in data)


def test_update_book(client):
    created = client.post(
        "/books", json={"title": "Old", "author": "Author", "year": 2000}
    ).get_json()
    resp = client.put(
        f"/books/{created['id']}", json={"title": "New", "year": 2020}
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "New"
    assert data["author"] == "Author"  # unchanged
    assert data["year"] == 2020


def test_update_book_not_found(client):
    resp = client.put("/books/9999", json={"title": "X"})
    assert resp.status_code == 404


def test_delete_book(client):
    created = client.post(
        "/books", json={"title": "Gone", "author": "Author"}
    ).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_delete_book_not_found(client):
    resp = client.delete("/books/9999")
    assert resp.status_code == 404
