import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(db_path=str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def make_book(client, **overrides):
    payload = {
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt",
        "year": 1999,
        "isbn": "978-0201616224",
    }
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
    assert body["title"] == "The Pragmatic Programmer"
    assert body["author"] == "Andrew Hunt"
    assert body["year"] == 1999
    assert body["isbn"] == "978-0201616224"


def test_create_book_requires_title_and_author(client):
    resp = client.post("/books", json={"year": 2020})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert "'title' is required" in errors
    assert "'author' is required" in errors

    resp = client.post("/books", json={"title": "   ", "author": "Someone"})
    assert resp.status_code == 400
    assert "'title' must be a non-empty string" in resp.get_json()["errors"]


def test_create_book_rejects_invalid_year(client):
    resp = make_book(client, year="not-a-year")
    assert resp.status_code == 400
    assert "'year' must be an integer" in resp.get_json()["errors"]


def test_list_books_and_author_filter(client):
    make_book(client)
    make_book(client, title="Refactoring", author="Martin Fowler")
    make_book(client, title="UML Distilled", author="Martin Fowler")

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Martin Fowler")
    books = resp.get_json()
    assert len(books) == 2
    assert all(b["author"] == "Martin Fowler" for b in books)

    resp = client.get("/books?author=Nobody")
    assert resp.get_json() == []


def test_get_book(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "The Pragmatic Programmer"


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/999")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Book not found"


def test_update_book(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.put(f"/books/{book_id}", json={"title": "Updated Title", "year": 2005})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "Updated Title"
    assert body["year"] == 2005
    assert body["author"] == "Andrew Hunt"  # unchanged


def test_update_book_validation_and_missing(client):
    resp = client.put("/books/42", json={"title": "X"})
    assert resp.status_code == 404

    book_id = make_book(client).get_json()["id"]
    resp = client.put(f"/books/{book_id}", json={"title": ""})
    assert resp.status_code == 400


def test_delete_book(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 404
