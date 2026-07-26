import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app(db_path=":memory:")
    app.testing = True
    with app.test_client() as client:
        yield client


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book(client):
    resp = client.post(
        "/books",
        json={"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "123"},
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["id"] > 0
    assert data["title"] == "Dune"
    assert data["author"] == "Herbert"
    assert data["year"] == 1965


def test_create_book_requires_title_and_author(client):
    assert client.post("/books", json={"author": "X"}).status_code == 400
    assert client.post("/books", json={"title": "Y"}).status_code == 400
    assert client.post("/books", json={"title": "  ", "author": "X"}).status_code == 400


def test_get_single_and_404(client):
    created = client.post("/books", json={"title": "A", "author": "B"}).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "A"
    assert client.get("/books/9999").status_code == 404


def test_list_and_author_filter(client):
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})
    client.post("/books", json={"title": "C", "author": "Alice"})

    assert len(client.get("/books").get_json()) == 3
    alice = client.get("/books?author=Alice").get_json()
    assert len(alice) == 2
    assert all(b["author"] == "Alice" for b in alice)


def test_update_book(client):
    created = client.post("/books", json={"title": "Old", "author": "B"}).get_json()
    resp = client.put(
        f"/books/{created['id']}",
        json={"title": "New", "author": "B", "year": 2000},
    )
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "New"
    assert resp.get_json()["year"] == 2000
    assert client.put("/books/9999", json={"title": "X", "author": "Y"}).status_code == 404


def test_delete_book(client):
    created = client.post("/books", json={"title": "A", "author": "B"}).get_json()
    assert client.delete(f"/books/{created['id']}").status_code == 204
    assert client.get(f"/books/{created['id']}").status_code == 404
    assert client.delete("/books/9999").status_code == 404
