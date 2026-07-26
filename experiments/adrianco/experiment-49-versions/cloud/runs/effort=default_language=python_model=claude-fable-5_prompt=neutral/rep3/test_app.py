import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(db_path=str(tmp_path / "test.db"))
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
    # Missing both required fields
    resp = client.post("/books", json={"year": 2020})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert any("title" in e for e in errors)
    assert any("author" in e for e in errors)

    # Empty title
    resp = make_book(client, title="   ")
    assert resp.status_code == 400

    # Non-integer year
    resp = make_book(client, year="nineteen sixty-five")
    assert resp.status_code == 400

    # Invalid JSON body
    resp = client.post("/books", data="not json", content_type="application/json")
    assert resp.status_code == 400


def test_list_books_and_author_filter(client):
    make_book(client)
    make_book(client, title="Children of Dune")
    make_book(client, title="Neuromancer", author="William Gibson", year=1984, isbn=None)

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Frank Herbert")
    books = resp.get_json()
    assert len(books) == 2
    assert all(b["author"] == "Frank Herbert" for b in books)

    # Case-insensitive match
    resp = client.get("/books?author=william gibson")
    assert len(resp.get_json()) == 1

    # No matches
    resp = client.get("/books?author=Nobody")
    assert resp.get_json() == []


def test_get_book(client):
    make_book(client)
    resp = client.get("/books/1")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Dune"

    resp = client.get("/books/999")
    assert resp.status_code == 404


def test_update_book(client):
    make_book(client)

    resp = client.put("/books/1", json={"title": "Dune Messiah", "year": 1969})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "Dune Messiah"
    assert body["year"] == 1969
    assert body["author"] == "Frank Herbert"  # unchanged

    # Validation on update
    resp = client.put("/books/1", json={"title": ""})
    assert resp.status_code == 400

    # Empty payload
    resp = client.put("/books/1", json={})
    assert resp.status_code == 400

    # Missing book
    resp = client.put("/books/999", json={"title": "Ghost"})
    assert resp.status_code == 404


def test_delete_book(client):
    make_book(client)
    resp = client.delete("/books/1")
    assert resp.status_code == 204
    assert client.get("/books/1").status_code == 404

    resp = client.delete("/books/1")
    assert resp.status_code == 404
