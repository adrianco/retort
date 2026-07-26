import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(db_path=str(tmp_path / "test_books.db"))
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def make_book(client, **overrides):
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book(client):
    resp = make_book(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] == 1
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "9780441172719"


def test_create_book_validation(client):
    resp = client.post("/books", json={"author": "Nobody"})
    assert resp.status_code == 400
    assert any("title" in e for e in resp.get_json()["errors"])

    resp = client.post("/books", json={"title": "   ", "author": "Nobody"})
    assert resp.status_code == 400

    resp = client.post("/books", json={"title": "X", "author": "Y", "year": "not-a-year"})
    assert resp.status_code == 400

    resp = client.post("/books", data="not json", content_type="application/json")
    assert resp.status_code == 400


def test_list_books_and_author_filter(client):
    make_book(client)
    make_book(client, title="Emma", author="Jane Austen", year=1815, isbn=None)
    make_book(client, title="Persuasion", author="Jane Austen", year=1817, isbn=None)

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Jane Austen")
    books = resp.get_json()
    assert len(books) == 2
    assert {b["title"] for b in books} == {"Emma", "Persuasion"}

    resp = client.get("/books?author=Unknown")
    assert resp.get_json() == []


def test_get_single_book(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Dune"

    resp = client.get("/books/999")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_update_book(client):
    book_id = make_book(client).get_json()["id"]

    resp = client.put(f"/books/{book_id}", json={"title": "Dune Messiah", "year": 1969})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "Dune Messiah"
    assert body["year"] == 1969
    assert body["author"] == "Frank Herbert"  # unchanged

    resp = client.put(f"/books/{book_id}", json={"title": ""})
    assert resp.status_code == 400

    resp = client.put("/books/999", json={"title": "Ghost"})
    assert resp.status_code == 404


def test_delete_book(client):
    book_id = make_book(client).get_json()["id"]

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204

    assert client.get(f"/books/{book_id}").status_code == 404
    assert client.delete(f"/books/{book_id}").status_code == 404
